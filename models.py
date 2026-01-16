from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
import uuid
import json
from config import MarketConfig

db = SQLAlchemy()

def generate_uuid():
    return str(uuid.uuid4())

class Account(db.Model):
    __tablename__ = 'accounts'
    
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    nickname = db.Column(db.String(80), unique=True, nullable=False)
    mail = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
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
            'createdAt': self.created_at.isoformat(),
            'balance': self.balance,
            'can_declare_bankruptcy': self.can_declare_bankruptcy,
            'bankruptcy_count': self.bankruptcy_count,
        }
        # Добавляем информацию о банкротстве если есть
        if self.bankruptcy_count > 0:
            result['last_bankruptcy'] = self.last_bankruptcy.isoformat()
        return result
    
    def to_dict_with_products(self):
        """Информация с товарами и подписками"""
        data = self.to_dict()
        
        # Активные товары продавца
        data['products'] = [
            product.to_dict_for_creator() 
            for product in self.products 
            if product.status in ['active', 'burned']
        ]
        
        # Активные подписки пользователя
        data['subscriptions'] = [
            subscription.to_dict() 
            for subscription in self.subscriptions
        ]
        
        return data

class Product(db.Model):
    __tablename__ = 'products'
    
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    creator_id = db.Column(db.String(36), db.ForeignKey('accounts.id'), nullable=False)
    
    # 📦 ОСНОВНАЯ ИНФОРМАЦИЯ
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    photo_url = db.Column(db.String(500), nullable=False)  # file_id
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 💰 ЦЕНЫ И ПОРТФЕЛЬ
    current_price = db.Column(db.Integer, nullable=False)      # Цена на сегодня
    next_day_price = db.Column(db.Integer, nullable=False)     # Цена на завтра
    portfolio = db.Column(db.Integer, default=0)               # Текущий портфель
    startup_capital = db.Column(db.Integer, nullable=False)    # Стартовый капитал продавца
    
    # 📊 ИСТОРИЯ ЦЕН (массив 6 чисел)
    price_history = db.Column(db.Text, default='[]')  # JSON: массив цен за 6 дней
    
    # 📍 СТАТУС
    status = db.Column(db.String(20), default='active')  # 'active', 'burned', 'burned_hidden'
    
    # СЧЕТЧИК ПОДПИСЧИКОВ
    active_subscriptions_count = db.Column(db.Integer, default=0)
    
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
    
    def to_dict_public(self, show_secret_data=False):
        """Общий вид карточки (для главной страницы)"""
        if self.status != 'active' and not show_secret_data:
            return None  # Не показываем burned товары всем
        
        return {
            'id': self.id,
            'title': self.title,
            'creator': {
                'id': self.creator.id,
                'nickname': self.creator.nickname
            },
            'current_price': self.current_price,
            'photo_url': f"/api/images/thumbnail/{self.photo_url}",
            'status': self.status,
            'active_subscriptions_count': self.active_subscriptions_count
        }
    
    def to_dict_detailed_public(self, show_secret_data=False):
        """Подробный вид для всех пользователей"""
        basic_info = self.to_dict_public(show_secret_data)
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
        data = self.to_dict_detailed_public(show_secret_data=True)
        data['subscription_price'] = subscription_price  # Цена, по которой подписался
        return data
    
    def to_dict_for_creator(self):
        """Данные для продавца (владельца)"""
        if self.status == 'burned_hidden':
            return None  # Скрытые товары не показываем даже продавцу
        
        data = self.to_dict_detailed_public(show_secret_data=True)
        if not data:  # Если товар burned, to_dict_detailed_public вернет None
            data = {
                'id': self.id,
                'title': self.title,
                'status': self.status,
                'current_price': self.current_price,
                'portfolio': self.portfolio,
                'startup_capital': self.startup_capital,
                'subscriptions_money' : self.subscriptions_money,
                'message': 'Товар прогорел'
            }
        else:
            data['next_day_price'] = self.next_day_price
            data['portfolio'] = self.portfolio
            data['startup_capital'] = self.startup_capital
            data['subscriptions_money'] = self.subscriptions_money
        
        return data
    
    def can_be_listed_by(self, account):
        """Проверяет, может ли пользователь выставить новый товар"""
        if self.creator_id != account.id:
            return False
        
        # Подсчитываем активные товары продавца
        active_products_count = len([
            p for p in account.products 
            if p.status == 'active'
        ])
        
        return active_products_count < MarketConfig.MAX_ACTIVE_PRODUCTS_PER_SELLER

class Subscription(db.Model):
    __tablename__ = 'subscriptions'
    
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    subscriber_id = db.Column(db.String(36), db.ForeignKey('accounts.id'), nullable=False)
    # product_id = db.Column(db.String(36), db.ForeignKey('products.id', ondelete='SET NULL'), nullable=True)
    product_id = db.Column(db.String(36), db.ForeignKey('products.id'), nullable=False)
    
    # 💰 ФИНАНСОВЫЕ ДАННЫЕ
    subscription_price = db.Column(db.Integer, nullable=False)  # Цена при подписке
    status = db.Column(db.String(20), default='active')  # 'active', 'cancelled'
    
    # Relationships
    subscriber = relationship("Account", back_populates="subscriptions")
    product = relationship("Product", back_populates="subscriptions")
    
    def to_dict(self):
        """Информация о подписке"""
        product_info = None
        if self.product:
            if self.status == 'active':
                product_info = self.product.to_dict_public()
            elif self.status == 'cancelled':
                # Для cancelled показываем базовую инфо даже если товар burned
                product_info = {
                    'id': self.product.id,
                    'title': self.product.title,
                    'status': self.product.status,
                    'current_price': self.product.current_price if self.product else 0,
                    'photo_url': f"/api/images/thumbnail/{self.product.photo_url}" if self.product else None
                }
        
        return {
            'id': self.id,
            'product_id': self.product_id,
            'product': product_info,
            'subscription_price': self.subscription_price,
            'current_price': self.product.current_price if self.product else 0,
            'status': self.status
        }
