# Market Investment Platform

Платформа для торговли товарами с инвестиционной составляющей. Позволяет создавать товары, подписываться на них и отслеживать изменение цен.

## 📦 Быстрый старт

### 1. Клонирование репозитория
```bash
git clone https://github.com/dimasik178/rikoa_backend.git
cd rikoa_backend-masterы
```

### 2. Настройка окружения

Создайте файл `.env` в корне проекта с содержанием:
```env
FLASK_ENV=production
DATABASE_URL=sqlite:///market.db
JWT_SECRET_KEY=ваш-секретный-ключ-для-jwt
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRES=3600
JWT_REFRESH_TOKEN_EXPIRES=2592000
SECRET_KEY=ваш-секретный-ключ-для-flask
```

### 3. Сборка Docker образа
```bash
docker build -t marketplace-app .
```

### 4. Запуск контейнера
```bash
docker run -d \
  -p 5000:5000 \
  --name marketplace \
  marketplace-app
```

### 5. Проверка работы
Откройте в браузере: `http://localhost:5000/api/health`

Должен появиться ответ:
```json
{"success": true, "status": "healthy"}
```

## 🚀 Запуск с сохранением данных

Для сохранения загруженных изображений и базы данных между перезапусками:

```bash
docker run -d \
  -p 5000:5000 \
  -v ./uploads:/app/uploads \
  -v ./photo_examples:/app/photo_examples \
  -v ./market.db:/app/market.db \
  --name marketplace \
  marketplace-app
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
docker logs marketplace
```

### Остановка контейнера
```bash
docker stop marketplace
```

### Запуск остановленного контейнера
```bash
docker start marketplace
```

### Удаление контейнера
```bash
docker rm marketplace
```

## 📁 Структура проекта

```
├── .dockerignore          # Файлы, игнорируемые Docker
├── .env                   # Переменные окружения
├── .gitignore             # Файлы, игнорируемые Git
├── Dockerfile             # Конфигурация Docker
├── README.md              # Документация проекта
├── requirements.txt       # Зависимости Python
├── config.py              # Конфигурация приложения
├── daily_updater.py       # Ежедневное обновление цен
├── database.py            # Работа с базой данных
├── docs.md                # Детальная документация API
├── jwt_manager.py         # Управление JWT токенами
├── main.py                # Точка входа
├── models.py              # Модели базы данных
├── search_engine.py       # Поисковый движок
├── seed.py                # Заполнение тестовыми данными
├── web_server.py          # Основной сервер
├── instance/              # Папка для базы данных SQLite
├── marketplace_env/       # Виртуальное окружение (локально)
├── photo_examples/        # Примеры изображений
└── uploads/thumbnails     # Загруженные изображения
```

## 🔧 Устранение проблем

### 1. Порт уже занят
Измените порт в команде запуска:
```bash
docker run -d -p 8080:5000 --name marketplace marketplace-app
```

### 2. Ошибка базы данных
Удалите старую базу и перезапустите:
```bash
rm market.db
docker restart marketplace
```

### 3. Проблемы с изображениями
Убедитесь, что папки имеют правильные права:
```bash
chmod -R 755 uploads photo_examples
```

## 📞 Поддержка

При возникновении проблем:
1. Проверьте логи: `docker logs marketplace`
2. Убедитесь, что порт 5000 свободен
3. Проверьте наличие файла `.env`
4. Пересоберите образ: `docker build -t marketplace-app .`

---

**Готово!** Сервер запущен на http://localhost:5000 🚀