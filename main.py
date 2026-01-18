from web_server import create_app
import os
from dotenv import load_dotenv
import signal
import sys
import threading
import schedule
import time
from daily_updater import update_daily_prices
from config import MarketConfig
PRICE_UPDATE_TIME = MarketConfig.PRICE_UPDATE_TIME


# Флаг для остановки
stop_scheduler = threading.Event()
scheduler_thread = None

def safe_update():
    """Безопасное обновление с обработкой ошибок"""
    try:
        update_daily_prices()
    except Exception as e:
        print(f"❌ Ошибка при обновлении цен: {e}")

def run_scheduler():
    """Контролируемый планировщик"""
    print(f"⏰ Планировщик запущен. Обновление в {PRICE_UPDATE_TIME}")
    
    schedule.every().day.at(PRICE_UPDATE_TIME).do(safe_update)
    
    while not stop_scheduler.is_set():
        schedule.run_pending()
        # Ждем с проверкой флага
        for _ in range(60):
            if stop_scheduler.is_set():
                break
            time.sleep(1)
    print("✅ Планировщик остановлен")

def stop_all():
    """Остановка при завершении приложения"""
    print("🛑 Останавливаем планировщик...")
    stop_scheduler.set()
    if scheduler_thread:
        scheduler_thread.join(timeout=5)

def shutdown_handler(signum, frame):
    """Обработчик сигналов завершения"""
    print(f"🛑 Получен сигнал {signum}, завершаем работу...")
    stop_all()  # Сначала останавливаем планировщик
    sys.exit(0)

def main():
    """Основная функция запуска"""
    # Сначала создаем Flask приложение (для инициализации БД)
    app = create_app()
    
    # Теперь запускаем планировщик (после инициализации БД)
    if not os.environ.get('WERKZEUG_RUN_MAIN'): # Основной процесс
        global scheduler_thread
        scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        scheduler_thread.start()
    else: # Избегаем дублирование запусков обновлений цен на рынке
        print("🔄 Reloader process detected, scheduler not started")
    
    print("🚀 Market API Server starting...")
    print("📊 Database initialized")
    print("🌐 JSON API ready")
    print("💰 Investment system: ACTIVE")
    print(f"⏰ Price scheduler: ACTIVE (update at {PRICE_UPDATE_TIME})")
    print(f"🔗 Server running at: http://localhost:5000")
    print("\n📚 Available endpoints:")
    print("   GET  /api/health - Health check")
    print("   POST /api/auth/register - Register")
    print("   POST /api/auth/login - Login")
    print("   POST /api/auth/refresh - Refresh token")
    print("   GET  /api/auth/profile - User profile")
    print("   GET  /api/products - List products")
    print("   POST /api/products - Create product")
    print("   GET  /api/products/<id> - Product details")
    
    return app

if __name__ == "__main__":
    # Загружаем переменные из .env
    load_dotenv()
    
    # Регистрируем обработчики сигналов
    signal.signal(signal.SIGTERM, shutdown_handler)
    signal.signal(signal.SIGINT, shutdown_handler)
    
    # Запускаем приложение
    app = main()
    
    # Используем FLASK_ENV для определения режима
    debug_mode = os.getenv('FLASK_ENV') == 'development'
    
    app.run(host="0.0.0.0", port=5000, debug=debug_mode)
