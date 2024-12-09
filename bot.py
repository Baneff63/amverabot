import os
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters
import requests
import sqlite3
import logging
from datetime import datetime


# === Логирование ===
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
YANDEX_DISK_TOKEN = os.getenv("YANDEX_DISK_TOKEN")
COMPANY_GROUP_ID = int(os.getenv("COMPANY_GROUP_ID"))

YANDEX_DISK_API_URL = "https://cloud-api.yandex.net/v1/disk/resources"

# === База данных ===

# Функция для создания базы данных и таблиц
def create_db():
    connection = sqlite3.connect('data/bot_database.db')  # Название файла базы данных
    cursor = connection.cursor()

    # Создание таблицы пользователей
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,          -- Идентификатор пользователя
        username TEXT,                        -- Имя пользователя
        orders_count INTEGER DEFAULT 0,       -- Количество заказов
        last_orders TEXT                      -- Строка с последними заказами
    );
    ''')

    # Создание таблицы заказов
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS orders (
        order_id INTEGER PRIMARY KEY AUTOINCREMENT, -- Идентификатор заказа
        user_id INTEGER,                            -- Идентификатор пользователя
        order_number TEXT,                          -- Номер заказа
        status TEXT,                                -- Статус заказа
        comment TEXT,                               -- Комментарий
        FOREIGN KEY (user_id) REFERENCES users(user_id)  -- Связь с пользователем
    );
    ''')

    # Закрытие соединения с базой данных
    connection.commit()
    connection.close()

# Вызовем функцию для создания базы данных и таблиц при старте бота
create_db()

def get_user_profile(user_id):
    connection = sqlite3.connect('data/bot_database.db')
    cursor = connection.cursor()

    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    profile = cursor.fetchone()

    connection.close()

    return profile if profile else None

def update_user_profile(user_id, username, order_number):
    # Получаем текущий профиль пользователя
    profile = get_user_profile(user_id)

    # Если профиль не найден, создаём новый
    if not profile:
        connection = sqlite3.connect('data/bot_database.db')
        cursor = connection.cursor()

        cursor.execute('''
        INSERT INTO users (user_id, username, orders_count, last_orders)
        VALUES (?, ?, ?, ?);
        ''', (user_id, username, 0, ''))

        connection.commit()
        connection.close()
        profile = get_user_profile(user_id)  # Обновляем профиль после вставки

    # Обновляем количество заказов и последние заказы
    orders_count = profile[2] + 1
    last_orders = f'{order_number}\n' + profile[3]
    if len(last_orders.split('\n')) > 5:
        last_orders = '\n'.join(last_orders.split('\n')[:5])  # Оставляем только 5 последних заказов

    connection = sqlite3.connect('data/bot_database.db')
    cursor = connection.cursor()

    cursor.execute('''
    UPDATE users
    SET orders_count = ?, last_orders = ?
    WHERE user_id = ?;
    ''', (orders_count, last_orders, user_id))

    connection.commit()
    connection.close()

    return get_user_profile(user_id)

def add_order(user_id, order_number, status, comment):
    connection = sqlite3.connect('data/bot_database.db')
    cursor = connection.cursor()

    cursor.execute('''
    INSERT INTO orders (user_id, order_number, status, comment)
    VALUES (?, ?, ?, ?);
    ''', (user_id, order_number, status, comment))

    connection.commit()
    connection.close()

def get_user_orders(user_id):
    connection = sqlite3.connect('data/bot_database.db')
    cursor = connection.cursor()

    cursor.execute('SELECT * FROM orders WHERE user_id = ?', (user_id,))
    orders = cursor.fetchall()

    connection.close()

    return orders if orders else None

def add_user(user_id, username):
    # Проверяем, существует ли пользователь в базе данных
    profile = get_user_profile(user_id)

    if not profile:
        # Если пользователя нет, добавляем нового
        connection = sqlite3.connect('data/bot_database.db')
        cursor = connection.cursor()

        cursor.execute('''
        INSERT INTO users (user_id, username, orders_count, last_orders)
        VALUES (?, ?, ?, ?);
        ''', (user_id, username, 0, ''))

        connection.commit()
        connection.close()
        logger.info(f"Пользователь {username} с ID {user_id} был добавлен в базу данных.")
    else:
        logger.info(f"Пользователь {username} с ID {user_id} уже существует в базе данных.")


