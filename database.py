from models import db, Account, Product, Subscription
from flask import Flask
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy import desc, and_
from werkzeug.security import generate_password_hash, check_password_hash
from config import MarketConfig
import json

class TransactionManager:
    """Управление транзакциями и блокировками"""
    
    @staticmethod
    def execute_transaction(func, *args, **kwargs):
        """Выполняет функцию в транзакции с блокировкой"""
        try:
            result = func(*args, **kwargs)
            db.session.commit()
            return result
        except SQLAlchemyError as e:
            db.session.rollback()
            raise Exception(f"Transaction failed: {str(e)}")
        except Exception as e:
            db.session.rollback()
            raise e

class ProductManager:
    """Управление товарами и портфелем"""
    
    @staticmethod
    def validate_price(price):
        """Валидация цены товара"""
        if not isinstance(price, int) or price <= 0:
            raise ValueError("Цена должна быть положительным целым числом")
        
        if price < MarketConfig.MIN_PRODUCT_PRICE:
            raise ValueError(f"Минимальная цена: {MarketConfig.MIN_PRODUCT_PRICE} AC")
        
        if price > MarketConfig.MAX_PRODUCT_PRICE:
            raise ValueError(f"Максимальная цена: {MarketConfig.MAX_PRODUCT_PRICE} AC")
        
        return price
    
    @staticmethod
    def calculate_startup_capital(price):
        """Рассчитывает стартовый капитал продавца"""
        return price * MarketConfig.SELLER_STARTUP_MULTIPLIER
    
    @staticmethod
    def check_seller_limit(account_id):
        """Проверяет лимит активных товаров продавца"""
        active_count = Product.query.filter_by(
            creator_id=account_id, 
            status='active'
        ).count()
        
        if active_count >= MarketConfig.MAX_ACTIVE_PRODUCTS_PER_SELLER:
            raise ValueError(f"Превышен лимит активных товаров ({MarketConfig.MAX_ACTIVE_PRODUCTS_PER_SELLER})")
        
        return True

class SubscriptionManager:
    """Управление подписками"""
    
    @staticmethod
    def subscribe_user(account_id, product_id, current_price):
        """Оформляет подписку пользователя на товар"""
        # Проверяем существующую подписку
        existing = Subscription.query.filter_by(
            subscriber_id=account_id,
            product_id=product_id,
            status='active'
        ).first()
        
        if existing:
            return existing
        
        # Создаем новую подписку
        subscription = Subscription(
            subscriber_id=account_id,
            product_id=product_id,
            subscription_price=current_price,
            status='active'
        )
        
        db.session.add(subscription)
        return subscription
    
    @staticmethod
    def unsubscribe_user(subscription, current_price, portfolio):
        """Отписывает пользователя от товара"""
        # Проверяем, достаточно ли денег в портфеле
        if portfolio < current_price:
            # Прогорание товара
            payout_amount = portfolio
            is_burned = True
        else:
            payout_amount = current_price
            is_burned = False
        
        # Обновляем подписку
        subscription.status = 'cancelled'
        
        return payout_amount, is_burned

