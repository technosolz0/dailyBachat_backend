from app.core.database import engine
from sqlalchemy import text

def add_password_column():
    with engine.connect() as conn:
        print("Adding hashed_password column to users table...")
        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN hashed_password VARCHAR;"))
            conn.commit()
            print("Successfully added hashed_password column.")
        except Exception as e:
            if "already exists" in str(e):
                print("Column hashed_password already exists.")
            else:
                print(f"Error: {e}")

        print("Adding name, phone, password, device_info, and fcm_token columns to otps table...")
        try:
            conn.execute(text("ALTER TABLE otps ADD COLUMN name VARCHAR;"))
        except Exception: pass
        try:
            conn.execute(text("ALTER TABLE otps ADD COLUMN phone_number VARCHAR;"))
        except Exception: pass
        try:
            conn.execute(text("ALTER TABLE otps ADD COLUMN hashed_password VARCHAR;"))
        except Exception: pass
        try:
            conn.execute(text("ALTER TABLE otps ADD COLUMN device_info VARCHAR;"))
        except Exception: pass
        try:
            conn.execute(text("ALTER TABLE otps ADD COLUMN fcm_token VARCHAR;"))
        except Exception: pass
        conn.commit()
        print("Successfully updated otps table.")
        except Exception as e:
            if "already exists" in str(e):
                print("Columns already exist in otps table.")
            else:
                print(f"Error logic: {e}")

if __name__ == "__main__":
    add_password_column()
