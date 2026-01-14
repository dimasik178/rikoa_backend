# Market Investment Platform

Платформа для торговли товарами с инвестиционной составляющей. Позволяет создавать товары, подписываться на них и отслеживать изменение цен.

## 📦 Быстрый старт

### 1. Клонирование репозитория
```bash
git clone https://github.com/dimasik178/rikoa_backend.git
cd rikoa_backend
```

### 2. Настройка окружения

Создайте файл `.env` в корне проекта с содержанием:
```env
# Database
DATABASE_URL=sqlite:///market.db

# Flask
FLASK_ENV=production # development or production 

# JWT
JWT_SECRET_KEY=your-secret-key-blazorandreact-jwt
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRES=3600
JWT_REFRESH_TOKEN_EXPIRES=2592000
SECRET_KEY=your-secret-key-blazorandreact-flask
```

### 3. Сборка Docker образа
```bash
sudo docker build -t school-art-market .
```

## 🚀 Запуск контейнера

### Вариант A: Простой запуск
```bash
sudo docker run -d \
  --name art-market \
  -p 5000:5000 \
  -v art-market-uploads:/app/uploads \
  -v art-market-data:/app \
  school-art-market
```

### Вариант B: С монтированием папки с фото
```bash
sudo docker run -d \
  --name art-market \
  -p 5000:5000 \
  -v $(pwd)/photo_examples:/app/photo_examples \
  -v art-market-uploads:/app/uploads \
  -v art-market-data:/app \
  school-art-market
```

### Вариант C: С пробросом `.env` файла
```bash
sudo docker run -d \
  --name art-market \
  -p 5000:5000 \
  -v $(pwd)/.env:/app/.env \
  -v $(pwd)/photo_examples:/app/photo_examples \
  -v art-market-uploads:/app/uploads \
  school-art-market
```

### 5. Проверка работы
Откройте в браузере: `http://localhost:5000/api/health`

Или выполните:
```bash
curl http://localhost:5000/api/health
```

Должен появиться ответ:
```json
{
  "status": "healthy",
  "success": true,
  "timestamp": "2026-01-14T17:15:35.367234+00:00",
  "version": "2.0"
}
```

## 📚 Основные API эндпоинты

- `GET /api/health` - Проверка работы сервера
- `POST /api/auth/register` - Регистрация
- `POST /api/auth/login` - Вход
- `GET /api/products` - Список товаров
- `POST /api/products` - Создать товар (требуется токен)
- `GET /api/products/<id>` - Информация о товаре

## 🛠️ Дополнительные команды

### Просмотр логов
```bash
sudo docker logs art-market
```

### Остановка контейнера
```bash
sudo docker stop art-market
```

### Запуск остановленного контейнера
```bash
sudo docker start art-market
```

### Удаление контейнера
```bash
sudo docker rm art-market
```

## 📁 Структура проекта

```
├── .dockerignore          # Файлы, игнорируемые Docker
├── .env                   # Переменные окружения
├── .gitignore             # Файлы, игнорируемые Git
├── Dockerfile             # Конфигурация Docker
├── README.md              # Документация проекта
├── docs.md                # Детальная документация API
├── requirements.txt       # Зависимости Python
├── supervisord.conf       # Конфигурация supervisord для запуска daily_updater.py и main.py
├── config.py              # Конфигурация приложения
├── daily_updater.py       # Ежедневное обновление цен
├── database.py            # Работа с базой данных
├── jwt_manager.py         # Управление JWT токенами
├── main.py                # Точка входа
├── models.py              # Модели базы данных
├── photo_examples         # Фото для заполнения базы данных
│   ├──1-20.jpg            # Двадцать тестовых фото
├── search_engine.py       # Поисковой движок 
├── seed.py                # Заполнение бд тестовыми данными
├── web_server.py          # Основной сервер - роуты Flask
├── instance/              # Папка для базы данных SQLite
├── marketplace_env/       # Виртуальное окружение (локально)
├── photo_examples/        # Примеры изображений
└── uploads/thumbnails     # Загруженные изображения пользователей
```

## 🔧 Устранение проблем

### 1. Порт уже занят
Измените порт в команде запуска:
```bash
sudo docker run -d -p 8080:5000 --name art-market school-art-market
```

### 2. Ошибка базы данных
Удалите старую базу и перезапустите:
```bash
rm market.db
sudo docker restart art-market
```

### 3. Проблемы с изображениями
Убедитесь, что папки имеют правильные права:
```bash
chmod -R 755 uploads photo_examples
```

## 📞 Поддержка

При возникновении проблем:
1. Проверьте логи: `sudo docker logs art-market`
2. Убедитесь, что порт 5000 свободен
3. Проверьте наличие файла `.env`
4. Пересоберите образ: `sudo docker build -t school-art-market .`

---

**Готово!** Сервер запущен на http://localhost:5000 🚀


**Полезные команды:**
```bash
# Посмотреть логи
sudo docker logs art-market
# Заполнить бд тестовыми данными
sudo docker exec art-market python seed.py
# Обновить цены на платформе, не дожидаясь следующего дня
sudo docker exec art-market python daily_updater.py --run-now
# Войти в контейнер
sudo docker exec -it art-market /bin/bash
# Узнать время в контейнере
sudo docker exec art-market date

# Посмотреть запущенные контейнеры
sudo docker ps
# Посмотреть все контейнеры, включая остановленные
sudo docker ps -a 
# Остановить контейнер
sudo docker stop art-market
# Запустить контейнер
sudo docker start art-market
# Перезапустить
sudo docker restart art-market
# Удалить контейнер
sudo docker rm -f art-market
# Удалить образ
sudo docker rmi school-art-market
```