## Документация:

```markdown
# 📋 Market API - Документация

Документация REST API для платформы "Рынок товар с инвестициями".  
**Версия:** 2.0  
**Базовый URL:** `http://localhost:5000/api`

---

## 📊 Формат ответа

### Успешный ответ:
```json
{
    "success": true,
    "data": { ... }
}
```

### Ошибка:
```json
{
    "success": false,
    "error": "Описание ошибки"
}
```

---

## 🔐 Аутентификация

Для защищенных эндпоинтов требуется JWT токен в заголовке:
```
Authorization: Bearer <access_token>
```

Токен можно получить через:
- `/auth/login` - вход
- `/auth/register` - регистрация
- `/auth/refresh` - обновление токена

---

## 📋 Эндпоинты API

### 1. 🩺 Проверка работоспособности

**GET** `/health`

**Ответ:**
```json
{
    "success": true,
    "status": "healthy",
    "timestamp": "2026-01-09T22:07:08.027927",
    "version": "2.0"
}
```

---

### 2. 👤 Регистрация

**POST** `/auth/register`

**Тело запроса (JSON):**
```json
{
    "login": "username123",
    "mail": "user@example.com",
    "password": "securepassword123"
}
```

**Ответ:**
```json
{
    "success": true,
    "message": "Регистрация успешна",
    "data": {
        "user": {
            "id": "dded37fe-0c12-4605-8b35-92ee53428cef",
            "nickname": "username123",
            "mail": "user@example.com",
            "createdAt": "2026-01-09T22:07:08.027927",
            "balance": 100
        },
        "tokens": {
            "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
            "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
            "token_type": "Bearer"
        }
    }
}
```

---

### 3. 🔑 Вход

**POST** `/auth/login`

**Тело запроса (JSON):**
```json
{
    "login": "username123",
    "password": "securepassword123"
}
```

**Ответ:**
```json
{
    "success": true,
    "message": "Вход выполнен",
    "data": {
        "user": {
            "id": "dded37fe-0c12-4605-8b35-92ee53428cef",
            "nickname": "username123",
            "mail": "user@example.com",
            "createdAt": "2026-01-09T22:07:08.027927",
            "balance": 100
        },
        "tokens": {
            "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
            "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
            "token_type": "Bearer",
            "expires_in": 3600
        }
    }
}
```

---

### 4. 🔄 Обновление токена

**POST** `/auth/refresh`

