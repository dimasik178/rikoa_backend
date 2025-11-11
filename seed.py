# 🔧 КОНСТАНТЫ ДЛЯ НАСТРОЙКИ
NUM_USERS = 15                    # Количество пользователей
NUM_PRODUCTS = 20                # Количество созданных артов
PURCHASE_PERCENTAGE = 0.6        # Процент покупки артов другими пользователями (60%)



import os
import random
import uuid
from PIL import Image
from web_server import create_app
from database import db_manager


# Заменяем функцию process_uploaded_image
def process_uploaded_image(file, upload_folder):
    """Обрабатывает загруженное изображение с динамическим разрешением"""
    try:
        # Загружаем изображение
        image = Image.open(file)
        width, height = image.size
        
        # Генерируем уникальное имя файла
        file_id = str(uuid.uuid4())
        
        # 🔥 ДИНАМИЧЕСКОЕ РАЗРЕШЕНИЕ ДЛЯ ПРЕВЬЮ
        if width > 2000 or height > 2000:
            thumbnail_size = (800, 800)
        elif width > 1000 or height > 1000:
            thumbnail_size = (1200, 1200)
        else:
            thumbnail_size = (min(width, 1600), min(height, 1600))
        
        original_extension = image.format.lower()
        thumbnail_filename = f"{file_id}_thumbnail.{original_extension}"

        # Создаем и сохраняем превью
        image.thumbnail(thumbnail_size, Image.Resampling.LANCZOS)
        thumbnail_path = os.path.join(upload_folder, 'thumbnails', thumbnail_filename)
        
        # Сохраняем превью
        if image.format == 'PNG':
            image.save(thumbnail_path, optimize=True)
        else:
            if image.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', image.size, (255, 255, 255))
                background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
                image = background
            image.save(thumbnail_path, optimize=True, quality=80)
        
        image.close()
        
        return {
            'thumbnail': thumbnail_filename,
            'file_id': file_id
        }, None
        
    except Exception as e:
        return None, f"Image processing error: {str(e)}"
    
class SimpleFile:
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

def seed_database_simple():
    """Упрощенная версия заполнения БД"""
    
    app = create_app()
    
    with app.app_context():
        print("🚀 Начинаем заполнение базы данных...")
        print(f"📊 Конфигурация:")
        print(f"   👥 Пользователей: {NUM_USERS}")
        print(f"   🎨 Артов: {NUM_PRODUCTS}")
        print(f"   💰 Процент покупок: {PURCHASE_PERCENTAGE * 100}%")
        
        # Проверяем папку с фото
        photo_examples_dir = 'photo_examples'
        if not os.path.exists(photo_examples_dir):
            print("❌ Папка photo_examples не найдена!")
            return
        
        # Получаем все доступные изображения из папки
        image_files = [f for f in os.listdir(photo_examples_dir) 
                      if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp'))]
        
        if not image_files:
            print("❌ Нет изображений в папке photo_examples!")
            return
        
        print(f"📁 Найдено {len(image_files)} изображений")
        
        # Проверяем, что хватает изображений для создания артов
        if len(image_files) < NUM_PRODUCTS:
            print(f"⚠️  Внимание: запрошено {NUM_PRODUCTS} артов, но найдено только {len(image_files)} изображений")
            print("   Будут использованы все доступные изображения")
        
        # Создаем пользователей
        print("👥 Создаем пользователей...")
        users = []
        for i in range(NUM_USERS):
            try:
                password = "123456"
                user = db_manager.create_account(
                    nickname=f"artist_{i+1}",
                    mail=f"artist_{i+1}@gallery.com",
                    password=password
                )
                users.append(user)
                print(f'   ✅ Создан пользователь: artist_{i+1} Пароль: "{password}"')
            except Exception as e:
                print(f"   ⚠️ Пользователь artist_{i+1} уже существует")
        
        # Список прилагательных для названий
        adjectives = [
            "Великолепный", "Прекрасный", "Удивительный", "Завораживающий", 
            "Волшебный", "Изумительный", "Потрясающий", "Невероятный",
            "Восхитительный", "Божественный", "Незабываемый", "Фантастический",
            "Эксклюзивный", "Уникальный", "Редкий", "Ценный", "Элегантный",
            "Изящный", "Совершенный", "Бесподобный"
        ]
        
        # Создаем арты
        print("🎨 Создаем арты...")
        products = []
        
        # Выбираем случайные изображения для артов
        selected_images = random.sample(image_files, min(NUM_PRODUCTS, len(image_files)))
        
        for i, image_file in enumerate(selected_images):
            try:
                image_path = os.path.join(photo_examples_dir, image_file)
                creator = random.choice(users)
                
                # Создаем название из имени файла (без расширения) и случайного прилагательного
                filename_without_ext = os.path.splitext(image_file)[0]
                adjective = random.choice(adjectives)
                title = f"{adjective} {filename_without_ext}"
                
                # Имитируем загрузку файла
                file_obj = SimpleFile(image_path)
                
                # Получаем настройки из конфига приложения
                upload_folder = app.config['UPLOAD_FOLDER']
                # thumbnail_size = app.config['THUMBNAIL_SIZE']
                
                image_info, error = process_uploaded_image(file_obj, upload_folder)
                
                if not error:
                    product = db_manager.create_product(
                        photo_url=image_info['file_id'],
                        creator_id=creator.id,
                        title=title,
                        price=random.randint(100, 2000),
                        description="Прекрасное произведение искусства"
                    )
                    products.append(product)
                    print(f"   ✅ Создан арт: {product.title} (цена: {product.price})")
                else:
                    print(f"   ❌ Ошибка обработки изображения: {error}")
                
                file_obj.close()
                        
            except Exception as e:
                print(f"   ❌ Ошибка создания арта: {e}")
        
        # Создаем покупки
        print("💰 Создаем покупки...")
        purchase_count = 0
        
        for product in products:
            # Для каждого арта создаем покупки в соответствии с процентом
            num_potential_buyers = len(users) - 1  # Исключаем создателя
            num_purchases = int(num_potential_buyers * PURCHASE_PERCENTAGE)
            
            # Выбираем случайных покупателей (кроме создателя)
            potential_buyers = [user for user in users if user.id != product.creator_id]
            if potential_buyers:  # Проверяем, что есть кому покупать
                buyers = random.sample(potential_buyers, min(num_purchases, len(potential_buyers)))
                
                for buyer in buyers:
                    try:
                        db_manager.create_purchase(buyer.id, product.id)
                        purchase_count += 1
                        print(f"   ✅ Покупка: {buyer.nickname} → {product.title}")
                    except Exception:
                        pass  # Игнорируем дублирующиеся покупки
        
        # Статистика
        print("\n🎉 Заполнение завершено!")
        print(f"📊 Итоговая статистика:")
        print(f"   👥 Пользователей создано: {len(users)}")
        print(f"   🎨 Артов создано: {len(products)}")
        print(f"   💰 Покупок совершено: {purchase_count}")
        if products:
            print(f"   📈 Среднее количество покупок на арт: {purchase_count / len(products):.1f}")

if __name__ == "__main__":
    seed_database_simple()
