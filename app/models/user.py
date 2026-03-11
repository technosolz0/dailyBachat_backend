from sqlalchemy import Column, String, DateTime, func
from app.core.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True) # This will store the Firebase UID
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String)
    phone_number = Column(String)
    device_info = Column(String)
    fcm_token = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
