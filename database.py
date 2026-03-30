from models import db, Account, Product, Purchase
from flask import Flask
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy import desc, and_
from werkzeug.security import generate_password_hash, check_password_hash
from config import MarketConfig
from datetime import datetime, timezone
import json
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


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


class BankruptcyManager:
    """Управление банкротством"""

    @staticmethod
    def check_bankruptcy_conditions(account: Account) -> tuple[bool, str]:
        """Проверяет условия для объявления банкротства"""
        
        # 1. Проверяем флаг cooldown (можно банкротиться только 1 раз в день)
        if not account.can_declare_bankruptcy:
            return False, "Банкротство можно объявлять только 1 раз в день."
        
        # 2. Проверяем баланс (должен быть меньше BANKRUPTCY_RESET_BALANCE)
        if account.balance >= MarketConfig.BANKRUPTCY_RESET_BALANCE:
            return False, f"Нельзя объявить банкротство при балансе ≥ {MarketConfig.BANKRUPTCY_RESET_BALANCE} AC"
        
        # 3. Проверяем активные товары на продаже
        active_products = [p for p in account.products_for_sale if not p.is_sold]
        if active_products:
            return False, "Нельзя объявить банкротство с активными товарами на продаже. Сначала снимите товары с продажи."
        
        # 4. Проверяем купленные товары - они не мешают банкротству
        # (у пользователя могут быть купленные товары, это не блокирует банкротство)
        
        return True, ""

    @staticmethod
    def declare_bankruptcy(account: Account) -> dict:
        """Объявляет банкротство пользователя"""
        
        # Проверяем условия
        can_declare, message = BankruptcyManager.check_bankruptcy_conditions(account)
        if not can_declare:
            raise ValueError(message)
        
        try:
            old_balance = account.balance
            
            # Устанавливаем новый баланс
            account.balance = MarketConfig.BANKRUPTCY_RESET_BALANCE
            
            # Увеличиваем счетчик банкротств
            account.bankruptcy_count += 1
            
            # Обновляем дату последнего банкротства
            account.last_bankruptcy = datetime.utcnow()
            
            # Запрещаем повторное банкротство до следующего дня
            account.can_declare_bankruptcy = False
            
            db.session.commit()
            
            return {
                'message': f'💸 Банкротство объявлено! Баланс изменён: {old_balance} → {account.balance} AC',
                'old_balance': old_balance,
                'new_balance': account.balance,
                'bankruptcy_count': account.bankruptcy_count,
                'last_bankruptcy': account.last_bankruptcy.isoformat(),
                'can_declare_bankruptcy': account.can_declare_bankruptcy
            }
            
        except Exception as e:
            db.session.rollback()
            raise ValueError(f"Ошибка при объявлении банкротства: {str(e)}")
    
    @staticmethod
    def reset_bankruptcy_cooldown_for_all():
        """Сбрасывает cooldown банкротства для всех пользователей (вызывается раз в день)"""
        try:
            # Устанавливаем can_declare_bankruptcy = True для всех пользователей
            Account.query.update({Account.can_declare_bankruptcy: True})
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            raise e

