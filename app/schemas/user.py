from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    id: str # Firebase UID
    email: EmailStr
    name: Optional[str] = None
    phone_number: Optional[str] = None
    device_info: Optional[str] = None
    fcm_token: Optional[str] = None

class UserCreate(UserBase):
    pass

class UserUpdate(BaseModel):
    name: Optional[str] = None
    phone_number: Optional[str] = None
    device_info: Optional[str] = None
    fcm_token: Optional[str] = None

class UserInDB(UserBase):
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None
    user_id: Optional[str] = None

class OTPRequest(BaseModel):
    email: EmailStr

class OTPVerify(BaseModel):
    email: EmailStr
    otp: str
