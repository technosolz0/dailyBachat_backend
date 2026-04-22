from app.core.database import engine
from sqlalchemy import text
import logging

def add_missing_columns():
    with engine.connect() as conn:
        # 1. Update users table
        print("Checking users table...")
        cols_to_add_users = [
            ("hashed_password", "VARCHAR"),
            ("device_info", "VARCHAR"),
            ("fcm_token", "VARCHAR"),
            ("is_premium", "BOOLEAN DEFAULT FALSE"),
            ("is_admin", "BOOLEAN DEFAULT FALSE")
        ]
        
        for col_name, col_type in cols_to_add_users:
            try:
                # Use a savepoint or just rollback on failure to clear transaction state
                conn.execute(text(f"ALTER TABLE users ADD COLUMN {col_name} {col_type};"))
                conn.commit()
                print(f"Added {col_name} to users.")
            except Exception as e:
                conn.rollback() # CRITICAL: Clear the aborted transaction state
                if "already exists" in str(e).lower():
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
                conn.rollback() # CRITICAL: Clear the aborted transaction state
                if "already exists" in str(e).lower():
                    pass
                else:
                    print(f"Error adding {col_name} to otps: {e}")

        # 3. Update loans table
        print("Checking loans table...")
        cols_to_add_loans = [
            ("person_phone", "VARCHAR"),
            ("creator_name", "VARCHAR"),
            ("payment_history", "JSON DEFAULT '[]'::json"),
            ("reason", "VARCHAR"),
            ("expected_return_date", "TIMESTAMP WITH TIME ZONE")
        ]
        
        for col_name, col_type in cols_to_add_loans:
            try:
                conn.execute(text(f"ALTER TABLE loans ADD COLUMN {col_name} {col_type};"))
                conn.commit()
                print(f"Added {col_name} to loans.")
            except Exception as e:
                conn.rollback()
                if "already exists" in str(e).lower():
                    pass
                else:
                    print(f"Error adding {col_name} to loans: {e}")

        # 4. Update customers table (optional check)
        print("Checking customers table...")
        try:
            conn.execute(text("ALTER TABLE customers ADD COLUMN address VARCHAR;"))
            conn.commit()
            print("Added address to customers.")
        except Exception as e:
            conn.rollback()
            if "already exists" in str(e).lower():
                pass
            else:
                print(f"Error adding address to customers: {e}")

        print("Migration check complete.")

if __name__ == "__main__":
    add_missing_columns()
