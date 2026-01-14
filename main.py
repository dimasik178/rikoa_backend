from web_server import create_app
import os
from dotenv import load_dotenv
import signal
import sys

def shutdown_handler(signum, frame):
    print(f"Получен сигнал {signum}, завершаем работу...")
    sys.exit(0)

def main():
    app = create_app()
    
    print("🚀 Market API Server starting...")
    print("📊 Database initialized")
    print("🌐 JSON API ready")
    print("💰 Investment system: ACTIVE")
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

# Регистрируем обработчики
signal.signal(signal.SIGTERM, shutdown_handler)
signal.signal(signal.SIGINT, shutdown_handler)

if __name__ == "__main__":
    load_dotenv()  # Загружаем переменные из .env
    
    app = main()
    
    # Используем FLASK_ENV для определения режима
    debug_mode = os.getenv('FLASK_ENV') == 'development'
    
    app.run(host="0.0.0.0", port=5000, debug=debug_mode)