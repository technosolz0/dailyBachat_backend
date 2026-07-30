from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
from datetime import datetime
from app.core.security import decrypt_data

class UserBase(BaseModel):
    id: str # Firebase UID
    email: Optional[str] = None
    name: Optional[str] = None
    phone_number: Optional[str] = None
    device_info: Optional[str] = None
    fcm_token: Optional[str] = None

    class Config:
        from_attributes = True

    @field_validator('phone_number', mode='before')
    @classmethod
    def decrypt_phone(cls, v):
        if v and v != "N/A":
            try:
                res = decrypt_data(v)
                if res and res.startswith("gAAAAA"):
                    return "N/A"
                return res
            except Exception:
                return "N/A"
        return v

class UserCreate(UserBase):
    password: str
    referred_by_code: Optional[str] = None

class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone_number: Optional[str] = None
    device_info: Optional[str] = None
    fcm_token: Optional[str] = None

class UserInDB(UserBase):
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    is_admin: bool = False
    is_premium: bool = False
    premium_expiry: Optional[datetime] = None
    is_active: bool = True
    last_login: Optional[datetime] = None
    referral_code: Optional[str] = None
    referred_by_id: Optional[str] = None
    referral_count: int = 0

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
    phone_number: str # Fixed from 'phone' to 'phone_number' for consistency
    password: str
    device_info: Optional[str] = None
    fcm_token: Optional[str] = None
    referred_by_code: Optional[str] = None

class OTPVerify(BaseModel):
    email: EmailStr
    otp: str
    device_info: Optional[str] = None
    fcm_token: Optional[str] = None

class DeletionRequest(BaseModel):
    user_id: str
    reason: str

class AdminLoginRequest(BaseModel):
    email: EmailStr
    password: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    device_info: Optional[str] = None
    fcm_token: Optional[str] = None

class UserLoginResponse(BaseModel):
    user: UserInDB
    access_token: str
    token_type: str
    firebase_custom_token: Optional[str] = None

    class Config:
        from_attributes = True

class ForgotPasswordRequest(BaseModel):
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None

class ResetPasswordRequest(BaseModel):
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    otp: str
    new_password: str

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str
