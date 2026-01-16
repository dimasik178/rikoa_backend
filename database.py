from models import db, Account, Product, Subscription
from flask import Flask
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy import desc, and_
from werkzeug.security import generate_password_hash, check_password_hash
from config import MarketConfig
from datetime import datetime

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
        
        # 1. Проверяем флаг cooldown
        if not account.can_declare_bankruptcy:
            return False, "Банкротство можно объявлять только 1 раз до следующего обновления цен."
        
        # 2. Проверяем баланс (должен быть меньше BANKRUPTCY_RESET_BALANCE)
        if account.balance >= MarketConfig.BANKRUPTCY_RESET_BALANCE:
            return False, f"Нельзя объявить банкротство при балансе ≥ {MarketConfig.BANKRUPTCY_RESET_BALANCE} AC"
        
        # 3. Проверяем активные товары
        active_products = [p for p in account.products if p.status == 'active']
        if active_products:
            return False, "Нельзя объявить банкротство с активными товарами. Cначала снимите товары с продажи."
        
        # 4. Проверяем активные подписки
        active_subscriptions = [s for s in account.subscriptions if s.status == 'active']
        if active_subscriptions:
            return False, "Нельзя объявить банкротство с активными подписками. Cначала отпишитесь от товаров."
        
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
            
            # Запрещаем повторное банкротство до следующего обновления цен
            account.can_declare_bankruptcy = False
            
            db.session.commit()
            
            return {
                'success': True,
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
        """Сбрасывает cooldown банкротства для всех пользователей (вызывается при обновлении цен)"""
        try:
            # Устанавливаем can_declare_bankruptcy = True для всех пользователей
            Account.query.update({Account.can_declare_bankruptcy: True})
            db.session.commit()
            return True
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
    
    # ========== БАНКРОТСТВО ==========
    
    def declare_bankruptcy(self, account_id: str) -> dict:
        """Объявляет банкротство для пользователя"""
        account = self.get_account_by_id(account_id)
        if not account:
            raise ValueError("Пользователь не найден")
        
        return BankruptcyManager.declare_bankruptcy(account)
    
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
        """Получает товары пользователя (active и burned, но не burned_hidden)"""
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
        """Снимает товар с продажи или скрывает прогоревший товар"""
        product = self.get_product(product_id)
        if not product:
            raise ValueError("Товар не найден")
        
        if product.creator_id != seller_id:
            raise ValueError("Только владелец может снять/скрыть товар")
        
        seller = self.get_account_by_id(seller_id)
        try:
            # СЛУЧАЙ 1: Активный товар
            if product.status == 'active':
                # 1. Продавец забирает ВЕСЬ портфель
                seller.balance += product.portfolio
                
                # 2. Все активные подписки становятся 'cancelled'
                active_subscriptions = Subscription.query.filter_by(
                    product_id=product_id,
                    status='active'
                ).all()
                
                if not active_subscriptions:
                    portfolio = product.portfolio
                    db.session.delete(product)
                    db.session.commit()
                    return {
                        'success': True,
                        'message': f'Товар снят с продажи. Получено: {portfolio} AC',
                        'portfolio_transferred': portfolio,
                        'subscriptions_cancelled': 0,
                        'product_deleted': True,
                    }

                subscription_ids = [sub.id for sub in active_subscriptions]

                for subscription in active_subscriptions:
                    subscription.status = 'cancelled'

                # 3. Товар становится burned_hidden
                product.status = 'burned_hidden'
                portfolio = product.portfolio
                product.portfolio = 0
                
                db.session.commit()
                
                return {
                    'success': True,
                    'message': f'Товар снят с продажи. Получено: {portfolio} AC',
                    'portfolio_transferred': portfolio,
                    'subscriptions_cancelled': len(active_subscriptions),
                    'subscription_ids_deleted': subscription_ids,
                    'product_status': 'burned_hidden'
                }

            # СЛУЧАЙ 2: Прогоревший товар (burned)
            elif product.status == 'burned':
                # 1. Просто меняем статус на burned_hidden
                product.status = 'burned_hidden'
                
                # 2. Проверяем, нужно ли удалять товар полностью
                # (если нет подписчиков)
                remaining_subs = Subscription.query.filter_by(
                    product_id=product_id,
                ).all()

                if not remaining_subs:
                    db.session.delete(product)
                    db.session.commit()
                    return {
                        'success': True,
                        'message': 'Товар скрыт и удален (не осталось подписчиков)',
                        'portfolio_transferred': 0,
                        'product_deleted': True
                    }
                db.session.commit()
                return {
                    'success': True,
                    'message': 'Товар скрыт из профиля продавца',
                    'portfolio_transferred': 0,
                    'product_deleted': False
                }
            
            # СЛУЧАЙ 3: Уже скрытый товар
            elif product.status == 'burned_hidden':
                return {
                    'success': True,
                    'message': 'Товар уже скрыт',
                    'portfolio_transferred': 0,
                    'product_deleted': False
                }
            
            else:
                raise ValueError(f"Неизвестный статус товара: {product.status}")
                
        except Exception as e:
            db.session.rollback()
            raise ValueError(f'Ошибка: {str(e)}')
    
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
        ).first()
        
        if not subscription:
            raise ValueError("Активная подписка не найдена")
        
        product : Product
        product = subscription.product
        
        # СЛУЧАЙ 1: Товар active - обычная отписка с выплатой
        if product.status == 'active':
            def transaction():
                # Проверяем, хватит ли денег в портфеле
                payout_amount = product.current_price
                is_burned = False
                
                if product.portfolio < product.current_price:
                    # Товар прогорает!
                    payout_amount = product.portfolio
                    is_burned = True
                    
                    # Меняем статус ВСЕХ подписок этого товара на 'cancelled'
                    all_subscriptions = Subscription.query.filter_by(
                        product_id=product_id,
                        status='active'
                    ).all()
                    for sub in all_subscriptions:
                        sub.status = 'cancelled'
                    
                    # Меняем статус товара
                    product.status = 'burned'
                    product.portfolio = 0
                    product.subscriptions_money -= payout_amount
                    product.active_subscriptions_count -= 1
                else:
                    # Обычная отписка - удаляем подписку
                    db.session.delete(subscription)
                    product.portfolio -= payout_amount
                    product.subscriptions_money -= payout_amount
                    product.active_subscriptions_count -= 1
                
                # Выплачиваем пользователю
                user = self.get_account_by_id(account_id)
                user.balance += payout_amount
                
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
        
        # СЛУЧАЙ 2: Товар burned или burned_hidden - просто удаляем подписку
        elif product.status in ['burned', 'burned_hidden']:
            # Просто удаляем подписку (денег не возвращаем)
            db.session.delete(subscription)
            
            # Проверяем, нужно ли удалять товар полностью
            # (burned_hidden + нет подписчиков)
            if product.status == 'burned_hidden':
                remaining_subs = Subscription.query.filter_by(
                    product_id=product_id
                ).count()
                
                if remaining_subs == 0:
                    # Полностью удаляем товар из БД
                    db.session.delete(product)
            
            db.session.commit()
            
            return {
                'success': True,
                'message': 'Отписка от прогоревшего товара выполнена',
                'payout_amount': 0,
                'product_deleted': product.status == 'burned_hidden' and not Subscription.query.filter_by(product_id=product_id).first()
            }
        
        else:
            raise ValueError(f"Неизвестный статус товара: {product.status}")
    
    def get_user_subscriptions(self, account_id: str):
        """Получает подписки пользователя"""
        return Subscription.query.filter_by(
            subscriber_id=account_id,
            status='active'
        ).order_by(desc(Subscription.id)).all()
    
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