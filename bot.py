import os
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
import requests
import logging

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


# === Основные функции бота ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Пользователь {update.effective_user.username} начал новый заказ.")
    await update.message.reply_text(
        "Привет! Пожалуйста, загрузите фото или видео с выполнения заказа. Вы можете загрузить несколько файлов. Нажмите 'Завершить загрузку', когда закончите.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Завершить загрузку", callback_data="finish_media")],
            [InlineKeyboardButton("Отменить", callback_data="cancel")]
        ])
    )
    context.user_data['state'] = 'MEDIA'
    context.user_data['media'] = []  # Список для хранения всех загружаемых файлов


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

    # Сохраняем файл с уникальным именем
    file = await context.bot.get_file(media_file.file_id)
    file_path = f"temp_{update.message.chat_id}_{len(context.user_data['media']) + 1}.{file_extension}"
    await file.download_to_drive(file_path)

    # Добавляем путь к файлу в список
    context.user_data['media'].append(file_path)
    logger.info(f"Файл {file_path} добавлен в список медиа.")
    await update.message.reply_text("Файл добавлен. Вы можете загрузить еще один файл или завершить загрузку.")


async def finish_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not context.user_data.get('media'):
        logger.warning("Пользователь нажал 'Завершить загрузку', не добавив медиа.")
        await query.message.reply_text("Вы не загрузили ни одного файла. Пожалуйста, загрузите хотя бы один файл.")
        return

    logger.info(f"Пользователь завершил загрузку медиа. Файлы: {context.user_data['media']}")
    context.user_data['state'] = 'ORDER_NUMBER'
    await query.message.reply_text("Введите номер заказа (только цифры):")


async def handle_order_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('state') != 'ORDER_NUMBER':
        return

    order_number = update.message.text
    if not check_folder_exists(order_number):
        await update.message.reply_text("Папка для указанного заказа не найдена. Введите корректный номер заказа.")
        return

    logger.info(f"Номер заказа подтверждён: {order_number}")
    context.user_data['order_number'] = order_number
    context.user_data['state'] = 'CONFIRM'
    await update.message.reply_text(
        "Всё прошло хорошо?",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Да", callback_data="yes"), InlineKeyboardButton("Нет", callback_data="no")]
        ])
    )


async def handle_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    context.user_data['success'] = query.data  # Сохраняем ответ "yes" или "no"
    logger.info(f"Пользователь подтвердил состояние: {'успешно' if query.data == 'yes' else 'неуспешно'}.")
    context.user_data['state'] = 'COMMENT'
    await query.message.reply_text("Оставьте комментарий (если комментария нет, введите прочерк):")


async def handle_comment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('state') != 'COMMENT':
        return

    context.user_data['comment'] = update.message.text
    context.user_data['state'] = 'FINISHED'

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
    # Отправка отчета в группу
    success_message = "Да" if context.user_data['success'] == "yes" else "Нет"
    report_caption = (
        f"📋 **Новый отчёт о заказе**:\n"
        f"📦 Номер заказа: {order_number}\n"
        f"✅ Всё прошло хорошо: {success_message}\n"
        f"📝 Комментарий: {context.user_data['comment']}"
    )
    await context.bot.send_message(chat_id=COMPANY_GROUP_ID, text=report_caption)

    # Очистка данных и предложение начать новый заказ
    context.user_data.clear()
    logger.info("Отчёт отправлен. Данные пользователя очищены.")
    await update.message.reply_text(
        "Отчёт успешно отправлен! Хотите загрузить новый заказ?",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Начать новый заказ", callback_data="restart")]])
    )

async def restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await start(update, context)


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

    application.run_polling()


if __name__ == "__main__":
    main()
