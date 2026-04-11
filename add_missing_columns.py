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
        cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name='users' AND column_name='is_admin';")
        if not cursor.fetchone():
            print("Adding is_admin to users...")
            cursor.execute("ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT FALSE;")

        cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name='users' AND column_name='is_active';")
        if not cursor.fetchone():
            print("Adding is_active to users...")
            cursor.execute("ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT TRUE;")

        cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name='users' AND column_name='last_login';")
        if not cursor.fetchone():
            print("Adding last_login to users...")
            cursor.execute("ALTER TABLE users ADD COLUMN last_login TIMESTAMP WITH TIME ZONE;")

        # Commit changes and close
        conn.commit()
        print("Database updated successfully!")
        cursor.close()
        conn.close()

    except Exception as e:
        print(f"Error updating database: {e}")

if __name__ == "__main__":
    update_db()
