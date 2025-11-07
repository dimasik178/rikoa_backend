# ArtMarket API Documentation v2.0

## Базовый URL
```
http://localhost:5000/api
```

## 🆕 Основные изменения v2.0

### ✅ **Новая функциональность:**
- Загрузка изображений через `multipart/form-data`
- Поддержка форматов: PNG, JPG, JPEG, GIF, WebP
- Автоматическое создание превью (400x400px)
- Оптимизация изображений для экономии трафика
- Убраны `message` поля при успешных ответах

### 🔄 **Устаревшее:**
- JSON метод с `photoUrl` больше не поддерживается
- Все загрузки изображений теперь через form-data

---

## 📋 Схемы данных

### Account (Пользователь)
```json
{
  "id": "string",
  "nickname": "string", 
  "mail": "string",
  "createdAt": "datetime",
  "bayed": "Product[]",
  "posted": "Product[]"
}
```

### Product (Арт)
```json
{
  "id": "string",
  "photoUrl": "string",
  "originalPhotoUrl": "string",
  "title": "string",
  "price": "int",
  "description": "string",
  "updatedAt": "datetime",
  "creator": "Account"
}
```

### Product with Buyers (Арт с покупателями)
```json
{
  "id": "string",
  "photoUrl": "string",
  "originalPhotoUrl": "string", 
  "title": "string",
  "price": "int",
  "description": "string",
  "updatedAt": "datetime",
  "creator": "Account",
  "buyers_count": "int",
  "buyers": "Account[]"
}
```

---

## 🔐 Аутентификация

### 1. Регистрация пользователя
[[Регистрация пользователя]]
**POST** `/register`

**Content-Type:** `application/json`

**Тело запроса:**
```json
{
  "nickname": "artlover",
  "mail": "artlover@example.com",
  "password": "securepassword123"
}
```

**Успешный ответ (201):**
```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "nickname": "artlover",
  "mail": "artlover@example.com",
  "createdAt": "2024-01-15T10:30:00.000000",
  "bayed": [],
  "posted": []
}
```

**Ошибки:**
- `400` - Missing required fields
- `400` - Account with this nickname or mail already exists

---

### 2. Вход в систему
[[Вход пользоватя]]
**POST** `/login`

**Content-Type:** `application/json`

**Тело запроса:**
```json
{
  "nickname": "user1",
  "password": "password"
}
```

**Успешный ответ (200):**
```json
{     
  "bayed": [],
  "createdAt": "2025-10-26T18:10:58.550639",
  "id": "4720f657-b4cc-4491-a1d2-a247dcb4a567",
  "mail": "user1@example.com",
  "nickname": "user1",
  "posted": [
    {
      "description": "This is my beautiful artwork",
      "id": "deda462d-1d76-4779-b6c2-fd46be016ba0",
      "originalPhotoUrl": "http://localhost:5000/api/images/original/b33f6ff4-f983-44fc-9a73-e88c49118d6a",
      "photoUrl": "http://localhost:5000/api/images/thumbnail/b33f6ff4-f983-44fc-9a73-e88c49118d6a",
      "price": 500,
      "title": "My Amazing Art",
      "updatedAt": "2025-11-05T14:51:32.353459"
    }
  ]
}
```

**Ошибки:**
- `400` - Missing nickname or password
- `401` - Invalid credentials

---

## 🎨 Работа с артами

### 3. Получить список артов с пагинацией
[[Получить список артов с пагинацией]]
**GET** `/api/products?page=1`

**Параметры:**
- `page` - номер страницы (по умолчанию: 1)
- `per_page` - элементов на странице (по умолчанию: 12)

**Успешный ответ (200):**
```json
{
  "products": [
    {
      "id": "p1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "photoUrl": "http://localhost:5000/api/images/thumbnails/file-uuid_thumbnail.jpg",
      "originalPhotoUrl": "http://localhost:5000/api/images/file-uuid_original.jpg",
      "title": "Sunset Mountains",
      "price": 150,
      "description": "Beautiful mountain landscape",
      "updatedAt": "2024-01-15T11:00:00.000000",
      "creator": {
        "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "nickname": "artlover",
        "mail": "artlover@example.com",
        "createdAt": "2024-01-15T10:30:00.000000"
      }
    }
  ],
  "total": 45,
  "pages": 4,
  "current_page": 1
}
```

---

### 4. 🆕 Создать новый арт (form-data)

[[Создать новый арт (form-data)]]
**POST** `/products`

**Content-Type:** `multipart/form-data`