def add_order_number_column():
    conn = sqlite3.connect('data/bot_database.db')
    cursor = conn.cursor()

    try:
        cursor.execute('''
            ALTER TABLE users ADD COLUMN order_number INTEGER;
        ''')
        conn.commit()
        print("Поле 'order_number' успешно добавлено!")
    except sqlite3.OperationalError as e:
        print(f"Ошибка при добавлении поля 'order_number': {e}")
    finally:
        conn.close()



# === Вспомогательные функции для работы с Яндекс.Диском ===
def check_folder_exists(order_number):
    logger.info(f"Проверка существования папки для заказа: {order_number}")
    headers = {"Authorization": f"OAuth {YANDEX_DISK_TOKEN}"}
    response = requests.get(f"{YANDEX_DISK_API_URL}?path={order_number}", headers=headers)
    if response.status_code == 200:
        logger.info(f"Папка {order_number} существует.")
    else:
        logger.warning(f"Папка {order_number} не найдена.")
    return response.status_code == 200


def upload_to_yandex_disk(order_number, file_path, file_name):
    logger.info(f"Попытка загрузить файл {file_name} в папку {order_number} на Яндекс.Диск.")
    headers = {"Authorization": f"OAuth {YANDEX_DISK_TOKEN}"}
    response = requests.get(
        f"{YANDEX_DISK_API_URL}/upload?path={order_number}/{file_name}&overwrite=true",
        headers=headers
    )
    if response.status_code == 200:
        upload_url = response.json().get("href")
        logger.info(f"Получена ссылка для загрузки файла: {upload_url}")
        with open(file_path, "rb") as f:
            upload_response = requests.put(upload_url, files={"file": f})
            if upload_response.status_code == 201:
                logger.info(f"Файл {file_name} успешно загружен.")
                return True
            else:
                logger.error(f"Ошибка загрузки файла {file_name}: {upload_response.status_code}")
    else:
        logger.error(f"Не удалось получить ссылку для загрузки файла {file_name}.")
    return False


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Пользователь {update.effective_user.username} начал новый заказ.")

    user_id = update.effective_user.id  # Получаем ID пользователя
    username = update.effective_user.full_name  # Получаем имя пользователя
    add_user(user_id, username)  # Добавляем пользователя в базу данных, если он еще не зарегистрирован

    # Инициализация данных, если они ещё не установлены
    if 'orders_count' not in context.user_data:
        context.user_data['orders_count'] = 0  # Количество заказов
    if 'last_orders' not in context.user_data:
        context.user_data['last_orders'] = []  # Список последних заказов

    # Кнопки для интерфейса
    keyboard = [
        [InlineKeyboardButton("Завершить загрузку", callback_data="finish_media")],
        [InlineKeyboardButton("Отменить", callback_data="cancel")],
        [InlineKeyboardButton("Профиль", callback_data="profile")]
    ]

    # Отправляем сообщение с кнопками
    await update.message.reply_text(
        "Привет! Пожалуйста, загрузите фото или видео с выполнения заказа. Вы можете загрузить несколько файлов. Нажмите 'Завершить загрузку', когда закончите.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    # Сохраняем состояние пользователя
    context.user_data['state'] = 'MEDIA'
    context.user_data['media'] = []  # Список для хранения всех загружаемых файлов
    context.user_data['location'] = None  # Для хранения геопозиции
    context.user_data['order_number'] = None  # Для хранения номера заказа



# Обработчик для кнопки "Профиль"
async def handle_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    # Получаем данные профиля из базы данных
    profile = get_user_profile(user_id)

    # Получаем имя пользователя
    user = update.effective_user
    user_name = user.name if user.name else "Неизвестный пользователь"

    # Формируем текст для вывода
    orders_count = profile[2] if profile else 0
    last_orders = profile[3].split('\n') if profile and profile[3] else []

    profile_info = (
            "🧑‍💼 **Профиль пользователя**:\n"
            f"👤 **Имя:** {user_name}\n"
            f"📊 **Количество заказов:** {orders_count}\n\n"

            "📦 **Последние заказы**:\n"
            "----------------------------\n"
            + (  # Список последних заказов
                "\n".join([f"**Заказ №{idx + 1}**: {order}" for idx, order in enumerate(last_orders)])
                if last_orders else "❌ Нет заказов"
            ) +
            "\n----------------------------\n\n"

            "🔗 **Полезные ссылки**:\n"
            "💬 [Техподдержка](https://t.me/baneoff9)\n"
            "📍 [Посмотреть на карте](https://yandex.ru/maps/51/samara/?indoorLevel=1&ll=50.182523%2C53.205483&mode=whatshere&whatshere%5Bpoint%5D=50.180952%2C53.206432&whatshere%5Bzoom%5D=16&z=18.03) — Офис PSP\n"
             
            "\n✨ **Что делать дальше?**\n"
            "📈 Вы можете обновить профиль или создать новый заказ!"
    )



    # Обработка разных типов обновлений
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.reply_text(profile_info, parse_mode='Markdown')
    elif update.message:
        await update.message.reply_text(profile_info, parse_mode='Markdown')


async def update_profile(user_id, order_number, context):
    try:
        # Используем данные из текущего контекста
        username = context.user_data.get('username') or "Неизвестный пользователь"

        # Обновляем профиль пользователя в базе данных
        update_user_profile(user_id, username, order_number)

        # Выводим лог, что профиль обновлен
        logger.info(f"Профиль пользователя {user_id} обновлен после заказа №{order_number}")
    except Exception as e:
        logger.error(f"Ошибка при обновлении профиля: {e}")


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Реализуем отмену
    await update.callback_query.message.reply_text("Загрузка отменена.")

    # Можно сбросить все сохраненные данные в контексте пользователя, если нужно
    context.user_data.clear()


# Обработчик для кнопки "Профиль"
from telegram.ext import CommandHandler, CallbackQueryHandler

# Обработчик медиа (фото/видео)
async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('state') != 'MEDIA':
        logger.warning("Пользователь попытался загрузить файл вне состояния 'MEDIA'.")
        return

    media_file = None
    file_extension = None

    # Проверяем, что это фото или видео
    if update.message.photo:
        media_file = update.message.photo[-1]
        file_extension = "jpg"
    elif update.message.video:
        media_file = update.message.video
        file_extension = "mp4"

    if media_file is None:
        logger.warning("Пользователь загрузил неподдерживаемый формат файла.")
        await update.message.reply_text("Поддерживаются только фото и видео.")
        return

    if media_file.file_size > 20 * 1024 * 1024:  # Ограничение 20 МБ
        await update.message.reply_text("Файл слишком большой. Поддерживаются файлы до 20 МБ.")
        return

    # Сохраняем файл с уникальным именем
    file = await context.bot.get_file(media_file.file_id)
    file_path = f"temp_{update.message.chat_id}_{len(context.user_data['media']) + 1}.{file_extension}"
    await file.download_to_drive(file_path)

    # Добавляем путь к файлу в список
    context.user_data['media'].append(file_path)
    logger.info(f"Файл {file_path} добавлен в список медиа.")
    await update.message.reply_text("Файл добавлен. Вы можете загрузить еще один файл или завершить загрузку.")

# Обработчик завершения загрузки медиа
async def finish_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not context.user_data.get('media'):
        logger.warning("Пользователь нажал 'Завершить загрузку', не добавив медиа.")
        await query.message.reply_text("Вы не загрузили ни одного файла. Пожалуйста, загрузите хотя бы один файл.")
        return

    logger.info(f"Пользователь завершил загрузку медиа. Файлы: {context.user_data['media']}")

    # Сохраняем номер заказа перед отправкой отчета
    order_number = context.user_data['order_number']

    # Переход к запросу геопозиции
    context.user_data['state'] = 'ORDER_NUMBER'
    await query.message.reply_text("Введите номер заказа (только цифры):")


# Обработчик номера заказа
async def handle_order_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('state') != 'ORDER_NUMBER':
        return

    order_number = update.message.text
    if not check_folder_exists(order_number):
        await update.message.reply_text("Папка для указанного заказа не найдена. Введите корректный номер заказа.")
        return

    logger.info(f"Номер заказа подтверждён: {order_number}")

    # Сохраняем номер заказа в контексте
    context.user_data['order_number'] = order_number

    # Переход к запросу геопозиции
    context.user_data['state'] = 'GEOPOSITION'
    await update.message.reply_text("Отправьте геопозицию, где был выполнен заказ.")



# Обработчик геопозиции
async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('state') != 'GEOPOSITION':
        logger.warning("Пользователь отправил геопозицию вне состояния 'GEOPOSITION'.")
        return

    location = update.message.location
    context.user_data['location'] = location  # Сохраняем геопозицию
    logger.info(f"Геопозиция получена: {location.latitude}, {location.longitude}")

    # Формируем ссылку на Яндекс.Карты
    yandex_maps_url = f"https://yandex.ru/maps/?ll={location.longitude},{location.latitude}&z=15"

    # Отправляем пользователю информацию
    await update.message.reply_text(
        f"Геопозиция сохранена. Вы можете просмотреть её на Яндекс.Картах: {yandex_maps_url}")

    # Переход к запросу комментария
    context.user_data['state'] = 'CONFIRM'
    await update.message.reply_text(
        "Всё прошло хорошо?",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Да", callback_data="yes"), InlineKeyboardButton("Нет", callback_data="no")]
        ])
    )



