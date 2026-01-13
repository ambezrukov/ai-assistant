FROM python:3.11-slim

# Метаданные
LABEL maintainer="AI Assistant"
LABEL description="Personal AI Assistant with Claude, Whisper, and Google integrations"

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    git \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Создание рабочей директории
WORKDIR /app

# Копирование requirements
COPY requirements.txt .

# Установка Python зависимостей
RUN pip install --no-cache-dir -r requirements.txt

# Копирование приложения
COPY . .

# Создание необходимых директорий
RUN mkdir -p /app/data /app/logs /app/credentials

# Переменные окружения
ENV PYTHONUNBUFFERED=1

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/api/v1/health')"

# Запуск приложения
CMD ["python", "main.py"]
