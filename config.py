from dotenv import load_dotenv
import os 
# 🔧 КОНФИГУРАЦИЯ ПРОЕКТА "МАРКЕТПЛЕЙС С БОНУСАМИ"

#===================================[ Изменения ]====================================#
#                                    Версия: 4.1                                     #
#         Обновил часть бизнеслогики: теперь каждый товар имеет собственного         #
#   владельца и нельзя просто так выставлять одновременно нескольким пользователям   #
#         одинаковое изображение. Права на владение передаются взамен на AC!         #
#====================================================================================#

load_dotenv()
MARKET_VERSION = "4.1.3" # Версия проекта, возвращается на /api/health

# 🌱 НАСТРОЙКИ ЗАПОЛНЕНИЯ БАЗЫ ДАННЫХ (для seed.py)
class SeedConfig:
    """Конфигурация сидинга"""
    NUM_USERS = 20                    # Количество пользователей
    NUM_PRODUCTS = 50                 # Количество товаров (Если нужно больше, то добавить больше уникальных изображений)
    PURCHASE_PERCENTAGE = 0.3         # Процент товаров, которые будут куплены (30%)
    MAX_PURCHASES_PER_PRODUCT = 1     # Максимум покупок одного товара (1 = каждый товар покупается только один раз)

# 🔐 JWT НАСТРОЙКИ
class JWTConfig:
    """Конфигурация JWT токенов"""
    SECRET_KEY = os.getenv("JWT_SECRET_KEY")
    ALGORITHM = os.getenv("JWT_ALGORITHM")
    ACCESS_TOKEN_EXPIRES = os.getenv("JWT_ACCESS_TOKEN_EXPIRES") # 1 час в секундах
    REFRESH_TOKEN_EXPIRES = os.getenv("JWT_REFRESH_TOKEN_EXPIRES") # 30 дней в секундах
    TOKEN_LOCATION = 'headers'  # 'cookies'

class AccountNamesConfig:
    """Конфигурация полей аккаунта"""
    MIN_NICKNAME_LENGTH = 3
    MAX_NICKNAME_LENGTH = 80
    MIN_EMAIL_LENGTH = 5
    MAX_EMAIL_LENGTH = 120
    MIN_PASSWORD_LENGTH = 6

# 💰 ЭКОНОМИЧЕСКАЯ СИСТЕМА
class MarketConfig:
    """Конфигурация рыночных правил"""
    
    # БАЛАНС И ЦЕНЫ
    STARTING_BALANCE = 100           # Начальный баланс пользователя
    BANKRUPTCY_RESET_BALANCE = 100   # Баланс после банкротства
    REGISTRATION_BONUS = 200         # Бонус за регистрацию
    DAILY_BONUS_AMOUNT = 50          # Ежедневный бонус
    DAILY_BONUS_MAX_BALANCE = 500    # Максимальный баланс для получения бонуса
    
    # КОМИССИЯ
    COMMISSION_PERCENT = 0.05        # 5% комиссия с продажи (0.05 = 5%)
    
    # ЦЕНЫ ТОВАРОВ
    MIN_PRODUCT_PRICE = 10           # Минимальная цена товара
    MAX_PRODUCT_PRICE = 10000        # Максимальная цена товара
    
    # ВЫСТАВЛЕНИЕ ТОВАРА
    MAX_ACTIVE_PRODUCTS_PER_SELLER = 8  # Максимально активных товаров у продавца
    
    # ВРЕМЕННЫЕ НАСТРОЙКИ
    PRICE_UPDATE_TIME = "00:00"       # 0:00 - время обновления истории баланса
    BALANCE_HISTORY_DAYS = 30         # Дней в графике баланса
    
    # ВАЛИДАЦИЯ
    MIN_TITLE_LENGTH = 3
    MAX_TITLE_LENGTH = 100
    MIN_DESCRIPTION_LENGTH = 10
    MAX_DESCRIPTION_LENGTH = 1000

# 🖼️ КОНФИГУРАЦИЯ ВОДЯНЫХ ЗНАКОВ
class WatermarkConfig:
    """Конфигурация водяных знаков"""
    WATERMARK_TEXT = "DEMO_ART_MARKET"           # Текст водяного знака
    WATERMARK_OPACITY = 0.6                      # Непрозрачность (0-1) - чем больше значение, тем отчётливее видно вотермарку
    WATERMARK_FONT_SIZE_RATIO = 0.05             # Размер шрифта от ширины изображения
    WATERMARK_FONT_PATH = "fonts/Roboto-Regular.ttf"  # Путь к файлу шрифта (относительно корня проекта)
    WATERMARK_MIN_FONT_SIZE = 16                 # Минимальный размер шрифта в пикселях

# ⚙️ НАСТРОЙКИ СЕРВЕРА
class ServerConfig:
    """Конфигурация сервера"""
    
    SECRET_KEY = os.getenv("SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # НАСТРОЙКИ ЗАГРУЗКИ ФАЙЛОВ
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    UPLOAD_FOLDER = 'uploads'
    ORIGINALS_FOLDER = 'uploads/originals'      # Оригинальные изображения
    WATERMARKED_FOLDER = 'uploads/watermarked'  # Изображения с водяным знаком
    ALLOWED_EXTENSIONS = {'JPEG', 'PNG', 'GIF', 'WEBP', 'BMP', 'TIFF', 'JPG'}
    MAX_PROCESSING_TIME = 30  # Максимальное время обработки в секундах
    MAX_IMAGE_DIMENSION = 10000  # Максимальный размер изображения
    MIN_IMAGE_DIMENSION = 10  # Минимальный размер изображения

# 📊 НАСТРОЙКИ API
class ApiConfig:
    """Конфигурация возвращаемых данных"""
    PRODUCTS_PER_PAGE = 14           # Количество товаров на страницу
    SEARCH_RESULTS_PER_PAGE = 14     # Количество результатов поиска на страницу
    MAX_SEARCH_RESULTS = 100         # Максимальное количество результатов поиска
    PLAYERS_PER_PAGE = 20            # Количество игроков на страницу в рейтинге
    MIN_PLAYERS_PER_PAGE = 1         # Минимальное количество игроков на странице
    MAX_PLAYERS_PER_PAGE = 100       # Максимальное количество игроков на странице

# 🔍 НАСТРОЙКИ ПОИСКА (оставляем из предыдущей версии)
class SearchConfig:
    """Конфигурация поисковой системы"""

    # Поля для поиска (True = учитывать, False = игнорировать)
    SEARCH_FIELDS = {
        "title": True,        # Название товара
        "description": True,  # Описание товара
        "creator": False,     # Имя продавца (отключено)
    }

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
