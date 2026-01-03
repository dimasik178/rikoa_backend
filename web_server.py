from flask import Flask, request, jsonify, send_file
from database import db_manager
import os
import datetime
from datetime import timezone, datetime
import uuid
from PIL import Image
from functools import wraps
import threading
import time
from config import ServerConfig, ApiConfig, MarketConfig
from search_engine import search_engine
from models import Product, Subscription

def create_app():
    app = Flask(__name__)
    
    # Конфигурация Flask
    app.config['SQLALCHEMY_DATABASE_URI'] = ServerConfig.SQLALCHEMY_DATABASE_URI
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = ServerConfig.SQLALCHEMY_TRACK_MODIFICATIONS
    app.config['SECRET_KEY'] = ServerConfig.SECRET_KEY
    app.config['MAX_CONTENT_LENGTH'] = ServerConfig.MAX_CONTENT_LENGTH
    app.config['UPLOAD_FOLDER'] = ServerConfig.UPLOAD_FOLDER
    app.config['ALLOWED_EXTENSIONS'] = ServerConfig.ALLOWED_EXTENSIONS
    app.config['MAX_PROCESSING_TIME'] = ServerConfig.MAX_PROCESSING_TIME
    app.config['MAX_IMAGE_DIMENSION'] = ServerConfig.MAX_IMAGE_DIMENSION
    
    # Создаем папки для загрузок
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'thumbnails'), exist_ok=True)
    
    # Инициализация базы данных
    db_manager.init_app(app)
    
    # CORS заголовки
    @app.after_request
    def after_request(response):
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
        return response
    
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
        """Декоратор для проверки токена"""
        @wraps(f)
        def decorated(*args, **kwargs):
            token = None
            
            auth_header = request.headers.get('Authorization')
            if auth_header and auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
            
            if not token:
                return jsonify({'success': False, 'error': 'Токен отсутствует'}), 401
            
            account = db_manager.get_account_by_id(token)
            if not account:
                return jsonify({'success': False, 'error': 'Неверный токен'}), 401
            
            return f(account, *args, **kwargs)
        
        return decorated
    
    # ========== ОБРАБОТЧИКИ ОШИБОК ==========
    
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'success': False, 'error': 'Ресурс не найден'}), 404
    
    @app.errorhandler(415)
    def unsupported_media_type(error):
        return jsonify({'success': False, 'error': 'Неподдерживаемый тип медиа'}), 415
    
    @app.errorhandler(413)
    def too_large(error):
        return jsonify({'success': False, 'error': 'Файл слишком большой'}), 413
    
    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({'success': False, 'error': 'Внутренняя ошибка сервера'}), 500
    
    # ========== API ЭНДПОИНТЫ ==========
    
    # 1. Health check
    @app.route('/api/health', methods=['GET'])
    def health_check():
        return jsonify({
            'success': True,
            'status': 'healthy',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'version': '2.0'
        })
    
    # 2. Регистрация
    @app.route('/api/auth/register', methods=['POST'])
    def register():
        data = get_json_data()
        
        if not data or not all(k in data for k in ['login', 'mail', 'password']):
            return jsonify({'success': False, 'error': 'Отсутствуют обязательные поля'}), 400
        
        try:
            account = db_manager.create_account(
                nickname=data['login'],
                mail=data['mail'],
                password=data['password']
            )
            
            account_data = account.to_dict()
            account_data['token'] = account.id
            
            return jsonify({
                'success': True,
                'message': 'Регистрация успешна',
                'data': account_data
            }), 201
            
        except ValueError as e:
            return jsonify({'success': False, 'error': str(e)}), 400
        except Exception as e:
            return jsonify({'success': False, 'error': 'Ошибка регистрации'}), 500
    
    # 3. Вход
    @app.route('/api/auth/login', methods=['POST'])
    def login():
        data = get_json_data()
        
        if not data or not all(k in data for k in ['login', 'password']):
            return jsonify({'success': False, 'error': 'Отсутствуют логин или пароль'}), 400
        
        account = db_manager.get_account_by_credentials(
            nickname=data['login'],
            password=data['password']
        )
        
        if account:
            account_data = account.to_dict()
            account_data['token'] = account.id
            
            return jsonify({
                'success': True,
                'message': 'Вход выполнен',
                'data': account_data
            })
        else:
            return jsonify({'success': False, 'error': 'Неверные учетные данные'}), 401
    
    # 4. Профиль пользователя
    @app.route('/api/auth/profile', methods=['GET'])
    @token_required
    def get_profile(current_account):
        return jsonify({
            'success': True,
            'data': current_account.to_dict_with_products()
        })
    
    # 5. Список товаров (главная страница)
    @app.route('/api/products', methods=['GET'])
    def get_products():
        page = request.args.get('page', 1, type=int)
        
        # Получаем токен из заголовка
        token = None
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
        
        # Получаем пагинацию
        pagination = db_manager.get_products_paginated(
            page=page, 
            per_page=ApiConfig.PRODUCTS_PER_PAGE
        )
        
        products_data = []
        
        if not token:
            # Без токена - общий вид
            products_data = [product.to_dict_public() for product in pagination.items]
        else:
            # С токеном - определяем тип пользователя
            account = db_manager.get_account_by_id(token)
            if account:
                for product in pagination.items:
                    if product.creator_id == account.id:
                        # Продавец
                        products_data.append(product.to_dict_for_creator())
                    else:
                        # Проверяем подписку
                        subscription = Subscription.query.filter_by(
                            subscriber_id=account.id,
                            product_id=product.id,
                            status='active'
                        ).first()
                        
                        if subscription:
                            # Подписчик
                            products_data.append(
                                product.to_dict_for_subscriber(subscription.subscription_price)
                            )
                        else:
                            # Просто пользователь
                            products_data.append(product.to_dict_public())
            else:
                products_data = [product.to_dict_public() for product in pagination.items]
        
        return jsonify({
            'success': True,
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
            return jsonify({'success': False, 'error': 'Товар не найден'}), 404
        
        # Проверяем статус товара
        if product.status == 'burned':
            # Для прогоревшего товара только базовая информация
            if not token or db_manager.get_account_by_id(token).id != product.creator_id:
                return jsonify({
                    'success': True,
                    'data': {
                        **product.to_dict_public(),
                        'status': 'burned',
                        'message': 'Этот товар прогорел'
                    }
                })
        
        if not token:
            # Без токена
            return jsonify({
                'success': True,
                'data': product.to_dict_detailed_public()
            })
        
        account = db_manager.get_account_by_id(token)
        if not account:
            return jsonify({
                'success': True,
                'data': product.to_dict_detailed_public()
            })
        
        if product.creator_id == account.id:
            # Продавец
            return jsonify({
                'success': True,
                'data': product.to_dict_for_creator()
            })
        else:
            # Проверяем подписку
            subscription = Subscription.query.filter_by(
                subscriber_id=account.id,
                product_id=product.id,
                status='active'
            ).first()
            
            if subscription:
                # Подписчик
                return jsonify({
                    'success': True,
                    'data': product.to_dict_for_subscriber(subscription.subscription_price)
                })
            else:
                # Просто пользователь
                return jsonify({
                    'success': True,
                    'data': product.to_dict_detailed_public()
                })
    
    # 7. Создание товара
    @app.route('/api/products', methods=['POST'])
    @token_required
    def create_product(current_account):
        if request.content_type and 'multipart/form-data' in request.content_type:
            if 'image' not in request.files:
                return jsonify({'success': False, 'error': 'Файл изображения не предоставлен'}), 400
            
            file = request.files['image']
            if file.filename == '':
                return jsonify({'success': False, 'error': 'Файл не выбран'}), 400
            
            if not allowed_file(file.filename):
                return jsonify({'success': False, 'error': 'Неподдерживаемый формат файла'}), 400
            
            title = request.form.get('title')
            price = request.form.get('price')
            description = request.form.get('description', '')
            
            if not all([title, price]):
                return jsonify({'success': False, 'error': 'Отсутствуют обязательные поля'}), 400
            
            try:
                price = int(price)
            except ValueError:
                return jsonify({'success': False, 'error': 'Цена должна быть числом'}), 400
            
            # Валидация длины
            if len(title) < MarketConfig.MIN_TITLE_LENGTH:
                return jsonify({'success': False, 'error': f'Название должно быть не менее {MarketConfig.MIN_TITLE_LENGTH} символов'}), 400
            
            if len(title) > MarketConfig.MAX_TITLE_LENGTH:
                return jsonify({'success': False, 'error': f'Название должно быть не более {MarketConfig.MAX_TITLE_LENGTH} символов'}), 400
            
            if len(description) > MarketConfig.MAX_DESCRIPTION_LENGTH:
                return jsonify({'success': False, 'error': f'Описание должно быть не более {MarketConfig.MAX_DESCRIPTION_LENGTH} символов'}), 400
            
            # Обработка изображения
            image_info, error = process_uploaded_image(file)
            if error:
                return jsonify({'success': False, 'error': f'Ошибка обработки изображения: {error}'}), 400
            
            try:
                product = db_manager.create_product(
                    creator_id=current_account.id,
                    title=title,
                    price=price,
                    description=description,
                    photo_url=image_info['file_id']
                )
                
                return jsonify({
                    'success': True,
                    'message': 'Товар успешно создан',
                    'data': product.to_dict_for_creator()
                }), 201
                
            except ValueError as e:
                return jsonify({'success': False, 'error': str(e)}), 400
            except Exception as e:
                return jsonify({'success': False, 'error': 'Ошибка создания товара'}), 500
            
        else:
            return jsonify({'success': False, 'error': 'Используйте form-data для загрузки изображений'}), 400
    
    # 8. Изменение цены товара
    @app.route('/api/products/<product_id>/price', methods=['PUT'])
    @token_required
    def update_product_price(current_account, product_id):
        data = get_json_data()
        
        if not data or 'new_price' not in data:
            return jsonify({'success': False, 'error': 'Отсутствует новая цена'}), 400
        
        try:
            new_price = int(data['new_price'])
        except ValueError:
            return jsonify({'success': False, 'error': 'Цена должна быть числом'}), 400
        
        try:
            product = db_manager.update_product_price(
                product_id=product_id,
                seller_id=current_account.id,
                new_price=new_price
            )
            
            return jsonify({
                'success': True,
                'message': f'Цена изменена. Новая цена установится в {MarketConfig.PRICE_UPDATE_HOUR}:00',
                'data': product.to_dict_for_creator()
            })
            
        except ValueError as e:
            return jsonify({'success': False, 'error': str(e)}), 400
        except Exception as e:
            return jsonify({'success': False, 'error': 'Ошибка изменения цены'}), 500
    
    # 9. Подписка на товар
    @app.route('/api/products/<product_id>/subscribe', methods=['POST'])
    @token_required
    def subscribe_to_product(current_account, product_id):
        try:
            result = db_manager.subscribe_to_product(current_account.id, product_id)
            return jsonify(result)
            
        except ValueError as e:
            return jsonify({'success': False, 'error': str(e)}), 400
        except Exception as e:
            return jsonify({'success': False, 'error': 'Ошибка подписки'}), 500
    
    # 10. Отписка от товара
    @app.route('/api/products/<product_id>/unsubscribe', methods=['POST'])
    @token_required
    def unsubscribe_from_product(current_account, product_id):
        try:
            result = db_manager.unsubscribe_from_product(current_account.id, product_id)
            return jsonify(result)
            
        except ValueError as e:
            return jsonify({'success': False, 'error': str(e)}), 400
        except Exception as e:
            return jsonify({'success': False, 'error': 'Ошибка отписки'}), 500
    
    # 11. Снятие товара с продажи
    @app.route('/api/products/<product_id>/remove', methods=['POST'])
    @token_required
    def remove_product(current_account, product_id):
        try:
            result = db_manager.remove_product(product_id, current_account.id)
            return jsonify(result)
            
        except ValueError as e:
            return jsonify({'success': False, 'error': str(e)}), 400
        except Exception as e:
            # print(e) # TODO Ошибка, при снятии товара с продажи (500) 
            return jsonify({'success': False, 'error': 'Ошибка снятия товара'}), 500
    
    # 12. Удаление прогоревшего товара
    @app.route('/api/products/<product_id>', methods=['DELETE'])
    @token_required
    def delete_burned_product(current_account, product_id):
        try:
            result = db_manager.delete_burned_product(product_id, current_account.id)
            return jsonify(result)
            
        except ValueError as e:
            return jsonify({'success': False, 'error': str(e)}), 400
        except Exception as e:
            return jsonify({'success': False, 'error': 'Ошибка удаления товара'}), 500
    
    # 13. Поиск товаров
    @app.route('/api/products/search', methods=['GET'])
    def search_products():
        search_term = request.args.get('q', '').strip()
        limit = request.args.get('limit', 20, type=int)
        min_score = request.args.get('min_score', 0.1, type=float)
        
        if not search_term:
            return jsonify({'success': False, 'error': 'Поисковый запрос обязателен'}), 400
        
        if limit <= 0 or limit > 100:
            return jsonify({'success': False, 'error': 'Лимит должен быть от 1 до 100'}), 400
        
        if min_score < 0 or min_score > 1:
            return jsonify({'success': False, 'error': 'Минимальный порог должен быть от 0 до 1'}), 400
        
        try:
            products = db_manager.get_all_active_products()
            
            if not products:
                return jsonify({
                    'success': True,
                    'data': {
                        'results': [],
                        'metadata': {
                            'query': search_term,
                            'total_found': 0,
                            'limit': limit,
                            'min_score': min_score
                        }
                    }
                })
            
            search_results = search_engine.search(
                products=products,
                search_term=search_term,
                max_results=limit
            )
            
            filtered_results = [
                (product, score) for product, score in search_results 
                if score >= min_score
            ]
            
            formatted_results = []
            for product, score in filtered_results:
                product_dict = product.to_dict_public()
                product_dict['relevance_score'] = round(score, 3)
                formatted_results.append(product_dict)
            
            return jsonify({
                'success': True,
                'data': {
                    'results': formatted_results,
                    'metadata': {
                        'query': search_term,
                        'total_products': len(products),
                        'total_found': len(formatted_results),
                        'limit': limit,
                        'min_score': min_score,
                        'has_more': len(formatted_results) == limit
                    }
                }
            })
            
        except Exception as e:
            app.logger.error(f"Search error: {str(e)}")
            return jsonify({'success': False, 'error': 'Ошибка поиска'}), 500
    
    # 14. Получение изображения
    @app.route('/api/images/thumbnail/<file_id>')
    def serve_thumbnail_image(file_id):
        try:
            product = db_manager.get_product_by_photo_url(file_id)
            if not product or (product.status != 'active' and product.status != 'burned'):
                return jsonify({'success': False, 'error': 'Товар не найден'}), 404
            
            # Пытаемся найти файл
            for ext in ['jpeg', 'jpg', 'png', 'gif', 'webp', 'bmp', 'tiff']:
                thumbnail_path = os.path.join(
                    app.config['UPLOAD_FOLDER'], 
                    'thumbnails', 
                    f"{file_id}_thumbnail.{ext}"
                )
                if os.path.exists(thumbnail_path):
                    return send_file(thumbnail_path)
            
            return jsonify({'success': False, 'error': 'Изображение не найдено'}), 404
            
        except Exception as e:
            return jsonify({'success': False, 'error': 'Ошибка загрузки изображения'}), 404
    
    # 15. Получение подписок пользователя
    @app.route('/api/account/subscriptions', methods=['GET'])
    @token_required
    def get_user_subscriptions(current_account):
        subscriptions = db_manager.get_user_subscriptions(current_account.id)
        
        subscriptions_data = []
        for subscription in subscriptions:
            product = db_manager.get_product(subscription.product_id)
            if product:
                sub_data = subscription.to_dict()
                sub_data['product'] = product.to_dict_public()
                subscriptions_data.append(sub_data)
        
        return jsonify({
            'success': True,
            'data': subscriptions_data
        })
    
    # # 16. Получение подписчиков товара TODO Возможно лишний роут
    # @app.route('/api/products/<product_id>/subscribers', methods=['GET'])
    # def get_product_subscribers(product_id):
    #     product = db_manager.get_product(product_id)
    #     if not product:
    #         return jsonify({'success': False, 'error': 'Товар не найден'}), 404
        
    #     subscribers = db_manager.get_product_subscribers(product_id)
        
    #     subscribers_data = []
    #     for subscription in subscribers:
    #         account = db_manager.get_account_by_id(subscription.subscriber_id)
    #         if account:
    #             subscribers_data.append({
    #                 'account': account.to_dict(),
    #                 'subscription_price': subscription.subscription_price,
    #                 'current_price': product.current_price
    #             })
        
    #     return jsonify({
    #         'success': True,
    #         'data': {
    #             'product': product.to_dict_public(),
    #             'subscribers': subscribers_data,
    #             'total': len(subscribers_data)
    #         }
    #     })
    
    return app
