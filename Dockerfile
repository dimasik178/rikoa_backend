# Используем официальный образ Python
FROM python:3.11-slim

# Устанавливаем временную зону (Москва)
ENV TZ=Europe/Moscow

# Устанавливаем рабочую директорию
WORKDIR /app

# Устанавливаем необходимые системные пакеты
RUN apt-get update && apt-get install -y \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# Копируем файл зависимостей
COPY requirements.txt .

# Устанавливаем зависимости Python
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь проект
COPY . .

# Создаем необходимые директории
RUN mkdir -p uploads uploads/thumbnails photo_examples instance

# Открываем порт
EXPOSE 5000

# Запуск
CMD ["python", "main.py"]