from app import app, init_db

# Initialize database on application startup
init_db()

if __name__ == "__main__":
    app.run()