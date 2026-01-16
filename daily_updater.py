import schedule
from datetime import datetime
import time
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
    """Обновляет цены товаров в 0:00 (МСК)"""
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

def run_scheduler():
    """Запускает планировщик задач"""
    logger.info("⏰ Планировщик ежедневного обновления запущен")
    
    # Время обновления в контейнере
    # После установки TZ=Europe/Moscow можно использовать 00:00
    schedule.every().day.at("00:00").do(update_daily_prices)
    
    current_time = datetime.now().strftime("%H:%M:%S")
    logger.info(f"Текущее время в контейнере: {current_time}")
    logger.info("Следующее обновление в 00:00 (Москва)")
    
    # Первая проверка через 5 секунд после запуска
    time.sleep(5)
    logger.info("Планировщик начал работу...")
    
    while True:
        try:
            schedule.run_pending()
            time.sleep(60)  # Проверяем каждую минуту
        except KeyboardInterrupt:
            logger.info("Планировщик остановлен")
            break
        except Exception as e:
            logger.error(f"Ошибка в планировщике: {e}")
            time.sleep(60)

if __name__ == "__main__":
    # Если переданы аргументы командной строки
    if len(os.sys.argv) > 1 and os.sys.argv[1] == "--run-now":
        # Запускаем обновление немедленно
        update_daily_prices()
    else:
        # Запускаем планировщик
        run_scheduler()