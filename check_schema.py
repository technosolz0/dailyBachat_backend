from app.core.database import engine
from sqlalchemy import inspect

def check_schema():
    inspector = inspect(engine)
    for table_name in inspector.get_table_names():
        print(f"Table: {table_name}")
        for column in inspector.get_columns(table_name):
            print(f"  Column: {column['name']} ({column['type']})")

if __name__ == "__main__":
    try:
        check_schema()
    except Exception as e:
        print(f"Error checking schema: {e}")
