from datetime import datetime, timedelta
import random
from app.core import security
from app.schemas.user import Token, OTPRequest, OTPVerify

router = APIRouter()

# Temporary stores (In production, use Redis/DB)
otp_store = {}
pending_users = {} # Store user details until OTP verified

# Placeholder for user database logic
async def authenticate_user(email: str, password: str):
    # In a real app, this would query your DB
    # For now, let's mock it for testing
    if email == "user@example.com" and password == "password":
        return {"id": "1", "email": email, "full_name": "Test User"}
    return None

@router.post("/login", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=security.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        data={"sub": user["email"]}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/register/request")
async def register_request(user_data: dict): # user_data contains name, email, phone, password
    email = user_data.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")
    
    # Generate OTP
    otp = str(random.randint(100000, 999999))
    expiry = datetime.utcnow() + timedelta(minutes=10)
    
    otp_store[email] = {"otp": otp, "expires": expiry}
    pending_users[email] = user_data # Save details for later
    
    print(f"DEBUG: OTP for {email} is {otp}")
    
    return {"message": "OTP sent to email. Please verify to complete registration."}

@router.post("/register/verify")
async def register_verify(request: OTPVerify):
    email = request.email
    otp = request.otp
    
    if email not in otp_store:
        raise HTTPException(status_code=400, detail="No OTP request found")
    
    stored_data = otp_store[email]
    if datetime.utcnow() > stored_data["expires"]:
        del otp_store[email]
        raise HTTPException(status_code=400, detail="OTP expired")
    
    if otp != stored_data["otp"]:
        raise HTTPException(status_code=400, detail="Invalid OTP")
    
    # OTP Valid -> Create User
    user_data = pending_users.get(email)
    if not user_data:
        raise HTTPException(status_code=400, detail="User data lost. Please restart registration.")
    
    # TODO: Save user_data to Database (SQLAlchemy)
    # Mocking successful creation
    new_user_id = "user_" + str(random.randint(1000, 9999))
    
    # Cleanup
    del otp_store[email]
    del pending_users[email]
    
    return {
        "message": "User registered successfully",
        "user_id": new_user_id,
        "email": email
    }

@router.post("/otp/send")
async def send_otp(request: OTPRequest):
    otp = str(random.randint(100000, 999999))
    expiry = datetime.utcnow() + timedelta(minutes=10) # 10 minute expiry
    
    otp_store[request.email] = {"otp": otp, "expires": expiry}
    
    # TODO: Integration with email service (e.g. SendGrid, Mailgun)
    # For now, we'll just print it to the console
    print(f"DEBUG: OTP for {request.email} is {otp}")
    
    return {"message": "OTP sent successfully to your email"}

@router.post("/otp/verify")
async def verify_otp(request: OTPVerify):
    if request.email not in otp_store:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OTP not requested for this email"
        )
    
    stored_data = otp_store[request.email]
    
    if datetime.utcnow() > stored_data["expires"]:
        del otp_store[request.email]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OTP expired"
        )
    
    if request.otp != stored_data["otp"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OTP"
        )
    
    # OTP is valid, clear it
    del otp_store[request.email]
    
    # Here you would typically register the user if they were in a pending state
    # or return a session token
    return {"message": "OTP verified successfully"}
