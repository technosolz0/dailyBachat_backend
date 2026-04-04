from datetime import datetime, timedelta
import random
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core import security
from app.core.database import get_db
from app.models.user import User
from app.schemas.user import Token, RegisterRequest, OTPVerify, UserCreate, UserInDB

from app.core.email_service import email_service
from app.models.otp import OTP

router = APIRouter()

@router.post("/register/request")
async def register_request(user_data: RegisterRequest, db: Session = Depends(get_db)):
    """
    Step 1: Receive user details and send OTP via Email.
    """
    # Normalize email
    email = user_data.email.lower().strip()
    
    # Generate OTP
    otp_code = str(random.randint(100000, 999999))
    
    # Store in DB
    db_otp = db.query(OTP).filter(OTP.email == email).first()
    expires_at = datetime.utcnow() + timedelta(minutes=10)
    
    if db_otp:
        db_otp.otp = otp_code
        db_otp.expires_at = expires_at
        db_otp.created_at = datetime.utcnow()
    else:
        db_otp = OTP(email=email, otp=otp_code, expires_at=expires_at)
        db.add(db_otp)
    
    db.commit()
    
    # Send OTP via Email
    success = email_service.send_otp(email, otp_code)
    
    if not success:
        # For now, let's include it in response if mail fails just to avoid blocking tests
        # or we could raise an error.
        # But per user request, we want it SENT.
        raise HTTPException(
            status_code=500, 
            detail="Failed to send verification email. Please check your email configuration."
        )

    return {"message": "OTP sent successfully to your email"}

@router.post("/register/verify")
async def register_verify(verification: OTPVerify, db: Session = Depends(get_db)):
    """
    Step 2: Verify OTP.
    """
    email = verification.email.lower().strip()
    
    db_otp = db.query(OTP).filter(OTP.email == email).first()
    
    if not db_otp:
        raise HTTPException(status_code=400, detail="OTP not requested or expired")
    
    if db_otp.otp != verification.otp:
        raise HTTPException(status_code=400, detail="Invalid OTP")
    
    if datetime.utcnow() > db_otp.expires_at:
        db.delete(db_otp)
        db.commit()
        raise HTTPException(status_code=400, detail="OTP expired")

    # Cleanup OTP
    db.delete(db_otp)
    db.commit()
    
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
