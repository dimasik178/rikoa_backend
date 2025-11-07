from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
import uuid

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
    
    # Relationships
    posted = relationship("Product", back_populates="creator", foreign_keys="Product.creator_id")
    purchases = relationship("Purchase", back_populates="account")
    
    def to_dict(self):
        """Базовая структура аккаунта без рекурсии"""
        return {
            'id': self.id,
            'nickname': self.nickname,
            'mail': self.mail,
            'createdAt': self.created_at.isoformat() if self.created_at else None
        }
    
    def to_dict_with_products(self):
        """Структура с продуктами (для профиля)"""
        data = self.to_dict()
        try:
            # Используем упрощенные версии продуктов чтобы избежать рекурсии
            data['bayed'] = [self._simplify_product(purchase.product) for purchase in self.purchases]
            data['posted'] = [self._simplify_product(product) for product in self.posted]
        except Exception as e:
            data['bayed'] = []
            data['posted'] = []
        return data
    
    def _simplify_product(self, product):
        """Упрощенное представление продукта без рекурсии"""
        if not product:
            return None
            
        return {
            'id': product.id,
            'photoUrl': product.get_image_urls()['thumbnail'],
            'title': product.title,
            'price': product.price,
            'description': product.description or '',
            'updatedAt': product.updated_at.isoformat() if product.updated_at else None
            # Не включаем creator чтобы избежать рекурсии
        }

class Product(db.Model):
    __tablename__ = 'products'
    
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    photo_url = db.Column(db.String(500), nullable=False)  # Теперь хранит file_id
    creator_id = db.Column(db.String(36), db.ForeignKey('accounts.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    price = db.Column(db.Integer, nullable=False)
    description = db.Column(db.Text)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    creator = relationship("Account", back_populates="posted", foreign_keys=[creator_id])
    purchases = relationship("Purchase", back_populates="product")
    

    
    def get_image_urls(self):
        """Генерирует URL для изображений"""
        base_url = 'http://localhost:5000'
        return {
            'thumbnail': f"{base_url}/api/images/thumbnail/{self.photo_url}"
        }
    
    # def get_image_urls(self):
    #     """Генерирует URL для изображений"""
    #     base_url = 'http://localhost:5000/api/images'
    #     return {
    #         'original': f"{base_url}/original/{self.photo_url}",
    #         'thumbnail': f"{base_url}/thumbnail/{self.photo_url}"
    #     }
    
    def to_dict(self):
        """Базовая структура продукта"""
        image_urls = self.get_image_urls()
        
        return {
            'id': self.id,
            'photoUrl': image_urls['thumbnail'],  # По умолчанию показываем превью
            'title': self.title,
            'price': self.price,
            'description': self.description or '',
            'updatedAt': self.updated_at.isoformat() if self.updated_at else None,
            'creator': self.creator.to_dict() if self.creator else None  # Только базовая информация
        }
    
    def to_dict_with_buyers(self):
        """Расширенная структура с информацией о покупателях"""
        data = self.to_dict()
        try:
            data['buyers_count'] = len(self.purchases)
            data['buyers'] = [purchase.account.to_dict() for purchase in self.purchases]  # Только базовая информация
        except Exception:
            data['buyers_count'] = 0
            data['buyers'] = []
        return data

class Purchase(db.Model):
    __tablename__ = 'purchases'
    
    id = db.Column(db.String(36), primary_key=True, default=generate_uuid)
    account_id = db.Column(db.String(36), db.ForeignKey('accounts.id'), nullable=False)
    product_id = db.Column(db.String(36), db.ForeignKey('products.id'), nullable=False)
    purchased_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    account = relationship("Account", back_populates="purchases")
    product = relationship("Product", back_populates="purchases")
    
    def to_dict(self):
        return {
            'id': self.id,
            'account_id': self.account_id,
            'product_id': self.product_id,
            'purchased_at': self.purchased_at.isoformat() if self.purchased_at else None
        }
