from datetime import datetime, timedelta
import random
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.core import security
from app.core.database import get_db
from app.models.user import User
from app.schemas.user import Token, OTPRequest, OTPVerify, UserCreate, UserInDB

router = APIRouter()

# Temporary stores (In production, use Redis/DB)
otp_store = {}
pending_users = {} # Store user details until OTP verified

@router.post("/sync", response_model=UserInDB)
async def sync_user(user: UserCreate, db: Session = Depends(get_db)):
    """
    Sync Firebase user to our Postgres DB.
    Checks if user exists, updates if they do, creates if they don't.
    """
    db_user = db.query(User).filter(User.id == user.id).first()
    if db_user:
        # Update existing user info
        db_user.email = user.email
        db_user.name = user.name
        db_user.phone_number = user.phone_number
        db_user.device_info = user.device_info
        db_user.fcm_token = user.fcm_token
    else:
        # Create new user
        db_user = User(**user.dict())
        db.add(db_user)
    
    db.commit()
    db.refresh(db_user)
    return db_user

@router.get("/me", response_model=UserInDB)
async def read_users_me(db: Session = Depends(get_db)):
    # Placeholder: In real app, get user_id from token
    user_id = "test_user" 
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

# ... (Keep existing OTP logic if needed, but the primary sync is via /sync)

