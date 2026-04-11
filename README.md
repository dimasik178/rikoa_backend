# 🛍️ ArtMarket - Маркетплейс с бонусной системой

Платформа для покупки и продажи виртуальных товаров с системой бонусов и антиинфляционными механизмами.

*"Проект создан исключительно в образовательных целях"*

*"Не содержит механизмов реальных финансовых операций"*

*"Все транзакции осуществляются в виртуальных игровых единицах AC (Art Coins)"*

*"Система имитирует маркетплейс для изучения основ экономики и веб-разработки"*

---

## ✨ Особенности версии 4.1.3

- 🎁 **Бонус за регистрацию** - 200 AC при создании аккаунта
- 📅 **Ежедневный бонус** - 50 AC для пользователей с балансом < 500 AC
- 💰 **Комиссия 5%** - защита от инфляции, деньги сгорают при каждой продаже
- 🖼️ **Водяные знаки** - защита изображений для непроданных товаров
- 🏦 **Банкротство** - сброс баланса до 100 AC (1 раз в день)
- 📊 **График баланса** - история изменения баланса за 30 дней
- 🔍 **Умный поиск** - с триграммами и ранжированием
- 💠 **Защита прав обладателя** - при продаже товара, право на владение товаром переходит покупателю
- 🔒 **Защита от дублирования** - одинаковые фото нельзя выставить дважды
---

## ⚡️ Быстрый старт (2 команды)

### 1. Клонируйте и соберите
```bash
git clone https://github.com/dimasik178/rikoa_backend.git
cd rikoa_backend
sudo docker build -t art-market .
```

### 2. Запустите
```bash
sudo docker run -d \
  --name art-market \
  -p 5000:5000 \
  -v "$PWD/instance:/app/instance" \
  -v "$PWD/uploads:/app/uploads" \
  -v "$PWD/photo_examples:/app/photo_examples" \
  -v "$PWD/fonts:/app/fonts" \
  art-market
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
  "timestamp": "2026-03-30T10:00:00.000000",
  "version": "4.1.3"
}
```

---

## 📚 Основные API эндпоинты

### Аутентификация
- `POST /api/auth/register` - Регистрация (+200 AC бонус)
- `POST /api/auth/login` - Вход
- `POST /api/auth/refresh` - Обновление токена
- `GET /api/auth/profile` - Профиль (товары на продаже + купленные)

### Товары
- `GET /api/products` - Список товаров (с водяным знаком)
- `GET /api/products/<id>` - Детали товара
- `POST /api/products` - Создать товар (требуется токен)
- `POST /api/products/<id>/buy` - Купить товар
- `POST /api/products/<id>/remove` - Удалить товар (только непроданный)
- `GET /api/products/search` - Поиск товаров

### Аккаунт
- `GET /api/account/purchases` - История покупок
- `GET /api/account/sales` - История продаж
- `GET /api/account/stats` - Статистика (график баланса)
- `POST /api/account/daily-bonus` - Получить ежедневный бонус
- `POST /api/account/bankruptcy` - Объявить банкротство

### Изображения
- `GET /api/images/original/<id>` - Оригинал (только владельцу)
- `GET /api/images/watermarked/<id>` - С водяным знаком

### Рейтинг
- `GET /api/players/rating` - Рейтинг игроков

### Системные
- `GET /api/health` - Проверка работы сервера

---

## 💰 Экономическая система

### Начальный баланс
- **Стартовый баланс:** 100 AC
- **Бонус за регистрацию:** +200 AC
- **Итого:** 300 AC

### Ежедневный бонус
- **Сумма:** 50 AC
- **Условия:** баланс < 500 AC, 1 раз в день

### Комиссия
- **Процент:** 5% от суммы покупки
- **Округление:** вверх (ceil)
- **Куда идет:** сгорает (удаляется из системы)

**Примеры:**
- Товар за 10 AC → комиссия 1 AC, продавец получает 9 AC
- Товар за 21 AC → комиссия 2 AC, продавец получает 19 AC

### Банкротство
- **Условия:** баланс < 100 AC, нет активных товаров, 1 раз в день
- **Результат:** баланс = 100 AC, счетчик банкротств +1

---

## 🖼️ Защита изображений

### Оригинальные изображения
- Доступны только **владельцу товара** (продавцу или покупателю)
- Требуется JWT токен
- URL: `/api/images/original/{file_id}`

### Изображения с водяным знаком
- Доступны **всем пользователям**
- Только для **непроданных** товаров
- Водяной знак: "DEMO_ART_MARKET" (40% прозрачности)
- URL: `/api/images/watermarked/{file_id}`

---

## 🛠️ Дополнительные команды

### Управление контейнером
```bash
# Просмотр логов
sudo docker logs art-market

# Остановка
sudo docker stop art-market

# Запуск остановленного
sudo docker start art-market

# Перезапуск
sudo docker restart art-market

# Удаление
sudo docker rm -f art-market
```

