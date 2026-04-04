import os
import random
import uuid
import hashlib
from PIL import Image
from web_server import create_app
from database import db_manager
from config import SeedConfig, MarketConfig
from watermark import add_watermark
import logging

logger = logging.getLogger(__name__)


def compute_file_hash(file_path: str) -> str:
    """Вычисляет SHA256 хеш файла"""
    hash_sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()


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


def process_uploaded_image_for_seed(file, originals_folder, watermarked_folder):
    """Упрощенная обработка изображения для сидинга"""
    original_path = None
    watermarked_path = None
    
    try:
        os.makedirs(originals_folder, exist_ok=True)
        os.makedirs(watermarked_folder, exist_ok=True)
        
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        
        if file_size > ServerConfig.MAX_CONTENT_LENGTH:
            return None, "Файл слишком большой"
        
        image = Image.open(file)
        width, height = image.size
        
        if width > ServerConfig.MAX_IMAGE_DIMENSION or height > ServerConfig.MAX_IMAGE_DIMENSION:
            return None, "Размеры изображения слишком большие"
        
        if image.format not in ServerConfig.ALLOWED_EXTENSIONS:
            return None, "Неподдерживаемый формат изображения"
        
        file_id = str(uuid.uuid4())
        original_extension = image.format.lower()
        original_filename = f"{file_id}.{original_extension}"
        original_path = os.path.join(originals_folder, original_filename)
        
        if image.format == 'PNG':
            image.save(original_path, optimize=True)
        else:
            if image.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', image.size, (255, 255, 255))
                background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
                image = background
            image.save(original_path, optimize=True, quality=85)
        
        watermarked_path = os.path.join(watermarked_folder, original_filename)
        if not add_watermark(original_path, watermarked_path):
            return None, "Ошибка добавления водяного знака"
        
        original_hash = compute_file_hash(original_path)
        watermarked_hash = compute_file_hash(watermarked_path)
        
        image.close()
        
        return {
            'file_id': file_id,
            'original_path': original_path,
            'watermarked_path': watermarked_path,
            'original_hash': original_hash,
            'watermarked_hash': watermarked_hash
        }, None
        
    except Exception as e:
        if original_path and os.path.exists(original_path):
            os.remove(original_path)
        if watermarked_path and os.path.exists(watermarked_path):
            os.remove(watermarked_path)
        return None, f"Ошибка: {str(e)}"


