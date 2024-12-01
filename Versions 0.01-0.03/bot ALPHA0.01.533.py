import os
import logging
from aiogram import Bot, Dispatcher
from aiogram.types import Message, FSInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from PyPDF3 import PdfFileWriter, PdfFileReader
from PyPDF3.pdf import PageObject

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_TOKEN = '7814014008:AAHXEAuNW5RP7AUbS2CUdgdNglXJKE82aCw'

bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

def arrange_pdfs_in_grid(pdf_files, output_file="merged_grid.pdf", columns=2, rows=2):
    """
    Объединяет страницы из PDF файлов в одну сетку на одной странице PDF.
    """
    input_pdfs = [PdfFileReader(open(pdf_file, "rb"), strict=False) for pdf_file in pdf_files]

    # Определяем размеры первой страницы
    first_page = input_pdfs[0].getPage(0)
    page_width = first_page.mediaBox.upperRight[0]
    page_height = first_page.mediaBox.upperRight[1]

    # Рассчитываем размер новой страницы для сетки
    total_width = columns * page_width
    total_height = rows * page_height

    output_pdf = PdfFileWriter()
    new_page = PageObject.createBlankPage(None, total_width, total_height)

    page_count = 0
    for pdf in input_pdfs:
        for page in pdf.pages:
            col = page_count % columns
            row = page_count // columns
            if row >= rows:
                # Если сетка заполнена, добавляем текущую страницу в итоговый PDF и создаем новую
                output_pdf.addPage(new_page)
                new_page = PageObject.createBlankPage(None, total_width, total_height)
                row = 0
                page_count = 0

            # Вычисляем смещение для вставки текущей страницы
            x_offset = col * page_width
            y_offset = total_height - (row + 1) * page_height

            # Добавляем страницу на позицию
            new_page.mergeTranslatedPage(page, x_offset, y_offset)
            page_count += 1

    # Добавляем последнюю страницу
    output_pdf.addPage(new_page)

    # Сохраняем итоговый PDF
    with open(output_file, "wb") as out_pdf:
        output_pdf.write(out_pdf)

    return output_file

@dp.message(Command("start"))
async def start_handler(message: Message):
    await message.answer("Добро пожаловать! Отправьте PDF файлы, и я размещу их на одной странице в виде сетки.")

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

    if len(pdf_files) >= 2:  # Объединяем, если есть минимум 4 файла
        await message.answer("Достаточно файлов получено. Обрабатываю...")
        try:
            merged_file = arrange_pdfs_in_grid(pdf_files)
            await message.answer_document(FSInputFile(merged_file), caption="Ваш PDF файл готов.")
        except Exception as e:
            logger.error(f"Ошибка при обработке файлов: {e}")
            await message.answer("Произошла ошибка при обработке файлов.")
        finally:
            # Очищаем временные данные и файлы
            cleanup_files(pdf_files)
            if 'merged_file' in locals():
                cleanup_files([merged_file])
            await state.clear()
    else:
        await message.answer(f"Файл {file_name} получен. Всего файлов: {len(pdf_files)}. Отправьте еще.")

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