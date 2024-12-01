import os
import logging
import random
import string
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, FSInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from PyPDF2 import PdfReader, PdfWriter, PageObject

# Инициализация бота
API_TOKEN = '7814014008:AAHXEAuNW5RP7AUbS2CUdgdNglXJKE82aCw'
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

TEMP_FOLDER = "downloads"
router = Router()

def random_filename(extension="pdf"):
    """Генерирует случайное имя файла."""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=8)) + f".{extension}"

from PyPDF2 import Transformation

from PyPDF2 import PageObject, PdfReader, PdfWriter
import os


from PyPDF2 import PdfReader, PdfWriter, PageObject

def merge_pdfs_with_spacing(pdf_files, spacing=20):
    """
    Объединяет страницы из PDF-файлов по порядку с небольшим отступом.
    
    :param pdf_files: Список путей к PDF-файлам.
    :param spacing: Отступ между страницами (в пунктах).
    :return: Путь к объединенному PDF-файлу.
    """
    writer = PdfWriter()
    pages = []
    
    for file in pdf_files:
        reader = PdfReader(file)
        pages.extend(reader.pages)
    
    if not pages:
        raise ValueError("Нет страниц для обработки.")
    
    # Вычисление размеров итогового PDF
    first_page = pages[0]
    page_width = float(first_page.mediabox.width)
    page_height = float(first_page.mediabox.height)
    
    # Рассчитываем итоговую высоту страницы с учетом отступов
    total_height = len(pages) * (page_height + spacing) - spacing
    
    # Создаем новый пустой документ
    output_file = os.path.join(TEMP_FOLDER, random_filename())
    
    # Создаем страницу для итогового PDF
    new_page = PageObject.create_blank_page(width=page_width, height=total_height)
    
    y_offset = total_height - page_height  # Начинаем с верхнего отступа
    for page in pages:
        # Создаем новый объект страницы, чтобы добавить на нее отступ
        new_page.mergeTranslatedPage(page, tx=0, ty=y_offset)
        y_offset -= (page_height + spacing)  # Сдвигаем для следующей страницы
    
    writer.add_page(new_page)
    
    # Записываем в новый файл
    os.makedirs(TEMP_FOLDER, exist_ok=True)
    with open(output_file, "wb") as out_file:
        writer.write(out_file)
    
    return output_file

@router.message(Command("start"))
async def start_handler(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Добро пожаловать! Отправьте минимум 2 PDF файла, и я объединю их в один.")

@router.message(F.document.mime_type == "application/pdf")
async def document_handler(message: Message, state: FSMContext):
    os.makedirs(TEMP_FOLDER, exist_ok=True)
    document = message.document
    file_path = os.path.join(TEMP_FOLDER, document.file_name)

    # Скачиваем файл
    await bot.download(document.file_id, file_path)

    # Загружаем состояние
    data = await state.get_data()
    pdf_files = data.get("pdf_files", [])
    pdf_files.append(file_path)

    # Сохраняем обновленный список файлов
    await state.update_data(pdf_files=pdf_files)

    # Проверяем, достаточно ли файлов для обработки
    if len(pdf_files) >= 2:
        await message.answer("Достаточно файлов получено. Обрабатываю...")
        merged_file = None  # Инициализируем переменную перед использованием
        try:
            # Исправлено: используем правильное имя функции
            merged_file = merge_pdfs_with_spacing(pdf_files)
            await message.answer_document(FSInputFile(merged_file), caption="Ваш PDF файл готов.")
        except Exception as e:
            logger.error(f"Ошибка при объединении PDF: {e}")
            await message.answer("Произошла ошибка при обработке файлов.")
        finally:
            # Очистка временных файлов
            if merged_file:
                cleanup_files(pdf_files + [merged_file])
            else:
                cleanup_files(pdf_files)
            await state.clear()


def cleanup_files(files):
    """Удаляет временные файлы."""
    for file in files:
        try:
            if os.path.exists(file):
                os.remove(file)
                logger.info(f"Удален временный файл: {file}")
        except Exception as e:
            logger.warning(f"Ошибка при удалении файла {file}: {e}")

async def main():
    logger.info("Запуск бота...")
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())