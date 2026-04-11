import psycopg2
import os
from dotenv import load_dotenv

# Load database environment variables
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

def update_db():
    try:
        # Connect to the database
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()

        # Add missing columns to quotations table
        print("Checking quotations table...")
        cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name='quotations' AND column_name='advance_amount';")
        if not cursor.fetchone():
            print("Adding advance_amount to quotations...")
            cursor.execute("ALTER TABLE quotations ADD COLUMN advance_amount FLOAT DEFAULT 0.0;")
        
        cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name='quotations' AND column_name='tax_percent';")
        if not cursor.fetchone():
            print("Adding tax_percent to quotations...")
            cursor.execute("ALTER TABLE quotations ADD COLUMN tax_percent FLOAT DEFAULT 0.0;")

        # Add missing column to invoices table
        print("Checking invoices table...")
        cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name='invoices' AND column_name='tax_percent';")
        if not cursor.fetchone():
            print("Adding tax_percent to invoices...")
            cursor.execute("ALTER TABLE invoices ADD COLUMN tax_percent FLOAT DEFAULT 0.0;")

        # Add missing columns to users table
        print("Checking users table...")
        columns_to_add = [
            ("id", "VARCHAR PRIMARY KEY"),
            ("email", "VARCHAR UNIQUE NOT NULL"),
            ("name", "VARCHAR"),
            ("phone_number", "VARCHAR"),
            ("device_info", "VARCHAR"),
            ("fcm_token", "VARCHAR"),
            ("created_at", "TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP"),
            ("updated_at", "TIMESTAMP WITH TIME ZONE"),
            ("deletion_requested", "BOOLEAN DEFAULT FALSE"),
            ("deletion_reason", "VARCHAR"),
            ("deletion_requested_at", "TIMESTAMP WITH TIME ZONE"),
            ("is_admin", "BOOLEAN DEFAULT FALSE"),
            ("is_active", "BOOLEAN DEFAULT TRUE"),
            ("last_login", "TIMESTAMP WITH TIME ZONE")
        ]

        for col_name, col_type in columns_to_add:
            cursor.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name='users' AND column_name='{col_name}';")
            if not cursor.fetchone():
                print(f"Adding {col_name} to users...")
                cursor.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type};")

        # Commit changes and close
        conn.commit()
        print("Database updated successfully!")
        cursor.close()
        conn.close()

    except Exception as e:
        print(f"Error updating database: {e}")

if __name__ == "__main__":
    update_db()
