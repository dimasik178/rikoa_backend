from web_server import create_app

def main():
    app = create_app()
    
    print("🚀 Market API Server starting...")
    print("📊 Database initialized")
    print("🌐 JSON API ready")
    print("💰 Investment system: ACTIVE")
    
    return app

if __name__ == "__main__":
    app = main()
    app.run(host="0.0.0.0", port=5000, debug=True)