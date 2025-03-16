# docker/Dockerfile
FROM python:3.9-slim

# Установка необходимых пакетов
RUN apt-get update && apt-get install -y \
    cifs-utils \
    smbclient \
    libsmbclient-dev \
    && rm -rf /var/lib/apt/lists/*

# Создание рабочей директории
WORKDIR /app

# Создание директории для монтирования Samba
RUN mkdir -p /mnt/samba

# Копирование файла с зависимостями
COPY requirements.txt .

# Установка зависимостей Python
RUN pip install --no-cache-dir -r requirements.txt

# Копирование кода приложения
COPY . .

# Открытие порта
EXPOSE 5000

# Команда для запуска приложения
CMD ["python", "run.py"]