from models import db, Account, Product, Purchase
from flask import Flask
from sqlalchemy.exc import IntegrityError
from sqlalchemy import desc
from werkzeug.security import generate_password_hash, check_password_hash

class DatabaseManager:
    def __init__(self, app: Flask = None):
        if app:
            self.init_app(app)
    
    def init_app(self, app: Flask):
        db.init_app(app)
        with app.app_context():
            db.create_all()
    
    # Account methods
    def create_account(self, nickname: str, mail: str, password: str) -> Account:
        # Генерация хэша пароля
        password_hash = generate_password_hash(password)
        account = Account(nickname=nickname, mail=mail, password=password_hash)
        db.session.add(account)
        try:
            db.session.commit()
            return account
        except IntegrityError:
            db.session.rollback()
            raise ValueError("Account with this nickname or mail already exists")
    
    def get_account_by_credentials(self, nickname: str, password: str) -> Account:
        account = Account.query.filter_by(nickname=nickname).first()
        if account and check_password_hash(account.password, password):
            return account
        return None
    
    def get_account_by_id(self, account_id: str) -> Account:
        return Account.query.get(account_id)
    
    def get_account_by_nickname(self, nickname: str) -> Account:
        return Account.query.filter_by(nickname=nickname).first()
    
    # Product methods
    def create_product(self, photo_url: str, creator_id: str, title: str, 
                      price: int, description: str) -> Product:
        product = Product(
            photo_url=photo_url,
            creator_id=creator_id,
            title=title,
            price=price,
            description=description
        )
        db.session.add(product)
        db.session.commit()
        return product
    
    def get_product(self, product_id: str) -> Product:
        return Product.query.get(product_id)
    
    def get_products_paginated(self, page: int = 1, per_page: int = 10):
        return Product.query.order_by(desc(Product.updated_at)).paginate(
            page=page, per_page=per_page, error_out=False
        )
    
    def get_user_products(self, account_id: str):
        return Product.query.filter_by(creator_id=account_id).order_by(desc(Product.updated_at)).all()
    
    def get_purchased_products(self, account_id: str):
        purchases = Purchase.query.filter_by(account_id=account_id).order_by(desc(Purchase.purchased_at)).all()
        return [purchase.product for purchase in purchases]
    
    def update_product_description(self, product_id: str, description: str) -> Product:
        product = Product.query.get(product_id)
        if product:
            product.description = description
            db.session.commit()
        return product
    
    # Purchase methods
    def create_purchase(self, account_id: str, product_id: str) -> Purchase:
        # Check if purchase already exists
        existing_purchase = Purchase.query.filter_by(
            account_id=account_id, product_id=product_id
        ).first()
        
        if existing_purchase:
            return existing_purchase
        
        purchase = Purchase(account_id=account_id, product_id=product_id)
        db.session.add(purchase)
        db.session.commit()
        return purchase
    
    def get_product_buyers(self, product_id: str):
        purchases = Purchase.query.filter_by(product_id=product_id).order_by(desc(Purchase.purchased_at)).all()
        return [purchase.account for purchase in purchases]
    
    def has_user_purchased_product(self, account_id: str, product_id: str) -> bool:
        return Purchase.query.filter_by(account_id=account_id, product_id=product_id).first() is not None

# Global instance
db_manager = DatabaseManager()
