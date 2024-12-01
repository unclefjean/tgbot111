import os
import zipfile
import logging
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, FSInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from PyPDF2 import PdfReader, PdfWriter
from PIL import Image
from io import BytesIO
import aiofiles
import shutil

# Токен бота
API_TOKEN = '7814014008:AAHXEAuNW5RP7AUbS2CUdgdNglXJKE82aCw'

# Логирование
logging.basicConfig(level=logging.INFO)

# Создание бота и диспетчера
bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Главные кнопки выбора
main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="4 на 1 лист")],
        [KeyboardButton(text="8 на 1 лист"), KeyboardButton(text="9 на 1 лист")],
        [KeyboardButton(text="A4 для термопринтера")]
    ],
    resize_keyboard=True
)

# Функция объединения PDF
def merge_pdfs(files, layout='4 на 1 лист'):
    writer = PdfWriter()
    for file in files:
        reader = PdfReader(file)
        for page in reader.pages:
            writer.add_page(page)  # Простое добавление страниц (оптимизация по layout не реализована)
    output_file = f"merged_{layout.replace(' ', '_')}.pdf"
    with open(output_file, 'wb') as f:
        writer.write(f)
    return output_file

# Функция распаковки ZIP
def extract_zip(file_path, extract_to="extracted"):
    os.makedirs(extract_to, exist_ok=True)
    with zipfile.ZipFile(file_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)
    return [os.path.join(extract_to, file) for file in os.listdir(extract_to) if file.endswith('.pdf')]

# Функция очистки временных файлов
def cleanup_files(files):
    for file in files:
        if os.path.exists(file):
            os.remove(file)

# Команда /start
@dp.message(Command("start"))
async def start_handler(message: Message):
    await message.answer("Я помогу объединить PDF или обработать архив ZIP. Выберите формат:", reply_markup=main_keyboard)

# Команда /help
@dp.message(Command("help"))
async def help_handler(message: Message):
    await message.answer("Отправьте PDF или ZIP файл, а затем выберите формат. Доступные форматы:\n"
                         "1. 4 на 1 лист\n"
                         "2. 8 на 1 лист\n"
                         "3. 9 на 1 лист\n"
                         "4. A4 для термопринтера")

# Обработка кнопок выбора формата
@dp.message(lambda message: message.text in {"4 на 1 лист", "8 на 1 лист", "9 на 1 лист", "A4 для термопринтера"})
async def layout_handler(message: Message, state: FSMContext):
    await state.update_data(layout=message.text)
    await message.answer(f"Вы выбрали: {message.text}. Теперь загрузите PDF или ZIP файл.")

# Обработка загруженных документов
@dp.message(lambda message: message.document is not None)
async def document_handler(message: Message, state: FSMContext):
    try:
        document = message.document
        file_name = document.file_name
        layout = (await state.get_data()).get("layout", "4 на 1 лист")
        file_path = f"downloads/{file_name}"
        os.makedirs("downloads", exist_ok=True)

        # Скачиваем файл
        await bot.download(document, file_path)
        await message.answer(f"Файл {file_name} загружен. Начинаю обработку...")

        # Проверка типа файла
        if file_name.endswith(".zip"):
            await message.answer("Это архив. Распаковываю...")
            extracted_files = extract_zip(file_path)
            await message.answer(f"Распаковано {len(extracted_files)} PDF файлов.")
            merged_file = merge_pdfs(extracted_files, layout)
            await message.answer_document(FSInputFile(merged_file))
            # Очистка временных файлов
            cleanup_files(extracted_files + [merged_file])
        elif file_name.endswith(".pdf"):
            merged_file = merge_pdfs([file_path], layout)
            await message.answer_document(FSInputFile(merged_file))
            cleanup_files([merged_file])

        cleanup_files([file_path])
    except Exception as e:
        logging.error(f"Ошибка обработки файла {message.document.file_name}: {e}")
        await message.answer(f"Произошла ошибка при обработке файла: {e}")

# Асинхронное сохранение файла
async def save_file(file_data, file_path):
    async with aiofiles.open(file_path, 'wb') as f:
        await f.write(file_data)

# Запуск бота
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())