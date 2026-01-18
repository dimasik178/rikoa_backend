from datetime import datetime
import logging
import os
from web_server import create_app
from database import db_manager
from database import BankruptcyManager

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def update_daily_prices():
    """Обновляет цены товаров и збрасывает cooldown банкротств"""
    logger.info("🔄 Начало ежедневного обновления цен...")
    
    # Создаем приложение вручную, без контекста запроса
    app = create_app()
    with app.app_context():
        try:
            print(f"🔄 Начало ежедневного обновления в {datetime.now()}")
            
            # 🔄 ШАГ 1: Сбрасываем cooldown банкротства для всех пользователей
            logger.info("🔄 Сброс cooldown банкротства...")
            BankruptcyManager.reset_bankruptcy_cooldown_for_all()
            logger.info("✅ Cooldown банкротства сброшен для всех пользователей")
            
            # 🔄 ШАГ 2: Обновляем цены товаров
            products = db_manager.get_daily_update_products()
            updated_count = 0
            
            for product in products:
                try:
                    # Обновляем историю цен
                    db_manager.update_product_price_history(product)
                    updated_count += 1
                except Exception as e:
                    logger.error(f"Ошибка обновления товара {product.id}: {e}")
                    continue
            
            logger.info(f"✅ Обновлено {updated_count} товаров")
            
        except Exception as e:
            logger.error(f"❌ Ошибка обновления: {e}")
            raise

if __name__ == "__main__":
    # Если переданы аргументы командной строки
    if len(os.sys.argv) > 1 and os.sys.argv[1] == "--run-now":
        # Запускаем обновление немедленно
        update_daily_prices()
    else:
        print('Доступен запуск только с параметром "--run-now", для немедленного обновления цен на платформе')