def seed_database():
    """Заполнение базы данных тестовыми данными"""
    
    app = create_app()
    
    with app.app_context():
        print("=" * 60)
        print("🚀 НАЧАЛО ЗАПОЛНЕНИЯ БАЗЫ ДАННЫХ")
        print("=" * 60)
        print(f"\n📊 КОНФИГУРАЦИЯ СИДИНГА:")
        print(f"   👥 Пользователей: {SeedConfig.NUM_USERS}")
        print(f"   🎨 Уникальных фото: {SeedConfig.NUM_PRODUCTS}")
        print(f"   💰 Процент покупок: {SeedConfig.PURCHASE_PERCENTAGE * 100}%")
        print(f"   🎁 Бонус за регистрацию: {MarketConfig.REGISTRATION_BONUS} AC")
        print(f"   💰 Комиссия: {MarketConfig.COMMISSION_PERCENT * 100}%")
        print(f"   📦 Макс. товаров: {MarketConfig.MAX_ACTIVE_PRODUCTS_PER_SELLER}")
        
        originals_folder = 'uploads/originals'
        watermarked_folder = 'uploads/watermarked'
        photo_examples_dir = 'photo_examples'
        
        if not os.path.exists(photo_examples_dir):
            print("\n❌ Папка photo_examples не найдена!")
            return
        
        image_files = [f for f in os.listdir(photo_examples_dir) 
                      if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.tiff'))]
        
        if len(image_files) < SeedConfig.NUM_PRODUCTS:
            print(f"\n⚠️ В photo_examples только {len(image_files)} фото, а нужно {SeedConfig.NUM_PRODUCTS}")
            print(f"   Будет создано {len(image_files)} товаров")
            num_products = len(image_files)
        else:
            num_products = SeedConfig.NUM_PRODUCTS
            random.shuffle(image_files)
            image_files = image_files[:num_products]
        
        print(f"\n📁 Используется {len(image_files)} уникальных изображений")
        
        # ========== 1. СОЗДАНИЕ ПОЛЬЗОВАТЕЛЕЙ ==========
        print("\n" + "=" * 60)
        print("👥 ШАГ 1: СОЗДАНИЕ ПОЛЬЗОВАТЕЛЕЙ")
        print("=" * 60)
        
        users = []
        for i in range(SeedConfig.NUM_USERS):
            try:
                user = db_manager.create_account(
                    nickname=f"user_{i+1}",
                    mail=f"user_{i+1}@market.com",
                    password="123456"
                )
                users.append(user)
                print(f'   ✅ [{i+1}/{SeedConfig.NUM_USERS}] user_{i+1} (баланс: {user.balance} AC)')
            except Exception as e:
                print(f"   ⚠️ Ошибка: {e}")
        
        if not users:
            print("\n❌ Не удалось создать пользователей!")
            return
        
        print(f"\n✅ Создано {len(users)} пользователей")
        
        # ========== 2. ПЕРВЫЙ КРУГ ПРОДАЖ (создание товаров) ==========
        print("\n" + "=" * 60)
        print("🎨 ШАГ 2: ПЕРВЫЙ КРУГ — СОЗДАНИЕ ТОВАРОВ")
        print("=" * 60)
        
        adjectives = ["Уникальный", "Эксклюзивный", "Ценный", "Редкий", "Премиальный",
                      "Инновационный", "Современный", "Классический", "Элегантный", "Стильный",
                      "Функциональный", "Надежный", "Качественный", "Популярный", "Модный",
                      "Винтажный", "Коллекционный", "Лимитированный", "Авторский", "Дизайнерский"]
        
        nouns = ["Товар", "Продукт", "Арт", "Объект", "Изделие", "Аксессуар", "Элемент",
                 "Экземпляр", "Предмет", "Образец", "Шедевр", "Экспонат", "Реликвия"]
        
        products = []
        
        for i, image_file in enumerate(image_files):
            try:
                image_path = os.path.join(photo_examples_dir, image_file)
                
                # Рандомный продавец
                seller = random.choice(users)
                
                # Проверка лимита
                active_count = len([p for p in seller.products_for_sale if p.on_sale])
                if active_count >= MarketConfig.MAX_ACTIVE_PRODUCTS_PER_SELLER:
                    available = [u for u in users if len([p for p in u.products_for_sale if p.on_sale]) < MarketConfig.MAX_ACTIVE_PRODUCTS_PER_SELLER]
                    if available:
                        seller = random.choice(available)
                    else:
                        print(f"   ⚠️ Товар {i+1} пропущен — нет свободных продавцов")
                        continue
                
                adjective = random.choice(adjectives)
                noun = random.choice(nouns)
                title = f"{adjective} {noun} #{i+1}"
                price = random.randint(MarketConfig.MIN_PRODUCT_PRICE, 500)
                
                descriptions = [
                    f"Это прекрасный товар '{title}'. Качественное исполнение и стильный дизайн.",
                    f"Эксклюзивный экземпляр '{title}' в единственном экземпляре.",
                    f"Коллекционный предмет '{title}'. Редкая находка для ценителей.",
                    f"Уникальное предложение - {title}. Только сегодня по такой цене!"
                ]
                description = random.choice(descriptions)
                
                file_obj = SimpleFile(image_path)
                image_info, error = process_uploaded_image_for_seed(
                    file_obj, originals_folder, watermarked_folder
                )
                file_obj.close()
                
                if error:
                    print(f"   ❌ {error}")
                    continue
                
                product = db_manager.create_product(
                    creator_id=seller.id,
                    owner_id=seller.id,
                    title=title,
                    price=price,
                    description=description,
                    photo_url=image_info['file_id'],
                    original_hash=image_info['original_hash'],
                    watermarked_hash=image_info['watermarked_hash'],
                    on_sale=True
                )
                
                products.append(product)
                print(f'   ✅ [{i+1}/{num_products}] {title[:35]} — {price} AC (продавец: {seller.nickname})')
                
            except Exception as e:
                print(f"   ❌ Ошибка: {e}")
        
        if not products:
            print("\n❌ Не удалось создать товары!")
            return
        
        print(f"\n✅ Создано {len(products)} товаров")
        
        # ========== 3. ПЕРВЫЙ КРУГ ПОКУПОК ==========
        print("\n" + "=" * 60)
        print("💰 ШАГ 3: ПЕРВЫЙ КРУГ — ПОКУПКИ")
        print("=" * 60)
        
        num_to_buy = int(len(products) * SeedConfig.PURCHASE_PERCENTAGE)
        purchase_count = 0
        
        if num_to_buy > 0:
            products_shuffled = products.copy()
            random.shuffle(products_shuffled)
            products_to_buy = products_shuffled[:num_to_buy]
            
            print(f"\n📊 Планируется купить {num_to_buy} товаров ({SeedConfig.PURCHASE_PERCENTAGE * 100}%)")
            
            for idx, product in enumerate(products_to_buy):
                potential_buyers = [u for u in users if u.id != product.owner_id and u.balance >= product.price]
                
                if not potential_buyers:
                    continue
                
                buyer = random.choice(potential_buyers)
                
                try:
                    db_manager.buy_product(buyer.id, product.id)
                    purchase_count += 1
                    if purchase_count % 5 == 0:
                        print(f'   ✅ Куплено: {purchase_count}/{num_to_buy}')
                except Exception as e:
                    pass
            
            print(f"\n✅ Совершено покупок: {purchase_count}")
        
        # ========== 4. ВТОРОЙ КРУГ — ПЕРЕПРОДАЖИ ==========
        print("\n" + "=" * 60)
        print("🔄 ШАГ 4: ВТОРОЙ КРУГ — ПЕРЕПРОДАЖИ")
        print("=" * 60)
        
        # Берём купленные товары
        purchased_products = [p for p in products if not p.on_sale and p.purchased_at]
        
        if purchased_products:
            relist_percentage = SeedConfig.PURCHASE_PERCENTAGE
            num_to_relist = int(len(purchased_products) * relist_percentage)
            
            if num_to_relist > 0:
                products_to_relist = random.sample(purchased_products, min(num_to_relist, len(purchased_products)))
                print(f"\n📊 Планируется перевыставить {len(products_to_relist)} товаров")
                
                relist_count = 0
                for product in products_to_relist:
                    try:
                        # Проверяем, что владелец не превысил лимит
                        owner_active = len([p for p in product.owner.products_for_sale if p.on_sale])
                        if owner_active >= MarketConfig.MAX_ACTIVE_PRODUCTS_PER_SELLER:
                            continue
                        
                        product.on_sale = True
                        db_manager.db.session.commit()
                        relist_count += 1
                    except Exception as e:
                        pass
                
                print(f"✅ Перевыставлено: {relist_count} товаров")
        
        # ========== 5. ВТОРОЙ КРУГ ПОКУПОК ==========
        print("\n" + "=" * 60)
        print("💰 ШАГ 5: ВТОРОЙ КРУГ — ПОВТОРНЫЕ ПОКУПКИ")
        print("=" * 60)
        
        # Берём товары, которые сейчас в продаже (включая перевыставленные)
        available_products = [p for p in products if p.on_sale]
        
        if available_products:
            num_to_buy_second = int(len(available_products) * SeedConfig.PURCHASE_PERCENTAGE)
            purchase_count_second = 0
            
            if num_to_buy_second > 0:
                products_to_buy_second = random.sample(available_products, min(num_to_buy_second, len(available_products)))
                print(f"\n📊 Планируется купить {len(products_to_buy_second)} товаров во второй раз")
                
                for product in products_to_buy_second:
                    potential_buyers = [u for u in users if u.id != product.owner_id and u.balance >= product.price]
                    
                    if not potential_buyers:
                        continue
                    
                    buyer = random.choice(potential_buyers)
                    
                    try:
                        db_manager.buy_product(buyer.id, product.id)
                        purchase_count_second += 1
                        if purchase_count_second % 5 == 0:
                            print(f'   ✅ Куплено: {purchase_count_second}/{num_to_buy_second}')
                    except Exception as e:
                        pass
                
                print(f"\n✅ Совершено повторных покупок: {purchase_count_second}")
        
        # ========== 6. ЕЖЕДНЕВНЫЕ БОНУСЫ ==========
        print("\n" + "=" * 60)
        print("🎁 ШАГ 6: НАЧИСЛЕНИЕ БОНУСОВ")
        print("=" * 60)
        
        bonus_count = 0
        for user in users:
            try:
                if user.balance < MarketConfig.DAILY_BONUS_MAX_BALANCE:
                    db_manager.claim_daily_bonus(user.id)
                    bonus_count += 1
            except:
                pass
        
        print(f"✅ Бонусы начислены {bonus_count} пользователям")
        
        # ========== 7. СТАТИСТИКА ==========
        print("\n" + "=" * 60)
        print("📊 ИТОГОВАЯ СТАТИСТИКА")
        print("=" * 60)
        
        total_balance = sum(u.balance for u in users)
        total_spent = sum(u.total_spent for u in users)
        total_earned = sum(u.total_earned for u in users)
        
        products_on_sale = len([p for p in products if p.on_sale])
        products_sold_total = len([p for p in products if not p.on_sale and p.purchased_at])
        
        print(f"\n👥 ПОЛЬЗОВАТЕЛИ: {len(users)}")
        print(f"   Общий баланс: {total_balance} AC")
        print(f"   Всего потрачено: {total_spent} AC")
        print(f"   Всего заработано: {total_earned} AC")
        
        print(f"\n🎨 ТОВАРЫ: {len(products)}")
        print(f"   В продаже: {products_on_sale}")
        print(f"   Продано (всего операций): {products_sold_total}")
        
        print("\n" + "=" * 60)
        print("🎉 ЗАПОЛНЕНИЕ БАЗЫ ДАННЫХ ЗАВЕРШЕНО!")
        print("=" * 60)
        
        print("\n🔑 Тестовые данные:")
        print("   Логин: user_1 ... user_20")
        print("   Пароль: 123456")


if __name__ == "__main__":
    from config import ServerConfig
    seed_database()
