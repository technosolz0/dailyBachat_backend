import sys
import uuid
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.user import User
from app.core.security import get_password_hash

def create_admin(name: str, email: str, password: str, phone: str = None):
    db = SessionLocal()
    try:
        # Check if user already exists
        email = email.lower().strip()
        user = db.query(User).filter(User.email == email).first()
        
        if user:
            print(f"User with email '{email}' already exists.")
            confirm = input(f"Do you want to promote this user to admin and update their password? (y/n): ")
            if confirm.lower() == 'y':
                user.is_admin = True
                user.hashed_password = get_password_hash(password)
                if name:
                    user.name = name
                if phone:
                    user.phone_number = phone
                db.commit()
                print(f"Successfully updated user {email} to admin.")
            else:
                print("Operation cancelled.")
            return

        # Create new admin user
        new_user = User(
            id=str(uuid.uuid4()),
            email=email,
            name=name,
            phone_number=phone,
            hashed_password=get_password_hash(password),
            is_admin=True,
            is_active=True
        )
        
        db.add(new_user)
        db.commit()
        print(f"Successfully created admin user: {email}")
        print(f"Name: {name}")
        print(f"ID: {new_user.id}")
        
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    print("--- DailyBachat Admin Creation Script ---")
    
    if len(sys.argv) >= 4:
        name = sys.argv[1]
        email = sys.argv[2]
        password = sys.argv[3]
        phone = sys.argv[4] if len(sys.argv) > 4 else None
    else:
        name = input("Enter Admin Name: ")
        email = input("Enter Admin Email: ")
        password = input("Enter Admin Password: ")
        phone = input("Enter Admin Phone (optional): ")
        if not phone:
            phone = None

    if not email or not password:
        print("Email and Password are required.")
        sys.exit(1)
        
    create_admin(name, email, password, phone)
