import os
import sqlite3
from app.database import engine, Base
from app.models import models
from app.utils.auth import get_password_hash
from app.database import SessionLocal

def initialize_project():
    print("--- Starting Blind Voice Project Setup ---")

    # 1. Create Uploads Directory
    if not os.path.exists("uploads"):
        os.makedirs("uploads")
        print("[+] Created 'uploads/' folder.")
    else:
        print("[*] 'uploads/' folder already exists.")

    # 2. Create Database and Tables
    print("[*] Initializing Database...")
    Base.metadata.create_all(bind=engine)
    print("[+] Database tables created successfully.")

    # 3. Create a Default Admin User (Optional but helpful)
    db = SessionLocal()
    try:
        admin_exists = db.query(models.User).filter(models.User.username == "admin").first()
        if not admin_exists:
            new_admin = models.User(
                username="admin",
                hashed_password=get_password_hash("admin123"),
                role="admin"
            )
            db.add(new_admin)
            db.commit()
            print("[+] Default Admin created: User: admin | Pass: admin123")
        else:
            print("[*] Admin user already exists.")
    except Exception as e:
        print(f"[-] Error creating admin: {e}")
    finally:
        db.close()

    print("--- Setup Complete! Run 'uvicorn app.main:app --reload' to start ---")

if __name__ == "__main__":
    initialize_project()