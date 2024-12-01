from aiogram import Bot, Dispatcher
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, FSInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from PyPDF2 import PdfReader, PdfWriter
from PIL import Image, ImageDraw, ImageFont  # Добавляем ImageDraw и ImageFont
import os

# Токен бота
API_TOKEN = '7814014008:AAHXEAuNW5RP7AUbS2CUdgdNglXJKE82aCw'

# Создание бота и диспетчера
bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Главные кнопки выбора
main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="4 на 1 лист")],
        [KeyboardButton(text="8 на 1 лист"), KeyboardButton(text="9 на 1 лист")],
        [KeyboardButton(text="2 на 1 лист"), KeyboardButton(text="3 на 1 лист")],
        [KeyboardButton(text="A4 для термопринтера")]
    ],
    resize_keyboard=True
)

# Кнопка "Скачать результат"
result_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Скачать результат")],
        [KeyboardButton(text="Отправить новый файл")]
    ],
    resize_keyboard=True
)

# Функция для объединения PDF и расположения страниц на одном листе
from PyPDF2 import PdfReader, PdfWriter
from PyPDF2.generic import RectangleObject

def merge_pdfs(files, layout='4 на 1 лист'):
    layout_map = {
        '4 на 1 лист': (2, 2),
        '8 на 1 лист': (4, 2),
        '9 на 1 лист': (3, 3),
        '2 на 1 лист': (1, 2),
        '3 на 1 лист': (2, 3),
        'A4 для термопринтера': (1, 1)
    }
    
    rows, cols = layout_map.get(layout, (2, 2))
    page_width, page_height = 595, 842  # Размер A4 в пунктах

    writer = PdfWriter()
    canvas_width, canvas_height = page_width * cols, page_height * rows

    # Создаём холст для объединения страниц
    page = writer.add_blank_page(width=canvas_width, height=canvas_height)

    x_offset, y_offset = 0, canvas_height
    for file in files:
        reader = PdfReader(file)
        for pdf_page in reader.pages:
            # Размер текущей страницы
            pdf_page_width = pdf_page.mediabox.width
            pdf_page_height = pdf_page.mediabox.height
            
            # Добавляем страницу на холст
            page.merge_page(pdf_page)

            x_offset += pdf_page_width
            if x_offset >= canvas_width:  # Следующая строка
                x_offset = 0
                y_offset -= pdf_page_height
                if y_offset < 0:
                    break

    output_file = f"merged_{layout.replace(' ', '_')}.pdf"
    with open(output_file, "wb") as f:
        writer.write(f)

    return output_file

# Обработка команды /start
@dp.message(Command("start"))
async def start_handler(message: Message):
    await message.answer("Я помогу объединить PDF. Выберите формат:", reply_markup=main_keyboard)

# Обработка кнопок выбора формата
@dp.message(lambda message: message.text in {"4 на 1 лист", "8 на 1 лист", "9 на 1 лист", "2 на 1 лист", "3 на 1 лист", "A4 для термопринтера"})
async def layout_handler(message: Message, state: FSMContext):
    await state.update_data(layout=message.text)
    await message.answer(f"Вы выбрали: {message.text}. Теперь загрузите PDF файл.")

# Обработка загруженных документов
@dp.message(lambda message: message.document is not None)
async def document_handler(message: Message, state: FSMContext):
    document = message.document
    file_name = document.file_name
    layout = (await state.get_data()).get("layout", "4 на 1 лист")
    file_path = f"downloads/{file_name}"
    os.makedirs("downloads", exist_ok=True)

    # Скачиваем файл
    await bot.download(document, file_path)
    await message.answer(f"Файл {file_name} загружен. Начинаю обработку...")

    # Добавляем файл в очередь
    pdf_files = (await state.get_data()).get("pdf_files", [])
    pdf_files.append(file_path)
    await state.update_data(pdf_files=pdf_files)

    # Проверка на достаточное количество файлов
    if len(pdf_files) >= 2:
        # Объединяем PDF
        merged_file = merge_pdfs(pdf_files, layout)
        await message.answer_document(FSInputFile(merged_file), reply_markup=result_keyboard)
        cleanup_files(pdf_files + [merged_file])
        await state.update_data(pdf_files=[])  # Очистить очередь
        await message.answer("Файлы успешно объединены! Нажмите 'Скачать результат', чтобы скачать файл.")
    else:
        await message.answer("Файл добавлен в очередь. Отправьте еще файлы или нажмите 'Скачать результат'.")

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

# Очищаем временные файлы
def cleanup_files(files):
    for file in files:
        if os.path.exists(file):
            os.remove(file)

# Запуск бота
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())