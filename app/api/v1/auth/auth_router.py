from datetime import datetime, timedelta
import random
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from app.core import security
from app.core.database import get_db
from app.models.user import User
from app.schemas.user import (
    Token, RegisterRequest, OTPVerify, UserCreate, 
    UserInDB, DeletionRequest, FCMUpdate, LoginRequest, UserLoginResponse,
    ForgotPasswordRequest, ResetPasswordRequest, ChangePasswordRequest
)
from app.core.security import (
    get_password_hash, verify_password, create_access_token, 
    get_current_user_id, encrypt_data, decrypt_data
)
from firebase_admin import auth
import uuid

from app.core.email_service import email_service
from app.models.otp import OTP

def find_user_by_phone(db: Session, phone: str):
    """
    Finds a user by phone number. Handles encryption by decrypting and checking if needed,
    but first tries exact match (just in case they aren't encrypted or they use deterministic encryption).
    """
    if not phone:
        return None
    
    # Try exact match first
    user = db.query(User).filter(User.phone_number == phone).first()
    if user:
        return user
        
    # Fallback: fetch all and decrypt (optimized would be having a hash)
    all_users = db.query(User).all()
    for u in all_users:
        if u.phone_number:
            try:
                decrypted = decrypt_data(u.phone_number)
                if decrypted == phone:
                    return u
            except Exception:
                continue
    return None

router = APIRouter()

@router.post("/register/request")
async def register_request(user_data: RegisterRequest, db: Session = Depends(get_db)):
    """
    Step 1: Receive user details and send OTP via Email.
    """
    email = user_data.email.lower().strip()
    hashed_password = get_password_hash(user_data.password)
    
    # Encrypt sensitive data
    encrypted_phone = encrypt_data(user_data.phone_number)
    
    # Generate OTP
    otp_code = str(random.randint(100000, 999999))
    
    # Store in DB with pending profile info
    db_otp = db.query(OTP).filter(OTP.email == email).first()
    expires_at = datetime.utcnow() + timedelta(minutes=10)
    
    if db_otp:
        db_otp.otp = otp_code
        db_otp.name = user_data.name
        db_otp.phone_number = encrypted_phone
        db_otp.hashed_password = hashed_password
        db_otp.device_info = user_data.device_info
        db_otp.fcm_token = user_data.fcm_token
        db_otp.expires_at = expires_at
        db_otp.created_at = datetime.utcnow()
    else:
        db_otp = OTP(
            email=email, 
            otp=otp_code, 
            name=user_data.name,
            phone_number=encrypted_phone,
            hashed_password=hashed_password,
            device_info=user_data.device_info,
            fcm_token=user_data.fcm_token,
            expires_at=expires_at
        )
        db.add(db_otp)
    
    db.commit()
    
    # MOBILE OTP (Firebase) - Currently commented out as requested
    """
    # To implement Firebase Mobile Auth, we would send a session info from client
    # and verify it here. For now, we only use Email OTP.
    """

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

    # Step 3: Create local user
    db_user = db.query(User).filter(User.email == email).first()
    if not db_user:
        db_user = User(
            id=str(uuid.uuid4()),
            email=email,
            name=db_otp.name,
            phone_number=db_otp.phone_number, # Already encrypted in OTP table
            hashed_password=db_otp.hashed_password,
            device_info=verification.device_info or db_otp.device_info,
            fcm_token=verification.fcm_token or db_otp.fcm_token,
            last_login=datetime.utcnow()
        )
        db.add(db_user)
    else:
        # User already exists, just update info
        db_user.device_info = verification.device_info or db_otp.device_info
        db_user.fcm_token = verification.fcm_token or db_otp.fcm_token
        db_user.last_login = datetime.utcnow()

    # Step 5: Generate Auth Tokens (Login user immediately after verification)
    access_token = create_access_token(data={"sub": db_user.id})
    
    # Generate Firebase Custom Token (Safely)
    try:
        custom_token_binary = auth.create_custom_token(db_user.id)
        custom_token = custom_token_binary.decode('utf-8') if isinstance(custom_token_binary, bytes) else custom_token_binary
    except Exception as fe:
        print(f"Firebase token failed during registration: {fe}")
        custom_token = None

    # Clean up OTP and commit
    db.delete(db_otp)
    db.commit()
    db.refresh(db_user)
    
    return {
        "message": "Account verified and created successfully", 
        "user": db_user,
        "access_token": access_token,
        "token_type": "bearer",
        "firebase_custom_token": custom_token
    }

