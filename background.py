from flask import Flask
from threading import Thread
import time
import requests
import os

app = Flask(__name__)

@app.route('/')
def home():
    return "I'm alive"

def run():
    # Получаем порт из окружения Render, если его нет — ставим 80 по умолчанию
    port = os.environ.get('PORT', 80)
    app.run(host='0.0.0.0', port=port)  # Flask будет слушать на всех интерфейсах

def ping_self():
    while True:
        try:
            # Замените на ваш актуальный URL на платформе Render
            requests.get("https://telegrambot1-wnh7.onrender.com/")
            print("Self-ping successful")
        except Exception as e:
            print(f"Self-ping failed: {e}")
        time.sleep(240)  # Пинг каждые 4 минуты

def keep_alive():
    t1 = Thread(target=run)
    t2 = Thread(target=ping_self)
    t1.start()
    t2.start()

# Важно, чтобы эта функция запускалась при старте
if __name__ == "__main__":
    keep_alive()
