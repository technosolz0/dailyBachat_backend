from sqlalchemy import Column, String, DateTime
from app.core.database import Base
from datetime import datetime

class OTP(Base):
    __tablename__ = "otps"

    email = Column(String, primary_key=True, index=True)
    otp = Column(String, nullable=False)
    name = Column(String)
    phone_number = Column(String)
    hashed_password = Column(String)
    device_info = Column(String)
    fcm_token = Column(String)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
