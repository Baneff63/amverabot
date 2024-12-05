import os
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
import requests

# Загрузка переменных окружения
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
YANDEX_DISK_TOKEN = os.getenv("YANDEX_DISK_TOKEN")
COMPANY_GROUP_ID = int(os.getenv("COMPANY_GROUP_ID"))

YANDEX_DISK_API_URL = "https://cloud-api.yandex.net/v1/disk/resources"


# === Вспомогательные функции для Яндекс.Диска ===

def check_folder_exists(order_number):
    """Проверка, существует ли папка на Яндекс.Диске."""
    headers = {"Authorization": f"OAuth {YANDEX_DISK_TOKEN}"}
    response = requests.get(f"{YANDEX_DISK_API_URL}?path={order_number}", headers=headers)
    print(f"DEBUG: Проверка папки для заказа {order_number}, статус: {response.status_code}")
    return response.status_code == 200


def upload_to_yandex_disk(order_number, file_path, file_name):
    """Загрузка файла на Яндекс.Диск."""
    headers = {"Authorization": f"OAuth {YANDEX_DISK_TOKEN}"}
    response = requests.get(
        f"{YANDEX_DISK_API_URL}/upload?path={order_number}/{file_name}&overwrite=true",
        headers=headers
    )
    print(f"DEBUG: Попытка получить ссылку на загрузку для {file_name}, статус: {response.status_code}")
    if response.status_code == 200:
        upload_url = response.json().get("href")
        with open(file_path, "rb") as f:
            upload_response = requests.put(upload_url, files={"file": f})
            print(f"DEBUG: Попытка загрузить файл на Яндекс.Диск, статус: {upload_response.status_code}")
            return upload_response.status_code == 201
    return False


# === Основные функции бота ===

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало нового заказа."""
    print("DEBUG: Вызвана функция start()")
    await update.message.reply_text(
        "Привет! Пожалуйста, загрузите фото с выполнения заказа. Вы можете загрузить несколько фотографий. Нажмите 'Завершить загрузку фото', когда закончите.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Завершить загрузку фото", callback_data="finish_photos")],
            [InlineKeyboardButton("Отменить", callback_data="cancel")]
        ])
    )
    context.user_data['state'] = 'PHOTO'
    context.user_data['photos'] = []  # Список для хранения путей к загруженным фотографиям
    print(f"DEBUG: Состояние установлено в PHOTO (текущее состояние: {context.user_data['state']})")


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка фото."""
    if context.user_data.get('state') != 'PHOTO':
        print(f"DEBUG: Получено фото в некорректном состоянии: {context.user_data.get('state')}")
        return

    print("DEBUG: Получено фото, начинаем обработку")
    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    file_path = f"temp_{update.message.chat_id}_{len(context.user_data['photos']) + 1}.jpg"
    await file.download_to_drive(file_path)

    # Добавляем путь к фото в список фотографий пользователя
    context.user_data['photos'].append(file_path)
    print(f"DEBUG: Фото сохранено, текущее количество фото: {len(context.user_data['photos'])}")

    await update.message.reply_text(
        "Фото добавлено. Вы можете загрузить еще одно фото или нажать 'Завершить загрузку фото'.")


async def finish_photos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Завершение загрузки фотографий."""
    query = update.callback_query
    await query.answer()

    if not context.user_data.get('photos'):
        await query.message.reply_text(
            "Вы не загрузили ни одной фотографии. Пожалуйста, загрузите хотя бы одну фотографию.")
        return

    context.user_data['state'] = 'ORDER_NUMBER'
    print(f"DEBUG: Переход к вводу номера заказа (текущее состояние: {context.user_data['state']})")
    await query.message.reply_text("Введите номер заказа (только цифры, без пробелов):")


async def handle_order_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка номера заказа."""
    if context.user_data.get('state') != 'ORDER_NUMBER':
        print(f"DEBUG: Получен номер заказа в некорректном состоянии: {context.user_data.get('state')}")
        return

    order_number = update.message.text
    print(f"DEBUG: Получен номер заказа: {order_number}")

    if not check_folder_exists(order_number):
        await update.message.reply_text(
            "Папка для указанного заказа не найдена на Яндекс.Диске. Пожалуйста, введите корректный номер заказа."
        )
        # Состояние остается 'ORDER_NUMBER', чтобы пользователь мог ввести правильный номер заказа
        print(
            f"DEBUG: Папка не найдена, остаемся в состоянии ORDER_NUMBER (текущее состояние: {context.user_data['state']})")
        return

    context.user_data['order_number'] = order_number
    context.user_data['state'] = 'ORDER_SUCCESS'
    print(
        f"DEBUG: Папка найдена, задаём вопрос о том, всё ли прошло хорошо (текущее состояние: {context.user_data['state']})")

    await update.message.reply_text(
        "Всё ли хорошо прошло?",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Да", callback_data="yes"), InlineKeyboardButton("Нет", callback_data="no")]
        ])
    )


