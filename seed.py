import os
import random
import uuid
from PIL import Image
from web_server import create_app
from database import db_manager
from config import SeedConfig, MarketConfig
# SeedConfig.NUM_USERS, SeedConfig.NUM_PRODUCTS, SeedConfig.PURCHASE_PERCENTAGE
from watermark import add_watermark
import logging

logger = logging.getLogger(__name__)


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
    try:
        # Создаем папки если их нет
        os.makedirs(originals_folder, exist_ok=True)
        os.makedirs(watermarked_folder, exist_ok=True)
        
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
        
        # Сохраняем оригинал
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
        
        # Создаем копию с водяным знаком
        watermarked_path = os.path.join(watermarked_folder, original_filename)
        if not add_watermark(original_path, watermarked_path):
            return None, "Ошибка добавления водяного знака"
        
        image.close()
        
        return {
            'file_id': file_id,
            'original_path': original_path,
            'watermarked_path': watermarked_path
        }, None
        
    except Exception as e:
        return None, f"Ошибка обработки изображения: {str(e)}"


def seed_database():
    """Заполнение базы данных тестовыми данными"""
    
    app = create_app()
    
    with app.app_context():
        print("=" * 60)
        print("🚀 НАЧАЛО ЗАПОЛНЕНИЯ БАЗЫ ДАННЫХ")
        print("=" * 60)
        print(f"\n📊 КОНФИГУРАЦИЯ СИДИНГА:")
        print(f"   👥 Пользователей: {SeedConfig.NUM_USERS}")
        print(f"   🎨 Товаров: {SeedConfig.NUM_PRODUCTS}")
        print(f"   💰 Процент покупок: {SeedConfig.PURCHASE_PERCENTAGE * 100}%")
        print(f"   🎁 Бонус за регистрацию: {MarketConfig.REGISTRATION_BONUS} AC")
        print(f"   💰 Комиссия с продаж: {MarketConfig.COMMISSION_PERCENT * 100}%")
        print(f"   📦 Макс. товаров у продавца: {MarketConfig.MAX_ACTIVE_PRODUCTS_PER_SELLER}")
        print(f"   💸 Минимальная цена: {MarketConfig.MIN_PRODUCT_PRICE} AC")
        
        # Папки для изображений
        originals_folder = 'uploads/originals'
        watermarked_folder = 'uploads/watermarked'
        
        # Проверяем папку с фото
        photo_examples_dir = 'photo_examples'
        if not os.path.exists(photo_examples_dir):
            print("\n❌ Папка photo_examples не найдена! Создайте папку с изображениями.")
            print("   mkdir photo_examples")
            print("   # поместите туда несколько изображений (.jpg, .png и т.д.)")
            return
        
        image_files = [f for f in os.listdir(photo_examples_dir) 
                      if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.tiff'))]
        
        if not image_files:
            print("\n❌ Нет изображений в папке photo_examples!")
            print("   Поместите несколько изображений в папку photo_examples/")
            return
        
        print(f"\n📁 Найдено изображений: {len(image_files)}")
        
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
                print(f'   ✅ [{i+1}/{SeedConfig.NUM_USERS}] Создан: user_{i+1} (Баланс: {user.balance} AC)')
            except Exception as e:
                print(f"   ⚠️ Ошибка создания user_{i+1}: {e}")
        
        if not users:
            print("\n❌ Не удалось создать пользователей!")
            return
        
        print(f"\n✅ Итого создано пользователей: {len(users)}")
        
        # ========== 2. СОЗДАНИЕ ТОВАРОВ ==========
        print("\n" + "=" * 60)
        print("🎨 ШАГ 2: СОЗДАНИЕ ТОВАРОВ")
        print("=" * 60)
        
        # Список прилагательных для названий
        adjectives = [
            "Уникальный", "Эксклюзивный", "Ценный", "Редкий", "Премиальный",
            "Инновационный", "Современный", "Классический", "Элегантный", "Стильный",
            "Функциональный", "Надежный", "Качественный", "Популярный", "Модный",
            "Винтажный", "Коллекционный", "Лимитированный", "Авторский", "Дизайнерский",
            "Экологичный", "Технологичный", "Эргономичный", "Компактный", "Универсальный"
        ]
        
        nouns = [
            "Товар", "Продукт", "Арт", "Объект", "Изделие",
            "Аксессуар", "Элемент", "Экземпляр", "Предмет", "Образец",
            "Шедевр", "Экспонат", "Реликвия", "Раритет", "Сокровище"
        ]
        
        # Создаем товары с циклическим использованием изображений
        products = []
        num_products_to_create = min(SeedConfig.NUM_PRODUCTS, len(image_files) * 2)  # Можно использовать каждое изображение несколько раз
        
        for i in range(num_products_to_create):
            try:
                # Выбираем изображение по кругу
                image_file = image_files[i % len(image_files)]
                image_path = os.path.join(photo_examples_dir, image_file)
                
                # Выбираем случайного продавца
                creator = random.choice(users)
                
                # Генерируем название
                adjective = random.choice(adjectives)
                noun = random.choice(nouns)
                title = f"{adjective} {noun} #{i+1}"
                
                # Генерируем цену (от MIN_PRODUCT_PRICE до 500 AC)
                price = random.randint(MarketConfig.MIN_PRODUCT_PRICE, 500)
                
                # Проверяем лимит товаров продавца
                active_products = len([p for p in creator.products_for_sale if not p.is_sold])
                if active_products >= MarketConfig.MAX_ACTIVE_PRODUCTS_PER_SELLER:
                    # Ищем другого продавца с меньшим количеством товаров
                    other_sellers = [u for u in users if len([p for p in u.products_for_sale if not p.is_sold]) < MarketConfig.MAX_ACTIVE_PRODUCTS_PER_SELLER]
                    if other_sellers:
                        creator = random.choice(other_sellers)
                    else:
                        print(f"   ⚠️ [{i+1}/{num_products_to_create}] Нет свободных продавцов, пропускаем")
                        continue
                
                # Обрабатываем изображение
                file_obj = SimpleFile(image_path)
                image_info, error = process_uploaded_image_for_seed(
                    file_obj, originals_folder, watermarked_folder
                )
                file_obj.close()
                
                if error:
                    print(f"   ❌ [{i+1}/{num_products_to_create}] Ошибка обработки: {error}")
                    continue
                
                if not image_info:
                    print(f"   ❌ [{i+1}/{num_products_to_create}] Не удалось обработать изображение")
                    continue
                
                # Генерируем описание
                descriptions = [
                    f"Это прекрасный товар '{title}'. Качественное исполнение, надежность и стильный дизайн.",
                    f"Эксклюзивный экземпляр '{title}' в единственном экземпляре. Идеальное состояние.",
                    f"Коллекционный предмет '{title}'. Редкая находка для ценителей.",
                    f"Уникальное предложение - {title}. Только сегодня по такой цене!",
                    f"Премиальный {noun.lower()} {title.lower()}. Доставка по всей стране.",
                ]
                description = random.choice(descriptions)
                
                # Создаем товар
                product = db_manager.create_product(
                    creator_id=creator.id,
                    title=title,
                    price=price,
                    description=description,
                    photo_url=image_info['file_id']
                )
                
                products.append(product)
                
                # Прогресс-бар
                if (i + 1) % 20 == 0 or i + 1 == num_products_to_create:
                    print(f'   ✅ Прогресс: {len(products)}/{num_products_to_create}')
                
            except Exception as e:
                print(f"   ❌ Ошибка создания товара {i+1}: {e}")
        
        if not products:
            print("\n❌ Не удалось создать ни одного товара!")
            return
        
        print(f"\n✅ Итого создано товаров: {len(products)}")
        
        # ========== 3. СОЗДАНИЕ ПОКУПОК ==========
        print("\n" + "=" * 60)
        print("💰 ШАГ 3: СОЗДАНИЕ ПОКУПОК")
        print("=" * 60)
        
        # Определяем количество товаров для покупки
        num_to_buy = int(len(products) * SeedConfig.PURCHASE_PERCENTAGE)
        
        if num_to_buy > 0:
            # Перемешиваем товары для случайного выбора
            products_shuffled = products.copy()
            random.shuffle(products_shuffled)
            products_to_buy = products_shuffled[:num_to_buy]
            
            print(f"\n📊 Планируется купить {num_to_buy} товаров ({SeedConfig.PURCHASE_PERCENTAGE * 100}% от всех)")
            
            purchase_count = 0
            failed_count = 0
            
            for idx, product in enumerate(products_to_buy):
                # Ищем покупателя (не продавца и с достаточным балансом)
                potential_buyers = [u for u in users if u.id != product.creator_id and u.balance >= product.price]
                
                if not potential_buyers:
                    print(f"   ⚠️ [{idx+1}/{num_to_buy}] Нет подходящих покупателей для '{product.title[:30]}...'")
                    failed_count += 1
                    continue
                
                # Выбираем случайного покупателя
                buyer = random.choice(potential_buyers)
                
                try:
                    # Выполняем покупку
                    db_manager.buy_product(buyer.id, product.id)
                    purchase_count += 1
                    
                    # Показываем прогресс каждые 10 покупок
                    if purchase_count % 10 == 0:
                        print(f'   ✅ Прогресс: {purchase_count}/{num_to_buy}')
                        
                except Exception as e:
                    print(f"   ❌ Ошибка покупки {product.title[:30]}: {e}")
                    failed_count += 1
            
            print(f"\n✅ Итого совершено покупок: {purchase_count}")
            if failed_count > 0:
                print(f"⚠️ Не удалось совершить: {failed_count}")
        else:
            print("\n⚠️ Покупки не создаются (SeedConfig.PURCHASE_PERCENTAGE = 0)")
        
        # ========== 4. НАЧИСЛЕНИЕ ЕЖЕДНЕВНЫХ БОНУСОВ ==========
        print("\n" + "=" * 60)
        print("🎁 ШАГ 4: НАЧИСЛЕНИЕ ЕЖЕДНЕВНЫХ БОНУСОВ")
        print("=" * 60)
        
        bonus_count = 0
        for user in users:
            try:
                if user.balance < MarketConfig.DAILY_BONUS_MAX_BALANCE:
                    db_manager.claim_daily_bonus(user.id)
                    bonus_count += 1
            except Exception as e:
                # Пропускаем ошибки (например, если бонус уже был получен сегодня)
                pass
        
        print(f"✅ Бонусы начислены {bonus_count} пользователям")
        
        # ========== 5. ИТОГОВАЯ СТАТИСТИКА ==========
        print("\n" + "=" * 60)
        print("📊 ИТОГОВАЯ СТАТИСТИКА")
        print("=" * 60)
        
        # Считаем статистику
        total_balance = sum(u.balance for u in users)
        total_spent = sum(u.total_spent for u in users)
        total_earned = sum(u.total_earned for u in users)
        
        # Считаем товары
        products_for_sale = len([p for p in products if not p.is_sold])
        products_sold = len([p for p in products if p.is_sold])
        
        print(f"\n👥 ПОЛЬЗОВАТЕЛИ:")
        print(f"   Всего создано: {len(users)}")
        print(f"   Общий баланс: {total_balance} AC")
        print(f"   Всего потрачено: {total_spent} AC")
        print(f"   Всего заработано: {total_earned} AC")
        
        print(f"\n🎨 ТОВАРЫ:")
        print(f"   Всего создано: {len(products)}")
        print(f"   В продаже: {products_for_sale}")
        print(f"   Продано: {products_sold}")
        print(f"   Процент продаж: {products_sold / len(products) * 100:.1f}%")
        
        print(f"\n💰 ЭКОНОМИКА:")
        print(f"   Средний баланс пользователя: {total_balance // len(users)} AC")
        print(f"   Средняя цена товара: {sum(p.price for p in products) // len(products)} AC")
        print(f"   Средняя цена проданных: {sum(p.price for p in products if p.is_sold) // max(products_sold, 1)} AC")
        
        # Показываем топ-5 пользователей по балансу
        print(f"\n🏆 ТОП-5 ПОЛЬЗОВАТЕЛЕЙ ПО БАЛАНСУ:")
        sorted_users = sorted(users, key=lambda u: u.balance, reverse=True)
        for i, user in enumerate(sorted_users[:5]):
            products_for_sale_count = len([p for p in user.products_for_sale if not p.is_sold])
            purchased_count = len([p for p in user.owned_products if p.is_sold])
            print(f"   {i+1}. {user.nickname}: {user.balance} AC (на продаже: {products_for_sale_count}, куплено: {purchased_count})")
        
        # Показываем топ-5 товаров по цене
        print(f"\n🏷️ ТОП-5 САМЫХ ДОРОГИХ ТОВАРОВ:")
        products_by_price = sorted(products, key=lambda p: p.price, reverse=True)
        for i, product in enumerate(products_by_price[:5]):
            status = "🔴 ПРОДАН" if product.is_sold else "🟢 В ПРОДАЖЕ"
            print(f"   {i+1}. {product.title[:40]}: {product.price} AC - {status}")
        
        # Показываем информацию о товарах в продаже
        if products_for_sale > 0:
            print(f"\n📦 В ПРОДАЖЕ ОСТАЛОСЬ {products_for_sale} ТОВАРОВ")
            print(f"   Минимальная цена: {min(p.price for p in products if not p.is_sold)} AC")
            print(f"   Максимальная цена: {max(p.price for p in products if not p.is_sold)} AC")
            print(f"   Средняя цена: {sum(p.price for p in products if not p.is_sold) // products_for_sale} AC")
        
        print("\n" + "=" * 60)
        print("🎉 ЗАПОЛНЕНИЕ БАЗЫ ДАННЫХ ЗАВЕРШЕНО!")
        print("=" * 60)
        
        print("\n📚 API v4.0 доступно по адресу: http://localhost:5000")
        print("\n🔑 Тестовые учетные данные:")
        print("   Логин: user_1 ... user_20")
        print("   Пароль: 123456")
        
        print("\n🚀 Для запуска сервера выполните: python main.py")
        print("💡 Для принудительного обновления: docker exec art-market python daily_updater.py --run-now")


if __name__ == "__main__":
    seed_database()
