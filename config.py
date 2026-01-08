from dotenv import load_dotenv
import os 
# 🔧 КОНФИГУРАЦИЯ ПРОЕКТА "РЫНОК ТОВАРОВ С ИНВЕСТИЦИЯМИ"

load_dotenv()

# 🌱 НАСТРОЙКИ ЗАПОЛНЕНИЯ БАЗЫ ДАННЫХ (для seed.py)
NUM_USERS = 15                    # Количество пользователей для сидинга
NUM_PRODUCTS = 20                # Количество товаров для сидинга
PURCHASE_PERCENTAGE = 0.6        # Процент подписок для сидинга

# 🔐 JWT НАСТРОЙКИ
class JWTConfig:
    """Конфигурация JWT токенов"""
    SECRET_KEY = 'your-jwt-secret-key-change-in-production'  # Должно быть в .env
    SECRET_KEY = os.getenv("JWT_SECRET_KEY")
    ALGORITHM = os.getenv("JWT_ALGORITHM")
    ACCESS_TOKEN_EXPIRES = os.getenv("JWT_ACCESS_TOKEN_EXPIRES") # 1 час в секундах
    REFRESH_TOKEN_EXPIRES = os.getenv("JWT_REFRESH_TOKEN_EXPIRES") # 30 дней в секундах
    TOKEN_LOCATION = 'headers'  # 'cookies'

# 💰 ЭКОНОМИЧЕСКАЯ СИСТЕМА
class MarketConfig:
    """Конфигурация рыночных правил"""
    
    # БАЛАНС И ЦЕНЫ
    STARTING_BALANCE = 100           # Начальный баланс пользователя
    MIN_PRODUCT_PRICE = 1            # Минимальная цена товара
    MAX_PRODUCT_PRICE = 10000        # Максимальная цена товара
    
    # ВЫСТАВЛЕНИЕ ТОВАРА
    SELLER_STARTUP_MULTIPLIER = 10   # 10× цена = стартовый капитал продавца
    MAX_ACTIVE_PRODUCTS_PER_SELLER = 8  # Максимально активных товаров у продавца
    
    # ВРЕМЕННЫЕ НАСТРОЙКИ
    PRICE_UPDATE_HOUR = 0            # 0:00 - время обновления цен
    PRICE_HISTORY_DAYS = 6           # Дней в графике цены (6 чисел)
    
    # ВАЛИДАЦИЯ
    MIN_TITLE_LENGTH = 3
    MAX_TITLE_LENGTH = 100
    MIN_DESCRIPTION_LENGTH = 10
    MAX_DESCRIPTION_LENGTH = 1000

# ⚙️ НАСТРОЙКИ СЕРВЕРА
class ServerConfig:
    """Конфигурация сервера"""
    
    # FLASK НАСТРОЙКИ
    SECRET_KEY = 'your-secret-key-here-change-in-production'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///market.db'
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # НАСТРОЙКИ ЗАГРУЗКИ ФАЙЛОВ
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    UPLOAD_FOLDER = 'uploads'
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp', 'tiff'}
    MAX_PROCESSING_TIME = 30  # Максимальное время обработки в секундах
    MAX_IMAGE_DIMENSION = 10000  # Максимальный размер изображения

# 📊 НАСТРОЙКИ API
class ApiConfig:
    """Конфигурация возвращаемых данных"""
    PRODUCTS_PER_PAGE = 14           # Количество товаров на страницу
    MAX_SEARCH_RESULTS = 100         # Максимальное количество результатов поиска

# 🔍 НАСТРОЙКИ ПОИСКА (оставляем из предыдущей версии)
class SearchConfig:
    """Конфигурация поисковой системы"""
    
    # Веса для разных типов совпадений
    WEIGHTS = {
        'exact_title': 50.0,
        'exact_artist': 45.0,
        'exact_match': 40.0,
        'phrase_exact': 25.0,
        'phrase_partial': 12.0,
        'all_words': 20.0,
        'ordered_words': 10.0,
        'word_exact': 8.0,
        'word_partial': 2.0,
        'similarity_high': 10.0,
        'similarity_medium': 5.0,
        'word_similarity': 6.0,
        'number_exact': 15.0,
        'number_partial': 5.0,
    }
    
    # Минимальные пороги для разных типов запросов
    MIN_SCORES = {
        'single_digit': 0.05,
        'short_number': 0.1,
        'single_char': 0.1,
        'two_chars': 0.3,
        'three_chars': 0.4,
        'multi_word': 0.2,
        'default': 0.3
    }
    
    # Штрафы и модификаторы
    PENALTIES = {
        'long_text_ratio': 5.0,
        'long_text_penalty': 0.7,
        'long_number_text_ratio': 10.0,
        'long_number_penalty': 0.8,
        'common_word_penalty': 0.2,
        'short_word_no_match': 0.3,
    }
    
    # Позиционные бонусы
    POSITION_BONUSES = {
        'phrase_exact': 10.0,
        'phrase_partial': 5.0,
    }
    
    # Общие слова для строгой фильтрации
    COMMON_WORDS = {
        'english': {
            'the', 'and', 'with', 'for', 'of', 'in', 'on', 'at', 'to',
            'a', 'an', 'is', 'are', 'this', 'that', 'these', 'those'
        },
        'russian': {
            'и', 'в', 'на', 'с', 'по', 'у', 'о', 'об', 'от', 'до',
            'не', 'но', 'за', 'к', 'из', 'или', 'а', 'же', 'бы', 'ли'
        }
    }
    
    # Параметры нечеткого поиска
    FUZZY_SEARCH = {
        'min_word_length': 4,
        'similarity_threshold_high': 0.9,
        'similarity_threshold_medium': 0.8,
        'word_similarity_threshold': 0.85,
    }
    
    # Параметры поиска чисел
    NUMBER_SEARCH = {
        'title_bonus': 5.0,
    }
    
    # Максимальные значения
    MAX_VALUES = {
        'similarity_text_length': 100,
        'results_limit': 100,
    }
