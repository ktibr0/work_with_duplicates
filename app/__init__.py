# app/__init__.py
from flask import Flask
import logging
import os

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Создание экземпляра приложения Flask
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY') or 'dev-secret-key'

# Импорт маршрутов
from app import routes

# run.py
from app import app

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)