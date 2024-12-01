import os
import logging
from aiogram import Bot, Dispatcher
from aiogram.types import Message, FSInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
import PyPDF2  # Используем PyPDF2 для работы с PDF

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_TOKEN = '7814014008:AAHXEAuNW5RP7AUbS2CUdgdNglXJKE82aCw'

bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

def merge_pdfs(pdf_files, output_file="merged_one_page.pdf"):
    """
    Объединяет несколько PDF-файлов в один.
    """
    merger = PyPDF2.PdfMerger()  # Исправленное имя класса PdfMerger
    
    for pdf_file in pdf_files:
        with open(pdf_file, "rb") as file:
            merger.append(PyPDF2.PdfReader(file))
    
    with open(output_file, "wb") as file:
        merger.write(file)
    
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

    if len(pdf_files) == 2:
        await message.answer("Два файла получены. Обрабатываю...")
        try:
            merged_file = merge_pdfs(pdf_files)
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