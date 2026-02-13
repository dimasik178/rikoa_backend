# Market Investment Platform
Платформа для торговли товарами с инвестиционной составляющей. Позволяет создавать товары, подписываться на них и отслеживать изменение цен.

"Проект создан исключительно в образовательных целях"

"Не содержит механизмов реальных финансовых операций"

"Все транзакции осуществляются в виртуальных игровых единицах"

"Система имитирует рыночные механизмы для изучения основ экономики"

## ⚡️ Быстрый старт (2 команды)

### 1. Клонируйте и соберите
```bash
git clone https://github.com/dimasik178/rikoa_backend.git
cd rikoa_backend
sudo docker build -t school-art-market .
```

### 2. Запустите
```bash
sudo docker run -d \
  --name art-market \
  -p 5000:5000 \
  -v art-market-uploads:/app/uploads \
  -v art-market-data:/app \
  school-art-market
```

### Проверка работы
Откройте в браузере: `http://localhost:5000/api/health`

Или выполните:
```bash
curl http://localhost:5000/api/health
```

Должен появиться ответ:
```json
{
  "status": "healthy",
  "timestamp": "2026-02-13T10:00:00.000000+00:00",
  "version": "3.2"
}
```

## 📚 Основные API эндпоинты

- `GET /api/health` - Проверка работы сервера
- `POST /api/auth/register` - Регистрация
- `POST /api/auth/login` - Вход
- `GET /api/products` - Список товаров с пагинацией
- `GET /api/auth/profile` - Профиль пользователя (требуется токен)
- `GET /api/products/search` - Поиск товаров с пагинацией
- `POST /api/products` - Создать товар (требуется токен)
- `GET /api/products/<id>` - Информация о товаре
- `POST /api/account/bankruptcy` - Объявить банкротство (требуется токен)
- `GET /api/players/rating` - Рейтинг игроков

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
# Посмотреть созданные образы (все: "-a")
docker images -a
# Удалить образ
sudo docker rmi school-art-market
# Посмотреть тома (к ним можно монтировать контейнеры)
sudo docker volume ls
# Удалить том
sudo docker volume rm art-market-data
```