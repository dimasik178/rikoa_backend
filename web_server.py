from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from database import db_manager
import os
import datetime
from datetime import timezone, datetime
import uuid
from PIL import Image
from functools import wraps
from config import ServerConfig, ApiConfig, MarketConfig, JWTConfig, MARKET_VERSION
from search_engine import search_engine
from models import Product, Subscription
from jwt_manager import jwt_manager
from dotenv import load_dotenv
    
def create_app():
    load_dotenv()  # Загружаем переменные
    
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
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'thumbnails'), exist_ok=True)
    
    # Инициализация базы данных
    db_manager.init_app(app)
    
    # ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========
    
    def allowed_file(filename):
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']
    
    def process_uploaded_image(file):
        """Обрабатывает загруженное изображение"""
        try:
            file.seek(0, os.SEEK_END)
            file_size = file.tell()
            file.seek(0)
            
            if file_size > 15 * 1024 * 1024:
                return None, "Файл слишком большой (максимум 15MB)"
            
            image = Image.open(file)
            width, height = image.size
            
            if width > app.config['MAX_IMAGE_DIMENSION'] or height > app.config['MAX_IMAGE_DIMENSION']:
                return None, f"Размеры изображения слишком большие (максимум {app.config['MAX_IMAGE_DIMENSION']}x{app.config['MAX_IMAGE_DIMENSION']})"
            
            if image.format not in ['JPEG', 'PNG', 'GIF', 'WEBP', 'BMP', 'TIFF']:
                return None, "Неподдерживаемый формат изображения"
            
            # Генерируем уникальный ID для файла
            file_id = str(uuid.uuid4())
            original_extension = image.format.lower()
            
            # Создаем превью
            thumbnail_size = (800, 800)
            thumbnail_filename = f"{file_id}_thumbnail.{original_extension}"
            thumbnail_path = os.path.join(app.config['UPLOAD_FOLDER'], 'thumbnails', thumbnail_filename)
            
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
        """Получает параметр is_active из запроса"""
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
        is_active = get_is_active_param()
        
        return jsonify(current_account.to_dict_with_products(is_active=is_active))
    
    # Обновление токена
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
    
    # 5. Список товаров (главная страница)
    @app.route('/api/products', methods=['GET'])
    def get_products():
        page = request.args.get('page', 1, type=int)
        is_active = get_is_active_param()
        
        # Без токена показываем только активные товары
        if not request.headers.get('Authorization'):
            is_active = True
        
        # Получаем пагинацию
        pagination = db_manager.get_products_paginated(
            page=page, 
            per_page=ApiConfig.PRODUCTS_PER_PAGE,
            is_active=is_active
        )
        
        products_data = []
        
        # Получаем токен из заголовка
        token = None
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
        
        if not token:
            # Без токена - общий вид
            products_data = [
                product.to_dict_public(show_is_active=False) 
                for product in pagination.items
                if product.to_dict_public(show_is_active=False) is not None
            ]
        else:
            # С токеном - определяем тип пользователя
            payload = jwt_manager.decode_token(token)
            user_id = payload.get('sub')
            account = db_manager.get_account_by_id(user_id)
            if account:
                for product in pagination.items:
                    if product.creator_id == account.id:
                        # Продавец
                        products_data.append(product.to_dict_for_creator())
                    else:
                        # Проверяем активную подписку
                        subscription = Subscription.query.filter_by(
                            subscriber_id=account.id,
                            product_id=product.id,
                            is_active=True
                        ).first()
                        
                        if subscription:
                            # Подписчик
                            products_data.append(
                                product.to_dict_for_subscriber(subscription.subscription_price)
                            )
                        else:
                            # Просто пользователь
                            products_data.append(product.to_dict_public(show_is_active=False))
            else:
                products_data = [
                    product.to_dict_public(show_is_active=False) 
                    for product in pagination.items
                    if product.to_dict_public(show_is_active=False) is not None
                ]
        
        return jsonify({
            'data': products_data,
            'pagination': {
                'page': page,
                'per_page': ApiConfig.PRODUCTS_PER_PAGE,
                'total': pagination.total,
                'pages': pagination.pages
            }
        })
    
    # 6. Подробная информация о товаре
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
        
        # Если товар неактивен и нет токена - 400
        if not product.is_active and not token:
            return jsonify({'error': 'Товар не найден или неактивен'}), 400
        
        if not token:
            # Без токена - показываем только если товар активен
            if not product.is_active:
                return jsonify({'error': 'Товар не найден или неактивен'}), 400
            return jsonify(product.to_dict_detailed_public(show_is_active=False))
        
        # С токеном
        payload = jwt_manager.decode_token(token)
        user_id = payload.get('sub')
        account = db_manager.get_account_by_id(user_id)
        
        if not account:
            return jsonify({'error': 'Пользователь не найден'}), 401
        
        # Проверяем права доступа к is_active
        show_is_active = False
        if product.creator_id == account.id:
            # Продавец - всегда видит is_active
            show_is_active = True
        else:
            # Проверяем активную подписку
            subscription = Subscription.query.filter_by(
                subscriber_id=account.id,
                product_id=product.id,
                is_active=True
            ).first()
            if subscription:
                # Подписчик - видит is_active
                show_is_active = True
        
        # Если товар неактивен и пользователь не продавец/подписчик - 400
        if not product.is_active and not show_is_active:
            return jsonify({'error': 'Товар не найден или неактивен'}), 400
        
        if product.creator_id == account.id:
            # Продавец
            return jsonify(product.to_dict_for_creator())
        else:
            # Ищем любую подписку пользователя на товар
            subscription = Subscription.query.filter_by(
                subscriber_id=account.id,
                product_id=product.id
            ).first()
            
            if subscription:
                # Подписчик (активный или неактивный)
                return jsonify(product.to_dict_for_subscriber(subscription.subscription_price))
            else:
                # Просто пользователь
                return jsonify(product.to_dict_detailed_public(show_is_active=show_is_active))
    
    # 7. Создание товара
    @app.route('/api/products', methods=['POST'])
    @token_required
    def create_product(current_account):
        if request.content_type and 'multipart/form-data' in request.content_type:
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
            
            # Валидация длины
            if len(title) < MarketConfig.MIN_TITLE_LENGTH:
                return jsonify({'error': f'Название должно быть не менее {MarketConfig.MIN_TITLE_LENGTH} символов'}), 400
            
            if len(title) > MarketConfig.MAX_TITLE_LENGTH:
                return jsonify({'error': f'Название должно быть не более {MarketConfig.MAX_TITLE_LENGTH} символов'}), 400
            
            if len(description) > MarketConfig.MAX_DESCRIPTION_LENGTH:
                return jsonify({'error': f'Описание должно быть не более {MarketConfig.MAX_DESCRIPTION_LENGTH} символов'}), 400
            
            # Обработка изображения
            image_info, error = process_uploaded_image(file)
            if error:
                return jsonify({'error': f'Ошибка обработки изображения: {error}'}), 400
            
            try:
                product = db_manager.create_product(
                    creator_id=current_account.id,
                    title=title,
                    price=price,
                    description=description,
                    photo_url=image_info['file_id']
                )
                
                return jsonify(product.to_dict_for_creator()), 201
                
            except ValueError as e:
                return jsonify({'error': str(e)}), 400
            except Exception as e:
                return jsonify({'error': 'Ошибка создания товара'}), 500
            
        else:
            return jsonify({'error': 'Используйте form-data для загрузки изображений'}), 400
    
    # 8. Изменение цены товара
    @app.route('/api/products/<product_id>/price', methods=['PUT'])
    @token_required
    def update_product_price(current_account, product_id):
        data = get_json_data()
        
        if not data or 'new_price' not in data:
            return jsonify({'error': 'Отсутствует новая цена'}), 400
        
        try:
            new_price = int(data['new_price'])
        except ValueError:
            return jsonify({'error': 'Цена должна быть числом'}), 400
        
        try:
            product = db_manager.update_product_price(
                product_id=product_id,
                seller_id=current_account.id,
                new_price=new_price
            )
            
            return jsonify(product.to_dict_for_creator())
            
        except ValueError as e:
            return jsonify({'error': str(e)}), 400
        except Exception as e:
            return jsonify({'error': 'Ошибка изменения цены'}), 500
    
    # 9. Подписка на товар
    @app.route('/api/products/<product_id>/subscribe', methods=['POST'])
    @token_required
    def subscribe_to_product(current_account, product_id):
        try:
            result = db_manager.subscribe_to_product(current_account.id, product_id)
            return jsonify(result)
            
        except ValueError as e:
            return jsonify({'error': str(e)}), 400
        except Exception as e:
            return jsonify({'error': 'Ошибка подписки'}), 500
    
    # 10. Отписка от товара
    @app.route('/api/products/<product_id>/unsubscribe', methods=['POST'])
    @token_required
    def unsubscribe_from_product(current_account, product_id):
        try:
            result = db_manager.unsubscribe_from_product(current_account.id, product_id)
            return jsonify(result)
            
        except ValueError as e:
            return jsonify({'error': str(e)}), 400
        except Exception as e:
            return jsonify({'error': 'Ошибка отписки'}), 500
    
    # 11. Снятие товара с продажи
    @app.route('/api/products/<product_id>/remove', methods=['POST'])
    @token_required
    def remove_product_from_sale(current_account, product_id):
        try:
            result = db_manager.remove_product(product_id, current_account.id)
            return jsonify(result)
        except ValueError as e:
            return jsonify({'error': str(e)}), 400
        except Exception as e:
            return jsonify({'error': 'Ошибка снятия товара'}), 500
    
    # 13. Поиск товаров
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
            # Поиск всегда возвращает только активные товары
            products = db_manager.get_all_products(is_active=True)
            
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
                product_dict = product.to_dict_public(show_is_active=False)
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
    
    # 14. Получение изображения
    @app.route('/api/images/thumbnail/<file_id>')
    def serve_thumbnail_image(file_id):
        try:
            product = db_manager.get_product_by_photo_url(file_id)
            if not product or not product.is_active:
                return jsonify({'error': 'Товар не найден'}), 404
            
            # Пытаемся найти файл
            for ext in ['jpeg', 'jpg', 'png', 'gif', 'webp', 'bmp', 'tiff']:
                thumbnail_path = os.path.join(
                    app.config['UPLOAD_FOLDER'], 
                    'thumbnails', 
                    f"{file_id}_thumbnail.{ext}"
                )
                if os.path.exists(thumbnail_path):
                    return send_file(thumbnail_path)
            
            return jsonify({'error': 'Изображение не найдено'}), 404
            
        except Exception as e:
            return jsonify({'error': 'Ошибка загрузки изображения'}), 404
    
    # 15. Получение подписок пользователя
    @app.route('/api/account/subscriptions', methods=['GET'])
    @token_required
    def get_user_subscriptions(current_account):
        is_active = get_is_active_param()
        
        subscriptions = db_manager.get_user_subscriptions(
            current_account.id, 
            is_active=is_active
        )
        
        # Фильтруем по активности товара
        filtered_subscriptions = []
        for subscription in subscriptions:
            product = db_manager.get_product(subscription.product_id)
            if product and product.is_active == is_active:
                sub_data = subscription.to_dict()
                filtered_subscriptions.append(sub_data)
        
        return jsonify({
            'data': filtered_subscriptions
        })
    
    # 16. Объявление банкротства
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
