from datetime import datetime
import logging
import os
from web_server import create_app
from database import db_manager

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def update_daily_data():
    """Ежедневное обновление: обновляет историю баланса, сбрасывает cooldown банкротства и бонуса"""
    logger.info("🔄 Начало ежедневного обновления...")
    
    # Создаем приложение вручную, без контекста запроса
    app = create_app()
    with app.app_context():
        try:
            print(f"🔄 Начало ежедневного обновления в {datetime.now()}")
            
            # ШАГ 1: Сбрасываем cooldown банкротства
            logger.info("🔄 Сброс cooldown банкротства...")
            db_manager.reset_all_bankruptcy_cooldowns()
            logger.info("✅ Cooldown банкротства сброшен")
            
            # ШАГ 2: Сбрасываем cooldown бонуса
            logger.info("🔄 Сброс cooldown бонуса...")
            db_manager.reset_all_daily_bonuses()
            logger.info("✅ Cooldown бонуса сброшен")
            
            # ШАГ 3: Обновляем историю баланса
            logger.info("🔄 Обновление истории баланса...")
            updated_count = db_manager.update_all_balance_histories()
            logger.info(f"✅ Обновлена история баланса для {updated_count} пользователей")
            
        except Exception as e:
            logger.error(f"❌ Ошибка обновления: {e}")
            raise

if __name__ == "__main__":
    # Если переданы аргументы командной строки
    if len(os.sys.argv) > 1 and os.sys.argv[1] == "--run-now":
        # Запускаем обновление немедленно
        update_daily_data()
    else:
        print('Доступен запуск только с параметром "--run-now", для немедленного обновления на платформе')
