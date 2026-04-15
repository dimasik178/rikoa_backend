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
    
    # 💰 БАЛАНС И СТАТИСТИКА
    balance = db.Column(db.Integer, default=MarketConfig.STARTING_BALANCE + MarketConfig.REGISTRATION_BONUS)
    total_spent = db.Column(db.Integer, default=0)      # Всего потрачено на покупки
    total_earned = db.Column(db.Integer, default=0)     # Всего заработано с продаж
    
    # 🏦 БАНКРОТСТВО
    bankruptcy_count = db.Column(db.Integer, default=0)  # Счетчик банкротств
    last_bankruptcy = db.Column(db.DateTime, nullable=True)  # Дата последнего банкротства
    can_declare_bankruptcy = db.Column(db.Boolean, default=True)  # Может ли объявить банкротство
    
    # 🎁 БОНУСЫ
    last_daily_bonus = db.Column(db.DateTime, nullable=True)  # Дата последнего получения бонуса
    can_claim_daily_bonus = db.Column(db.Boolean, default=True)  # Может ли получить бонус
    
    # 📊 ИСТОРИЯ БАЛАНСА (массив 30 чисел)
    balance_history = db.Column(db.Text, default='[]')  # JSON: массив балансов за 30 дней

    # Relationships
    products_for_sale = relationship(
        "Product", 
        foreign_keys="Product.owner_id",
        primaryjoin="and_(Account.id == Product.owner_id, Product.on_sale == True)",
        viewonly=True,
        overlaps="purchased_products"
    )
    
    purchased_products = relationship(
        "Product", 
        foreign_keys="Product.owner_id",
        primaryjoin="and_(Account.id == Product.owner_id, Product.on_sale == False)",
        viewonly=True,
        overlaps="products_for_sale"
    )
    
    purchases_as_buyer = relationship("Purchase", foreign_keys="Purchase.buyer_id", back_populates="buyer")
    purchases_as_seller = relationship("Purchase", foreign_keys="Purchase.seller_id", back_populates="seller")
    
    def to_dict(self):
        """Базовая информация об аккаунте"""
        result = {
            'id': self.id,
            'nickname': self.nickname,
            'mail': self.mail,
            'created_at': self.created_at.isoformat(),
            'balance': self.balance,
            'total_spent': self.total_spent,
            'total_earned': self.total_earned,
            'bankruptcy_count': self.bankruptcy_count,
            'can_declare_bankruptcy': self.can_declare_bankruptcy,
        }
        if self.last_bankruptcy:
            result['last_bankruptcy'] = self.last_bankruptcy.isoformat()
        return result
    
    def to_dict_with_products(self):
        """Информация с товарами и покупками"""
        data = self.to_dict()
        
        # Товары на продаже
        data['products_for_sale'] = [
            product.to_dict_for_creator() 
            for product in self.products_for_sale
        ]
        
        # Купленные товары (не в продаже)
        data['purchased_products'] = [
            product.to_dict_for_owner()
            for product in self.purchased_products
        ]
        
        # История баланса
        data['balance_history'] = self.get_balance_history_array()
        data['can_claim_daily_bonus'] = self.can_claim_daily_bonus
        
        return data
    
    def get_balance_history_array(self):
        """Возвращает массив истории баланса"""
        return json.loads(self.balance_history)
    
    def update_balance_history(self):
        """Обновляет историю баланса (вызывается в 00:00)"""
        history = json.loads(self.balance_history)
        history.append(self.balance)
        if len(history) > MarketConfig.BALANCE_HISTORY_DAYS:
            history.pop(0)
        self.balance_history = json.dumps(history)

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
    owner_id = db.Column(db.String(36), db.ForeignKey('accounts.id'), nullable=True)
    
    # 📦 ОСНОВНАЯ ИНФОРМАЦИЯ
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    photo_url = db.Column(db.String(500), nullable=False)  # file_id
    price = db.Column(db.Integer, nullable=False)          # Цена товара
    created_at = db.Column(db.DateTime, default=utc_now)
    
    # 🔐 ЗАКРЕПЛЕНИЕ АВТОРСКИХ ПРАВ
    original_hash = db.Column(db.String(64), nullable=False, unique=True)
    watermarked_hash = db.Column(db.String(64), nullable=False, unique=True)
    
    # 📍 СТАТУС
    on_sale = db.Column(db.Boolean, default=True)  # True = выставлен на продажу
    purchased_at = db.Column(db.DateTime, nullable=True)   # Дата покупки
    
    # Relationships
    creator = relationship("Account", foreign_keys=[creator_id])
    owner = relationship("Account", foreign_keys=[owner_id])
    purchases = relationship("Purchase", back_populates="product")
    
    def to_dict_public(self):
        """Для главной страницы — только товары в продаже"""
        if not self.on_sale:
            return None
        
        return {
            'id': self.id,
            'title': self.title,
            'creator': {
                'id': self.creator.id,
                'nickname': self.creator.nickname
            },
            'price': self.price,
            'photo_url': f"/api/images/watermarked/{self.photo_url}",
        }
    
    def to_dict_detailed_public(self):
        """Подробно для всех — только если в продаже"""
        if not self.on_sale:
            return None
            
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'creator': {
                'id': self.creator.id,
                'nickname': self.creator.nickname
            },
            'price': self.price,
            'photo_url': f"/api/images/watermarked/{self.photo_url}",
            'created_at': self.created_at.isoformat(),
        }
    
    def to_dict_for_creator(self):
        """Для продавца (владельца) — всегда доступно"""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'creator': {
                'id': self.creator.id,
                'nickname': self.creator.nickname
            },
            'price': self.price,
            'photo_url': f"/api/images/original/{self.photo_url}",
            'created_at': self.created_at.isoformat(),
            'on_sale': self.on_sale,
        }
    
    def to_dict_for_owner(self):
        """Для покупателя (владельца купленного товара)"""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'price': self.price,
            'photo_url': f"/api/images/original/{self.photo_url}",
            'creator': {
                'id': self.creator.id,
                'nickname': self.creator.nickname
            },
            'purchased_at': self.purchased_at.isoformat() if self.purchased_at else None,
            'on_sale': self.on_sale,
        }