**Form Data:**
| Поле               | Тип | Обязательное | Описание                                                               |
|-----------------|-----|------------------|-------------------------------------------------------|
| `image`             | file | ✅                     | Изображение арта (PNG, JPG, JPEG, GIF, WebP) |
| `title`             | text | ✅                    | Название арта                                                      |
| `price`             | text | ✅                    | Цена в AC (целое число)                                     |
| `creator_id`   | text | ✅                    | ID пользователя-создателя                                  |
| `description` | text | ❌                    | Описание арта                                                      |

**Ограничения:**
- Максимальный размер файла: 15MB
- Поддерживаемые форматы: PNG, JPG, JPEG, GIF, WebP
- Автоматически создается превью 400x400px

**Успешный ответ (201):**
```json
{
  "id": "p1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "photoUrl": "http://localhost:5000/api/images/thumbnails/file-uuid_thumbnail.jpg",
  "originalPhotoUrl": "http://localhost:5000/api/images/file-uuid_original.jpg",
  "title": "Beautiful Art",
  "price": 150,
  "description": "Amazing artwork",
  "updatedAt": "2024-01-15T10:30:00.000000",
  "creator": {
    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "nickname": "artlover",
    "mail": "artlover@example.com",
    "createdAt": "2024-01-15T10:30:00.000000"
  }
}
```

**Ошибки:**
- `400` - Missing required fields
- `400` - No image file provided
- `400` - Invalid file type
- `400` - File too large (max 15MB)
- `404` - Creator not found

---

### 5. Получить информацию о конкретном арте
**GET** `/products/{product_id}`

**Пример:**
```
GET /products/p1b2c3d4-e5f6-7890-abcd-ef1234567890
```

**Успешный ответ (200):**
```json
{
  "product": {
    "id": "p1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "photoUrl": "http://localhost:5000/api/images/thumbnails/file-uuid_thumbnail.jpg",
    "originalPhotoUrl": "http://localhost:5000/api/images/file-uuid_original.jpg",
    "title": "Sunset Mountains",
    "price": 150,
    "description": "Beautiful mountain landscape",
    "updatedAt": "2024-01-15T11:00:00.000000",
    "creator": {
      "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "nickname": "artlover",
      "mail": "artlover@example.com",
      "createdAt": "2024-01-15T10:30:00.000000"
    },
    "buyers_count": 3,
    "buyers": [
      {
        "id": "b1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "nickname": "buyer1",
        "mail": "buyer1@example.com",
        "createdAt": "2024-01-14T09:00:00.000000"
      }
    ]
  }
}
```

---

### 6. Обновить описание арта
**PUT** `/products/{product_id}`

**Content-Type:** `application/json`

**Тело запроса:**
```json
{
  "description": "Updated description with more details"
}
```

**Успешный ответ (200):**
```json
{
  "id": "p1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "photoUrl": "http://localhost:5000/api/images/thumbnails/file-uuid_thumbnail.jpg",
  "originalPhotoUrl": "http://localhost:5000/api/images/file-uuid_original.jpg",
  "title": "Sunset Mountains",
  "price": 150,
  "description": "Updated description with more details",
  "updatedAt": "2024-01-15T12:30:00.000000",
  "creator": {
    "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "nickname": "artlover",
    "mail": "artlover@example.com",
    "createdAt": "2024-01-15T10:30:00.000000"
  }
}
```

---

## 💰 Покупки

### 7. Купить арт (подписаться)
**POST** `/products/{product_id}/purchase`

**Content-Type:** `application/json`

