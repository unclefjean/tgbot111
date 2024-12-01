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
        [KeyboardButton(text="2 на 1 лист"), KeyboardButton(text="3 на 1 лист")],  # Добавлены кнопки 2 и 3 на 1 лист
        [KeyboardButton(text="A4 для термопринтера")]
    ],
    resize_keyboard=True
)

# Кнопки для управления результатами
result_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Скачать результат")],
        [KeyboardButton(text="Отправить новый файл")]
    ],
    resize_keyboard=True
)

# Функция объединения PDF с выбранным количеством страниц на листе
def merge_pdfs(files, layout='4 на 1 лист'):
    writer = PdfWriter()

    # Количество страниц на листе
    pages_per_sheet = {
        '2 на 1 лист': 2,
        '3 на 1 лист': 3,
        '4 на 1 лист': 4,
        '8 на 1 лист': 8,
        '9 на 1 лист': 9,
        'A4 для термопринтера': 1  # 1 на 1, стандартный
    }

    layout_pages = pages_per_sheet.get(layout, 4)  # По умолчанию 4 страницы на лист

    for file in files:
        reader = PdfReader(file)
        for page in reader.pages:
            writer.add_page(page)  # Пока просто добавляем страницы (сложные преобразования не реализованы)

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
                         "1. 2 на 1 лист\n"
                         "2. 3 на 1 лист\n"
                         "3. 4 на 1 лист\n"
                         "4. 8 на 1 лист\n"
                         "5. 9 на 1 лист\n"
                         "6. A4 для термопринтера")

# Обработка кнопок выбора формата
@dp.message(lambda message: message.text in {"4 на 1 лист", "8 на 1 лист", "9 на 1 лист", "A4 для термопринтера", "2 на 1 лист", "3 на 1 лист"})
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

        # Сохраняем файл в список
        if not hasattr(state, 'pdf_files'):
            await state.update_data(pdf_files=[])
        
        pdf_files = (await state.get_data()).get("pdf_files", [])
        pdf_files.append(file_path)
        await state.update_data(pdf_files=pdf_files)

        await message.answer("Файл добавлен в очередь. Отправьте еще файлы или нажмите 'Скачать результат'.")

        # Если есть два или больше файлов
        if len(pdf_files) > 1:
            merged_file = merge_pdfs(pdf_files, layout)
            await message.answer_document(FSInputFile(merged_file), reply_markup=result_keyboard)
            cleanup_files(pdf_files + [merged_file])
            await state.update_data(pdf_files=[])  # Очистить очередь после обработки
        else:
            await message.answer("Добавьте еще файлы или нажмите 'Скачать результат'.")

    except Exception as e:
        logging.error(f"Ошибка обработки файла {message.document.file_name}: {e}")
        await message.answer(f"Произошла ошибка при обработке файла: {e}")

# Обработчик команды для скачивания результата
@dp.message(lambda message: message.text == "Скачать результат")
async def download_result(message: Message, state: FSMContext):
    pdf_files = (await state.get_data()).get("pdf_files", [])
    layout = (await state.get_data()).get("layout", "4 на 1 лист")
    if len(pdf_files) >= 2:
        merged_file = merge_pdfs(pdf_files, layout)
        await message.answer_document(FSInputFile(merged_file), reply_markup=result_keyboard)
        cleanup_files(pdf_files + [merged_file])
        await state.update_data(pdf_files=[])  # Очистить очередь
    else:
        await message.answer("Не хватает файлов для объединения. Пожалуйста, отправьте хотя бы два PDF.")

# Обработчик команды для отправки нового файла
@dp.message(lambda message: message.text == "Отправить новый файл")
async def new_file(message: Message):
    await message.answer("Отправьте новый PDF или ZIP файл.", reply_markup=main_keyboard)

# Запуск бота
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())