class Purchase(db.Model):
    __tablename__ = 'purchases'
    
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    buyer_id = db.Column(db.String(36), db.ForeignKey('accounts.id'), nullable=False)
    seller_id = db.Column(db.String(36), db.ForeignKey('accounts.id'), nullable=False)
    product_id = db.Column(db.String(36), db.ForeignKey('products.id', ondelete='SET NULL'), nullable=True)
    
    # 📊 ДАННЫЕ О ПОКУПКЕ
    product_title = db.Column(db.String(200), nullable=False)  # Копия названия товара
    price = db.Column(db.Integer, nullable=False)              # Цена покупки
    commission = db.Column(db.Integer, nullable=False)         # Сгоревшая комиссия
    purchased_at = db.Column(db.DateTime, default=utc_now)
    
    # Relationships
    buyer = relationship("Account", foreign_keys=[buyer_id], back_populates="purchases_as_buyer")
    seller = relationship("Account", foreign_keys=[seller_id], back_populates="purchases_as_seller")
    product = relationship("Product", back_populates="purchases")
    
    def to_dict_for_buyer(self):
        """Данные для покупателя в истории покупок"""
        return {
            'id': self.product_id,
            'title': self.product_title,
            'price': self.price,
            'photo_url': f"/api/images/original/{self.product.photo_url}",
            'purchased_at': self.purchased_at.isoformat(),
            'seller': {
                'id': self.seller.id,
                'nickname': self.seller.nickname
            }
        }
    
    def to_dict_for_seller(self):
        """Данные для продавца в истории продаж"""
        return {
            'id': self.product_id,
            'title': self.product_title,
            'price': self.price,
            'commission': self.commission,
            'seller_gets': self.price - self.commission,
            'sold_at': self.purchased_at.isoformat(),
            'buyer': {
                'id': self.buyer.id,
                'nickname': self.buyer.nickname
            }
        }