### Работа с БД
```bash
# Заполнить тестовыми данными (20 пользователей, 100 товаров, 30% продаж)
sudo docker exec art-market python seed.py

# Принудительное обновление (история баланса + сброс банкротства)
sudo docker exec art-market python daily_updater.py --run-now
```

### Отладка
```bash
# Войти в контейнер
sudo docker exec -it art-market /bin/bash

# Узнать время в контейнере
sudo docker exec art-market date

# Просмотр базы данных
sudo docker exec art-market sqlite3 instance/market.db "SELECT * FROM accounts;"
```

### Управление Docker
```bash
# Список контейнеров
sudo docker ps -a

# Список образов
sudo docker images -a

# Удалить образ
sudo docker rmi art-market

# Список томов
sudo docker volume ls

# Удалить том
sudo docker volume rm art-market-data
```

---

## 📁 Структура проекта (v4.1.2)

```
├── .dockerignore              # Файлы, игнорируемые Docker
├── .env                       # Переменные окружения
├── .env.example               # Пример .env файла
├── .gitignore                 # Файлы, игнорируемые Git
├── Dockerfile                 # Конфигурация Docker
├── docker-compose.yml         # Конфигурация Docker-compose
├── docker-entrypoint.sh       # Проверка .env для запуска через Docker
├── README.md                  # Документация проекта
├── docs.md                    # Детальная документация API
├── requirements.txt           # Зависимости Python
├── config.py                  # Конфигурация приложения (бонусы, комиссия)
├── daily_updater.py           # Ежедневное обновление (история баланса)
├── database.py                # Работа с базой данных
├── jwt_manager.py             # Управление JWT токенами
├── main.py                    # Точка входа
├── models.py                  # Модели БД (Account, Product, Purchase)
├── search_engine.py           # Поисковой движок
├── seed.py                    # Заполнение БД тестовыми данными
├── watermark.py               # Наложение водяных знаков
├── web_server.py              # Основной сервер - роуты Flask
├── instance/                  # Папка для базы данных SQLite
├── uploads/                   # Загруженные изображения
│   ├── originals/             # Оригинальные изображения
│   └── watermarked/           # Изображения с водяным знаком
├── photo_examples/            # Примеры изображений для сидинга
└── marketplace_env/           # Виртуальное окружение (локально)
```

---

## 🔧 Устранение проблем

### 1. Порт уже занят
```bash
# Измените порт в команде запуска
sudo docker run -d -p 8080:5000 --name art-market art-market

# Или остановите процесс на порту 5000
sudo lsof -i :5000
sudo kill -9 <PID>
```

### 2. Ошибка базы данных
```bash
# Удалите старую базу и перезапустите
sudo docker exec art-market rm instance/market.db
sudo docker restart art-market
sudo docker exec art-market python seed.py
```

### 3. Проблемы с изображениями
```bash
# Убедитесь, что папки имеют правильные права
sudo docker exec art-market chmod -R 755 uploads
sudo docker exec art-market mkdir -p uploads/originals uploads/watermarked
```

### 4. Бонус не начисляется
- Проверьте баланс (должен быть < 500 AC)
- Проверьте, не получали ли бонус сегодня
- Проверьте дату в контейнере: `sudo docker exec art-market date`

### 5. Изображение не отображается
- Оригинал: убедитесь, что вы владелец товара
- Водяной знак: убедитесь, что товар не продан
- Проверьте наличие файла: `sudo docker exec art-market ls -la uploads/watermarked/`

---

## 📊 Примеры запросов

### Регистрация
```bash
curl -X POST http://localhost:5000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"login":"test","mail":"test@mail.com","password":"123456"}'
```

### Создание товара
```bash
curl -X POST http://localhost:5000/api/products \
  -H "Authorization: Bearer <token>" \
  -F "title=Мой товар" \
  -F "price=100" \
  -F "image=@/path/to/image.jpg"
```

### Покупка товара
```bash
curl -X POST http://localhost:5000/api/products/{id}/buy \
  -H "Authorization: Bearer <token>"
```

### Получение ежедневного бонуса
```bash
curl -X POST http://localhost:5000/api/account/daily-bonus \
  -H "Authorization: Bearer <token>"
```

---

## 📞 Поддержка

### Типичные проблемы:
1. **"Токен отсутствует"** - добавьте заголовок `Authorization: Bearer <token>`
2. **"Файл слишком большой"** - максимальный размер 16MB
3. **"Недостаточно средств"** - проверьте баланс пользователя
4. **"Превышен лимит товаров"** - максимум 8 товаров на продавца
5. **"Изображение не найдено"** - убедитесь, что файл существует и у вас есть права

### Отладка:
1. Проверьте логи: `sudo docker logs art-market`
2. Убедитесь, что порт 5000 свободен
3. Проверьте наличие файла `.env`
4. Пересоберите образ: `sudo docker build -t art-market .`

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
# Посмотреть подробную информацию о томе
sudo docker volume inspect art-market-data # Mountpoint - Путь куда вмонтированна папка
```