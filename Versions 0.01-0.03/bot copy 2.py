import os
import logging
from aiogram import Bot, Dispatcher
from aiogram.types import Message, FSInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from PyPDF3 import PdfFileWriter, PdfFileReader
from PyPDF3.pdf import PageObject

API_TOKEN = '7814014008:AAHXEAuNW5RP7AUbS2CUdgdNglXJKE82aCw'

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

TEMP_FOLDER = "downloads"

def arrange_pdfs_in_grid(pdf_files, output_file="merged_grid.pdf", columns=2, rows=1):
    """
    Объединяет страницы из PDF файлов в сетку (например, 4x2) на одной странице PDF.
    """
    input_pdfs = []
    for pdf_file in pdf_files:
        try:
            input_pdf = PdfFileReader(open(pdf_file, "rb"), strict=False)
            if input_pdf.getNumPages() == 0:
                logger.warning(f"Файл {pdf_file} пуст и будет пропущен.")
                continue
            input_pdfs.append(input_pdf)
        except Exception as e:
            logger.error(f"Ошибка при чтении PDF файла {pdf_file}: {e}")
            continue

    if not input_pdfs:
        raise ValueError("Не удалось обработать ни один из предоставленных PDF файлов.")

    # Размер страницы для размещения сетки
    first_page = input_pdfs[0].getPage(0)
    original_width = float(first_page.mediaBox.upperRight[0])
    original_height = float(first_page.mediaBox.upperRight[1])

    # Вычисляем размеры сетки
    page_width = original_width
    page_height = original_height
    total_width = columns * page_width
    total_height = rows * page_height

    output_pdf = PdfFileWriter()
    new_page = PageObject.createBlankPage(None, total_width, total_height)

    page_count = 0
    for pdf in input_pdfs:
        for page_num in range(pdf.getNumPages()):
            page = pdf.getPage(page_num)

            # Определяем текущий столбец и строку
            col = page_count % columns
            row = page_count // columns
            if row >= rows:
                # Если текущая страница заполнена, добавляем её в итоговый PDF
                output_pdf.addPage(new_page)
                new_page = PageObject.createBlankPage(None, total_width, total_height)
                row = 0
                page_count = 0

            # Вычисляем позицию для текущей страницы в сетке
            x_offset = col * page_width
            y_offset = total_height - (row + 1) * page_height

            # Вставляем страницу в сетку
            new_page.mergeTranslatedPage(page, x_offset, y_offset)
            page_count += 1

    # Добавляем последнюю страницу
    if page_count > 0:
        output_pdf.addPage(new_page)

    # Сохраняем итоговый PDF
    with open(output_file, "wb") as out_pdf:
        output_pdf.write(out_pdf)

    return output_file

@dp.message(Command("start"))
async def start_handler(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Добро пожаловать! Отправьте PDF файлы, и я размещу их на одной странице в виде сетки.")

@dp.message(lambda message: message.document is not None)
async def document_handler(message: Message, state: FSMContext):
    document = message.document
    file_name = document.file_name
    if not file_name.lower().endswith('.pdf'):
        await message.answer("Пожалуйста, отправьте только PDF файлы.")
        return

    os.makedirs(TEMP_FOLDER, exist_ok=True)
    file_path = os.path.join(TEMP_FOLDER, file_name)
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
        remaining = 2 - len(pdf_files)
        await message.answer(f"Файл {file_name} получен. Осталось еще {remaining} файл(а).")


def cleanup_files(files):
    for file in files:
        if os.path.exists(file):
            os.remove(file)
            logger.info(f"Удален временный файл: {file}")

def cleanup_temp_folder(folder="downloads"):
    if os.path.exists(folder):
        for file in os.listdir(folder):
            try:
                os.remove(os.path.join(folder, file))
                logger.info(f"Удален временный файл: {file}")
            except Exception as e:
                logger.warning(f"Ошибка при удалении файла {file}: {e}")
        logger.info(f"Папка {folder} очищена.")

async def main():
    logger.info("Запуск бота...")
    cleanup_temp_folder(TEMP_FOLDER)  # Очистка временных файлов при запуске
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())