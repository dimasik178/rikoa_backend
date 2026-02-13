import os
import random
import uuid
from PIL import Image
from web_server import create_app
from database import db_manager
from config import NUM_USERS, NUM_PRODUCTS, PURCHASE_PERCENTAGE, MarketConfig

class SimpleFile:
    """Имитация файла для обработки изображений"""
    def __init__(self, path):
        self.path = path
        self.filename = os.path.basename(path)
        self._file = None
    
    def seek(self, pos, whence=0):
        if self._file is None:
            self._file = open(self.path, 'rb')
        self._file.seek(pos, whence)
    
    def tell(self):
        if self._file is None:
            self._file = open(self.path, 'rb')
        return self._file.tell()
    
    def read(self, size=-1):
        if self._file is None:
            self._file = open(self.path, 'rb')
        return self._file.read(size)
    
    def close(self):
        if self._file:
            self._file.close()

def process_uploaded_image_for_seed(file):
    """Упрощенная обработка изображения для сидинга (отдельная от web_server)"""
    try:
        # Определяем путь для загрузок
        upload_folder = 'uploads'
        os.makedirs(upload_folder, exist_ok=True)
        os.makedirs(os.path.join(upload_folder, 'thumbnails'), exist_ok=True)
        
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        
        if file_size > 15 * 1024 * 1024:
            return None, "Файл слишком большой (максимум 15MB)"
        
        image = Image.open(file)
        width, height = image.size
        
        if width > 10000 or height > 10000:
            return None, "Размеры изображения слишком большие (максимум 10000x10000)"
        
        if image.format not in ['JPEG', 'PNG', 'GIF', 'WEBP', 'BMP', 'TIFF']:
            return None, "Неподдерживаемый формат изображения"
        
        # Генерируем уникальный ID для файла
        file_id = str(uuid.uuid4())
        original_extension = image.format.lower()
        
        # Создаем превью
        thumbnail_size = (800, 800)
        thumbnail_filename = f"{file_id}_thumbnail.{original_extension}"
        thumbnail_path = os.path.join(upload_folder, 'thumbnails', thumbnail_filename)
        
        # Сохраняем превью
        image.thumbnail(thumbnail_size, Image.Resampling.LANCZOS)
        
        if image.format == 'PNG':
            image.save(thumbnail_path, optimize=True)
        else:
            if image.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', image.size, (255, 255, 255))
                background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
                image = background
            image.save(thumbnail_path, optimize=True, quality=85)
        
        image.close()
        
        return {
            'thumbnail': thumbnail_filename,
            'file_id': file_id
        }, None
        
    except Exception as e:
        return None, f"Ошибка обработки изображения: {str(e)}"

