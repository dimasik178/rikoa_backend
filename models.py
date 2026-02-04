from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import desc
from sqlalchemy.orm import relationship
import uuid
import json
from config import MarketConfig

db = SQLAlchemy()

def generate_uuid():
    return str(uuid.uuid4())

def utc_now():
    """Возвращает UTC datetime без информации о часовом поясе, как это делал utcnow()"""
    return datetime.now(timezone.utc).replace(tzinfo=None)

class Account(db.Model):
    __tablename__ = 'accounts'
    
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    nickname = db.Column(db.String(80), unique=True, nullable=False)
    mail = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime, default=utc_now)
    
    # 💰 ТОЛЬКО БАЛАНС
    balance = db.Column(db.Integer, default=MarketConfig.STARTING_BALANCE)
    
    # 🏦 БАНКРОТСТВО
    bankruptcy_count = db.Column(db.Integer, default=0)  # Счетчик банкротств
    last_bankruptcy = db.Column(db.DateTime, nullable=True)  # Дата последнего банкротства
    can_declare_bankruptcy = db.Column(db.Boolean, default=True)  # Может ли объявить банкротство

    # Relationships
    products = relationship("Product", back_populates="creator")
    subscriptions = relationship("Subscription", back_populates="subscriber")
    
    def to_dict(self):
        """Базовая информация об аккаунте"""
        result = {
            'id': self.id,
            'nickname': self.nickname,
            'mail': self.mail,
            'created_at': self.created_at.isoformat(),
            'balance': self.balance,
            'can_declare_bankruptcy': self.can_declare_bankruptcy,
            'bankruptcy_count': self.bankruptcy_count,
        }
        # Добавляем информацию о банкротстве если есть
        if self.bankruptcy_count > 0:
            result['last_bankruptcy'] = self.last_bankruptcy.isoformat()
        return result
    
    def to_dict_with_products(self, is_active=True):
        """Информация с товарами и подписками с фильтрацией по is_active"""
        data = self.to_dict()
        
        # Товары продавца с фильтрацией по is_active
        data['products'] = [
            product.to_dict_for_creator() 
            for product in self.products 
            if product.is_active == is_active
        ]
        
        # Подписки пользователя с фильтрацией по is_active товара
        data['subscriptions'] = [
            subscription.to_dict() 
            for subscription in self.subscriptions
            if subscription.is_active == is_active and subscription.product.is_active == is_active
        ]
        
        return data

    @staticmethod
    def get_rating_paginated(page: int = 1, per_page: int = 20):
        """Получает рейтинг игроков по балансу с пагинацией"""
        return Account.query.order_by(
            desc(Account.balance)
        ).paginate(page=page, per_page=per_page, error_out=False)