# Обработчик подтверждения
async def handle_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # Сохраняем данные профиля
    profile = context.user_data.get('profile', {'orders_count': 0, 'last_orders': []})
    profile['orders_count'] += 1

    # Добавляем информацию о заказе
    last_order_info = f"Заказ №{context.user_data['order_number']} ({'успешно' if query.data == 'yes' else 'неуспешно'})"
    profile['last_orders'].append(last_order_info)
    profile['last_orders'] = profile['last_orders'][-5:]  # Сохраняем только последние 5 заказов

    context.user_data['success'] = query.data

    # Обновляем данные профиля
    context.user_data['profile'] = profile

    # Переход к следующему шагу
    context.user_data['state'] = 'COMMENT'
    await query.message.reply_text("Оставьте комментарий (если комментария нет, введите прочерк):")


def get_address_from_coordinates(latitude, longitude):
    api_key = os.getenv("APIMAPS")  # Замените на ваш ключ API для Яндекс
    url = f"https://geocode-maps.yandex.ru/1.x/?geocode={longitude},{latitude}&format=json&apikey={api_key}"

    try:
        response = requests.get(url)
        data = response.json()

        # Проверяем, есть ли ключ 'response' и нужные данные
        if 'response' in data and data["response"].get("GeoObjectCollection"):
            feature_member = data["response"]["GeoObjectCollection"].get("featureMember")
            if feature_member:
                address = feature_member[0]["GeoObject"]["name"]
                return address
        return "Адрес не найден"

    except Exception as e:
        # Логируем ошибку, если что-то пошло не так с запросом
        logger.error(f"Ошибка при получении адреса: {e}")
        return "Ошибка при получении адреса"


