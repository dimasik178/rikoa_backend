## 📋 Market API - Документация (Версия 2.1)

**Базовый URL:** `http://localhost:5000/api`

---

## 📊 Формат ответа

### Успешный ответ (200 OK):
```json
{
    "data": { ... }
}
```

или для списков:
```json
{
    "data": [...],
    "pagination": { ... }
}
```

### Ошибка (400+):
```json
{
    "error": "Описание ошибки"
}
```

---

## 🔐 Аутентификация

Для защищенных эндпоинтов требуется JWT токен в заголовке:
```
Authorization: Bearer <access_token>
```

---

## 📋 Эндпоинты API

### 1. 🩺 Проверка работоспособности
**GET** `/health`

**Ответ:**
```json
{
    "status": "healthy",
    "timestamp": "2026-01-09T22:07:08.027927",
    "version": "2.1"
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

**Ответ (201):**
```json
{
    "user": {
        "id": "dded37fe-0c12-4605-8b35-92ee53428cef",
        "nickname": "username123",
        "mail": "user@example.com",
        "created_at": "2026-01-09T22:07:08.027927",
        "balance": 100,
        "can_declare_bankruptcy": true,
        "bankruptcy_count": 0
    },
    "tokens": {
        "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
        "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
        "token_type": "Bearer"
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

**Ответ (200):**
```json
{
    "user": {
        "id": "dded37fe-0c12-4605-8b35-92ee53428cef",
        "nickname": "username123",
        "mail": "user@example.com",
        "created_at": "2026-01-09T22:07:08.027927",
        "balance": 100,
        "can_declare_bankruptcy": true,
        "bankruptcy_count": 0
    },
    "tokens": {
        "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
        "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
        "token_type": "Bearer",
        "expires_in": 3600
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

**Ответ (200):**
```json
{
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "token_type": "Bearer",
    "expires_in": 3600
}
```

---

### 5. 👤 Профиль пользователя
**GET** `/auth/profile`  
**Требуется токен**  
**Параметр:** `is_active` (по умолчанию: `true`)

**Ответ (200):**
```json
{
    "id": "dded37fe-0c12-4605-8b35-92ee53428cef",
    "nickname": "test6",
    "mail": "test6@mail.ru",
    "created_at": "2026-01-09T22:07:08.027927",
    "balance": 89,
    "can_declare_bankruptcy": true,
    "bankruptcy_count": 0,
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
            "is_active": true,
            "created_at": "2026-01-09T22:15:06.239156",
            "price_history": [0, 0, 0, 0, 0, 0],
            "subscribers_count": 0
        }
    ],
    "subscriptions": [
        {
            "id": "ec27a6f5-07e5-45e7-a185-81cb17f6fc95",
            "product_id": "0a0e2f6d-f9ce-4ec0-80c0-9348eec13a32",
            "subscription_price": 1,
            "current_price": 1,
            "is_active": true,
            "product": {
                "id": "0a0e2f6d-f9ce-4ec0-80c0-9348eec13a32",
                "title": "test1 tovar",
                "creator": {
                    "id": "b1a49600-8c0b-4038-8aa0-fa04f4f20fe6",
                    "nickname": "test1"
                },
                "current_price": 1,
                "photo_url": "/api/images/thumbnail/8b973eb0-e365-4d9e-a39a-27283fc44dfb",
                "subscribers_count": 1
            }
        }
    ]
}
```

---

### 6. 🛍️ Список товаров
**GET** `/products`  
**Параметры:**
- `page` (по умолчанию: 1)
- `is_active` (по умолчанию: `true`)

**Ответ (200) - неавторизованный пользователь:**
```json
{
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
            "subscribers_count": 0
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

**Для продавца/подписчика добавляются поля:**
- `is_active`: true/false
- `description`
- `price_history`
- `created_at`
- `next_day_price`, `portfolio`, `startup_capital`, `subscriptions_money` (только для продавца)
- `subscription_price` (только для подписчика)

---

### 7. 🔍 Детальная информация о товаре
**GET** `/products/{product_id}`

**Ответ (200):**
```json
{
    "creator": {
        "id": "34c61565-9844-4318-8dd9-f3a983ed29d3",
        "nickname": "user_7"
    },
    "current_price": 9,
    "id": "50b9ee48-8437-45cd-be09-5f99a56ec53e",
    "photo_url": "/api/images/thumbnail/4c517751-0061-4033-a161-236665a3744a",
    "is_active": true,
    "title": "Популярный Экземпляр #1",
    "price_history": [1, 1, 1, 1, 1, 4, 7],
    "created_at": "2026-01-09T22:15:06.239156",
    "subscribers_count": 12,
    "description": "Крутое описание крутейшего продукта"
}
```

**Ошибка (400):**
```json
{
    "error": "Товар не найден или неактивен"
}
```

---

### 8. ➕ Создание товара
**POST** `/products`  
**Требуется токен**  
**Content-Type:** `multipart/form-data`

**Поля формы:**
- `title` (3-100 символов)
- `price` (1-10000 AC)
- `description` (до 1000 символов, опционально)
- `image` (файл изображения)

**Ответ (201):**
```json
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
    "is_active": true,
    "created_at": "2026-01-09T22:15:06.239156",
    "price_history": [0, 0, 0, 0, 0, 0],
    "subscribers_count": 0
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

**Ответ (200):**
```json
{
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
    "is_active": true,
    "created_at": "2026-01-09T22:15:06.239156",
    "price_history": [0, 0, 0, 0, 0, 0],
    "subscribers_count": 0
}
```

---

### 10. 👍 Подписка на товар
**POST** `/products/{product_id}/subscribe`  
**Требуется токен**

**Ответ (200):**
```json
{
    "subscription": {
        "id": "ec27a6f5-07e5-45e7-a185-81cb17f6fc95",
        "product_id": "0a0e2f6d-f9ce-4ec0-80c0-9348eec13a32",
        "subscription_price": 1,
        "current_price": 1,
        "is_active": true,
        "product": {
            "id": "0a0e2f6d-f9ce-4ec0-80c0-9348eec13a32",
            "title": "test1 tovar",
            "creator": {
                "id": "b1a49600-8c0b-4038-8aa0-fa04f4f20fe6",
                "nickname": "test1"
            },
            "current_price": 1,
            "photo_url": "/api/images/thumbnail/8b973eb0-e365-4d9e-a39a-27283fc44dfb",
            "subscribers_count": 1
        }
    },
    "message": "Подписка оформлена за 1 AC"
}
```

---

### 11. 👎 Отписка от товара
**POST** `/products/{product_id}/unsubscribe`  
**Требуется токен**

**Ответ (200):**
```json
{
    "message": "Отписка выполнена. Выплачено: 1 AC",
    "payout_amount": 1
}
```

**При прогорании товара:**
```json
{
    "message": "Отписка выполнена. Выплачено: 50 AC",
    "payout_amount": 50,
    "warning": "Товар прогорел из-за недостатка средств в портфеле"
}
```

---

### 12. 🗑️ Снятие товара с продажи
**POST** `/products/{product_id}/remove`  
**Требуется токен**

**Ответ (200):**
```json
{
    "message": "Товар снят с продажи. Получено: 1000 AC",
    "portfolio_transferred": 1000,
    "subscriptions_cancelled": 5,
    "subscription_ids_deleted": ["sub-uuid-1", "sub-uuid-2"],
    "product_is_active": false
}
```

---

### 13. 🔎 Поиск товаров
**GET** `/products/search`  
**Параметры:**
- `q` - поисковый запрос (обязательно)
- `page` (по умолчанию: 1)
- `min_score` (по умолчанию: 0.1)

**Ответ (200):**
```json
{
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
            "subscribers_count": 1,
            "relevance_score": 0.856
        }
    ],
    "pagination": {
        "page": 1,
        "per_page": 14,
        "total": 5,
        "pages": 1
    }
}
```

---

### 14. 🖼️ Получение изображения
**GET** `/images/thumbnail/{file_id}`

**Ответ:** Изображение в бинарном формате

**Ошибка (404):**
```json
{
    "error": "Изображение не найдено"
}
```

---

### 15. 📋 Подписки пользователя
**GET** `/account/subscriptions`  
**Требуется токен**  
**Параметр:** `is_active` (по умолчанию: `true`)

**Ответ (200):**
```json
{
    "data": [
        {
            "id": "ec27a6f5-07e5-45e7-a185-81cb17f6fc95",
            "product_id": "0a0e2f6d-f9ce-4ec0-80c0-9348eec13a32",
            "subscription_price": 1,
            "current_price": 1,
            "is_active": true,
            "product": {
                "id": "0a0e2f6d-f9ce-4ec0-80c0-9348eec13a32",
                "title": "test1 tovar",
                "creator": {
                    "id": "b1a49600-8c0b-4038-8aa0-fa04f4f20fe6",
                    "nickname": "test1"
                },
                "current_price": 1,
                "photo_url": "/api/images/thumbnail/8b973eb0-e365-4d9e-a39a-27283fc44dfb",
                "subscribers_count": 1
            }
        }
    ]
}
```

---

### 16. 🏦 Объявление банкротства
**POST** `/account/bankruptcy`  
**Требуется токен**

**Ответ (200):**
```json
{
    "message": "💸 Банкротство объявлено! Баланс изменён: 50 → 100 AC",
    "old_balance": 50,
    "new_balance": 100,
    "bankruptcy_count": 1,
    "last_bankruptcy": "2024-01-17T14:30:00.000000",
    "can_declare_bankruptcy": false
}
```

---

### 17. 🏆 Рейтинг игроков
**GET** `/players/rating`  
**Параметры:**
- `page` (по умолчанию: 1)
- `per_page` (по умолчанию: 20, минимум: 1, максимум: 100)

**Ответ (200):**
```json
{
    "players": [
        {
            "id": "dded37fe-0c12-4605-8b35-92ee53428cef",
            "nickname": "username123",
            "balance": 1500,
            "bankruptcy_count": 0,
            "created_at": "2026-01-09T22:07:08.027927"
        }
    ],
    "pagination": {
        "page": 1,
        "per_page": 20,
        "total": 42,
        "pages": 3
    }
}
```

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
- "Нельзя объявить банкротство при балансе ≥ 100 AC"
- "Нельзя объявить банкротство с активными товарами"
- "Нельзя объявить банкротство с активными подписками"
- "Банкротство можно объявлять только 1 раз до следующего обновления цен"

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