def seed_database():
    """Заполнение базы данных тестовыми данными"""
    
    app = create_app()
    
    with app.app_context():
        print("🚀 Начинаем заполнение базы данных...")
        print(f"📊 Конфигурация:")
        print(f"   👥 Пользователей: {NUM_USERS}")
        print(f"   🎨 Товаров: {NUM_PRODUCTS}")
        print(f"   💰 Процент подписок: {PURCHASE_PERCENTAGE * 100}%")
        print(f"   💸 Начальный баланс: {MarketConfig.STARTING_BALANCE} AC")
        print(f"   📈 Стартовый капитал: {MarketConfig.SELLER_STARTUP_MULTIPLIER}× цена")
        print(f"   📦 Макс. товаров у продавца: {MarketConfig.MAX_ACTIVE_PRODUCTS_PER_SELLER}")
        
        # Проверяем папку с фото
        photo_examples_dir = 'photo_examples'
        if not os.path.exists(photo_examples_dir):
            print("❌ Папка photo_examples не найдена! Создайте папку с изображениями.")
            print("   mkdir photo_examples")
            print("   # поместите туда несколько изображений (.jpg, .png и т.д.)")
            return
        
        image_files = [f for f in os.listdir(photo_examples_dir) 
                      if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.tiff'))]
        
        if not image_files:
            print("❌ Нет изображений в папке photo_examples!")
            print("   Поместите несколько изображений в папку photo_examples/")
            return
        
        print(f"📁 Найдено {len(image_files)} изображений")
        
        # Создаем пользователей
        print("\n👥 Создаем пользователей...")
        users = []
        for i in range(NUM_USERS):
            try:
                user = db_manager.create_account(
                    nickname=f"user_{i+1}",
                    mail=f"user_{i+1}@market.com",
                    password="123456"
                )
                users.append(user)
                print(f'   ✅ Создан пользователь: user_{i+1} (Баланс: {user.balance} AC)')
            except Exception as e:
                print(f"   ⚠️ Пользователь user_{i+1} уже существует или ошибка: {e}")
        
        if not users:
            print("❌ Не удалось создать пользователей!")
            return
        
        # Список прилагательных для названий
        adjectives = [
            "Уникальный", "Эксклюзивный", "Ценный", "Редкий", "Премиальный",
            "Инновационный", "Современный", "Классический", "Элегантный", "Стильный",
            "Функциональный", "Надежный", "Качественный", "Популярный", "Модный"
        ]
        
        nouns = [
            "Товар", "Продукт", "Арт", "Объект", "Изделие",
            "Аксессуар", "Элемент", "Экземпляр", "Предмет", "Образец"
        ]
        
        # Создаем товары
        print("\n🎨 Создаем товары...")
        products = []
        
        # Берем первые N изображений или все, если их меньше
        num_products_to_create = min(NUM_PRODUCTS, len(image_files))
        selected_images = image_files[:num_products_to_create]
        
        for i, image_file in enumerate(selected_images):
            try:
                image_path = os.path.join(photo_examples_dir, image_file)
                creator = random.choice(users)
                
                # Генерируем название (3-100 символов)
                adjective = random.choice(adjectives)
                noun = random.choice(nouns)
                title = f"{adjective} {noun} #{i+1}"
                
                # Генерируем цену (от 1 до 10 AC)
                price = random.randint(1, 10)
                
                # Рассчитываем стартовый капитал
                startup_capital = price * MarketConfig.SELLER_STARTUP_MULTIPLIER
                
                print(f"   [{i+1}/{num_products_to_create}] Создаем товар: {title} (цена: {price} AC, стартовый капитал: {startup_capital} AC)")
                
                # Проверяем баланс продавца
                if creator.balance < startup_capital:
                    print(f"   ⚠️ У продавца {creator.nickname} недостаточно средств ({creator.balance} AC), пропускаем")
                    continue
                
                # Проверяем лимит товаров продавца
                active_products = len([p for p in creator.products if p.is_active])
                if active_products >= MarketConfig.MAX_ACTIVE_PRODUCTS_PER_SELLER:
                    print(f"   ⚠️ У продавца {creator.nickname} достигнут лимит товаров ({active_products}), пропускаем")
                    continue
                
                # Обрабатываем изображение
                file_obj = SimpleFile(image_path)
                image_info, error = process_uploaded_image_for_seed(file_obj)
                file_obj.close()
                
                if error:
                    print(f"   ❌ Ошибка обработки изображения: {error}")
                    continue
                
                if not image_info:
                    print(f"   ❌ Не удалось обработать изображение")
                    continue
                
                # Генерируем описание (до 1000 символов)
                description = f"Это прекрасный товар '{title}'. Качественное исполнение, надежность и стильный дизайн. Этот экземпляр обладает уникальными характеристиками и высокой ценностью для коллекционеров и инвесторов."
                
                # Создаем товар
                product = db_manager.create_product(
                    creator_id=creator.id,
                    title=title,
                    price=price,
                    description=description,
                    photo_url=image_info['file_id']
                )
                
                products.append(product)
                print(f"   ✅ Создан товар: {product.title} (Продавец: {creator.nickname}, Текущая цена: {product.current_price} AC, Портфель: {product.portfolio} AC)")
                
            except Exception as e:
                print(f"   ❌ Ошибка создания товара: {e}")
        
        if not products:
            print("❌ Не удалось создать ни одного товара!")
            return
        
        # Создаем подписки
        print("\n💰 Создаем подписки...")
        subscription_count = 0
        
        for product in products:
            # Определяем количество подписчиков для этого товара
            num_potential_subscribers = len(users) - 1
            num_subscriptions = int(num_potential_subscribers * PURCHASE_PERCENTAGE)
            
            # Исключаем продавца из списка потенциальных подписчиков
            potential_subscribers = [user for user in users if user.id != product.creator_id]
            
            if potential_subscribers and num_subscriptions > 0:
                # Выбираем подписчиков (но не больше, чем есть)
                num_to_select = min(num_subscriptions, len(potential_subscribers))
                subscribers = random.sample(potential_subscribers, num_to_select)
                
                for subscriber in subscribers:
                    try:
                        # Проверяем баланс подписчика
                        if subscriber.balance >= product.current_price:
                            db_manager.subscribe_to_product(subscriber.id, product.id)
                            subscription_count += 1
                            print(f"   ✅ Подписка: {subscriber.nickname} → {product.title} за {product.current_price} AC")
                    except Exception as e:
                        print(f"   ⚠️ Ошибка при создании подписки: {e}")
        
        # Генерируем историю цен для всех товаров
        print("\n📈 Генерируем историю цен...")
        for product in products:
            try:
                # Создаем небольшую историю цен (от 1 до 7 дней)
                days_history = random.randint(1, 7)
                for day in range(days_history):
                    # Генерируем случайное изменение цены
                    price_change = random.uniform(-0.2, 0.3)  # -20% до +30%
                    new_price = max(1, int(product.current_price * (1 + price_change)))
                    
                    # Обновляем цену (имитация дневного обновления)
                    product.current_price = new_price
                    # Здесь должен быть вызов метода обновления истории цен в БД
                
                print(f"   ✅ История цен для {product.title}: {days_history} дней, текущая цена: {product.current_price} AC")
            except Exception as e:
                print(f"   ⚠️ Ошибка генерации истории цен: {e}")
        
        # Статистика
        print("\n🎉 Заполнение завершено!")
        print(f"📊 Итоговая статистика:")
        print(f"   👥 Пользователей создано: {len(users)}")
        print(f"   🎨 Товаров создано: {len(products)}")
        print(f"   💰 Подписок создано: {subscription_count}")
        
        # Считаем общую экономику
        total_portfolio = sum(p.portfolio for p in products)
        total_subscriptions_money = sum(p.subscriptions_money for p in products)
        
        print(f"\n💼 Общая экономика:")
        print(f"   🏦 Общий портфель всех товаров: {total_portfolio} AC")
        print(f"   💸 Деньги от подписок: {total_subscriptions_money} AC")
        
        # Показываем балансы пользователей
        print(f"\n💳 Балансы пользователей (первые 10):")
        for user in users[:10]:
            active_products = len([p for p in user.products if p.is_active])
            subscriptions = len([s for s in user.subscriptions if s.is_active])
            print(f"   {user.nickname}: {user.balance} AC (товаров: {active_products}, подписок: {subscriptions})")
        
        # Показываем топ-5 товаров по подписчикам
        print(f"\n🏆 Топ-5 товаров по подписчикам:")
        products_by_subscribers = sorted(products, key=lambda p: p.subscribers_count, reverse=True)
        for i, product in enumerate(products_by_subscribers[:5]):
            print(f"   {i+1}. {product.title}: {product.subscribers_count} подписчиков, цена: {product.current_price} AC")
        
        print("\n🔗 API v2.1 доступно по адресу: http://localhost:5000")
        print("📚 Основные эндпоинты API:")
        print("   GET    /api/health - проверка работы")
        print("   POST   /api/auth/register - регистрация")
        print("   POST   /api/auth/login - вход")
        print("   POST   /api/auth/refresh - обновление токена")
        print("   GET    /api/auth/profile - профиль пользователя")
        print("   GET    /api/products - список товаров")
        print("   POST   /api/products - создать товар (multipart/form-data)")
        print("   GET    /api/products/<id> - информация о товаре")
        print("   PUT    /api/products/<id>/price - изменить цену")
        print("   POST   /api/products/<id>/subscribe - подписаться")
        print("   POST   /api/products/<id>/unsubscribe - отписаться")
        print("   POST   /api/products/<id>/remove - снять с продажи")
        print("   GET    /api/products/search - поиск товаров")
        print("   GET    /api/account/subscriptions - мои подписки")
        print("   POST   /api/account/bankruptcy - объявить банкротство")
        print("   GET    /api/players/rating - рейтинг игроков")
        print("   GET    /api/images/thumbnail/<file_id> - получить изображение")
        print("\n🚀 Для запуска сервера выполните: python main.py")

if __name__ == "__main__":
    seed_database()
