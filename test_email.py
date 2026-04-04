from app.core.email_service import email_service
import sys

def test_email(email):
    print(f"Attempting to send test OTP to {email}...")
    success = email_service.send_otp(email, "123456")
    if success:
        print("SUCCESS: email sent!")
    else:
        print("FAILED: check logs/connection")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_email.py <email>")
    else:
        test_email(sys.argv[1])