class DatabaseManager:
    def __init__(self, app: Flask = None):
        if app:
            self.init_app(app)
    
    def init_app(self, app: Flask):
        db.init_app(app)
        with app.app_context():
            db.create_all()
    
    # ========== АККАУНТЫ ==========
    
    def create_account(self, nickname: str, mail: str, password: str) -> Account:
        """Создает новый аккаунт"""
        password_hash = generate_password_hash(password)
        account = Account(nickname=nickname, mail=mail, password=password_hash)
        
        db.session.add(account)
        try:
            db.session.commit()
            return account
        except IntegrityError:
            db.session.rollback()
            raise ValueError("Пользователь с таким никнеймом или почтой уже существует")
    
    def get_account_by_credentials(self, nickname: str, password: str) -> Account:
        """Получает аккаунт по логину и паролю"""
        account = Account.query.filter_by(nickname=nickname).first()
        if account and check_password_hash(account.password, password):
            return account
        return None
    
    def get_account_by_id(self, account_id: str) -> Account:
        """Получает аккаунт по ID"""
        return Account.query.get(account_id)
    
    def get_account_by_nickname(self, nickname: str) -> Account:
        """Получает аккаунт по никнейму"""
        return Account.query.filter_by(nickname=nickname).first()
    
    # ========== ТОВАРЫ ==========
    
    def create_product(self, creator_id: str, title: str, price: int, 
                      description: str, photo_url: str) -> Product:
        """Создает новый товар"""
        # Валидация цены
        price = ProductManager.validate_price(price)
        
        # Получаем аккаунт продавца
        creator = self.get_account_by_id(creator_id)
        if not creator:
            raise ValueError("Продавец не найден")
        
        # Проверяем лимит товаров
        ProductManager.check_seller_limit(creator_id)
        
        # Рассчитываем стартовый капитал
        startup_capital = ProductManager.calculate_startup_capital(price)
        
        # Проверяем баланс продавца
        if creator.balance < startup_capital:
            raise ValueError(f"Недостаточно средств. Нужно: {startup_capital} AC, ваш баланс: {creator.balance} AC")
        
        # Создаем товар
        product = Product(
            creator_id=creator_id,
            title=title,
            current_price=price,
            next_day_price=price,
            description=description,
            photo_url=photo_url,
            startup_capital=startup_capital,
            portfolio=startup_capital,  # Начальный портфель = стартовый капитал
            status='active'
        )
        
        # Списываем стартовый капитал с баланса продавца
        creator.balance -= startup_capital
        
        db.session.add(product)
        db.session.commit()
        
        return product
    
    def get_product(self, product_id: str) -> Product:
        """Получает товар по ID"""
        return Product.query.get(product_id)
    
    def get_products_paginated(self, page: int = 1, per_page: int = 14):
        """Получает товары с пагинацией (только активные)"""
        return Product.query.filter_by(status='active').order_by(
            desc(Product.created_at)
        ).paginate(page=page, per_page=per_page, error_out=False)
    
    def get_user_products(self, account_id: str):
        """Получает товары пользователя (активные и прогоревшие)"""
        return Product.query.filter_by(creator_id=account_id).filter(
            Product.status.in_(['active', 'burned'])
        ).order_by(desc(Product.created_at)).all()
    
    def update_product_price(self, product_id: str, seller_id: str, new_price: int) -> Product:
        """Изменяет цену товара (устанавливает на следующий день)"""
        # Валидация цены
        new_price = ProductManager.validate_price(new_price)
        
        # Получаем товар
        product = self.get_product(product_id)
        if not product:
            raise ValueError("Товар не найден")
        
        # Проверяем права продавца
        if product.creator_id != seller_id:
            raise ValueError("Только владелец может изменять цену товара")
        
        # Проверяем, что товар активен
        if product.status != 'active':
            raise ValueError("Нельзя изменить цену неактивного товара")
        
        # Проверяем, что новая цена не превышает портфель
        if new_price > product.portfolio:
            raise ValueError(f"Цена не может превышать портфель ({product.portfolio} AC)")
        
        # Устанавливаем цену на следующий день
        product.next_day_price = new_price
        
        db.session.commit()
        return product
    
    def remove_product(self, product_id: str, seller_id: str):
        """Снимает товар с продажи (продавец забирает весь портфель)"""
        product = self.get_product(product_id)
        if not product:
            raise ValueError("Товар не найден")
        
        # Проверяем права продавца
        if product.creator_id != seller_id:
            raise ValueError("Только владелец может снять товар")
        
        # Получаем продавца
        seller = self.get_account_by_id(seller_id)
        
        # Переводим весь портфель на баланс продавца
        seller.balance += product.portfolio
        
        # Отменяем все активные подписки
        active_subscriptions = Subscription.query.filter_by(
            product_id=product_id,
            status='active'
        ).all()
        
        for subscription in active_subscriptions:
            subscription.status = 'cancelled'
        
        # Полностью удаляем товар из БД
        db.session.delete(product)
        db.session.commit()
        
        return {
            'success': True,
            'message': f'Товар снят с продажи. Получено: {product.portfolio} AC',
            'portfolio_transferred': product.portfolio,
            'subscriptions_cancelled': len(active_subscriptions)
        }
    
    def delete_burned_product(self, product_id: str, seller_id: str):
        """Удаляет прогоревший товар из лотов продавца"""
        product = self.get_product(product_id)
        if not product:
            raise ValueError("Товар не найден")
        
        # Проверяем права продавца
        if product.creator_id != seller_id:
            raise ValueError("Только владелец может удалить товар")
        
        # Проверяем статус товара
        if product.status != 'burned':
            raise ValueError("Можно удалять только прогоревшие товары")
        
        # Полностью удаляем товар из БД
        db.session.delete(product)
        db.session.commit()
        
        return {
            'success': True,
            'message': 'Прогоревший товар удален'
        }
    
    # ========== ПОДПИСКИ ==========
    
    def subscribe_to_product(self, account_id: str, product_id: str):
        """Подписка пользователя на товар"""
        # Получаем товар
        product = self.get_product(product_id)
        if not product or product.status != 'active':
            raise ValueError("Товар не найден или неактивен")
        
        # Проверяем, что пользователь не продавец
        if product.creator_id == account_id:
            raise ValueError("Нельзя подписаться на свой товар")
        
        # Получаем пользователя
        user = self.get_account_by_id(account_id)
        if not user:
            raise ValueError("Пользователь не найден")
        
        # Проверяем баланс
        if user.balance < product.current_price:
            raise ValueError(f"Недостаточно средств. Нужно: {product.current_price} AC, ваш баланс: {user.balance} AC")
        
        # Выполняем транзакцию
        def transaction():
            # Списываем деньги с баланса пользователя
            user.balance -= product.current_price
            
            # Добавляем деньги в портфель товара
            product.portfolio += product.current_price
            product.subscriptions_money += product.current_price
            product.active_subscriptions_count += 1
            
            # Создаем подписку
            subscription = SubscriptionManager.subscribe_user(
                account_id, product_id, product.current_price
            )
            
            return subscription
        
        subscription = TransactionManager.execute_transaction(transaction)
        
        return {
            'success': True,
            'subscription': subscription.to_dict(),
            'message': f'Подписка оформлена за {product.current_price} AC'
        }
    
    def unsubscribe_from_product(self, account_id: str, product_id: str):
        """Отписка пользователя от товара"""
        # Находим активную подписку
        subscription = Subscription.query.filter_by(
            subscriber_id=account_id,
            product_id=product_id,
            status='active'
        ).first()
        
        if not subscription:
            raise ValueError("Активная подписка не найдена")
        
        product = subscription.product
        
        # Проверяем, что товар активен или прогорел
        if product.status not in ['active', 'burned']:
            raise ValueError("Товар не доступен для отписки")
        
        # Выполняем транзакцию
        def transaction():
            payout_amount, is_burned = SubscriptionManager.unsubscribe_user(
                subscription, product.current_price, product.portfolio
            )
            
            # Получаем пользователя
            user = self.get_account_by_id(account_id)
            
            # Выплачиваем деньги пользователю
            user.balance += payout_amount
            
            # Обновляем портфель товара
            product.portfolio -= payout_amount
            product.subscriptions_money -= product.current_price  # Вычитаем по текущей цене
            product.active_subscriptions_count -= 1
            
            # Если товар прогорел
            if is_burned:
                product.status = 'burned'
                product.portfolio = 0
            
            return {
                'payout_amount': payout_amount,
                'is_burned': is_burned,
                'product_status': product.status
            }
        
        result = TransactionManager.execute_transaction(transaction)
        
        response = {
            'success': True,
            'message': f'Отписка выполнена. Выплачено: {result["payout_amount"]} AC',
            'payout_amount': result['payout_amount']
        }
        
        if result['is_burned']:
            response['warning'] = 'Товар прогорел из-за недостатка средств в портфеле'
        
        return response
    
    def get_user_subscriptions(self, account_id: str):
        """Получает подписки пользователя"""
        return Subscription.query.filter_by(
            subscriber_id=account_id,
            status='active'
        ).order_by(desc(Subscription.id)).all()
    
    def get_product_subscribers(self, product_id: str):
        """Получает подписчиков товара"""
        return Subscription.query.filter_by(
            product_id=product_id,
            status='active'
        ).all()
    
    # ========== ПОИСК ==========
    
    def get_all_active_products(self):
        """Получает все активные товары"""
        return Product.query.filter_by(status='active').all()
    
    def get_product_by_photo_url(self, file_id: str) -> Product:
        """Получает товар по photo_url (file_id)"""
        return Product.query.filter_by(photo_url=file_id).first()
    
    # ========== СИСТЕМНЫЕ ==========
    
    def get_daily_update_products(self):
        """Получает товары для ежедневного обновления"""
        return Product.query.filter_by(status='active').all()
    
    def update_product_price_history(self, product: Product):
        """Обновляет историю цен товара (для ежедневного обновления)"""
        product.update_price_history()
        db.session.commit()

# Глобальный экземпляр менеджера БД
db_manager = DatabaseManager()