import os
import logging
from aiogram import Bot, Dispatcher
from aiogram.types import Message, FSInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from PyPDF2 import PdfReader, PdfWriter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_TOKEN = '7814014008:AAHXEAuNW5RP7AUbS2CUdgdNglXJKE82aCw'

bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

def merge_pdfs_on_one_page(pdf_files, output_file="merged_one_page.pdf", columns=2, rows=2):
    """
    Объединяет страницы из нескольких PDF на одной странице A4.
    """
    writer = PdfWriter()

    # Создаем пустую страницу для добавления
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    
    page_width, page_height = A4  # Размер страницы A4
    cell_width = page_width / columns
    cell_height = page_height / rows
    
    temp_output_pdf = "temp_merged.pdf"
    c = canvas.Canvas(temp_output_pdf, pagesize=A4)

    # Размещение страниц из всех PDF в сетке
    page_count = 0
    for pdf_file in pdf_files:
        reader = PdfReader(pdf_file)
        for page_num in range(len(reader.pages)):
            if page_count >= columns * rows:
                c.showPage()  # Переход на новую страницу
                page_count = 0

            # Координаты для размещения текущей страницы
            col = page_count % columns
            row = page_count // columns
            x_position = col * cell_width
            y_position = page_height - (row + 1) * cell_height

            # Добавляем страницу в PDF
            page = reader.pages[page_num]
            writer.add_page(page)

            page_count += 1

    # Сохраняем временный объединенный файл
    writer.write(open(output_file, "wb"))

    return output_file

@dp.message(Command("start"))
async def start_handler(message: Message):
    await message.answer("Добро пожаловать! Отправьте два PDF файла, и я размещу их на одной странице.")

@dp.message(lambda message: message.document is not None)
async def document_handler(message: Message, state: FSMContext):
    document = message.document
    file_name = document.file_name
    if not file_name.lower().endswith('.pdf'):
        await message.answer("Пожалуйста, отправьте только PDF файлы.")
        return

    os.makedirs("downloads", exist_ok=True)
    file_path = f"downloads/{file_name}"
    await bot.download(document, file_path)
    logger.info(f"Файл {file_name} скачан в {file_path}")

    data = await state.get_data()
    pdf_files = data.get("pdf_files", [])
    pdf_files.append(file_path)
    await state.update_data(pdf_files=pdf_files)

    if len(pdf_files) == 2:  # Если два файла получены, начинаем обработку
        await message.answer("Два файла получены. Обрабатываю...")
        try:
            merged_file = merge_pdfs_on_one_page(pdf_files)
            await message.answer_document(FSInputFile(merged_file), caption="Ваш PDF файл готов.")
        except Exception as e:
            logger.error(f"Ошибка при обработке файлов: {e}")
            await message.answer("Произошла ошибка при обработке файлов.")
        finally:
            cleanup_files(pdf_files)
            if 'merged_file' in locals():
                cleanup_files([merged_file])
            await state.clear()
    else:
        await message.answer(f"Файл {file_name} получен. Всего файлов: {len(pdf_files)}.")

def cleanup_files(files):
    for file in files:
        if os.path.exists(file):
            os.remove(file)
            logger.info(f"Удален временный файл: {file}")

async def main():
    logger.info("Запуск бота...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())