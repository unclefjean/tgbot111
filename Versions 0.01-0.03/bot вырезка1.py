from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, CallbackContext
import fitz  # PyMuPDF


# Функция для вырезания накладной
def extract_invoice(file_path: str) -> str:
    output_file = "output.pdf"
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
    return output_file


# Команда /start
async def start(update: Update, context: CallbackContext):
    await update.message.reply_text("Привет! Отправьте мне PDF-файл с накладной, и я обработаю его для вас.")


# Обработка PDF-файлов
async def handle_document(update: Update, context: CallbackContext):
    document = update.message.document
    if document.mime_type != "application/pdf":
        await update.message.reply_text("Пожалуйста, отправьте PDF-файл.")
        return

    file = await document.get_file()
    input_file_path = f"input_{document.file_id}.pdf"
    await file.download_to_drive(input_file_path)

    try:
        # Обрабатываем PDF
        output_file_path = extract_invoice(input_file_path)
        with open(output_file_path, "rb") as output_file:
            await update.message.reply_document(document=output_file, filename="processed.pdf")
    except Exception as e:
        await update.message.reply_text(f"Произошла ошибка при обработке: {e}")
    finally:
        # Удаляем временные файлы
        import os
        os.remove(input_file_path)
        if os.path.exists(output_file_path):
            os.remove(output_file_path)


# Создание и запуск бота
def main():
    application = ApplicationBuilder().token("7814014008:AAHXEAuNW5RP7AUbS2CUdgdNglXJKE82aCw").build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.Document.PDF, handle_document))

    application.run_polling()


if __name__ == "__main__":
    main()