class Product(db.Model):
    __tablename__ = 'products'
    
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    creator_id = db.Column(db.String(36), db.ForeignKey('accounts.id'), nullable=False)
    
    # 📦 ОСНОВНАЯ ИНФОРМАЦИЯ
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    photo_url = db.Column(db.String(500), nullable=False)  # file_id
    created_at = db.Column(db.DateTime, default=utc_now)
    
    # 💰 ЦЕНЫ И ПОРТФЕЛЬ
    current_price = db.Column(db.Integer, nullable=False)      # Цена на сегодня
    next_day_price = db.Column(db.Integer, nullable=False)     # Цена на завтра
    portfolio = db.Column(db.Integer, default=0)               # Текущий портфель
    startup_capital = db.Column(db.Integer, nullable=False)    # Стартовый капитал продавца
    
    # 📊 ИСТОРИЯ ЦЕН (массив 6 чисел)
    price_history = db.Column(db.Text, default='[]')  # JSON: массив цен за 6 дней
    
    # 📍 СТАТУС (заменен на is_active)
    is_active = db.Column(db.Boolean, default=True)  # True = активен, False = неактивен (прогорел/снят)
    
    # СЧЕТЧИК ПОДПИСЧИКОВ (переименован)
    subscribers_count = db.Column(db.Integer, default=0)
    
    # ДЕНЬГИ С ПОДПИСОК (может быть отрицательным!)
    subscriptions_money = db.Column(db.Integer, default=0)
    
    # Relationships
    creator = relationship("Account", back_populates="products")
    subscriptions = relationship("Subscription", back_populates="product")
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # При создании next_day_price = current_price
        if 'current_price' in kwargs:
            self.next_day_price = kwargs['current_price']
        
        # Инициализация истории цен нулями
        self.price_history = json.dumps([0] * MarketConfig.PRICE_HISTORY_DAYS)
    
    def update_price_history(self):
        """Обновляет историю цен (вызывается в 0:00)"""
        history = json.loads(self.price_history)
        history.pop(0)  # Удаляем самую старую цену
        history.append(self.current_price)  # Добавляем вчерашнюю цену
        self.price_history = json.dumps(history)
        
        # Применяем next_day_price как новую текущую цену
        self.current_price = self.next_day_price
    
    def get_price_history_array(self):
        """Возвращает массив цен для графика"""
        return json.loads(self.price_history)
    
    def to_dict_public(self, show_is_active=False):
        """Общий вид карточки (для главной страницы) - только is_active==True"""
        if not self.is_active and not show_is_active:
            return None  # Не показываем неактивные товары всем
        
        result = {
            'id': self.id,
            'title': self.title,
            'creator': {
                'id': self.creator.id,
                'nickname': self.creator.nickname
            },
            'current_price': self.current_price,
            'photo_url': f"/api/images/thumbnail/{self.photo_url}",
            'subscribers_count': self.subscribers_count
        }
        
        # Показываем is_active только если явно запрошено
        if show_is_active:
            result['is_active'] = self.is_active
            
        return result
    
    def to_dict_detailed_public(self, show_is_active=False):
        """Подробный вид для всех пользователей"""
        basic_info = self.to_dict_public(show_is_active)
        if basic_info is None:
            return None
            
        return {
            **basic_info,
            'description': self.description,
            'created_at': self.created_at.isoformat(),
            'price_history': self.get_price_history_array(),
        }
    
    def to_dict_for_subscriber(self, subscription_price):
        """Данные для подписчика"""
        data = self.to_dict_detailed_public(show_is_active=True)
        data['subscription_price'] = subscription_price  # Цена, по которой подписался
        return data
    
    def to_dict_for_creator(self):
        """Данные для продавца (владельца)"""
        data = self.to_dict_detailed_public(show_is_active=True)
        if data:
            data['next_day_price'] = self.next_day_price
            data['portfolio'] = self.portfolio
            data['startup_capital'] = self.startup_capital
            data['subscriptions_money'] = self.subscriptions_money
        else:
            # Для неактивных товаров
            data = {
                'id': self.id,
                'title': self.title,
                'is_active': self.is_active,
                'current_price': self.current_price,
                'portfolio': self.portfolio,
                'startup_capital': self.startup_capital,
                'subscriptions_money': self.subscriptions_money
            }
        
        return data
    
    def can_be_listed_by(self, account):
        """Проверяет, может ли пользователь выставить новый товар"""
        if self.creator_id != account.id:
            return False
        
        # Подсчитываем активные товары продавца
        active_products_count = len([
            p for p in account.products 
            if p.is_active
        ])
        
        return active_products_count < MarketConfig.MAX_ACTIVE_PRODUCTS_PER_SELLER

class Subscription(db.Model):
    __tablename__ = 'subscriptions'
    
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    subscriber_id = db.Column(db.String(36), db.ForeignKey('accounts.id'), nullable=False)
    product_id = db.Column(db.String(36), db.ForeignKey('products.id'), nullable=False)
    
    # 💰 ФИНАНСОВЫЕ ДАННЫЕ
    subscription_price = db.Column(db.Integer, nullable=False)  # Цена при подписке
    is_active = db.Column(db.Boolean, default=True)  # True = активна, False = отменена
    
    # Relationships
    subscriber = relationship("Account", back_populates="subscriptions")
    product = relationship("Product", back_populates="subscriptions")
    
    def to_dict(self):
        """Информация о подписке"""
        product_info = None
        if self.product:
            product_info = self.product.to_dict_public(show_is_active=True)
        
        return {
            'id': self.id,
            'product_id': self.product_id,
            'product': product_info,
            'subscription_price': self.subscription_price,
            'current_price': self.product.current_price if self.product else 0,
            'is_active': self.is_active
        }
