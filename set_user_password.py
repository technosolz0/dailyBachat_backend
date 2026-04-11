from app.core.database import SessionLocal
from app.models.user import User
from app.core.security import get_password_hash
import sys

def set_password(email, password):
    db = SessionLocal()
    user = db.query(User).filter(User.email == email).first()
    if not user:
        print(f"User {email} not found.")
        return
    
    user.hashed_password = get_password_hash(password)
    db.commit()
    print(f"Password set for {email}")
    db.close()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python set_user_password.py <email> <password>")
    else:
        set_password(sys.argv[1], sys.argv[2])
