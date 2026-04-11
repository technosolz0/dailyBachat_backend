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
    is_admin: bool = False
    is_premium: bool = False
    is_active: bool = True
    last_login: Optional[datetime] = None

class FCMUpdate(BaseModel):
    fcm_token: str

class AdminUserUpdate(BaseModel):
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None
    is_premium: Optional[bool] = None

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None
    user_id: Optional[str] = None

class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    phone: str
    password: str
    device_info: Optional[str] = None

class OTPVerify(BaseModel):
    email: EmailStr
    otp: str

class DeletionRequest(BaseModel):
    user_id: str
    reason: str

class AdminLoginRequest(BaseModel):
    email: EmailStr
    password: str
