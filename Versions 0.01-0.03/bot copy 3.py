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


def merge_pdfs_in_row(pdf_files, output_file="merged_linear.pdf"):
    """
    Объединяет страницы из PDF файлов в один документ, размещая их последовательно (каждая страница занимает отдельный лист).
    """
    output_pdf = PdfFileWriter()
    open_files = []  # Список для хранения открытых файлов, чтобы их закрыть позже

    try:
        for pdf_file in pdf_files:
            try:
                file = open(pdf_file, "rb")  # Открываем файл
                open_files.append(file)  # Сохраняем открытый файл
                input_pdf = PdfFileReader(file, strict=False)

                if input_pdf.getNumPages() == 0:
                    logger.warning(f"Файл {pdf_file} пуст и будет пропущен.")
                    continue

                # Добавляем все страницы текущего PDF в итоговый PDF
                for page_num in range(input_pdf.getNumPages()):
                    page = input_pdf.getPage(page_num)
                    output_pdf.addPage(page)

            except Exception as e:
                logger.error(f"Ошибка при обработке файла {pdf_file}: {e}")
                continue

        # Сохраняем итоговый PDF
        with open(output_file, "wb") as out_pdf:
            output_pdf.write(out_pdf)

        logger.info(f"Итоговый PDF файл сохранен как {output_file}.")
        return output_file

    finally:
        # Закрываем все открытые файлы
        for file in open_files:
            file.close()
            logger.info(f"Файл закрыт: {file.name}")


@dp.message(Command("start"))
async def start_handler(message: Message, state: FSMContext):
    await state.clear()
    cleanup_temp_folder(TEMP_FOLDER)
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

    if len(pdf_files) >= 2:
        await message.answer("Достаточно файлов получено. Обрабатываю...")
        merged_file = None  # Инициализация переменной

        try:
            merged_file = arrange_pdfs_in_grid(pdf_files)
            await message.answer_document(FSInputFile(merged_file), caption="Ваш PDF файл готов.")
        except Exception as e:
            logger.error(f"Ошибка при обработке файлов: {e}")
            await message.answer("Произошла ошибка при обработке файлов.")
        finally:
            # Очищаем временные данные и файлы
            cleanup_files(pdf_files)
            if merged_file and os.path.exists(merged_file):
                cleanup_files([merged_file])
            await state.clear()
    else:
        remaining = 2 - len(pdf_files)
        await message.answer(f"Файл {file_name} получен. Осталось еще {remaining} файл(а).")


def cleanup_files(files):
    """
    Удаляет список указанных файлов.
    """
    for file in files:
        try:
            if os.path.exists(file):
                os.remove(file)
                logger.info(f"Удален временный файл: {file}")
        except Exception as e:
            logger.warning(f"Ошибка при удалении файла {file}: {e}")


def cleanup_temp_folder(folder="downloads"):
    """
    Очищает временную папку, удаляя все файлы в ней.
    """
    if os.path.exists(folder):
        for file in os.listdir(folder):
            file_path = os.path.join(folder, file)
            try:
                os.remove(file_path)
                logger.info(f"Удален временный файл: {file_path}")
            except Exception as e:
                logger.warning(f"Ошибка при удалении файла {file_path}: {e}")


async def main():
    logger.info("Запуск бота...")
    cleanup_temp_folder(TEMP_FOLDER)
    await dp.start_polling(bot)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())