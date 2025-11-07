from web_server import create_app

def main():
    app = create_app()
    
    print("🚀 RikoaTech API Server starting...")
    print("📊 Database initialized")
    print("🌐 JSON API ready")
    print("\n🆕 NEW TZ Endpoints:")
    print("GET    /api/product?page=1 - Get products (6 per page)")
    print("GET    /api/product/<id>/buyers - Get product buyers (max 6)")
    print("GET    /photos/<id> - Get product image")
    print("POST   /api/product/buy - Purchase product")
    print("POST   /api/auth/login - Login")
    print("POST   /api/auth/register - Register")
    print("GET    /api/auth/profile - Get profile (Bearer token)")
    
    print("\n📋 Legacy endpoints (for compatibility):")
    print("GET    /api/products - Get products with pagination")
    print("POST   /api/products - Create product")
    print("GET    /api/products/<id> - Get product details")
    
    return app

if __name__ == "__main__":
    app = main()
    app.run(host="0.0.0.0", port=5000, debug=True)
