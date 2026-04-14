from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os
from dotenv import load_dotenv
from cryptography.fernet import Fernet
import base64

load_dotenv()

# Security configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-keep-this-private") # Default for dev, override with .env
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")
if not ENCRYPTION_KEY:
    # Generate a key if not present (only for dev, should be fixed in prod)
    ENCRYPTION_KEY = Fernet.generate_key().decode()
    print(f"WARNING: ENCRYPTION_KEY not found in environment. Generated one: {ENCRYPTION_KEY}")

cipher_suite = Fernet(ENCRYPTION_KEY.encode())

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["pbkdf2_sha256", "bcrypt"], deprecated="auto")

def encrypt_data(data: str) -> str:
    if not data:
        return data
    return cipher_suite.encrypt(data.encode()).decode()

def decrypt_data(encrypted_data: str) -> str:
    if not encrypted_data:
        return encrypted_data
    try:
        return cipher_suite.decrypt(encrypted_data.encode()).decode()
    except Exception:
        return encrypted_data # Return as is if decryption fails (might be unencrypted)

def verify_password(plain_password: str, hashed_password: str):
    if not plain_password:
        return False
    # bcrypt limit is 72 bytes. Truncate and convert to string for safety.
    password_bytes = plain_password.encode('utf-8')[:71]
    safe_password = password_bytes.decode('utf-8', 'ignore')
    return pwd_context.verify(safe_password, hashed_password)

def get_password_hash(password: str) -> str:
    if not password:
        password = "placeholder_password"
    
    # bcrypt has a 72-byte limit. We truncate to 71 bytes and decode back to string.
    # This avoids "Sync error: password cannot be longer than 72 bytes" even in stub mode.
    password_bytes = password.encode('utf-8')[:71]
    safe_password = password_bytes.decode('utf-8', 'ignore')
    
    print(f"Hashing password (original length: {len(password)}, safe length: {len(safe_password)})")
    return pwd_context.hash(safe_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

security = HTTPBearer()

def get_current_user_id(auth: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """
    Decodes the JWT token to retrieve the User ID (uid).
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        token = auth.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        return user_id
    except JWTError:
        raise credentials_exception
