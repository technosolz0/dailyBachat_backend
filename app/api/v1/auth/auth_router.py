from datetime import datetime, timedelta
import random
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core import security
from app.core.database import get_db
from app.models.user import User
from app.schemas.user import Token, RegisterRequest, OTPVerify, UserCreate, UserInDB

router = APIRouter()

# Temporary stores (In production, use Redis/DB)
otp_store = {}
pending_users = {} # Store user details until OTP verified

@router.post("/register/request")
async def register_request(user_data: RegisterRequest):
    """
    Step 1: Receive user details and send OTP (mocked for now).
    """
    # In a real app, send actual Email/SMS OTP
    otp = str(random.randint(100000, 999999))
    otp_store[user_data.email] = {
        "otp": otp,
        "expires": datetime.now() + timedelta(minutes=10)
    }
    pending_users[user_data.email] = user_data.dict()
    
    # print(f"DEBUG: OTP for {user_data.email} is {otp}")
    return {"message": "OTP sent successfully", "otp": otp} # Returning OTP for easy testing

@router.post("/register/verify")
async def register_verify(verification: OTPVerify, db: Session = Depends(get_db)):
    """
    Step 2: Verify OTP. User creation will happen via /sync after Firebase registration.
    """
    stored_otp_data = otp_store.get(verification.email)
    if not stored_otp_data:
        raise HTTPException(status_code=400, detail="OTP not requested or expired")
    
    if stored_otp_data["otp"] != verification.otp:
        raise HTTPException(status_code=400, detail="Invalid OTP")
    
    if datetime.now() > stored_otp_data["expires"]:
        del otp_store[verification.email]
        raise HTTPException(status_code=400, detail="OTP expired")

    # Cleanup stores
    if verification.email in otp_store:
        del otp_store[verification.email]
    
    # We keep pending_users for a bit longer or just rely on Flutter to send data to /sync
    # For now, let's just return success.
    return {"message": "OTP verified successfully", "success": True}

@router.post("/sync", response_model=UserInDB)
async def sync_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.id == user.id).first()
    if db_user:
        db_user.email = user.email
        db_user.name = user.name
        db_user.phone_number = user.phone_number
        db_user.device_info = user.device_info
        db_user.fcm_token = user.fcm_token
    else:
        db_user = User(**user.dict())
        db.add(db_user)
    
    db.commit()
    db.refresh(db_user)
    return db_user

@router.get("/me", response_model=UserInDB)
async def read_users_me(db: Session = Depends(get_db)):
    user_id = "test_user" 
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user
