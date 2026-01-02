from web_server import create_app

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
    print("   GET  /api/products - List products")
    print("   POST /api/products - Create product")
    print("   GET  /api/products/<id> - Product details")
    
    return app

if __name__ == "__main__":
    app = main()
    app.run(host="0.0.0.0", port=5000, debug=True)