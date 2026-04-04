import smtplib
import ssl
from email.message import EmailMessage
import os
from pydantic_settings import BaseSettings

class EmailSettings(BaseSettings):
    EMAIL_USERNAME: str
    EMAIL_PASSWORD: str
    SMTP_HOST: str
    SMTP_PORT: int
    SMTP_SSL: bool = True

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = EmailSettings()

class EmailService:
    def __init__(self):
        self.username = settings.EMAIL_USERNAME
        self.password = settings.EMAIL_PASSWORD
        self.host = settings.SMTP_HOST
        self.port = settings.SMTP_PORT
        self.use_ssl = settings.SMTP_SSL

    def send_otp(self, to_email: str, otp_code: str):
        msg = EmailMessage()
        msg.set_content(f"Your DailyBachat verification code is: {otp_code}\n\nThis code will expire in 10 minutes.")
        msg["Subject"] = "DailyBachat Verification Code"
        msg["From"] = self.username
        msg["To"] = to_email

        try:
            if self.use_ssl:
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(self.host, self.port, context=context) as server:
                    server.login(self.username, self.password)
                    server.send_message(msg)
            else:
                with smtplib.SMTP(self.host, self.port) as server:
                    # In some hosts, we might need server.starttls()
                    server.login(self.username, self.password)
                    server.send_message(msg)
            return True
        except Exception as e:
            print(f"FAILED TO SEND EMAIL: {e}")
            return False

email_service = EmailService()
