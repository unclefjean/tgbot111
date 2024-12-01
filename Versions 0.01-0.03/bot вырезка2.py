from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, CallbackContext
import os
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


# Функция для вырезания накладной
def extract_invoice(file_path: str) -> str:
    logger.info(f"Начата обработка файла: {file_path}")
    output_file = f"output_{os.path.basename(file_path)}"
    pdf_document = fitz.open(file_path)
    output_document = fitz.open()

    for page_num in range(len(pdf_document)):
        page = pdf_document[page_num]

        # Определяем размеры страницы
        page_width, page_height = page.rect.width, page.rect.height

        # Параметры сетки:
        # 1/4 ширины и 1/4 высоты (первая сетка сверху)
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
        "Привет! Отправьте мне PDF-файлы с накладными по одному, а когда закончите, введите команду /combine, чтобы объединить их в один документ."
    )


# Обработка PDF-файлов
async def handle_document(update: Update, context: CallbackContext):
    document = update.message.document
    if document.mime_type != "application/pdf":
        await update.message.reply_text("Пожалуйста, отправьте PDF-файл.")
        return

    temp_dir = "temp"
    os.makedirs(temp_dir, exist_ok=True)

    try:
        # Скачиваем файл
        file = await document.get_file()
        input_file_path = os.path.join(temp_dir, f"input_{document.file_id}.pdf")
        await file.download_to_drive(input_file_path)
        logger.info(f"Файл загружен: {input_file_path}")

        # Обрабатываем файл
        processed_file_path = extract_invoice(input_file_path)
        processed_files.append(processed_file_path)
        await update.message.reply_text(f"Файл обработан и добавлен в список для объединения.")

    except Exception as e:
        logger.error(f"Ошибка при обработке файла: {e}")
        await update.message.reply_text(f"Произошла ошибка при обработке: {e}")


# Команда /combine для объединения файлов
async def combine(update: Update, context: CallbackContext):
    if not processed_files:
        await update.message.reply_text("Список файлов для объединения пуст. Отправьте PDF-файлы перед использованием команды /combine.")
        return

    try:
        output_file_path = "combined_output.pdf"
        combine_pdfs(processed_files, output_file_path)

        with open(output_file_path, "rb") as output_file:
            await update.message.reply_document(document=output_file, filename="combined_processed.pdf")
        logger.info(f"Объединённый файл отправлен: {output_file_path}")

    except Exception as e:
        logger.error(f"Ошибка при объединении файлов: {e}")
        await update.message.reply_text(f"Произошла ошибка при объединении: {e}")

    finally:
        # Удаляем временные файлы
        for file_path in processed_files:
            if os.path.exists(file_path):
                os.remove(file_path)
        processed_files.clear()


# Создание и запуск бота
def main():
    application = ApplicationBuilder().token("7814014008:AAHXEAuNW5RP7AUbS2CUdgdNglXJKE82aCw").build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("combine", combine))
    application.add_handler(MessageHandler(filters.Document.PDF, handle_document))

    logger.info("Бот запущен.")
    application.run_polling()


if __name__ == "__main__":
    main()