@router.post("/login", response_model=UserLoginResponse)
async def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    """
    Authenticates user, creates JWT, and generates Firebase Custom Token for Chat.
    """
    try:
        email = login_data.email.lower().strip()
        user = db.query(User).filter(User.email == email).first()
        
        if not user or not user.hashed_password or not verify_password(login_data.password, user.hashed_password):
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        # Generate JWT
        access_token = create_access_token(data={"sub": user.id})
        
        # Generate Firebase Custom Token (Safely)
        try:
            custom_token_binary = auth.create_custom_token(user.id)
            custom_token = custom_token_binary.decode('utf-8') if isinstance(custom_token_binary, bytes) else custom_token_binary
        except Exception as fe:
            print(f"Firebase token failed: {fe}")
            custom_token = None
        
        # Update login details
        user.last_login = datetime.utcnow()
        if login_data.device_info:
            user.device_info = login_data.device_info
        if login_data.fcm_token:
            user.fcm_token = login_data.fcm_token
            
        db.commit()
        
        return {
            "user": user,
            "access_token": access_token,
            "token_type": "bearer",
            "firebase_custom_token": custom_token
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_msg = f"In-app error: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

@router.post("/forgot-password/request")
async def forgot_password_request(data: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """
    Send OTP for password reset (Phone preferred, Email fallback).
    """
    user = None
    identifier = ""
    is_phone = False

    if data.phone_number:
        user = find_user_by_phone(db, data.phone_number)
        identifier = data.phone_number
        is_phone = True
    elif data.email:
        email = data.email.lower().strip()
        user = db.query(User).filter(User.email == email).first()
        identifier = email
    
    if not user:
        detail = "User with this phone number not found" if is_phone else "User with this email not found"
        raise HTTPException(status_code=404, detail=detail)
        
    otp_code = str(random.randint(100000, 999999))
    expires_at = datetime.utcnow() + timedelta(minutes=10)
    
    # Cleanup old OTPs for this identifier
    db.query(OTP).filter((OTP.email == identifier) | (OTP.phone_number == identifier)).delete()
    
    db_otp = OTP(
        email=user.email if not is_phone else None,
        phone_number=identifier if is_phone else None,
        otp=otp_code, 
        expires_at=expires_at
    )
    db.add(db_otp)
    db.commit()
    
    if is_phone:
        # With Firebase Auth, the frontend handles sending the SMS.
        # This endpoint now just validates that the user exists.
        return {"message": "User verified. Please proceed with Firebase Phone Auth."}
    else:
        email_service.send_otp(user.email, otp_code)
        return {"message": f"Reset OTP sent to your email (DEBUG: {otp_code})"}

@router.post("/forgot-password/reset")
async def forgot_password_reset(data: ResetPasswordRequest, db: Session = Depends(get_db)):
    """
    Reset password using OTP (supports phone or email).
    """
    identifier = data.phone_number if data.phone_number else (data.email.lower().strip() if data.email else None)
    if not identifier:
        raise HTTPException(status_code=400, detail="Missing identifier (email or phone_number)")

    db_otp = db.query(OTP).filter(
        (OTP.email == identifier) | (OTP.phone_number == identifier)
    ).first()
    
    if not db_otp or db_otp.otp != data.otp or datetime.utcnow() > db_otp.expires_at:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")
        
    user = None
    if data.phone_number:
        user = find_user_by_phone(db, data.phone_number)
    else:
        user = db.query(User).filter(User.email == identifier).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    user.hashed_password = get_password_hash(data.new_password)
    db.delete(db_otp)
    db.commit()
    return {"message": "Password reset successfully"}

@router.post("/change-password")
async def change_password(
    data: ChangePasswordRequest, 
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """
    Change password for authenticated user.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    if not verify_password(data.old_password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect old password")
        
    user.hashed_password = get_password_hash(data.new_password)
    db.commit()
    return {"message": "Password changed successfully"}

@router.post("/sync", response_model=UserLoginResponse)
async def sync_user(user: UserCreate, db: Session = Depends(get_db)):
    """
    Sync user data from Firebase/Auth. Stores device info and records last login.
    Returns access token for backend authentication.
    """
    try:
        encrypted_phone = encrypt_data(user.phone_number)
        
        # 1. Try to find user by their Firebase UID
        db_user = db.query(User).filter(User.id == user.id).first()
        
        # 2. If not found by ID, try to find by Email (for users who signed up via email/password first)
        if not db_user and user.email:
            db_user = db.query(User).filter(User.email == user.email.lower().strip()).first()
            if db_user:
                # Update the ID to the Firebase UID for future syncs
                db_user.id = user.id

        # 3. Handle registration or update
        if db_user:
            # Update existing user info
            if user.email:
                db_user.email = user.email.lower().strip()
            db_user.name = user.name or db_user.name
            db_user.phone_number = encrypted_phone
            db_user.device_info = user.device_info or db_user.device_info
            db_user.fcm_token = user.fcm_token or db_user.fcm_token
            db_user.last_login = datetime.utcnow()
        else:
            # Register new phone user
            user_dict = user.dict()
            if user.email:
                user_dict['email'] = user.email.lower().strip()
            user_dict['phone_number'] = encrypted_phone
            # Hash the password (check if it exists)
            password_to_hash = user.password if user.password else "internal_auto_sync_placeholder"
            user_dict['hashed_password'] = get_password_hash(password_to_hash)
            # Remove the raw password field before creating model
            if 'password' in user_dict:
                del user_dict['password']
            
            db_user = User(**user_dict)
            db_user.last_login = datetime.utcnow()
            db.add(db_user)
        
        db.commit()
        db.refresh(db_user)
        
        # Generate JWT for the synced user
        access_token = create_access_token(data={"sub": db_user.id})
        
        return {
            "user": db_user,
            "access_token": access_token,
            "token_type": "bearer"
        }
    except Exception as e:
        import traceback
        error_msg = f"Sync error: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

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
