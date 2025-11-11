from flask import Flask, request, jsonify, send_file
from database import db_manager
import os
import datetime
from datetime import timezone
from datetime import datetime
import uuid
from PIL import Image
from functools import wraps
import threading
import time

def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///art_market.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SECRET_KEY'] = 'your-secret-key-here' #TODO
    
    # Настройки для загрузки изображений
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
    app.config['UPLOAD_FOLDER'] = 'uploads'
    app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    app.config['MAX_PROCESSING_TIME'] = 30  # 🔥 Максимальное время обработки в секундах
    app.config['MAX_IMAGE_DIMENSION'] = 10000  # 🔥 Максимальный размер изображения по любой стороне
    
    # Создаем папку для загрузок
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'thumbnails'), exist_ok=True)
    
    # Initialize database
    db_manager.init_app(app)
    
    def allowed_file(filename):
        """Проверка расширения файла"""
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']
    

    def process_uploaded_image_with_timeout(file, timeout=30):
        """Обрабатывает загруженное изображение с таймаутом"""
        result = [None]
        error = [None]
        
        def process():
            try:
                result[0], error[0] = process_uploaded_image(file)
            except Exception as e:
                error[0] = f"Processing error: {str(e)}"
        
        thread = threading.Thread(target=process)
        thread.start()
        thread.join(timeout)
        
        if thread.is_alive():
            return None, "Image processing timeout - file too large or complex"
        
        return result[0], error[0]

    def process_uploaded_image(file):
        """Обрабатывает загруженное изображение из form-data с динамическим разрешением"""
        try:
            start_time = time.time()
            
            # Проверяем размер файла
            file.seek(0, os.SEEK_END)
            file_size = file.tell()
            file.seek(0)
            
            if file_size > 15 * 1024 * 1024:
                return None, "File too large (max 15MB)"
            
            # Загружаем изображение
            image = Image.open(file)
            
            # Проверяем размеры изображения
            width, height = image.size
            max_dimension = app.config['MAX_IMAGE_DIMENSION']
            
            if width > max_dimension or height > max_dimension:
                return None, f"Image dimensions too large (max {max_dimension}x{max_dimension})"
            
            # Проверяем формат
            if image.format not in ['JPEG', 'PNG', 'GIF', 'WEBP']:
                return None, "Unsupported image format"
            
            # Генерируем уникальное имя файла
            file_id = str(uuid.uuid4())
            
            # Сохраняем оригинал с правильным расширением
            original_extension = image.format.lower()
            original_filename = f"{file_id}_original.{original_extension}"
            
            # 🔥 ДИНАМИЧЕСКОЕ РАЗРЕШЕНИЕ ДЛЯ ПРЕВЬЮ
            # Определяем оптимальный размер превью на основе оригинала
            if width > 2000 or height > 2000:
                thumbnail_size = (800, 800)
            elif width > 1000 or height > 1000:
                thumbnail_size = (1200, 1200)
            else:
                thumbnail_size = (min(width, 1600), min(height, 1600))
            
            # Сохраняем оригинальное расширение для превью
            thumbnail_filename = f"{file_id}_thumbnail.{original_extension}"

            # Сохраняем оригинал
            original_path = os.path.join(app.config['UPLOAD_FOLDER'], original_filename)
            
            # Оптимизируем сохранение оригинала
            if image.format == 'PNG':
                image.save(original_path, optimize=True)
            else:
                image.save(original_path, optimize=True, quality=85)

            # 🔥 СОЗДАЕМ ПРЕВЬЮ С ДИНАМИЧЕСКИМ РАЗМЕРОМ
            thumbnail_image = image.copy()
            thumbnail_image.thumbnail(thumbnail_size, Image.Resampling.LANCZOS)
            
            thumbnail_path = os.path.join(app.config['UPLOAD_FOLDER'], 'thumbnails', thumbnail_filename)
            
            # Сохраняем превью с тем же форматом что и оригинал
            if thumbnail_image.format == 'PNG':
                thumbnail_image.save(thumbnail_path, optimize=True)
            else:
                if thumbnail_image.mode in ('RGBA', 'LA', 'P'):
                    background = Image.new('RGB', thumbnail_image.size, (255, 255, 255))
                    background.paste(thumbnail_image, mask=thumbnail_image.split()[-1] if thumbnail_image.mode == 'RGBA' else None)
                    thumbnail_image = background
                thumbnail_image.save(thumbnail_path, optimize=True, quality=80)
            
            # Очищаем память
            image.close()
            thumbnail_image.close()
            
            processing_time = time.time() - start_time
            if processing_time > 10:
                print(f"Long image processing: {processing_time:.2f}s, size: {width}x{height}")
            
            return {
                'original': original_filename,
                'thumbnail': thumbnail_filename,
                'file_id': file_id
            }, None
            
        except Exception as e:
            return None, f"Image processing error: {str(e)}"
    
    def get_json_data():
        """Безопасное получение JSON данных из запроса"""
        if request.is_json:
            return request.get_json()
        elif request.content_type and 'application/x-www-form-urlencoded' in request.content_type:
            return request.form.to_dict()
        elif request.content_type and 'multipart/form-data' in request.content_type:
            return request.form.to_dict()
        else:
            try:
                return request.get_json(force=True, silent=True) or {}
            except:
                return {}

    def token_required(f):
        """Декоратор для проверки токена"""
        @wraps(f)
        def decorated(*args, **kwargs):
            token = None
            
            # Проверяем заголовок Authorization
            auth_header = request.headers.get('Authorization')
            if auth_header and auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
            
            if not token:
                return jsonify({'error': 'Token is missing'}), 401
            
            # В реальном приложении здесь была бы проверка токена
            # Для простоты используем ID аккаунта как токен
            account = db_manager.get_account_by_id(token)
            if not account:
                return jsonify({'error': 'Invalid token'}), 401
            
            return f(account, *args, **kwargs)
        
        return decorated
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Resource not found'}), 404
    
    @app.errorhandler(415)
    def unsupported_media_type(error):
        return jsonify({'error': 'Unsupported Media Type. Please use application/json'}), 415
    
    @app.errorhandler(413)
    def too_large(error):
        return jsonify({'error': 'File too large'}), 413
    
    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({'error': 'Internal server error'}), 500

    # Health check route
    @app.route('/api/health', methods=['GET'])
    def health_check():
        return jsonify({
            'status': 'healthy', 
            'message': 'RikoaTech ArtMarket API is running',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'version': '3.0'
        })

    # Authentication routes - изменены пути
    @app.route('/api/auth/register', methods=['POST'])
    def register():
        data = get_json_data()
        if not data or not all(k in data for k in ['login', 'mail', 'password']):
            return jsonify({'error': 'Missing required fields: login, mail, password'}), 400
        
        try:
            account = db_manager.create_account(
                nickname=data['login'],  # используем login как nickname
                mail=data['mail'],
                password=data['password']
            )
            # Добавляем токен в ответ (используем ID как токен для простоты)
            account_data = account.to_dict_with_products()
            account_data['token'] = account.id
            return jsonify(account_data), 201
        except ValueError as e:
            return jsonify({'error': str(e)}), 400
        except Exception as e:
            return jsonify({'error': 'Registration failed'}), 500
    
    @app.route('/api/auth/login', methods=['POST'])
    def login():
        data = get_json_data()
        if not data or not all(k in data for k in ['login', 'password']):
            return jsonify({'error': 'Missing login or password'}), 400
        
        account = db_manager.get_account_by_credentials(
            nickname=data['login'],  # используем login как nickname
            password=data['password']
        )
        
        if account:
            # Добавляем токен в ответ
            account_data = account.to_dict_with_products()
            account_data['token'] = account.id
            return jsonify(account_data)
        else:
            return jsonify({'error': 'Invalid credentials'}), 401

    @app.route('/api/auth/profile', methods=['GET'])
    @token_required
    def get_profile(current_account):
        """Получить информацию о профиле по токену"""
        return jsonify(current_account.to_dict_with_products())

    # Product routes - изменены пути и лимиты
    @app.route('/api/product', methods=['GET'])
    def get_products():
        page = request.args.get('page', 1, type=int)
        per_page = 6  # 🔄 ФИКСИРОВАННО 6 штук
        
        pagination = db_manager.get_products_paginated(page=page, per_page=per_page)
        
        return jsonify([product.to_dict() for product in pagination.items])

    @app.route('/api/product/<product_id>/buyers', methods=['GET'])
    def get_product_buyers(product_id):
        buyers = db_manager.get_product_buyers(product_id)
        # 🔄 Ограничиваем 6 пользователями
        limited_buyers = buyers[:6]
        return jsonify([buyer.to_dict() for buyer in limited_buyers])

    # 🔄 НОВЫЙ РОУТ ДЛЯ ПОКУПКИ
    @app.route('/api/product/buy', methods=['POST'])
    @token_required
    def purchase_product(current_account):
        data = get_json_data()
        if not data or 'id' not in data:
            return jsonify({'error': 'Missing product id'}), 400
        
        product_id = data['id']
        product = db_manager.get_product(product_id)
        if not product:
            return jsonify({'error': 'Product not found'}), 404
        
        try:
            purchase = db_manager.create_purchase(current_account.id, product_id)
            return jsonify({'success': True, 'purchase': purchase.to_dict()}), 201
        except Exception as e:
            return jsonify({'error': 'Failed to process purchase'}), 500

    # Image serving routes - изменен путь
    @app.route('/photos/<file_id>')
    def serve_image(file_id):
        """Отдает оригинальное изображение по ID продукта"""
        try:
            # Ищем продукт по ID чтобы получить file_id
            product = db_manager.get_product(file_id)
            if not product:
                return jsonify({'error': 'Product not found'}), 404
            
            # Ищем оригинальное изображение
            uploads_dir = app.config['UPLOAD_FOLDER']
            for filename in os.listdir(uploads_dir):
                if filename.startswith(f"{product.photo_url}_original."):
                    file_path = os.path.join(uploads_dir, filename)
                    return send_file(file_path)
            
            return jsonify({'error': 'Image not found'}), 404
        except Exception as e:
            return jsonify({'error': 'Image not found'}), 404

    # 🔄 СТАРЫЕ РОУТЫ (оставлены для обратной совместимости)
    @app.route('/api/products', methods=['POST'])
    def create_product():
        # ... существующий код без изменений ...
        if request.content_type and 'multipart/form-data' in request.content_type:
            # Обработка form-data
            if 'image' not in request.files:
                return jsonify({'error': 'No image file provided'}), 400
            
            file = request.files['image']
            if file.filename == '':
                return jsonify({'error': 'No image selected'}), 400
            
            if not allowed_file(file.filename):
                return jsonify({'error': 'Invalid file type'}), 400
            
            # Получаем остальные данные из form
            title = request.form.get('title')
            price = request.form.get('price')
            creator_id = request.form.get('creator_id')
            description = request.form.get('description', '')
            
            if not all([title, price, creator_id]):
                return jsonify({'error': 'Missing required fields: title, price, creator_id'}), 400
            
            try:
                price = int(price)
            except ValueError:
                return jsonify({'error': 'Price must be a number'}), 400
            
            # Verify creator exists
            creator = db_manager.get_account_by_id(creator_id)
            if not creator:
                return jsonify({'error': 'Creator not found'}), 404
            
            # Обрабатываем загруженное изображение
            image_info, error = process_uploaded_image_with_timeout(file, timeout=app.config['MAX_PROCESSING_TIME'])
            if error:
                return jsonify({'error': f'Image processing failed: {error}'}), 400
            
            # Создаем продукт
            product = db_manager.create_product(
                photo_url=image_info['file_id'],
                creator_id=creator_id,
                title=title,
                price=price,
                description=description
            )
            
            return jsonify(product.to_dict()), 201
            
        else:
            return jsonify({'error': 'Please use form-data for image upload'}), 400

    @app.route('/api/products/<product_id>', methods=['GET'])
    def get_product_detail(product_id):
        product = db_manager.get_product(product_id)
        if not product:
            return jsonify({'error': 'Product not found'}), 404
        
        return jsonify(product.to_dict_with_buyers())

    @app.route('/api/accounts/<account_id>', methods=['GET'])
    def get_account(account_id):
        account = db_manager.get_account_by_id(account_id)
        if not account:
            return jsonify({'error': 'Account not found'}), 404
        
        return jsonify(account.to_dict_with_products())

    # Вспомогательные роуты для изображений (для обратной совместимости)
    @app.route('/api/images/original/<file_id>')
    def serve_original_image(file_id):
        """Отдает оригинальное изображение по ID"""
        try:
            uploads_dir = app.config['UPLOAD_FOLDER']
            for filename in os.listdir(uploads_dir):
                if filename.startswith(f"{file_id}_original."):
                    file_path = os.path.join(uploads_dir, filename)
                    return send_file(file_path)
            return jsonify({'error': 'Original image not found'}), 404
        except Exception as e:
            return jsonify({'error': 'Image not found'}), 404

    @app.route('/api/images/thumbnail/<file_id>')
    def serve_thumbnail_image(file_id):
        """Отдает превью изображения по ID"""
        try:
            thumbnail_path = os.path.join(app.config['UPLOAD_FOLDER'], 'thumbnails', f"{file_id}_thumbnail.jpeg")
            if os.path.exists(thumbnail_path):
                return send_file(thumbnail_path)
            else:
                return jsonify({'error': 'Thumbnail not found'}), 404
        except Exception as e:
            print("Ошибка serve_thumbnail_image:", e)
            return jsonify({'error': 'Thumbnail not found'}), 404

    return app
