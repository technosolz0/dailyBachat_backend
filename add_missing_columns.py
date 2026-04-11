from app.core.database import engine
from sqlalchemy import text

def add_missing_columns():
    with engine.connect() as conn:
        # 1. Update users table
        print("Checking users table...")
        cols_to_add_users = [
            ("hashed_password", "VARCHAR"),
            ("device_info", "VARCHAR"),
            ("fcm_token", "VARCHAR")
        ]
        
        for col_name, col_type in cols_to_add_users:
            try:
                conn.execute(text(f"ALTER TABLE users ADD COLUMN {col_name} {col_type};"))
                conn.commit()
                print(f"Added {col_name} to users.")
            except Exception as e:
                if "already exists" in str(e):
                    pass
                else:
                    print(f"Error adding {col_name} to users: {e}")

        # 2. Update otps table
        print("Checking otps table...")
        cols_to_add_otps = [
            ("name", "VARCHAR"),
            ("phone_number", "VARCHAR"),
            ("hashed_password", "VARCHAR"),
            ("device_info", "VARCHAR"),
            ("fcm_token", "VARCHAR")
        ]
        
        for col_name, col_type in cols_to_add_otps:
            try:
                conn.execute(text(f"ALTER TABLE otps ADD COLUMN {col_name} {col_type};"))
                conn.commit()
                print(f"Added {col_name} to otps.")
            except Exception as e:
                if "already exists" in str(e):
                    pass
                else:
                    print(f"Error adding {col_name} to otps: {e}")

        # 3. Update loans table (New field for notifications)
        print("Checking loans table...")
        try:
            conn.execute(text("ALTER TABLE loans ADD COLUMN person_phone VARCHAR;"))
            conn.commit()
            print("Added person_phone to loans.")
        except Exception as e:
            if "already exists" in str(e):
                print("Column person_phone already exists in loans.")
            else:
                print(f"Error adding person_phone to loans: {e}")

        print("Migration check complete.")

if __name__ == "__main__":
    add_missing_columns()
