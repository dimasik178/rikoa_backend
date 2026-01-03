import schedule
import time
from datetime import datetime
from web_server import create_app
from database import db_manager

def update_daily_prices():
    """Обновляет цены товаров в 0:00"""
    app = create_app()
    with app.app_context():
        try:
            print(f"🔄 Начало ежедневного обновления в {datetime.now()}")
            
            # Получаем все активные товары
            products = db_manager.get_daily_update_products()
            updated_count = 0
            
            for product in products:
                # Обновляем историю цен
                db_manager.update_product_price_history(product)
                updated_count += 1
            
            print(f"✅ Обновлено {updated_count} товаров")
            
        except Exception as e:
            print(f"❌ Ошибка обновления: {e}")

if __name__ == "__main__":
    # Запускаем в 0:00 каждый день
    schedule.every().day.at("00:00").do(update_daily_prices)
    # schedule.every(5).minutes.do(update_daily_prices) # TEST
    
    print("⏰ Планировщик ежедневного обновления запущен")
    
    # Бесконечный цикл
    while True:
        # input() # TEST
        # update_daily_prices() # TEST
        schedule.run_pending()
        time.sleep(60)  # Проверяем каждую минуту
