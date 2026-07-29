from app.core.database import engine
from sqlalchemy import text
import logging

def add_missing_columns():
    with engine.connect() as conn:
        # 1. Update users table
        print("Checking users table...")
        cols_to_add_users = [
            ("name", "VARCHAR"),
            ("phone_number", "VARCHAR"),
            ("hashed_password", "VARCHAR"),
            ("device_info", "VARCHAR"),
            ("fcm_token", "VARCHAR"),
            ("is_premium", "BOOLEAN DEFAULT FALSE"),
            ("is_admin", "BOOLEAN DEFAULT FALSE"),
            ("referral_code", "VARCHAR"),
            ("referred_by_id", "VARCHAR")
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

        # Create unique index for referral_code
        try:
            conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_referral_code ON users (referral_code);"))
            conn.commit()
            print("Created unique index on users.referral_code.")
        except Exception as e:
            conn.rollback()
            print(f"Error creating unique index on users.referral_code: {e}")

        # 2. Update otps table
        print("Checking otps table...")
        # Drop NOT NULL constraint on email to make it nullable
        try:
            conn.execute(text("ALTER TABLE otps ALTER COLUMN email DROP NOT NULL;"))
            conn.commit()
            print("Dropped NOT NULL constraint from otps.email.")
        except Exception as e:
            conn.rollback()
            print(f"Note on otps.email NOT NULL removal: {e}")

        # Drop old primary key constraint if it exists
        try:
            conn.execute(text("ALTER TABLE otps DROP CONSTRAINT IF EXISTS otps_pkey;"))
            conn.commit()
            print("Dropped primary key constraint otps_pkey.")
        except Exception as e:
            conn.rollback()
            print(f"Note on dropping otps_pkey: {e}")

        # Add id column as serial primary key
        try:
            conn.execute(text("ALTER TABLE otps ADD COLUMN id SERIAL PRIMARY KEY;"))
            conn.commit()
            print("Added id SERIAL PRIMARY KEY to otps.")
        except Exception as e:
            conn.rollback()
            if "already exists" in str(e).lower():
                pass
            else:
                print(f"Error adding id to otps: {e}")

        cols_to_add_otps = [
            ("name", "VARCHAR"),
            ("phone_number", "VARCHAR"),
            ("hashed_password", "VARCHAR"),
            ("device_info", "VARCHAR"),
            ("fcm_token", "VARCHAR"),
            ("referred_by_code", "VARCHAR")
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
            ("expected_return_date", "TIMESTAMP WITH TIME ZONE"),
            ("reminder_2days_sent", "BOOLEAN DEFAULT FALSE"),
            ("reminder_1day_sent", "BOOLEAN DEFAULT FALSE"),
            ("reminder_duedate_sent", "BOOLEAN DEFAULT FALSE")
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
            ("pdf_url", "VARCHAR"),
            ("reminder_2days_sent", "BOOLEAN DEFAULT FALSE"),
            ("reminder_1day_sent", "BOOLEAN DEFAULT FALSE"),
            ("reminder_duedate_sent", "BOOLEAN DEFAULT FALSE")
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

        # 7. Update group_splits table
        print("Checking group_splits table...")
        cols_to_add_splits = [
            ("expenses", "JSON DEFAULT '[]'::json")
        ]
        for col_name, col_type in cols_to_add_splits:
            try:
                conn.execute(text(f"ALTER TABLE group_splits ADD COLUMN {col_name} {col_type};"))
                conn.commit()
                print(f"Added {col_name} to group_splits.")
            except Exception as e:
                conn.rollback()
                if "already exists" in str(e).lower():
                    pass
                else:
                    print(f"Error adding {col_name} to group_splits: {e}")

        print("Migration check complete.")

if __name__ == "__main__":
    add_missing_columns()
