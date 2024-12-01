from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, CallbackContext
import os
import zipfile
import logging
import fitz  # PyMuPDF
import uuid  # Для генерации случайных имен

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Глобальный список для хранения обработанных файлов
processed_files = []

# Папка для временных файлов
TEMP_DIR = "temp"
os.makedirs(TEMP_DIR, exist_ok=True)

# Функция для вырезания накладной
def extract_invoice(file_path: str) -> str:
    logger.info(f"Начата обработка файла: {file_path}")
    output_file = os.path.join(TEMP_DIR, f"output_{uuid.uuid4().hex}.pdf")
    pdf_document = fitz.open(file_path)
    output_document = fitz.open()

    for page_num in range(len(pdf_document)):
        page = pdf_document[page_num]
        # Определяем размеры страницы
        page_width, page_height = page.rect.width, page.rect.height
        # Параметры сетки
        grid_width = page_width / 2
        grid_height = page_height / 2
        # Координаты первой сетки
        invoice_rect = fitz.Rect(0, 0, grid_width, grid_height)
        # Вырезаем область накладной
        invoice_page = output_document.new_page(width=invoice_rect.width, height=invoice_rect.height)
        invoice_page.show_pdf_page(invoice_page.rect, pdf_document, page_num, clip=invoice_rect)

    # Сохраняем обработанный PDF
    output_document.save(output_file)
    pdf_document.close()
    output_document.close()

    logger.info(f"Файл обработан и сохранён: {output_file}")
    return output_file

# Функция для объединения PDF-файлов
def combine_pdfs(input_files: list, output_file: str):
    logger.info("Начинается объединение файлов.")
    output_document = fitz.open()

    for file_path in input_files:
        document = fitz.open(file_path)
        output_document.insert_pdf(document)
        document.close()

    output_document.save(output_file)
    output_document.close()
    logger.info(f"Файлы успешно объединены: {output_file}")

# Команда /start
async def start(update: Update, context: CallbackContext):
    await update.message.reply_text(
        "Привет! Вот что я умею:\n"
        "1. Отправьте мне PDF-файлы или ZIP-архивы с накладными.\n"
        "2. Я обработаю их и сохраню для объединения.\n"
        "3. Введите команду /combine, чтобы объединить все обработанные файлы в один PDF.\n"
        "4. Если нужна помощь, используйте команду /help."
    )

# Команда /help
async def help_command(update: Update, context: CallbackContext):
    await update.message.reply_text(
        "Доступные команды:\n"
        "/start - Начало работы.\n"
        "/help - Показать это сообщение.\n"
        "/combine - Объединить обработанные файлы в один PDF.\n\n"
        "📩 **Обратная связь и коммерческие предложения:**\n"
        "Свяжитесь со мной по номеру: +77011254287"
    )

# Обработка PDF-файлов
async def handle_document(update: Update, context: CallbackContext):
    document = update.message.document
    temp_file_path = os.path.join(TEMP_DIR, f"{document.file_id}.pdf")

    try:
        file = await document.get_file()
        await file.download_to_drive(temp_file_path)
        logger.info(f"Файл загружен: {temp_file_path}")

        if document.mime_type == "application/pdf":
            processed_file_path = extract_invoice(temp_file_path)
            processed_files.append(processed_file_path)
            await update.message.reply_text(f"Файл обработан и добавлен в список для объединения.")
        elif document.mime_type == "application/zip":
            extracted_files = extract_zip(temp_file_path)
            await update.message.reply_text(f"ZIP-архив обработан, добавлено {len(extracted_files)} файлов.")
        else:
            await update.message.reply_text("Пожалуйста, отправьте PDF-файл или ZIP-архив.")

    except Exception as e:
        logger.error(f"Ошибка при обработке файла: {e}")
        await update.message.reply_text(f"Произошла ошибка: {e}")

# Распаковка ZIP-архива
def extract_zip(zip_file_path: str) -> list:
    logger.info(f"Распаковка ZIP-архива: {zip_file_path}")
    extracted_files = []
    try:
        with zipfile.ZipFile(zip_file_path, 'r') as archive:
            for file_name in archive.namelist():
                if file_name.endswith(".pdf"):
                    extracted_path = os.path.join(TEMP_DIR, f"extracted_{uuid.uuid4().hex}.pdf")
                    with open(extracted_path, "wb") as f:
                        f.write(archive.read(file_name))
                    # Обработка каждого PDF-файла из архива
                    processed_file_path = extract_invoice(extracted_path)
                    extracted_files.append(processed_file_path)
                    # Добавление в глобальный список
                    processed_files.append(processed_file_path)
    except Exception as e:
        logger.error(f"Ошибка при распаковке ZIP-архива: {e}")
    return extracted_files

import random
import string
# Функция для генерации случайного имени файла
def generate_random_filename(extension="pdf") -> str:
    random_string = ''.join(random.choices(string.ascii_letters + string.digits, k=10))  # 10 случайных символов
    return f"{random_string}.{extension}"

# Команда /combine
async def combine(update: Update, context: CallbackContext):
    if not processed_files:
        await update.message.reply_text("Список файлов для объединения пуст. Отправьте файлы перед использованием команды /combine.")
        return

    try:
        # Генерация пути к файлу с уникальным именем
        output_file_path = os.path.join(TEMP_DIR, f"combined_{uuid.uuid4().hex}.pdf")
        combine_pdfs(processed_files, output_file_path)

        # Генерация случайного имени для отправляемого файла
        random_filename = generate_random_filename()

        with open(output_file_path, "rb") as output_file:
            await update.message.reply_document(document=output_file, filename=random_filename)

    except Exception as e:
        logger.error(f"Ошибка при объединении файлов: {e}")
        await update.message.reply_text(f"Произошла ошибка при объединении: {e}")
    finally:
        clear_temp_files()

# Очистка временных файлов
def clear_temp_files():
    logger.info("Удаление временных файлов...")
    for root, _, files in os.walk(TEMP_DIR):
        for file in files:
            os.remove(os.path.join(root, file))
    processed_files.clear()

# Создание и запуск бота
def main():
    application = ApplicationBuilder().token("7814014008:AAHXEAuNW5RP7AUbS2CUdgdNglXJKE82aCw").build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("combine", combine))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))

    logger.info("Бот запущен.")
    application.run_polling()


if __name__ == "__main__":
    main()