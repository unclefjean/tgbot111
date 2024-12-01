import os
import zipfile
import logging
import fitz  # PyMuPDF
import uuid
import random
import string
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackContext,
)

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

# Генерация случайного имени файла
def generate_random_filename(extension="pdf") -> str:
    random_string = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
    return f"{random_string}.{extension}"

# Функция для вырезания накладной
def extract_invoice(file_path: str) -> str:
    logger.info(f"Начата обработка файла: {file_path}")
    output_file = os.path.join(TEMP_DIR, f"output_{uuid.uuid4().hex}.pdf")
    
    # Открываем PDF с помощью fitz
    pdf_document = fitz.open(file_path)
    output_document = fitz.open()

    for page_num in range(len(pdf_document)):
        page = pdf_document[page_num]
        page_width, page_height = page.rect.width, page.rect.height
        grid_width = page_width / 2
        grid_height = page_height / 2
        invoice_rect = fitz.Rect(0, 0, grid_width, grid_height)
        invoice_page = output_document.new_page(
            width=invoice_rect.width, height=invoice_rect.height
        )
        invoice_page.show_pdf_page(
            invoice_page.rect, pdf_document, page_num, clip=invoice_rect
        )

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

# Очистка временных файлов
def clear_temp_files():
    logger.info("Удаление временных файлов...")
    for root, _, files in os.walk(TEMP_DIR):
        for file in files:
            os.remove(os.path.join(root, file))
    processed_files.clear()

# Команда /start
async def start(update: Update, context: CallbackContext):
    await update.message.reply_text(
        "Привет! Я бот для обработки накладных.\n"
        "Чтобы начать, используйте следующие команды:\n"
        "/help - чтобы получить помощь.\n"
        "Отправьте мне PDF или ZIP-файл для обработки. Я обработаю их и сохраню для объединения.\n"
        "Используйте /combine чтобы объединить все обработанные файлы(PDF или ZIP-архив) в один PDF-файл."
    )

# Команда /help
async def help_command(update: Update, context: CallbackContext):
    await update.message.reply_text(
        "📖 **Доступные команды:**\n"
        "/start - чтобы начать работу с ботом.\n"
        "/help - получить помощь по использованию бота.\n"
        "/combine - объединить все обработанные файлы в один PDF.\n\n"
        "📩 Для вопросов: +77011254287"
    )

# Обработка документов
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
            await update.message.reply_text("PDF обработан и добавлен в список. Используйте /combine если добавили несколько файлов.")
        elif document.mime_type == "application/zip":
            extracted_files = extract_zip(temp_file_path)
            await update.message.reply_text(f"ZIP обработан: {len(extracted_files)} файлов добавлено. Используйте /combine если добавили несколько файлов.")
        else:
            await update.message.reply_text("Отправьте PDF или ZIP-файл.")

    except Exception as e:
        logger.error(f"Ошибка обработки файла: {e}")
        await update.message.reply_text(f"Ошибка: {e}")

# Распаковка ZIP
def extract_zip(zip_file_path: str) -> list:
    logger.info(f"Распаковка ZIP: {zip_file_path}")
    extracted_files = []

    try:
        with zipfile.ZipFile(zip_file_path, 'r') as archive:
            for file_name in archive.namelist():
                if file_name.endswith(".pdf"):
                    extracted_path = os.path.join(TEMP_DIR, f"extracted_{uuid.uuid4().hex}.pdf")
                    with open(extracted_path, "wb") as f:
                        f.write(archive.read(file_name))
                    processed_file_path = extract_invoice(extracted_path)
                    extracted_files.append(processed_file_path)
                    processed_files.append(processed_file_path)
    except Exception as e:
        logger.error(f"Ошибка распаковки ZIP: {e}")
    return extracted_files

# Команда /combine
async def combine(update: Update, context: CallbackContext):
    if not processed_files:
        await update.message.reply_text("Нет файлов для объединения. Отправьте файлы для обработки.")
        return

    try:
        output_file_path = os.path.join(TEMP_DIR, f"combined_{uuid.uuid4().hex}.pdf")
        combine_pdfs(processed_files, output_file_path)
        random_filename = generate_random_filename()

        with open(output_file_path, "rb") as output_file:
            await update.message.reply_document(document=output_file, filename=random_filename)

    except Exception as e:
        logger.error(f"Ошибка объединения: {e}")
        await update.message.reply_text(f"Ошибка объединения: {e}")
    finally:
        clear_temp_files()

# Основная функция
def main():
    application = ApplicationBuilder().token("7814014008:AAHXEAuNW5RP7AUbS2CUdgdNglXJKE82aCw").build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    application.add_handler(CommandHandler("combine", combine))

    logger.info("Бот запущен.")
    application.run_polling()

if __name__ == "__main__":
    main()