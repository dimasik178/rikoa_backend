from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from database import db_manager
import os
import datetime
from datetime import timezone, datetime
import uuid
import logging
import hashlib
from PIL import Image
from functools import wraps
from config import ServerConfig, ApiConfig, JWTConfig, MARKET_VERSION
from search_engine import search_engine
from jwt_manager import jwt_manager
from dotenv import load_dotenv
from watermark import add_watermark

logger = logging.getLogger(__name__)


def create_app():
    load_dotenv()  # Загружаем переменные
    
    # Обязательные поля
    required_vars = [
        'DATABASE_URL',
        'SECRET_KEY', 
        'JWT_SECRET_KEY',
        'JWT_ALGORITHM',
        'JWT_ACCESS_TOKEN_EXPIRES',
        'JWT_REFRESH_TOKEN_EXPIRES'
    ]
    
    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        raise ValueError(f"❌ Отсутствуют в .env: {', '.join(missing)}")
    
    app = Flask(__name__)
    
    # Инициализация CORS
    CORS(app, resources={
        r"/api/*": {
            "origins": "*",  # Разрешаем все источники
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"],
            "expose_headers": ["Content-Type", "Authorization"],
            "supports_credentials": False,
            "max_age": 600
        }
    })

    # Используем FLASK_ENV для конфигурации
    if os.getenv('FLASK_ENV') == 'development':
        app.config['DEBUG'] = True
        app.config['TESTING'] = True
    else:
        app.config['DEBUG'] = False
        app.config['TESTING'] = False
    
    # Конфигурация Flask
    app.config['SQLALCHEMY_DATABASE_URI'] = ServerConfig.SQLALCHEMY_DATABASE_URI
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = ServerConfig.SQLALCHEMY_TRACK_MODIFICATIONS
    app.config['SECRET_KEY'] = ServerConfig.SECRET_KEY
    app.config['MAX_CONTENT_LENGTH'] = ServerConfig.MAX_CONTENT_LENGTH
    app.config['UPLOAD_FOLDER'] = ServerConfig.UPLOAD_FOLDER
    app.config['ALLOWED_EXTENSIONS'] = ServerConfig.ALLOWED_EXTENSIONS
    app.config['MAX_PROCESSING_TIME'] = ServerConfig.MAX_PROCESSING_TIME
    app.config['MAX_IMAGE_DIMENSION'] = ServerConfig.MAX_IMAGE_DIMENSION
    
    # JWT конфигурация
    app.config['JWT_SECRET_KEY'] = JWTConfig.SECRET_KEY
    app.config['JWT_ALGORITHM'] = JWTConfig.ALGORITHM
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = JWTConfig.ACCESS_TOKEN_EXPIRES
    app.config['JWT_REFRESH_TOKEN_EXPIRES'] = JWTConfig.REFRESH_TOKEN_EXPIRES
    
    # Инициализация JWT
    jwt_manager.init_app(app)
    
    # Создаем папки для загрузок
    os.makedirs(ServerConfig.ORIGINALS_FOLDER, exist_ok=True)
    os.makedirs(ServerConfig.WATERMARKED_FOLDER, exist_ok=True)
    
    # Инициализация базы данных
    db_manager.init_app(app)

    # Загружаем хеши товаров в память при старте
    with app.app_context():
        db_manager.load_hashes_into_memory(app)
    
    # ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========
    
    def allowed_file(filename):
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']
    
    def compute_file_hash_from_stream(file) -> str:
        """Вычисляет SHA256 хеш из файлового потока"""
        hash_sha256 = hashlib.sha256()
        file.seek(0)
        for chunk in iter(lambda: file.read(8192), b""):
            hash_sha256.update(chunk)
        file.seek(0)
        return hash_sha256.hexdigest()

    def compute_file_hash_from_path(file_path: str) -> str:
        """Вычисляет SHA256 хеш файла по пути"""
        hash_sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()

    def process_uploaded_image(file, current_user_id):
        try:
            file.seek(0, os.SEEK_END)
            file_size = file.tell()
            file.seek(0)
            
            if file_size > ServerConfig.MAX_CONTENT_LENGTH:
                return None, "Файл слишком большой (максимум 16MB)"
            
            # 1. Хеш оригинала
            original_hash = compute_file_hash_from_stream(file)
            
            # 2. Проверяем через репозиторий
            can_proceed, msg, stored_owner = db_manager.check_image_can_be_sold(original_hash, current_user_id)
            if not can_proceed:
                return None, msg
            
            # 3. Открываем изображение
            image = Image.open(file)
            width, height = image.size
            
            if width > ServerConfig.MAX_IMAGE_DIMENSION or height > ServerConfig.MAX_IMAGE_DIMENSION:
                return None, f"Размеры изображения слишком большие (максимум {ServerConfig.MAX_IMAGE_DIMENSION}x{ServerConfig.MAX_IMAGE_DIMENSION})"
            
            if image.format not in ['JPEG', 'PNG', 'GIF', 'WEBP', 'BMP', 'TIFF']:
                return None, "Неподдерживаемый формат изображения"
            
            # 4. Генерируем ID и сохраняем оригинал
            file_id = str(uuid.uuid4())
            original_extension = image.format.lower()
            original_filename = f"{file_id}.{original_extension}"
            original_path = os.path.join(ServerConfig.ORIGINALS_FOLDER, original_filename)
            watermarked_path = os.path.join(ServerConfig.WATERMARKED_FOLDER, original_filename)
            
            # Сохраняем оригинал
            if image.format == 'PNG':
                image.save(original_path, optimize=True)
            else:
                if image.mode in ('RGBA', 'LA', 'P'):
                    background = Image.new('RGB', image.size, (255, 255, 255))
                    background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
                    image = background
                image.save(original_path, optimize=True, quality=85)
            
            # 5. Создаём водяную копию
            if not add_watermark(original_path, watermarked_path):
                return None, "Ошибка добавления водяного знака"
            
            # 6. Хеш водяной версии
            watermarked_hash = compute_file_hash_from_path(watermarked_path)
            
            # 7. Проверяем водянку
            if db_manager.is_watermarked_hash(watermarked_hash):
                os.remove(original_path)
                os.remove(watermarked_path)
                return None, "Это изображение уже выставлялось ранее"
            
            image.close()
            
            return {
                'file_id': file_id,
                'original_path': original_path,
                'watermarked_path': watermarked_path,
                'original_hash': original_hash,
                'watermarked_hash': watermarked_hash,
                'action': msg  # 'new' или 'relist'
            }, None
            
        except Exception as e:
            return None, f"Ошибка обработки изображения: {str(e)}"
    
    def get_json_data():
        """Получает JSON данные из запроса"""
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
        """Декоратор для проверки JWT токена"""
        @wraps(f)
        def decorated(*args, **kwargs):
            token = None
            
            auth_header = request.headers.get('Authorization')
            if auth_header and auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
            
            if not token:
                return jsonify({'error': 'Токен отсутствует'}), 401
            
            try:
                payload = jwt_manager.decode_token(token)
                user_id = payload.get('sub')
                
                if not user_id:
                    return jsonify({'error': 'Неверный токен'}), 401
                
                account = db_manager.get_account_by_id(user_id)
                if not account:
                    return jsonify({'error': 'Пользователь не найден'}), 401
                
                # Проверяем, что токен не был отозван (опционально)
                if payload.get('type') != 'access':
                    return jsonify({'error': 'Неверный тип токена'}), 401
                
                return f(account, *args, **kwargs)
                
            except ValueError as e:
                return jsonify({'error': str(e)}), 401
            except Exception as e:
                return jsonify({'error': 'Неверный токен'}), 401
        
        return decorated
    
    def get_is_active_param():
        """Получает параметр is_active из запроса (для совместимости)"""
        is_active_str = request.args.get('is_active', 'true').lower()
        return is_active_str == 'true'
    
    # ========== ОБРАБОТЧИКИ ОШИБОК ==========
    
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Ресурс не найден'}), 404
    
    @app.errorhandler(415)
    def unsupported_media_type(error):
        return jsonify({'error': 'Неподдерживаемый тип медиа'}), 415
    
    @app.errorhandler(413)
    def too_large(error):
        return jsonify({'error': 'Файл слишком большой'}), 413
    
    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({'error': 'Внутренняя ошибка сервера'}), 500
    
    # ========== API ЭНДПОИНТЫ ==========
    
    # 1. Health check
    @app.route('/api/health', methods=['GET'])
    def health_check():
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'version': MARKET_VERSION
        })
    
    # 2. Регистрация
    @app.route('/api/auth/register', methods=['POST'])
    def register():
        data = get_json_data()
        
        if not data or not all(k in data for k in ['login', 'mail', 'password']):
            return jsonify({'error': 'Отсутствуют обязательные поля'}), 400
        
        try:
            account = db_manager.create_account(
                nickname=data['login'],
                mail=data['mail'],
                password=data['password']
            )
            
            # Создаем токены
            access_token = jwt_manager.create_access_token(account.id)
            refresh_token = jwt_manager.create_refresh_token(account.id)
            
            account_data = account.to_dict()
            
            return jsonify({
                'user': account_data,
                'tokens': {
                    'access_token': access_token,
                    'refresh_token': refresh_token,
                    'token_type': 'Bearer'
                }
            }), 201
            
        except ValueError as e:
            return jsonify({'error': str(e)}), 400
        except Exception as e:
            return jsonify({'error': 'Ошибка регистрации'}), 500
    
    # 3. Вход
    @app.route('/api/auth/login', methods=['POST'])
    def login():
        data = get_json_data()
        
        if not data or not all(k in data for k in ['login', 'password']):
            return jsonify({'error': 'Отсутствуют логин или пароль'}), 400
        
        account = db_manager.get_account_by_credentials(
            nickname=data['login'],
            password=data['password']
        )
        
        if account:
            # Создаем токены
            access_token = jwt_manager.create_access_token(account.id)
            refresh_token = jwt_manager.create_refresh_token(account.id)
            
            account_data = account.to_dict()
            
            return jsonify({
                'user': account_data,
                'tokens': {
                    'access_token': access_token,
                    'refresh_token': refresh_token,
                    'token_type': 'Bearer',
                    'expires_in': JWTConfig.ACCESS_TOKEN_EXPIRES
                }
            })
        else:
            return jsonify({'error': 'Неверные учетные данные'}), 401
    
    # 4. Профиль пользователя
    @app.route('/api/auth/profile', methods=['GET'])
    @token_required
    def get_profile(current_account):
        return jsonify(current_account.to_dict_with_products())
    
    # 5. Обновление токена
    @app.route('/api/auth/refresh', methods=['POST'])
    def refresh_token():
        data = get_json_data()
        
        if not data or 'refresh_token' not in data:
            return jsonify({'error': 'Refresh token отсутствует'}), 400
        
        try:
            new_access_token = jwt_manager.refresh_access_token(data['refresh_token'])
            
            if not new_access_token:
                return jsonify({'error': 'Неверный refresh token'}), 401
            
            return jsonify({
                'access_token': new_access_token,
                'token_type': 'Bearer',
                'expires_in': JWTConfig.ACCESS_TOKEN_EXPIRES
            })
            
        except ValueError as e:
            return jsonify({'error': str(e)}), 401
        except Exception:
            return jsonify({'error': 'Ошибка обновления токена'}), 500
    
    # 6. Список товаров (главная страница) - только непроданные, с водяным знаком
    @app.route('/api/products', methods=['GET'])
    def get_products():
        page = request.args.get('page', 1, type=int)
        
        # Получаем пагинацию товаров на продаже
        pagination = db_manager.get_products_on_sale_paginated(
            page=page, 
            per_page=ApiConfig.PRODUCTS_PER_PAGE
        )
        
        products_data = []
        for product in pagination.items:
            product_dict = product.to_dict_public()
            if product_dict:
                products_data.append(product_dict)
        
        return jsonify({
            'data': products_data,
            'pagination': {
                'page': page,
                'per_page': ApiConfig.PRODUCTS_PER_PAGE,
                'total': pagination.total,
                'pages': pagination.pages
            }
        })
    
    # 7. Детальная информация о товаре
    @app.route('/api/products/<product_id>', methods=['GET'])
    def get_product_detail(product_id):
        # Получаем токен
        token = None
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
        
        product = db_manager.get_product(product_id)
        if not product:
            return jsonify({'error': 'Товар не найден'}), 404
        
        # Без токена — только если товар в продаже
        if not token:
            if not product.on_sale:
                return jsonify({'error': 'Товар не найден'}), 404
            return jsonify(product.to_dict_detailed_public())
        
        # С токеном
        try:
            payload = jwt_manager.decode_token(token)
            user_id = payload.get('sub')
            account = db_manager.get_account_by_id(user_id)
            
            if not account:
                return jsonify({'error': 'Товар не найден'}), 404
            
            is_creator = product.creator_id == account.id
            is_owner = product.owner_id == account.id
            
            # Владелец видит всё
            if is_creator or is_owner:
                if is_owner and product.purchased_at:
                    return jsonify(product.to_dict_for_owner())
                return jsonify(product.to_dict_for_creator())
            
            # Не владелец — только если в продаже
            if not product.on_sale:
                return jsonify({'error': 'Товар не найден'}), 404
            
            return jsonify(product.to_dict_detailed_public())
            
        except Exception:
            return jsonify({'error': 'Товар не найден'}), 404
    
    # 8. Создание товара
    @app.route('/api/products', methods=['POST'])
    @token_required
    def create_product(current_account):
        if not (request.content_type and 'multipart/form-data' in request.content_type):
            return jsonify({'error': 'Используйте form-data для загрузки изображений'}), 400
        
        if 'image' not in request.files:
            return jsonify({'error': 'Файл изображения не предоставлен'}), 400
        
        file = request.files['image']
        if file.filename == '':
            return jsonify({'error': 'Файл не выбран'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Неподдерживаемый формат файла'}), 400
        
        title = request.form.get('title')
        price = request.form.get('price')
        description = request.form.get('description', '')
        
        if not all([title, price]):
            return jsonify({'error': 'Отсутствуют обязательные поля'}), 400
        
        try:
            price = int(price)
        except ValueError:
            return jsonify({'error': 'Цена должна быть числом'}), 400
        
        # Обрабатываем изображение
        image_info, error = process_uploaded_image(file, current_account.id)
        if error:
            return jsonify({'error': error}), 400
        
        try:
            if image_info['action'] == 'relist':
                # Перепродажа существующего товара
                product = db_manager.relist_product(
                    original_hash=image_info['original_hash'],
                    owner_id=current_account.id
                )
                return jsonify(product.to_dict_for_creator()), 200
            
            # Новый товар
            product = db_manager.create_product(
                creator_id=current_account.id,
                owner_id=current_account.id,
                title=title,
                price=price,
                description=description,
                photo_url=image_info['file_id'],
                original_hash=image_info['original_hash'],
                watermarked_hash=image_info['watermarked_hash'],
                on_sale=True
            )
            
            # Добавляем в память
            db_manager.add_new_product_to_memory(
                image_info['original_hash'],
                image_info['watermarked_hash'],
                current_account.id
            )
            
            return jsonify(product.to_dict_for_creator()), 201
            
        except ValueError as e:
            return jsonify({'error': str(e)}), 400
        except Exception as e:
            return jsonify({'error': 'Ошибка создания товара'}), 500
    
    # 9. Покупка товара
    @app.route('/api/products/<product_id>/buy', methods=['POST'])
    @token_required
    def buy_product(current_account, product_id):
        try:
            product = db_manager.buy_product(current_account.id, product_id)
            return jsonify(product.to_dict_for_owner()), 200
            
        except ValueError as e:
            return jsonify({'error': str(e)}), 400
        except Exception as e:
            return jsonify({'error': 'Ошибка покупки товара'}), 500
    
    # 10. Снятие товара с продажи (удаление)
    @app.route('/api/products/<product_id>/remove', methods=['POST'])
    @token_required
    def remove_product(current_account, product_id):
        try:
            result = db_manager.remove_product(product_id, current_account.id)
            return jsonify(result), 200
        except ValueError as e:
            return jsonify({'error': str(e)}), 400
        except Exception as e:
            return jsonify({'error': 'Ошибка удаления товара'}), 500
    
    # 11. Поиск товаров
    @app.route('/api/products/search', methods=['GET'])
    def search_products():
        search_term = request.args.get('q', '').strip()
        page = request.args.get('page', 1, type=int)
        min_score = request.args.get('min_score', 0.1, type=float)
        
        if not search_term:
            return jsonify({'error': 'Поисковый запрос обязателен'}), 400
        
        if min_score < 0 or min_score > 1:
            return jsonify({'error': 'Минимальный порог должен быть от 0 до 1'}), 400
        
        try:
            # Поиск всегда возвращает только непроданные товары
            products = db_manager.get_all_active_products()
            
            if not products:
                return jsonify({
                    'results': [],
                    'pagination': {
                        'page': page,
                        'per_page': ApiConfig.SEARCH_RESULTS_PER_PAGE,
                        'total': 0,
                        'pages': 0
                    }
                })
            
            # Получаем все результаты поиска
            search_results = search_engine.search(
                products=products,
                search_term=search_term,
                max_results=ApiConfig.MAX_SEARCH_RESULTS
            )
            
            # Фильтруем по минимальному порогу
            filtered_results = [
                (product, score) for product, score in search_results 
                if score >= min_score
            ]
            
            # Применяем пагинацию
            total_results = len(filtered_results)
            per_page = ApiConfig.SEARCH_RESULTS_PER_PAGE
            total_pages = (total_results + per_page - 1) // per_page
            
            start_idx = (page - 1) * per_page
            end_idx = start_idx + per_page
            paginated_results = filtered_results[start_idx:end_idx]
            
            # Форматируем результаты
            formatted_results = []
            for product, score in paginated_results:
                product_dict = product.to_dict_public()
                if product_dict:
                    product_dict['relevance_score'] = round(score, 3)
                    formatted_results.append(product_dict)
            
            return jsonify({
                'results': formatted_results,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': total_results,
                    'pages': total_pages
                }
            })
            
        except Exception as e:
            app.logger.error(f"Search error: {str(e)}")
            return jsonify({'error': 'Ошибка поиска'}), 500
    
    # 12. Оригинальное изображение (только для владельца)
    @app.route('/api/images/original/<file_id>')
    def serve_original_image(file_id):
        # Проверяем токен
        token = None
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
        
        if not token:
            return jsonify({'error': 'Изображение не найдено'}), 404
        
        try:
            payload = jwt_manager.decode_token(token)
            user_id = payload.get('sub')
            account = db_manager.get_account_by_id(user_id)
            
            if not account:
                return jsonify({'error': 'Изображение не найдено'}), 404
            
            # Находим товар по photo_url
            product = db_manager.get_product_by_photo_url(file_id)
            if not product:
                return jsonify({'error': 'Изображение не найдено'}), 404
            
            # Проверяем права: только создатель или владелец
            is_creator = product.creator_id == account.id
            is_owner = product.owner_id == account.id
            
            if not (is_creator or is_owner):
                return jsonify({'error': 'Изображение не найдено'}), 404
            
            # Ищем файл
            for ext in ['jpeg', 'jpg', 'png', 'gif', 'webp', 'bmp', 'tiff']:
                original_path = os.path.join(ServerConfig.ORIGINALS_FOLDER, f"{file_id}.{ext}")
                if os.path.exists(original_path):
                    return send_file(original_path)
            
            return jsonify({'error': 'Изображение не найдено'}), 404
            
        except Exception as e:
            return jsonify({'error': 'Изображение не найдено'}), 404
    
    # 13. Изображение с водяным знаком (для всех, только непроданные товары)
    @app.route('/api/images/watermarked/<file_id>')
    def serve_watermarked_image(file_id):
        try:
            # Находим товар по photo_url
            product = db_manager.get_product_by_photo_url(file_id)
            
            # Если товар не существует или продан - 404
            if not product or not product.on_sale:
                return jsonify({'error': 'Изображение не найдено'}), 404
            
            # Ищем файл с водяным знаком
            for ext in ['jpeg', 'jpg', 'png', 'gif', 'webp', 'bmp', 'tiff']:
                watermarked_path = os.path.join(ServerConfig.WATERMARKED_FOLDER, f"{file_id}.{ext}")
                if os.path.exists(watermarked_path):
                    return send_file(watermarked_path)
            
            return jsonify({'error': 'Изображение не найдено'}), 404
            
        except Exception as e:
            return jsonify({'error': 'Изображение не найдено'}), 404
    
    # 14. Мои покупки
    @app.route('/api/account/purchases', methods=['GET'])
    @token_required
    def get_user_purchases(current_account):
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        try:
            result = db_manager.get_user_purchases(current_account.id, page, per_page)
            return jsonify(result)
        except Exception as e:
            return jsonify({'error': 'Ошибка получения истории покупок'}), 500
    
    # 15. Мои продажи
    @app.route('/api/account/sales', methods=['GET'])
    @token_required
    def get_user_sales(current_account):
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        try:
            result = db_manager.get_user_sales(current_account.id, page, per_page)
            return jsonify(result)
        except Exception as e:
            return jsonify({'error': 'Ошибка получения истории продаж'}), 500
    
    # 16. Статистика профиля
    @app.route('/api/account/stats', methods=['GET'])
    @token_required
    def get_account_stats(current_account):
        try:
            stats = db_manager.get_account_stats(current_account.id)
            return jsonify(stats)
        except Exception as e:
            return jsonify({'error': 'Ошибка получения статистики'}), 500
    
    # 17. Ежедневный бонус
    @app.route('/api/account/daily-bonus', methods=['POST'])
    @token_required
    def claim_daily_bonus(current_account):
        try:
            result = db_manager.claim_daily_bonus(current_account.id)
            return jsonify(result)
        except ValueError as e:
            return jsonify({'error': str(e)}), 400
        except Exception as e:
            return jsonify({'error': 'Ошибка начисления бонуса'}), 500
    
    # 18. Банкротство
    @app.route('/api/account/bankruptcy', methods=['POST'])
    @token_required
    def declare_bankruptcy(current_account):
        try:
            result = db_manager.declare_bankruptcy(current_account.id)
            return jsonify(result)
        except ValueError as e:
            return jsonify({'error': str(e)}), 400
        except Exception as e:
            return jsonify({'error': 'Ошибка объявления банкротства'}), 500
    
    # 19. Рейтинг игроков
    @app.route('/api/players/rating', methods=['GET'])
    def get_player_rating():
        """Получает рейтинг игроков по балансу (сортировка по убыванию)"""
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', ApiConfig.PLAYERS_PER_PAGE, type=int)
        
        # Валидация параметров
        if per_page < ApiConfig.MIN_PLAYERS_PER_PAGE or per_page > ApiConfig.MAX_PLAYERS_PER_PAGE:
            return jsonify({
                'error': f'Количество игроков на странице должно быть от {ApiConfig.MIN_PLAYERS_PER_PAGE} до {ApiConfig.MAX_PLAYERS_PER_PAGE}'
            }), 400        
        
        try:
            rating_data = db_manager.get_player_rating_paginated(page=page, per_page=per_page)
            
            return jsonify({
                'players': rating_data['players'],
                'pagination': rating_data['pagination']
            })
            
        except Exception as e:
            app.logger.error(f"Error getting player rating: {str(e)}")
            return jsonify({'error': 'Ошибка получения рейтинга игроков'}), 500

    return app
