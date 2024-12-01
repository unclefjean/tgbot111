import os
import uuid
import logging
from aiogram import Bot, Dispatcher
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, FSInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

# Логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Токен
API_TOKEN = '7814014008:AAHXEAuNW5RP7AUbS2CUdgdNglXJKE82aCw'

# Бот и диспетчер
bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Главные кнопки
main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="4 на 1 лист")],
        [KeyboardButton(text="8 на 1 лист"), KeyboardButton(text="9 на 1 лист")],
        [KeyboardButton(text="2 на 1 лист"), KeyboardButton(text="3 на 1 лист")],
        [KeyboardButton(text="A4 для термопринтера")]
    ],
    resize_keyboard=True
)

# Очистка временных файлов
def cleanup_files(files):
    for file in files:
        if os.path.exists(file):
            os.remove(file)
            logger.info(f"Удалён файл: {file}")


# Генерация PDF с наложением страниц
def arrange_pages(pdf_files, rows, cols, output_file):
    page_width, page_height = A4
    padding = 10  # Отступы
    cell_width = (page_width - (cols + 1) * padding) / cols
    cell_height = (page_height - (rows + 1) * padding) / rows

    pdf_writer = PdfWriter()
    
    for pdf_file in pdf_files:
        pdf_reader = PdfReader(pdf_file)
        for page in pdf_reader.pages:
            # Масштабируем каждую страницу
            page.scale_to(cell_width, cell_height)
            pdf_writer.add_page(page)

    with open(output_file, "wb") as f:
        pdf_writer.write(f)


def merge_pdfs(files, layout):
    """
    Объединяет несколько PDF файлов в зависимости от выбранного макета.
    """
    layout_map = {
        "4 на 1 лист": (2, 2),
        "8 на 1 лист": (4, 2),
        "9 на 1 лист": (3, 3),
        "2 на 1 лист": (1, 2),
        "3 на 1 лист": (2, 3),
        "A4 для термопринтера": (1, 1)
    }
    rows, cols = layout_map.get(layout, (2, 2))
    output_file = f"merged_{layout.replace(' ', '_')}.pdf"

    arrange_pages(files, rows, cols, output_file)
    return output_file


@dp.message(Command("start"))
async def start_handler(message: Message):
    await message.answer("Привет! Я помогу объединить PDF файлы. Выберите формат:", reply_markup=main_keyboard)


@dp.message(lambda message: message.text in {
    "4 на 1 лист", "8 на 1 лист", "9 на 1 лист", "2 на 1 лист", "3 на 1 лист", "A4 для термопринтера"
})
async def layout_handler(message: Message, state: FSMContext):
    layout = message.text
    await state.update_data(layout=layout, pdf_files=[])
    await message.answer(f"Вы выбрали: {layout}. Теперь загрузите PDF файлы.")


@dp.message(lambda message: message.document is not None)
async def document_handler(message: Message, state: FSMContext):
    document = message.document
    state_data = await state.get_data()
    layout = state_data.get("layout")
    pdf_files = state_data.get("pdf_files", [])
    
    os.makedirs("downloads", exist_ok=True)
    
    # Уникальное имя файла (для одинаковых имён)
    unique_filename = f"{uuid.uuid4()}_{document.file_name}"
    file_path = f"downloads/{unique_filename}"

    await bot.download(document, file_path)
    logger.info(f"Файл {document.file_name} скачан как {unique_filename}.")

    pdf_files.append(file_path)
    await state.update_data(pdf_files=pdf_files)

    # Проверяем, нужно ли запрашивать ещё файлы
    files_needed = 2 if layout == "2 на 1 лист" else len(pdf_files)
    if len(pdf_files) >= files_needed:
        merged_file = merge_pdfs(pdf_files, layout)
        await message.answer_document(FSInputFile(merged_file), caption="Ваш файл объединён.")
        cleanup_files(pdf_files + [merged_file])
        await state.finish()
    else:
        await message.answer(f"Вы отправили {len(pdf_files)} файл(ов). Отправьте ещё {files_needed - len(pdf_files)}.")


async def main():
    logger.info("Запуск бота...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())