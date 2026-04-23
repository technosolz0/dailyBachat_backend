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

        # 4. Update customers table
        print("Checking customers table...")
        cols_to_add_customers = [
            ("address", "VARCHAR"),
            ("created_at", "TIMESTAMP WITH TIME ZONE DEFAULT NOW()")
        ]
        for col_name, col_type in cols_to_add_customers:
            try:
                conn.execute(text(f"ALTER TABLE customers ADD COLUMN {col_name} {col_type};"))
                conn.commit()
                print(f"Added {col_name} to customers.")
            except Exception as e:
                conn.rollback()
                if "already exists" in str(e).lower():
                    pass
                else:
                    print(f"Error adding {col_name} to customers: {e}")

        # 5. Update invoices table
        print("Checking invoices table...")
        cols_to_add_invoices = [
            ("date", "TIMESTAMP WITH TIME ZONE DEFAULT NOW()"),
            ("creator_name", "VARCHAR"),
            ("tax_percent", "FLOAT DEFAULT 0.0"),
            ("paid_amount", "FLOAT DEFAULT 0.0"),
            ("status", "VARCHAR DEFAULT 'pending'"),
            ("pdf_url", "VARCHAR")
        ]
        for col_name, col_type in cols_to_add_invoices:
            try:
                conn.execute(text(f"ALTER TABLE invoices ADD COLUMN {col_name} {col_type};"))
                conn.commit()
                print(f"Added {col_name} to invoices.")
            except Exception as e:
                conn.rollback()
                if "already exists" in str(e).lower():
                    pass
                else:
                    print(f"Error adding {col_name} to invoices: {e}")

        # 6. Update quotations table
        print("Checking quotations table...")
        cols_to_add_quotations = [
            ("date", "TIMESTAMP WITH TIME ZONE DEFAULT NOW()"),
            ("creator_name", "VARCHAR"),
            ("tax_percent", "FLOAT DEFAULT 0.0"),
            ("status", "VARCHAR DEFAULT 'draft'"),
            ("pdf_url", "VARCHAR"),
            ("advance_amount", "FLOAT DEFAULT 0.0")
        ]
        for col_name, col_type in cols_to_add_quotations:
            try:
                conn.execute(text(f"ALTER TABLE quotations ADD COLUMN {col_name} {col_type};"))
                conn.commit()
                print(f"Added {col_name} to quotations.")
            except Exception as e:
                conn.rollback()
                if "already exists" in str(e).lower():
                    pass
                else:
                    print(f"Error adding {col_name} to quotations: {e}")

        print("Migration check complete.")

if __name__ == "__main__":
    add_missing_columns()
