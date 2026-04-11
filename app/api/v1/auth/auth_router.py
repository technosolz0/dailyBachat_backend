from datetime import datetime, timedelta
import random
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from app.core import security
from app.core.database import get_db
from app.models.user import User
from app.schemas.user import (
    Token, RegisterRequest, OTPVerify, UserCreate, 
    UserInDB, DeletionRequest, FCMUpdate, LoginRequest, UserLoginResponse
)
from app.core.security import get_password_hash, verify_password, create_access_token
from firebase_admin import auth
import uuid

from app.core.email_service import email_service
from app.models.otp import OTP

router = APIRouter()

@router.post("/register/request")
async def register_request(user_data: RegisterRequest, db: Session = Depends(get_db)):
    """
    Step 1: Receive user details and send OTP via Email.
    """
    email = user_data.email.lower().strip()
    hashed_password = get_password_hash(user_data.password)
    
    # Generate OTP
    otp_code = str(random.randint(100000, 999999))
    
    # Store in DB with pending profile info
    db_otp = db.query(OTP).filter(OTP.email == email).first()
    expires_at = datetime.utcnow() + timedelta(minutes=10)
    
    if db_otp:
        db_otp.otp = otp_code
        db_otp.name = user_data.name
        db_otp.phone_number = user_data.phone_number
        db_otp.hashed_password = hashed_password
        db_otp.expires_at = expires_at
        db_otp.created_at = datetime.utcnow()
    else:
        db_otp = OTP(
            email=email, 
            otp=otp_code, 
            name=user_data.name,
            phone_number=user_data.phone_number,
            hashed_password=hashed_password,
            expires_at=expires_at
        )
        db.add(db_otp)
    
    db.commit()
    
    success = email_service.send_otp(email, otp_code)
    
    if not success:
        return {
            "message": f"OTP sent successfully (DEBUG: {otp_code})",
            "warning": "Email sending failed. Please check SMTP configuration."
        }

    return {"message": "OTP sent successfully to your email"}

@router.post("/register/verify")
async def register_verify(verification: OTPVerify, db: Session = Depends(get_db)):
    """
    Step 2: Verify OTP and create user.
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

    # Step 3: Create Shadow Firebase User for Chat
    try:
        fb_user = auth.get_user_by_email(email)
    except auth.UserNotFoundError:
        fb_user = auth.create_user(
            email=email,
            password=str(uuid.uuid4()), # We don't need their real password in Firebase
            display_name=db_otp.name
        )

    # Step 4: Create local user
    db_user = db.query(User).filter(User.email == email).first()
    if not db_user:
        db_user = User(
            id=fb_user.uid,
            email=email,
            name=db_otp.name,
            phone_number=db_otp.phone_number,
            hashed_password=db_otp.hashed_password
        )
        db.add(db_user)
    else:
        # Update existing user if they are re-verifying
        db_user.id = fb_user.uid
        db_user.name = db_otp.name
        db_user.phone_number = db_otp.phone_number
        db_user.hashed_password = db_otp.hashed_password

    db.delete(db_otp)
    db.commit()
    db.refresh(db_user)
    
    return {"message": "Account verified and created successfully", "user": db_user}

@router.post("/login", response_model=UserLoginResponse)
async def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    """
    Authenticates user, creates JWT, and generates Firebase Custom Token for Chat.
    """
    email = login_data.email.lower().strip()
    user = db.query(User).filter(User.email == email).first()
    
    if not user or not user.hashed_password or not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Generate JWT
    access_token = create_access_token(data={"sub": user.id})
    
    # Generate Firebase Custom Token
    custom_token = auth.create_custom_token(user.id).decode('utf-8')
    
    user.last_login = datetime.utcnow()
    db.commit()
    
    return {
        "user": user,
        "access_token": access_token,
        "token_type": "bearer",
        "firebase_custom_token": custom_token
    }

@router.post("/sync", response_model=UserInDB)
async def sync_user(user: UserCreate, db: Session = Depends(get_db)):
    """
    Sync user data from Firebase/Auth. Stores device info and records last login.
    """
    db_user = db.query(User).filter(User.id == user.id).first()
    if db_user:
        db_user.email = user.email
        db_user.name = user.name
        db_user.phone_number = user.phone_number
        db_user.device_info = user.device_info
        db_user.fcm_token = user.fcm_token
        db_user.last_login = datetime.utcnow()
    else:
        db_user = User(**user.dict())
        db_user.last_login = datetime.utcnow()
        db.add(db_user)
    
    db.commit()
    db.refresh(db_user)
    return db_user

@router.put("/fcm-token")
async def update_fcm_token(
    fcm_data: FCMUpdate, 
    x_user_id: str = Header(...),
    db: Session = Depends(get_db)
):
    """
    Update the FCM token for a user.
    """
    db_user = db.query(User).filter(User.id == x_user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    db_user.fcm_token = fcm_data.fcm_token
    db_user.updated_at = datetime.utcnow()
    db.commit()
    return {"message": "FCM token updated successfully"}

@router.get("/me", response_model=UserInDB)
async def read_users_me(
    db: Session = Depends(get_db),
    x_user_id: str = Header(...)
):
    db_user = db.query(User).filter(User.id == x_user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

@router.post("/delete-request")
async def delete_request(request: DeletionRequest, db: Session = Depends(get_db)):
    """
    Submits a deletion request for the user.
    """
    db_user = db.query(User).filter(User.id == request.user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    db_user.deletion_requested = True
    db_user.deletion_reason = request.reason
    db_user.deletion_requested_at = datetime.utcnow()
    
    db.commit()
    return {"message": "Deletion request submitted successfully. Admin will review and delete your account permanently."}