**Тело запроса:**
```json
{
  "account_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

**Успешный ответ (201):**
```json
{
  "id": "pur1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "account_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "product_id": "p1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "purchased_at": "2024-01-15T13:00:00.000000"
}
```

---

### 8. Получить список покупателей арта
**GET** `/products/{product_id}/buyers`

**Успешный ответ (200):**
```json
{
  "buyers": [
    {
      "id": "b1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "nickname": "artcollector",
      "mail": "collector@example.com",
      "createdAt": "2024-01-14T09:00:00.000000"
    }
  ]
}
```

---

## 👤 Профили пользователей

### 9. Получить информацию об аккаунте
[[Получить информацию об аккаунте]]
**GET** `/accounts/{account_id}`

**Успешный ответ (200):**
```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "nickname": "artlover",
  "mail": "artlover@example.com",
  "createdAt": "2024-01-15T10:30:00.000000",
  "bayed": [
    {
      "id": "p2b2c3d4-e5f6-7890-abcd-ef1234567890",
      "photoUrl": "http://localhost:5000/api/images/thumbnails/file2-uuid_thumbnail.jpg",
      "originalPhotoUrl": "http://localhost:5000/api/images/file2-uuid_original.jpg",
      "title": "Ocean Waves",
      "price": 200,
      "description": "Calming ocean scene",
      "updatedAt": "2024-01-14T15:30:00.000000"
    }
  ],
  "posted": [
    {
      "id": "p1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "photoUrl": "http://localhost:5000/api/images/thumbnails/file1-uuid_thumbnail.jpg",
      "originalPhotoUrl": "http://localhost:5000/api/images/file1-uuid_original.jpg",
      "title": "Sunset Mountains",
      "price": 150,
      "description": "Beautiful mountain landscape",
      "updatedAt": "2024-01-15T11:00:00.000000"
    }
  ]
}
```

---

## 🔍 Поиск

### 10. Поиск артов
**GET** `/search?q={query}`

**Пример:**
```
GET /search?q=mountains
```

**Успешный ответ (200):**
```json
{
  "products": [
    {
      "id": "p1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "photoUrl": "http://localhost:5000/api/images/thumbnails/file-uuid_thumbnail.jpg",
      "originalPhotoUrl": "http://localhost:5000/api/images/file-uuid_original.jpg",
      "title": "Sunset Mountains",
      "price": 150,
      "description": "Beautiful mountain landscape with sunset",
      "updatedAt": "2024-01-15T11:00:00.000000",
      "creator": {
        "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "nickname": "artlover",
        "mail": "artlover@example.com",
        "createdAt": "2024-01-15T10:30:00.000000"
      }
    }
  ]
}
```

---

## 🖼️ Работа с изображениями

### 11. Получить превью изображения
**GET** `/images/thumbnails/{filename}`

**Пример:**
```
GET /images/thumbnails/e7d13985-8136-4171-89db-5e464816b4ea_thumbnail.jpg
```

**Ответ:** Бинарные данные изображения (JPEG, 400x400px)

### 12. Получить оригинальное изображение
**GET** `/images/{filename}`

**Пример:**
```
GET /images/e7d13985-8136-4171-89db-5e464816b4ea_original.jpg
```

**Ответ:** Бинарные данные оригинального изображения

---

## 🩺 Системные эндпоинты

### 13. Проверка здоровья API
**GET** `/health`

**Успешный ответ (200):**
```json
{
  "status": "healthy",
  "message": "ArtMarket API is running"
}
```

---

## 📝 Примеры использования

### cURL - Создание арта:
```bash
curl -X POST http://localhost:5000/api/products \
  -F "image=@/path/to/your/image.jpg" \
  -F "title=My Amazing Art" \
  -F "price=200" \
  -F "creator_id=user-uuid-here" \
  -F "description=This is my beautiful artwork"
```

### Python - Создание арта:
```python
import requests

url = "http://localhost:5000/api/products"

with open('image.jpg', 'rb') as f:
    files = {'image': f}
    data = {
        'title': 'My Amazing Art',
        'price': '200',
        'creator_id': 'user-uuid-here',
        'description': 'This is my beautiful artwork'
    }
    response = requests.post(url, files=files, data=data)
    print(response.json())
```

### JavaScript - Создание арта:
```javascript
const formData = new FormData();
formData.append('image', fileInput.files[0]);
formData.append('title', 'My Amazing Art');
formData.append('price', '200');
formData.append('creator_id', 'user-uuid-here');
formData.append('description', 'This is my beautiful artwork');

fetch('http://localhost:5000/api/products', {
    method: 'POST',
    body: formData
})
.then(response => response.json())
.then(data => console.log(data));
```

---

## ⚠️ Обработка ошибок

### Формат ошибки:
```json
{
  "error": "Error description"
}
```

### Коды ошибок:
- `400` - Bad Request (неверные параметры запроса)
- `401` - Unauthorized (неверные учетные данные)
- `404` - Not Found (ресурс не найден)
- `413` - Payload Too Large (файл слишком большой)
- `415` - Unsupported Media Type (неверный Content-Type)
- `500` - Internal Server Error (внутренняя ошибка сервера)

---

## 🔧 Postman настройки

### Environment Variables:
- `base_url`: `http://localhost:5000/api`
- `user_id`: (автоматически заполнится после регистрации)
- `product_id`: (автоматически заполнится после создания арта)

### Тестовые скрипты:
```javascript
// После регистрации
if (pm.response.code === 201) {
    const data = pm.response.json();
    pm.environment.set("user_id", data.id);
}

// После создания арта
if (pm.response.code === 201) {
    const data = pm.response.json();
    pm.environment.set("product_id", data.id);
}
```

---

## 🚀 Рабочий процесс

1. **Регистрация пользователя**
2. **Логин для получения ID**
3. **Создание арта через form-data**
4. **Просмотр созданных артов**
5. **Покупка артов другими пользователями**
6. **Просмотр профиля с купленными и созданными артами**