**Тело запроса (JSON):**
```json
{
    "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

**Ответ:**
```json
{
    "success": true,
    "data": {
        "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
        "token_type": "Bearer",
        "expires_in": 3600
    }
}
```

---

### 5. 👤 Получение профиля

**GET** `/auth/profile`  
**Требуется токен**

**Ответ:**
```json
{
    "success": true,
    "data": {
        "id": "dded37fe-0c12-4605-8b35-92ee53428cef",
        "nickname": "test6",
        "mail": "test6@mail.ru",
        "createdAt": "2026-01-09T22:07:08.027927",
        "balance": 89,
        "products": [
            {
                "id": "85164644-1130-4058-9c6d-a80b78dcf595",
                "title": "tests6product",
                "description": "ffffffffffffffffffff",
                "creator": {
                    "id": "dded37fe-0c12-4605-8b35-92ee53428cef",
                    "nickname": "test6"
                },
                "current_price": 1,
                "next_day_price": 1,
                "photo_url": "/api/images/thumbnail/eac9a16b-6703-4b73-bc55-df6ad74f81ba",
                "portfolio": 10,
                "startup_capital": 10,
                "subscriptions_money": 0,
                "status": "active",
                "created_at": "2026-01-09T22:15:06.239156",
                "price_history": [0, 0, 0, 0, 0, 0],
                "active_subscriptions_count": 0
            }
        ],
        "subscriptions": [
            {
                "id": "ec27a6f5-07e5-45e7-a185-81cb17f6fc95",
                "product_id": "0a0e2f6d-f9ce-4ec0-80c0-9348eec13a32",
                "subscription_price": 1,
                "current_price": 1,
                "status": "active",
                "product": {
                    "id": "0a0e2f6d-f9ce-4ec0-80c0-9348eec13a32",
                    "title": "test1 tovar",
                    "creator": {
                        "id": "b1a49600-8c0b-4038-8aa0-fa04f4f20fe6",
                        "nickname": "test1"
                    },
                    "current_price": 1,
                    "photo_url": "/api/images/thumbnail/8b973eb0-e365-4d9e-a39a-27283fc44dfb",
                    "status": "active",
                    "active_subscriptions_count": 1
                }
            }
        ]
    }
}
```

---

### 6. 🛍️ Получение списка товаров

**GET** `/products`

**Параметры:**
- `page` - номер страницы (по умолчанию: 1)

**Ответы (зависят от роли):**

**Для неавторизованного пользователя:**
```json
{
    "success": true,
    "data": [
        {
            "id": "85164644-1130-4058-9c6d-a80b78dcf595",
            "title": "tests6product",
            "creator": {
                "id": "dded37fe-0c12-4605-8b35-92ee53428cef",
                "nickname": "test6"
            },
            "current_price": 1,
            "photo_url": "/api/images/thumbnail/eac9a16b-6703-4b73-bc55-df6ad74f81ba",
            "status": "active",
            "active_subscriptions_count": 0
        }
    ],
    "pagination": {
        "page": 1,
        "per_page": 14,
        "total": 1,
        "pages": 1
    }
}
```

**Для продавца товара (дополнительные поля):**
```json
{
    "id": "85164644-1130-4058-9c6d-a80b78dcf595",
    "title": "tests6product",
    "creator": { ... },
    "current_price": 1,
    "next_day_price": 1,
    "photo_url": "...",
    "portfolio": 10,
    "startup_capital": 10,
    "subscriptions_money": 0,
    "status": "active",
    "active_subscriptions_count": 0,
    "description": "ffffffffffffffffffff",
    "created_at": "2026-01-09T22:15:06.239156",
    "price_history": [0, 0, 0, 0, 0, 0]
}
```

**Для подписчика (дополнительные поля):**
```json
{
    "id": "85164644-1130-4058-9c6d-a80b78dcf595",
    "title": "tests6product",
    "creator": { ... },
    "current_price": 1,
    "photo_url": "...",
    "status": "active",
    "active_subscriptions_count": 0,
    "description": "ffffffffffffffffffff",
    "created_at": "2026-01-09T22:15:06.239156",
    "price_history": [0, 0, 0, 0, 0, 0],
    "subscription_price": 1
}
```

---

### 7. 🔍 Детальная информация о товаре

**GET** `/products/{product_id}`

**Параметры пути:**
- `product_id` - UUID товара

**Ответ (аналогично списку товаров, зависит от роли):**
```json
{
    "success": true,
    "data": { ... } // Один из форматов выше
}
```

---

### 8. ➕ Создание товара

**POST** `/products`  
**Требуется токен**  
**Content-Type:** `multipart/form-data`

**Поля формы:**
- `title` - название товара (3-100 символов)
- `price` - цена товара (1-10000 AC)
- `description` - описание товара (до 1000 символов, опционально)
- `image` - файл изображения

**Ответ:**
```json
{
    "success": true,
    "message": "Товар успешно создан",
    "data": {
        "id": "85164644-1130-4058-9c6d-a80b78dcf595",
        "title": "tests6product",
        "description": "ffffffffffffffffffff",
        "creator": {
            "id": "dded37fe-0c12-4605-8b35-92ee53428cef",
            "nickname": "test6"
        },
        "current_price": 1,
        "next_day_price": 1,
        "photo_url": "/api/images/thumbnail/eac9a16b-6703-4b73-bc55-df6ad74f81ba",
        "portfolio": 10,
        "startup_capital": 10,
        "subscriptions_money": 0,
        "status": "active",
        "created_at": "2026-01-09T22:15:06.239156",
        "price_history": [0, 0, 0, 0, 0, 0],
        "active_subscriptions_count": 0
    }
}
```

---

### 9. 💰 Изменение цены товара

**PUT** `/products/{product_id}/price`  
**Требуется токен**

**Тело запроса (JSON):**
```json
{
    "new_price": 150
}
```

**Ответ:**
```json
{
    "success": true,
    "message": "Цена изменена. Новая цена установится в 0:00",
    "data": {
        "id": "85164644-1130-4058-9c6d-a80b78dcf595",
        "title": "tests6product",
        "description": "ffffffffffffffffffff",
        "creator": { ... },
        "current_price": 1,
        "next_day_price": 150,
        "photo_url": "...",
        "portfolio": 10,
        "startup_capital": 10,
        "subscriptions_money": 0,
        "status": "active",
        "created_at": "2026-01-09T22:15:06.239156",
        "price_history": [0, 0, 0, 0, 0, 0],
        "active_subscriptions_count": 0
    }
}
```

---

### 10. 👍 Подписка на товар

**POST** `/products/{product_id}/subscribe`  
**Требуется токен**

**Ответ:**
```json
{
    "success": true,
    "subscription": {
        "id": "ec27a6f5-07e5-45e7-a185-81cb17f6fc95",
        "product_id": "0a0e2f6d-f9ce-4ec0-80c0-9348eec13a32",
        "subscription_price": 1,
        "current_price": 1,
        "status": "active",
        "product": {
            "id": "0a0e2f6d-f9ce-4ec0-80c0-9348eec13a32",
            "title": "test1 tovar",
            "creator": {
                "id": "b1a49600-8c0b-4038-8aa0-fa04f4f20fe6",
                "nickname": "test1"
            },
            "current_price": 1,
            "photo_url": "/api/images/thumbnail/8b973eb0-e365-4d9e-a39a-27283fc44dfb",
            "status": "active",
            "active_subscriptions_count": 1
        }
    },
    "message": "Подписка оформлена за 1 AC"
}
```

---

### 11. 👎 Отписка от товара

**POST** `/products/{product_id}/unsubscribe`  
**Требуется токен**

**Ответ (успешная отписка):**
```json
{
    "success": true,
    "message": "Отписка выполнена. Выплачено: 1 AC",
    "payout_amount": 1
}
```

**Ответ (прогорание товара):**
```json
{
    "success": true,
    "message": "Отписка выполнена. Выплачено: 50 AC",
    "payout_amount": 50,
    "warning": "Товар прогорел из-за недостатка средств в портфеле"
}
```

---

### 12. 🗑️ Снятие товара с продажи

**POST** `/products/{product_id}/remove`  
**Требуется токен**

**Ответ (активный товар):**
```json
{
    "success": true,
    "message": "Товар снят с продажи. Получено: 1000 AC",
    "portfolio_transferred": 1000,
    "subscriptions_cancelled": 5,
    "subscription_ids_deleted": ["sub-uuid-1", "sub-uuid-2"],
    "product_status": "burned_hidden"
}
```

**Ответ (прогоревший товар):**
```json
{
    "success": true,
    "message": "Товар скрыт из профиля продавца",
    "portfolio_transferred": 0,
    "product_deleted": false
}
```

---

### 13. 🔎 Поиск товаров

**GET** `/products/search`

**Параметры запроса:**
- `q` - поисковый запрос (обязательно)
- `limit` - лимит результатов (по умолчанию: 20, максимум: 100)
- `min_score` - минимальный порог релевантности (по умолчанию: 0.1)

**Пример:**
```
GET /api/products/search?q=тест&limit=10&min_score=0.3
```

**Ответ:**
```json
{
    "success": true,
    "data": {
        "results": [
            {
                "id": "0a0e2f6d-f9ce-4ec0-80c0-9348eec13a32",
                "title": "test1 tovar",
                "creator": {
                    "id": "b1a49600-8c0b-4038-8aa0-fa04f4f20fe6",
                    "nickname": "test1"
                },
                "current_price": 1,
                "photo_url": "/api/images/thumbnail/8b973eb0-e365-4d9e-a39a-27283fc44dfb",
                "status": "active",
                "active_subscriptions_count": 1,
                "relevance_score": 0.856
            }
        ],
        "metadata": {
            "query": "тест",
            "total_products": 42,
            "total_found": 5,
            "limit": 10,
            "min_score": 0.3,
            "has_more": false
        }
    }
}
```

---

### 14. 🖼️ Получение изображения

**GET** `/images/thumbnail/{file_id}`

**Параметры пути:**
- `file_id` - UUID файла изображения

**Ответ:** Изображение в бинарном формате

**Коды ошибок:**
- `404` - Изображение не найдено

---

### 15. 📋 Получение подписок пользователя

**GET** `/account/subscriptions`  
**Требуется токен**

**Ответ:**
```json
{
    "success": true,
    "data": [
        {
            "id": "ec27a6f5-07e5-45e7-a185-81cb17f6fc95",
            "product_id": "0a0e2f6d-f9ce-4ec0-80c0-9348eec13a32",
            "subscription_price": 1,
            "current_price": 1,
            "status": "active",
            "product": {
                "id": "0a0e2f6d-f9ce-4ec0-80c0-9348eec13a32",
                "title": "test1 tovar",
                "creator": {
                    "id": "b1a49600-8c0b-4038-8aa0-fa04f4f20fe6",
                    "nickname": "test1"
                },
                "current_price": 1,
                "photo_url": "/api/images/thumbnail/8b973eb0-e365-4d9e-a39a-27283fc44dfb",
                "status": "active",
                "active_subscriptions_count": 1
            }
        }
    ]
}
```

---

## 🏗️ Структура данных

### Пользователь (User)
```json
{
    "id": "uuid",
    "nickname": "string",
    "mail": "string",
    "createdAt": "ISO datetime",
    "balance": "integer"
}
```

### Товар (Product) - публичный вид
```json
{
    "id": "uuid",
    "title": "string",
    "creator": {
        "id": "uuid",
        "nickname": "string"
    },
    "current_price": "integer",
    "photo_url": "string",
    "status": "active|burned|burned_hidden",
    "active_subscriptions_count": "integer"
}
```

### Товар (Product) - для продавца (дополнительные поля)
```json
{
    ...,
    "next_day_price": "integer",
    "portfolio": "integer",
    "startup_capital": "integer",
    "subscriptions_money": "integer",
    "description": "string",
    "created_at": "ISO datetime",
    "price_history": [0, 0, 0, 0, 0, 0]
}
```

### Подписка (Subscription)
```json
{
    "id": "uuid",
    "product_id": "uuid",
    "subscription_price": "integer",
    "current_price": "integer",
    "status": "active|cancelled",
    "product": { ... }
}
```

---

## 💰 Экономические правила

### Создание товара
1. Продавец устанавливает цену (1-10000 AC)
2. Стартовый капитал = цена × 10
3. Баланс продавца уменьшается на стартовый капитал
4. Портфель товара = стартовый капитал

### Подписка
1. Пользователь платит текущую цену товара
2. Деньги добавляются в `portfolio` и `subscriptions_money`
3. `active_subscriptions_count` увеличивается на 1

### Отписка
1. Проверка: достаточно ли денег в портфеле для выплаты текущей цены
2. **Достаточно**: пользователь получает текущую цену
3. **Недостаточно**: пользователь получает остаток, товар прогорает

### Статусы товара
- **active** - активный, можно подписываться
- **burned** - прогоревший, показывается продавцу и подписчикам
- **burned_hidden** - скрытый прогоревший, показывается только подписчикам

### Цены
- История хранит 6 последних цен
- Цена обновляется ежедневно в 0:00
- Новая цена на следующий день устанавливается через `/products/{id}/price`

---

## ⚠️ Ошибки и статус-коды

### Общие ошибки:
- `400` - Некорректный запрос
- `401` - Неавторизован (нет/неверный токен)
- `403` - Нет прав доступа
- `404` - Ресурс не найден
- `413` - Файл слишком большой
- `415` - Неподдерживаемый тип данных
- `500` - Внутренняя ошибка сервера

### Бизнес-ошибки:
- "Недостаточно средств"
- "Превышен лимит активных товаров (8)"
- "Нельзя подписаться на свой товар"
- "Цена не может превышать портфель"
- "Товар не найден или неактивен"

---

## 🔧 Настройка и запуск

1. **Установка зависимостей:**
```bash
pip install -r requirements.txt
```

2. **Настройка .env файла:**
```env
FLASK_ENV=development
DATABASE_URL=sqlite:///market.db
JWT_SECRET_KEY=your-secret-key-change-in-production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRES=3600
JWT_REFRESH_TOKEN_EXPIRES=2592000
```

3. **Запуск сервера:**
```bash
python main.py
```

4. **Тестовые данные (опционально):**
```bash
python seed.py
```

---

## 📞 Поддержка

### Типичные проблемы:
1. **"Токен отсутствует"** - добавьте заголовок `Authorization: Bearer <token>`
2. **"Файл слишком большой"** - максимальный размер 16MB
3. **"Недостаточно средств"** - проверьте баланс пользователя
4. **"Превышен лимит товаров"** - максимум 8 активных товаров на продавца

### Отладка:
- Проверьте формат JSON в теле запроса
- Убедитесь, что заголовки правильно установлены
- Проверьте права доступа (только владелец может изменять/удалять товар)
