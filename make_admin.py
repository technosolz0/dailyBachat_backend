import sys
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.user import User

def promote_to_admin(email_or_id: str):
    db = SessionLocal()
    try:
        user = db.query(User).filter(
            (User.email == email_or_id) | (User.id == email_or_id)
        ).first()
        
        if not user:
            print(f"User with email or ID '{email_or_id}' not found.")
            return

        user.is_admin = True
        db.commit()
        print(f"Successfully promoted {user.email} (ID: {user.id}) to admin.")
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python make_admin.py <email_or_id>")
    else:
        promote_to_admin(sys.argv[1])
