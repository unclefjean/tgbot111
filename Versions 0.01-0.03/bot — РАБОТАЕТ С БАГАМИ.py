import os
import logging
from aiogram import Bot, Dispatcher
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, FSInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from PyPDF2 import PdfReader, PdfWriter
import fitz  # PyMuPDF
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

# Установим уровень логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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


def pdf_to_images(pdf_file):
    """Конвертирует PDF в список изображений"""
    doc = fitz.open(pdf_file)
    images = []
    for page_num in range(len(doc)):
        pix = doc[page_num].get_pixmap()
        img_path = f"temp_page_{page_num}.png"
        pix.save(img_path)
        images.append(img_path)
    return images


def arrange_pdfs_side_by_side(pdf_files, rows, cols, output_file):
    """Размещает страницы нескольких PDF файлов на одном листе с сохранением пропорций."""
    page_width, page_height = A4
    cell_width = page_width / cols
    cell_height = page_height / rows

    c = canvas.Canvas(output_file, pagesize=A4)

    img_index = 0
    for pdf_file in pdf_files:
        images = pdf_to_images(pdf_file)  # Конвертируем PDF в изображения
        for img_path in images:
            row = img_index // cols
            col = img_index % cols
            x_pos = col * cell_width
            y_pos = page_height - (row + 1) * cell_height

            # Проверяем пропорции изображения и масштабируем
            img = fitz.Pixmap(img_path)
            img_ratio = img.width / img.height
            cell_ratio = cell_width / cell_height

            if img_ratio > cell_ratio:
                # Изображение шире — масштабируем по ширине
                img_width = cell_width
                img_height = cell_width / img_ratio
            else:
                # Изображение выше — масштабируем по высоте
                img_height = cell_height
                img_width = cell_height * img_ratio

            x_offset = x_pos + (cell_width - img_width) / 2
            y_offset = y_pos + (cell_height - img_height) / 2

            c.drawImage(img_path, x_offset, y_offset, width=img_width, height=img_height)

            img_index += 1
            if img_index % (rows * cols) == 0:
                c.showPage()

        for img_path in images:
            os.remove(img_path)

    c.save()



def merge_pdfs(files, layout='4 на 1 лист'):
    """
    Объединяет несколько PDF файлов в один с расположением страниц в зависимости от выбранного макета.
    """
    layout_map = {
        '4 на 1 лист': (2, 2),
        '8 на 1 лист': (4, 2),
        '9 на 1 лист': (3, 3),
        '2 на 1 лист': (1, 2),  # This should ensure two pages per row
        '3 на 1 лист': (2, 3),
        'A4 для термопринтера': (1, 1)
    }
    rows, cols = layout_map.get(layout, (2, 2))
    output_file = f"merged_{layout.replace(' ', '_')}.pdf"
    arrange_pdfs_side_by_side(files, rows, cols, output_file)
    return output_file


@dp.message(Command("start"))
async def start_handler(message: Message):
    await message.answer("Я помогу объединить PDF. Выберите формат:", reply_markup=main_keyboard)


@dp.message(lambda message: message.text in {"4 на 1 лист", "8 на 1 лист", "9 на 1 лист", "2 на 1 лист", "3 на 1 лист", "A4 для термопринтера"})
async def layout_handler(message: Message, state: FSMContext):
    layout = message.text
    await state.update_data(layout=layout)
    await message.answer(f"Вы выбрали: {layout}. Теперь загрузите PDF файл.")


@dp.message(lambda message: message.document is not None)
async def document_handler(message: Message, state: FSMContext):
    document = message.document
    file_name = document.file_name
    layout = (await state.get_data()).get("layout", "4 на 1 лист")
    os.makedirs("downloads", exist_ok=True)
    file_path = f"downloads/{file_name}"

    await bot.download(document, file_path)
    logger.info(f"Файл {file_name} скачан в {file_path}")

    pdf_files = [file_path, file_path]
    await state.update_data(pdf_files=pdf_files)

    # Генерируем объединённый файл
    merged_file = merge_pdfs(pdf_files, layout)

    # Проверка перед отправкой
    if not os.path.exists(merged_file):
        logger.error(f"Файл {merged_file} не создан!")
        await message.answer("Ошибка при создании файла. Попробуйте ещё раз.")
        return

    # Отправляем объединённый файл
    await message.answer_document(FSInputFile(merged_file), caption="Ваш PDF файл объединён.", reply_markup=result_keyboard)

    cleanup_files([file_path, merged_file])
    await state.finish()

def cleanup_files(files):
    for file in files:
        if os.path.exists(file):
            os.remove(file)
            logger.info(f"Удалён временный файл: {file}")


@dp.message(lambda message: message.text == "Скачать результат")
async def download_result(message: Message, state: FSMContext):
    pdf_files = (await state.get_data()).get("pdf_files", [])
    layout = (await state.get_data()).get("layout", "4 на 1 лист")
    if len(pdf_files) >= 2:
        merged_file = merge_pdfs(pdf_files, layout)
        await message.answer_document(FSInputFile(merged_file), reply_markup=result_keyboard)
        cleanup_files(pdf_files + [merged_file])
        await state.update_data(pdf_files=[])
    else:
        await message.answer("Не хватает файлов для объединения. Отправьте хотя бы два PDF.")


async def main():
    logger.info("Запуск бота...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())