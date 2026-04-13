from sqlalchemy import Column, String, DateTime, Integer
from app.core.database import Base
from datetime import datetime

class OTP(Base):
    __tablename__ = "otps"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, index=True, nullable=True)
    phone_number = Column(String, index=True, nullable=True)
    otp = Column(String, nullable=False)
    name = Column(String)
    hashed_password = Column(String)
    device_info = Column(String)
    fcm_token = Column(String)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