class ProductManager:
    """Управление товарами"""
    
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
    def calculate_commission(price: int) -> tuple[int, int]:
        """
        Рассчитывает комиссию и сумму продавцу
        Возвращает: (commission, seller_gets)
        
        Использует Decimal для точного округления вверх:
        commission = ceil(price * 0.05)
        """
        # Используем Decimal для точных вычислений
        price_dec = Decimal(str(price))
        commission_percent = Decimal(str(MarketConfig.COMMISSION_PERCENT))
        
        # commission = ceil(price * 0.05)
        commission_raw = price_dec * commission_percent
        # Округление вверх: -(-commission_raw // 1)
        commission = -(-commission_raw // Decimal('1'))
        
        seller_gets = price_dec - commission
        
        return int(commission), int(seller_gets)
    
    @staticmethod
    def check_seller_limit(account_id):
        """Проверяет лимит активных товаров продавца (непроданных)"""
        active_count = Product.query.filter_by(
            creator_id=account_id, 
            is_sold=False
        ).count()
        
        if active_count >= MarketConfig.MAX_ACTIVE_PRODUCTS_PER_SELLER:
            raise ValueError(f"Превышен лимит активных товаров ({MarketConfig.MAX_ACTIVE_PRODUCTS_PER_SELLER})")
        
        return True


class BonusManager:
    """Управление бонусами"""
    
    @staticmethod
    def can_claim_daily_bonus(account: Account) -> tuple[bool, str]:
        """Проверяет, может ли пользователь получить ежедневный бонус"""
        
        # Проверяем баланс
        if account.balance >= MarketConfig.DAILY_BONUS_MAX_BALANCE:
            return False, f"Баланс превышает лимит для получения бонуса ({MarketConfig.DAILY_BONUS_MAX_BALANCE} AC)"
        
        # Проверяем, получал ли бонус сегодня
        if account.last_daily_bonus:
            # Сравниваем даты (без времени)
            last_bonus_date = account.last_daily_bonus.date()
            today = datetime.utcnow().date()
            
            if last_bonus_date == today:
                return False, "Сегодня бонус уже получен"
        
        return True, ""
    
    @staticmethod
    def claim_daily_bonus(account: Account) -> dict:
        """Начисляет ежедневный бонус"""
        
        can_claim, message = BonusManager.can_claim_daily_bonus(account)
        if not can_claim:
            raise ValueError(message)
        
        try:
            old_balance = account.balance
            bonus = MarketConfig.DAILY_BONUS_AMOUNT
            
            # Начисляем бонус
            account.balance += bonus
            account.total_earned += bonus
            account.last_daily_bonus = datetime.utcnow()
            
            db.session.commit()
            
            return {
                'message': 'Бонус начислен',
                'bonus': bonus,
                'new_balance': account.balance
            }
            
        except Exception as e:
            db.session.rollback()
            raise ValueError(f"Ошибка начисления бонуса: {str(e)}")


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
        """Создает новый аккаунт с бонусом за регистрацию"""
        password_hash = generate_password_hash(password)
        
        # Начальный баланс = стартовый + бонус
        initial_balance = MarketConfig.STARTING_BALANCE + MarketConfig.REGISTRATION_BONUS
        
        account = Account(
            nickname=nickname, 
            mail=mail, 
            password=password_hash,
            balance=initial_balance,
            total_earned=MarketConfig.REGISTRATION_BONUS
        )
        
        # Инициализируем историю баланса
        history = [initial_balance] * MarketConfig.BALANCE_HISTORY_DAYS
        account.balance_history = json.dumps(history)
        
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
    
    # ========== БАНКРОТСТВО ==========
    
    def declare_bankruptcy(self, account_id: str) -> dict:
        """Объявляет банкротство для пользователя"""
        account = self.get_account_by_id(account_id)
        if not account:
            raise ValueError("Пользователь не найден")
        
        return BankruptcyManager.declare_bankruptcy(account)
    
    # ========== БОНУСЫ ==========
    
    def claim_daily_bonus(self, account_id: str) -> dict:
        """Начисляет ежедневный бонус пользователю"""
        account = self.get_account_by_id(account_id)
        if not account:
            raise ValueError("Пользователь не найден")
        
        return BonusManager.claim_daily_bonus(account)
    
    # ========== ТОВАРЫ ==========
    
    def create_product(self, creator_id: str, title: str, price: int, 
                      description: str, photo_url: str) -> Product:
        """Создает новый товар (без списания средств)"""
        # Валидация цены
        price = ProductManager.validate_price(price)
        
        # Получаем аккаунт продавца
        creator = self.get_account_by_id(creator_id)
        if not creator:
            raise ValueError("Продавец не найден")
        
        # Проверяем лимит товаров
        ProductManager.check_seller_limit(creator_id)
        
        # Валидация длины
        if len(title) < MarketConfig.MIN_TITLE_LENGTH:
            raise ValueError(f"Название должно быть не менее {MarketConfig.MIN_TITLE_LENGTH} символов")
        if len(title) > MarketConfig.MAX_TITLE_LENGTH:
            raise ValueError(f"Название должно быть не более {MarketConfig.MAX_TITLE_LENGTH} символов")
        if len(description) > MarketConfig.MAX_DESCRIPTION_LENGTH:
            raise ValueError(f"Описание должно быть не более {MarketConfig.MAX_DESCRIPTION_LENGTH} символов")
        
        # Создаем товар (деньги не списываются!)
        product = Product(
            creator_id=creator_id,
            owner_id=creator_id,  # Изначально владелец = создатель
            title=title,
            price=price,
            description=description,
            photo_url=photo_url,
            is_sold=False
        )
        
        db.session.add(product)
        db.session.commit()
        
        return product
    
    def get_product(self, product_id: str) -> Product:
        """Получает товар по ID"""
        return Product.query.get(product_id)
    
    def get_product_by_photo_url(self, file_id: str) -> Product:
        """Получает товар по photo_url (file_id)"""
        return Product.query.filter_by(photo_url=file_id).first()
    
    def get_products_paginated(self, page: int = 1, per_page: int = 14):
        """Получает непроданные товары с пагинацией"""
        return Product.query.filter_by(is_sold=False).order_by(
            desc(Product.created_at)
        ).paginate(page=page, per_page=per_page, error_out=False)
    
    def get_user_products_for_sale(self, account_id: str):
        """Получает товары пользователя на продаже (непроданные)"""
        return Product.query.filter_by(
            creator_id=account_id, 
            is_sold=False
        ).order_by(desc(Product.created_at)).all()
    
    def get_user_purchased_products(self, account_id: str):
        """Получает купленные пользователем товары"""
        return Product.query.filter_by(
            owner_id=account_id, 
            is_sold=True
        ).order_by(desc(Product.purchased_at)).all()
    
    def buy_product(self, buyer_id: str, product_id: str) -> Product:
        """Покупка товара"""
        
        # Получаем товар
        product = self.get_product(product_id)
        if not product:
            raise ValueError("Товар не найден")
        
        # Проверяем, что товар не продан
        if product.is_sold:
            raise ValueError("Товар уже продан")
        
        # Получаем покупателя и продавца
        buyer = self.get_account_by_id(buyer_id)
        seller = self.get_account_by_id(product.creator_id)
        
        if not buyer or not seller:
            raise ValueError("Пользователь не найден")
        
        # Проверяем, что покупатель не продавец
        if buyer_id == product.creator_id:
            raise ValueError("Нельзя купить свой товар")
        
        # Проверяем баланс покупателя
        if buyer.balance < product.price:
            raise ValueError(f"Недостаточно средств. Нужно: {product.price} AC, ваш баланс: {buyer.balance} AC")
        
        # Рассчитываем комиссию
        commission, seller_gets = ProductManager.calculate_commission(product.price)
        
        # Выполняем транзакцию
        def transaction():
            # 1. Списываем деньги с покупателя
            buyer.balance -= product.price
            buyer.total_spent += product.price
            
            # 2. Начисляем деньги продавцу (минус комиссия)
            seller.balance += seller_gets
            seller.total_earned += seller_gets
            
            # 3. Обновляем товар
            product.owner_id = buyer_id
            product.is_sold = True
            product.purchased_at = datetime.utcnow()
            
            # 4. Создаем запись о покупке
            purchase = Purchase(
                buyer_id=buyer_id,
                seller_id=product.creator_id,
                product_id=product_id,
                product_title=product.title,
                price=product.price,
                commission=commission
            )
            db.session.add(purchase)
            
            return product
        
        product = TransactionManager.execute_transaction(transaction)
        
        return product
    
    def remove_product(self, product_id: str, seller_id: str):
        """Удаляет товар (только если не продан)"""
        product = self.get_product(product_id)
        if not product:
            raise ValueError("Товар не найден")
        
        # Проверяем права
        if product.creator_id != seller_id:
            raise ValueError("Только владелец может удалить товар")
        
        # Проверяем, что товар не продан
        if product.is_sold:
            raise ValueError("Нельзя удалить проданный товар")
        
        try:
            # Полностью удаляем товар из БД
            db.session.delete(product)
            db.session.commit()
            
            return {
                'message': 'Товар удален',
                'product_id': product_id
            }
            
        except Exception as e:
            db.session.rollback()
            raise ValueError(f'Ошибка удаления товара: {str(e)}')
    
    # ========== ИСТОРИЯ ПОКУПОК/ПРОДАЖ ==========
    
    def get_user_purchases(self, account_id: str, page: int = 1, per_page: int = 20):
        """Получает историю покупок пользователя с пагинацией"""
        pagination = Purchase.query.filter_by(
            buyer_id=account_id
        ).order_by(desc(Purchase.purchased_at)).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        purchases_data = [purchase.to_dict_for_buyer() for purchase in pagination.items]
        
        return {
            'data': purchases_data,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': pagination.total,
                'pages': pagination.pages
            }
        }
    
    def get_user_sales(self, account_id: str, page: int = 1, per_page: int = 20):
        """Получает историю продаж пользователя с пагинацией"""
        pagination = Purchase.query.filter_by(
            seller_id=account_id
        ).order_by(desc(Purchase.purchased_at)).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        sales_data = [purchase.to_dict_for_seller() for purchase in pagination.items]
        
        return {
            'data': sales_data,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': pagination.total,
                'pages': pagination.pages
            }
        }
    
    # ========== СТАТИСТИКА ==========
    
    def get_account_stats(self, account_id: str) -> dict:
        """Получает статистику аккаунта"""
        account = self.get_account_by_id(account_id)
        if not account:
            raise ValueError("Пользователь не найден")
        
        return {
            'balance_history': account.get_balance_history_array(),
            'total_spent': account.total_spent,
            'total_earned': account.total_earned,
            'current_balance': account.balance,
            'bankruptcy_count': account.bankruptcy_count
        }
    
    # ========== РЕЙТИНГ ==========
    
    def get_player_rating_paginated(self, page: int = 1, per_page: int = 20):
        """Получает рейтинг игроков по балансу с пагинацией"""
        pagination = Account.get_rating_paginated(page=page, per_page=per_page)
        
        players_data = []
        for account in pagination.items:
            player_data = {
                'id': account.id,
                'nickname': account.nickname,
                'balance': account.balance,
                'bankruptcy_count': account.bankruptcy_count,
                'created_at': account.created_at.isoformat()
            }
            players_data.append(player_data)
        
        return {
            'players': players_data,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': pagination.total,
                'pages': pagination.pages
            }
        }
    
    # ========== СИСТЕМНЫЕ ==========
    
    def get_all_active_products(self):
        """Получает все активные (непроданные) товары"""
        return Product.query.filter_by(is_sold=False).all()
    
    def update_all_balance_histories(self):
        """Обновляет историю баланса для всех пользователей"""
        accounts = Account.query.all()
        for account in accounts:
            account.update_balance_history()
        db.session.commit()
        return len(accounts)
    
    def reset_all_bankruptcy_cooldowns(self):
        """Сбрасывает cooldown банкротства для всех пользователей"""
        return BankruptcyManager.reset_bankruptcy_cooldown_for_all()


# Глобальный экземпляр менеджера БД
db_manager = DatabaseManager()