# Обработчик комментария
async def handle_comment(update: Update, context: ContextTypes.DEFAULT_TYPE,):
    logging.info(f"context.user_data перед обработкой: {context.user_data}")

    success_message = "загружается..." if context.user_data.get('success') == "yes" else "Нет"
    await update.message.reply_text(f"Отчёт {success_message}")

    if context.user_data.get('state') != 'COMMENT':
        return

    # Сохраняем комментарий пользователя
    context.user_data['comment'] = update.message.text
    context.user_data['state'] = 'FINISHED'

    # Логируем начало загрузки файлов
    logger.info("Загрузка файлов на Яндекс.Диск начата.")
    order_number = context.user_data['order_number']
    media_paths = context.user_data['media']

    # Загрузка файлов на Яндекс.Диск
    for idx, media_path in enumerate(media_paths):
        upload_successful = upload_to_yandex_disk(order_number, media_path, os.path.basename(media_path))
        if not upload_successful:
            logger.error(f"Ошибка при загрузке файла {idx + 1}: {media_path}")
        os.remove(media_path)  # Удаляем временный файл

    logger.info("Файлы успешно загружены. Отправка отчёта в группу.")

    # Обновление данных профиля в базе данных
    user_id = update.effective_user.id
    await update_profile(user_id, order_number, context)

    # Сохранение заказа в базу данных
    add_order(
        user_id=user_id,
        order_number=order_number,
        status=context.user_data.get('success') == "yes",  # Преобразуем успех в boolean
        comment=context.user_data['comment'],
    )

    user = update.effective_user
    user_name = user.name if user.name else "Неизвестный пользователь"

    # Формирование отчета
    success_message = "Да" if context.user_data['success'] == "yes" else "Нет"
    report_caption = (
        f"Новый отчёт от пользователя: {user_name}\n"
        f"📦 Номер заказа: {order_number}\n"
        f"✅ Всё прошло хорошо: {success_message}\n"
        f"📝 Комментарий: {context.user_data['comment']}\n"
    )

    # Проверка наличия геопозиции
    location = context.user_data.get('location')
    if location:
        latitude = location.latitude
        longitude = location.longitude

        # Получаем адрес по координатам
        address = get_address_from_coordinates(latitude, longitude)

        # Формируем ссылку на Яндекс.Карты с точной меткой
        yandex_maps_url = f"https://yandex.ru/maps/?ll={longitude},{latitude}&z=15&pt={longitude},{latitude},pm2rdm"  # Ссылка на Яндекс.Карты с точкой

        # Добавляем адрес и кнопку в отчет
        report_caption += f"📍 Геопозиция: {address}  [Смотреть на карте]({yandex_maps_url})\n"

    # Отправка отчета в группу
    await context.bot.send_message(chat_id=COMPANY_GROUP_ID, text=report_caption, parse_mode='Markdown')

    # Очистка данных и предложение начать новый заказ
    context.user_data.clear()
    logger.info("Отчёт отправлен. Данные пользователя очищены.")
    await update.message.reply_text(
        "Отчёт успешно отправлен! Хотите загрузить новый заказ?",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Начать новый заказ", callback_data="restart")]]),
    )