async def handle_success_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка вопроса 'Всё ли прошло хорошо?'."""
    query = update.callback_query
    await query.answer()

    context.user_data['success'] = query.data  # Сохраняем ответ ("yes" или "no")
    context.user_data['state'] = 'DISTANCE'
    print(f"DEBUG: Ответ на вопрос о заказе: {query.data} (текущее состояние: {context.user_data['state']})")

    await query.message.reply_text("Введите расстояние до центра Самары (в километрах, можно с десятичной точкой):")


async def handle_distance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода расстояния."""
    if 'order_number' not in context.user_data:
        await update.message.reply_text("Сначала введите номер заказа. Пожалуйста, введите номер заказа (только цифры, без пробелов):")
        return

    try:
        # Пытаемся преобразовать ввод в число
        distance = float(update.message.text)

        # Проверяем, что ввод не равен номеру заказа
        if distance == int(context.user_data['order_number']):
            await update.message.reply_text("Это не расстояние, а номер заказа. Пожалуйста, введите расстояние в километрах.")
            return

        # Сохраняем расстояние в user_data
        context.user_data['distance'] = distance
        context.user_data['state'] = 'COMMENT'

        print(f"DEBUG: Получено расстояние: {distance} км (текущее состояние: {context.user_data['state']})")
        await update.message.reply_text("Оставьте комментарий (если комментария нет, оставьте поле пустым):")
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите корректное число для расстояния.")


async def handle_comment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка комментария."""
    if context.user_data.get('state') != 'COMMENT':
        print(f"DEBUG: Получен комментарий в некорректном состоянии: {context.user_data.get('state')}")
        return

    comment = update.message.text
    context.user_data['comment'] = comment
    context.user_data['state'] = 'FINISHED'
    print(f"DEBUG: Получен комментарий: {comment} (текущее состояние: {context.user_data['state']})")

    # Теперь загрузим фото на Яндекс.Диск и отправим отчет
    order_number = context.user_data['order_number']
    photo_paths = context.user_data['photos']

    # Загружаем все фото на Яндекс.Диск
    for idx, photo_path in enumerate(photo_paths):
        upload_successful = upload_to_yandex_disk(order_number, photo_path, os.path.basename(photo_path))
        if upload_successful:
            await update.message.reply_text(f"Фото {idx + 1} успешно загружено на Яндекс.Диск.")
            print(f"DEBUG: Фото {idx + 1} успешно загружено на Яндекс.Диск")
        else:
            await update.message.reply_text(f"Ошибка при загрузке фото {idx + 1} на Яндекс.Диск.")
            print(f"DEBUG: Ошибка при загрузке фото {idx + 1} на Яндекс.Диск")

    # Отправляем отчёт в группу
    success_message = "Да" if context.user_data['success'] == "yes" else "Нет"
    report_caption = (
        f"📋 **Новый отчёт о заказе**:\n"
        f"📦 Номер заказа: {order_number}\n"
        f"✅ Всё прошло хорошо: {success_message}\n"
        f"📏 Расстояние до центра Самары: {context.user_data['distance']} км\n"
        f"📝 Комментарий: {comment if comment else 'Нет комментария'}"
    )
    try:
        with open(photo_paths[0], "rb") as photo:
            await context.bot.send_photo(
                chat_id=COMPANY_GROUP_ID,
                photo=photo,
                caption=report_caption,
                parse_mode="Markdown"
            )
        print("DEBUG: Отчёт успешно отправлен в группу")
    except Exception as e:
        await update.message.reply_text(f"Не удалось отправить отчёт в группу: {e}")
        print(f"ERROR: Не удалось отправить отчёт в группу: {e}")

    # Удаляем временные файлы
    for photo_path in photo_paths:
        os.remove(photo_path)
    print("DEBUG: Все временные файлы удалены")

    # Предлагаем начать новый заказ
    await update.message.reply_text(
        "Отчёт успешно отправлен! Хотите загрузить новый заказ?",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Начать новый заказ", callback_data="restart")]])
    )
    context.user_data.clear()


async def restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Перезапуск процесса."""
    query = update.callback_query
    await query.answer()
    await query.message.delete()  # Удаляем предыдущее сообщение с кнопкой

    # Перезапуск с вызовом функции start через callback_query
    await query.message.reply_text(
        "Привет! Пожалуйста, загрузите фото с выполнения заказа.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Завершить загрузку фото", callback_data="finish_photos")],
            [InlineKeyboardButton("Отменить", callback_data="cancel")]
        ])
    )
    context.user_data['state'] = 'PHOTO'
    context.user_data['photos'] = []  # Список для хранения путей к загруженным фотографиям
    print(f"DEBUG: Состояние установлено в PHOTO (текущее состояние: {context.user_data['state']})")


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена текущего процесса."""
    query = update.callback_query
    await query.answer()
    await query.message.reply_text("Действие отменено. Введите /start, чтобы начать заново.")
    context.user_data.clear()


# === Основной код ===

def main():
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # Добавляем обработчики, разделенные для каждого состояния
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.PHOTO & filters.ChatType.PRIVATE, handle_photo))
    application.add_handler(CallbackQueryHandler(finish_photos, pattern="^finish_photos$"))
    application.add_handler(
        MessageHandler(filters.TEXT & filters.ChatType.PRIVATE & filters.Regex(r'^\d+$'), handle_order_number))
    application.add_handler(CallbackQueryHandler(handle_success_question, pattern="^(yes|no)$"))
    application.add_handler(
        MessageHandler(filters.TEXT & filters.ChatType.PRIVATE & filters.Regex(r'^\d+(\.\d+)?$'), handle_distance))
    application.add_handler(MessageHandler(filters.TEXT & filters.ChatType.PRIVATE & ~filters.COMMAND, handle_comment))
    application.add_handler(CallbackQueryHandler(restart, pattern="^restart$"))
    application.add_handler(CallbackQueryHandler(cancel, pattern="^cancel$"))

    application.run_polling()


if __name__ == "__main__":
    main()
