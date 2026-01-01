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

def process_image_for_seed(file_path, upload_folder):
    """Упрощенная обработка изображения для сидинга"""
    try:
        # Используем ту же функцию, что и в web_server
        from web_server import process_uploaded_image
        
        file_obj = SimpleFile(file_path)
        image_info, error = process_uploaded_image(file_obj)
        file_obj.close()
        
        return image_info, error
        
    except Exception as e:
        return None, f"Image processing error: {str(e)}"

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
            return
        
        image_files = [f for f in os.listdir(photo_examples_dir) 
                      if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.tiff'))]
        
        if not image_files:
            print("❌ Нет изображений в папке photo_examples!")
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
        
        selected_images = random.sample(image_files, min(NUM_PRODUCTS, len(image_files)))
        
        for i, image_file in enumerate(selected_images):
            try:
                image_path = os.path.join(photo_examples_dir, image_file)
                creator = random.choice(users)
                
                # Генерируем название
                adjective = random.choice(adjectives)
                noun = random.choice(nouns)
                title = f"{adjective} {noun} #{i+1}"
                
                # Генерируем цену (от 10 до 100 AC)
                price = random.randint(10, 100)
                
                # Рассчитываем стартовый капитал
                startup_capital = price * MarketConfig.SELLER_STARTUP_MULTIPLIER
                
                print(f"   Создаем товар: {title} (цена: {price} AC, стартовый капитал: {startup_capital} AC)")
                
                # Проверяем баланс продавца
                if creator.balance < startup_capital:
                    print(f"   ⚠️ У продавца {creator.nickname} недостаточно средств ({creator.balance} AC), пропускаем")
                    continue
                
                # Проверяем лимит товаров продавца
                active_products = len([p for p in creator.products if p.status == 'active'])
                if active_products >= MarketConfig.MAX_ACTIVE_PRODUCTS_PER_SELLER:
                    print(f"   ⚠️ У продавца {creator.nickname} достигнут лимит товаров ({active_products}), пропускаем")
                    continue
                
                # Обрабатываем изображение
                upload_folder = app.config['UPLOAD_FOLDER']
                image_info, error = process_image_for_seed(image_path, upload_folder)
                
                if error:
                    print(f"   ❌ Ошибка обработки изображения: {error}")
                    continue
                
                # Создаем товар
                product = db_manager.create_product(
                    creator_id=creator.id,
                    title=title,
                    price=price,
                    description=f"Это прекрасный товар {title}. Качественное исполнение, надежность и стильный дизайн.",
                    photo_url=image_info['file_id']
                )
                
                products.append(product)
                print(f"   ✅ Создан товар: {product.title} (Продавец: {creator.nickname}, Портфель: {product.portfolio} AC)")
                
            except Exception as e:
                print(f"   ❌ Ошибка создания товара: {e}")
        
        # Создаем подписки
        print("\n💰 Создаем подписки...")
        subscription_count = 0
        
        for product in products:
            # Определяем количество подписчиков для этого товара
            num_potential_subscribers = len(users) - 1
            num_subscriptions = int(num_potential_subscribers * PURCHASE_PERCENTAGE)
            
            # Исключаем продавца из списка потенциальных подписчиков
            potential_subscribers = [user for user in users if user.id != product.creator_id]
            
            if potential_subscribers:
                # Выбираем подписчиков
                subscribers = random.sample(
                    potential_subscribers, 
                    min(num_subscriptions, len(potential_subscribers))
                )
                
                for subscriber in subscribers:
                    try:
                        # Проверяем баланс подписчика
                        if subscriber.balance >= product.current_price:
                            result = db_manager.subscribe_to_product(subscriber.id, product.id)
                            if result['success']:
                                subscription_count += 1
                                print(f"   ✅ Подписка: {subscriber.nickname} → {product.title} за {product.current_price} AC")
                            else:
                                print(f"   ⚠️ Ошибка подписки: {result.get('error', 'Unknown error')}")
                    except Exception as e:
                        print(f"   ⚠️ Ошибка при создании подписки: {e}")
        
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
            active_products = len([p for p in user.products if p.status == 'active'])
            subscriptions = len([s for s in user.subscriptions if s.status == 'active'])
            print(f"   {user.nickname}: {user.balance} AC (товаров: {active_products}, подписок: {subscriptions})")
        
        print("\n🔗 API доступно по адресу: http://localhost:5000")
        print("📚 Документация API:")
        print("   GET  /api/health - проверка работы")
        print("   POST /api/auth/register - регистрация")
        print("   POST /api/auth/login - вход")
        print("   GET  /api/products - список товаров")
        print("   POST /api/products - создать товар")
        print("   GET  /api/products/<id> - информация о товаре")

if __name__ == "__main__":
    seed_database()