async def restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()  # Ответ на клик по кнопке

    # Очищаем данные пользователя, чтобы начать с чистого листа
    context.user_data.clear()

    # Отправляем новое сообщение с кнопками
    keyboard = [
        [InlineKeyboardButton("Завершить загрузку", callback_data="finish_media")],
        [InlineKeyboardButton("Отменить", callback_data="cancel")],
        [InlineKeyboardButton("Профиль", callback_data="profile")]
    ]

    await query.message.reply_text(
        "Привет! Пожалуйста, загрузите фото или видео с выполнения заказа. Вы можете загрузить несколько файлов. Нажмите 'Завершить загрузку', когда закончите.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    # Сохраняем состояние пользователя
    context.user_data['state'] = 'MEDIA'
    context.user_data['media'] = []  # Список для хранения всех загружаемых файлов
    context.user_data['location'] = None  # Для хранения геопозиции
    context.user_data['order_number'] = None  # Для хранения номера заказа


# Основной код
def main():
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO, handle_media))
    application.add_handler(CallbackQueryHandler(finish_media, pattern="^finish_media$"))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'^\d+$'), handle_order_number))
    application.add_handler(CallbackQueryHandler(handle_confirm, pattern="^(yes|no)$"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_comment))
    application.add_handler(CallbackQueryHandler(restart, pattern="^restart$"))
    application.add_handler(CallbackQueryHandler(handle_profile, pattern='^profile$'))
    application.add_handler(CallbackQueryHandler(cancel, pattern='^cancel$'))

    # Добавляем обработчик для геопозиции
    application.add_handler(MessageHandler(filters.LOCATION, handle_location))  # Обрабатываем геопозицию

    application.run_polling()


if __name__ == "__main__":
    main()