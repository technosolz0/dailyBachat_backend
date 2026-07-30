import sys
from app.core.database import SessionLocal
from app.models.user import User
from app.core.security import decrypt_data

def cleanup_phones():
    db = SessionLocal()
    try:
        users = db.query(User).all()
        updated_count = 0
        for u in users:
            if u.phone_number and u.phone_number.startswith("gAAAAA"):
                decrypted = None
                try:
                    decrypted = decrypt_data(u.phone_number)
                except Exception:
                    pass

                if decrypted and not decrypted.startswith("gAAAAA") and decrypted != "N/A":
                    u.phone_number = decrypted
                    updated_count += 1
                    print(f"Decrypted phone for user {u.email or u.id}: {decrypted}")
                elif u.email and "@dailybachat.com" in u.email:
                    prefix = u.email.split("@")[0]
                    if prefix.isdigit():
                        u.phone_number = f"+{prefix}"
                        updated_count += 1
                        print(f"Extracted phone from email for user {u.email}: +{prefix}")
                    elif prefix.startswith("+") and prefix[1:].isdigit():
                        u.phone_number = prefix
                        updated_count += 1
                        print(f"Extracted phone from email for user {u.email}: {prefix}")
                else:
                    u.phone_number = None
                    updated_count += 1
                    print(f"Cleared un-decryptable cipher phone for user {u.email or u.id}")

        if updated_count > 0:
            db.commit()
            print(f"Successfully cleaned up {updated_count} user phone records in database.")
        else:
            print("No encrypted phone numbers needed cleanup.")

    except Exception as e:
        db.rollback()
        print(f"Error during cleanup: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    cleanup_phones()
