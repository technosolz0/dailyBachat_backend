from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User
from app.models.feedback import Feedback
from app.models.loan import Loan
from app.models.business import BusinessProfile
from app.models.invoice import Invoice
from app.models.transaction import Transaction

from app.schemas.user import UserInDB, AdminUserUpdate, AdminLoginRequest, Token as TokenSchema
from app.schemas.feedback import Feedback as FeedbackSchema
from app.schemas.loan import LoanInDB
from app.schemas.business import BusinessProfile as BusinessProfileSchema
from app.schemas.invoice import Invoice as InvoiceSchema
from app.schemas.transaction import TransactionInDB
from app.schemas.notification import NotificationSend, NotificationResponse
from app.core.firebase_config import send_push_notification, send_multicast_notification
from typing import List
from sqlalchemy import func
import os

from app.core.security import create_access_token
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

router = APIRouter()

# Setup OAuth2
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/admin/login")

# Static admin credentials from environment
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@dailybachat.com")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "Admin@123")

def get_current_admin(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """
    Decodes JWT token and verifies admin privileges.
    """
    from jose import jwt, JWTError
    from app.core.security import SECRET_KEY, ALGORITHM
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials")

    # Static admin bypass from token
    if user_id == ADMIN_EMAIL:
        return User(id=ADMIN_EMAIL, email=ADMIN_EMAIL, is_admin=True, name="Static Admin")
        
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized. Admin privileges required.")
    return user

@router.post("/login", response_model=TokenSchema)
async def admin_login(
    login_data: AdminLoginRequest,
    db: Session = Depends(get_db)
):
    """
    Authenticates admin using email and password. Returns a JWT token.
    """
    email = login_data.email
    password = login_data.password
    
    user_id = None
    user_name = None
    
    if email == ADMIN_EMAIL and password == ADMIN_PASSWORD:
        user_id = email
        user_name = "Super Admin"
    else:
        # Check DB
        user = db.query(User).filter(User.email == email).first()
        if user and user.is_admin:
            # Note: In production, verify user password here!
            user_id = user.id
            user_name = user.name
    
    if user_id:
        access_token = create_access_token(data={"sub": user_id})
        return {
            "access_token": access_token,
            "token_type": "bearer"
        }
        
    raise HTTPException(status_code=401, detail="Invalid credentials or not an admin")

@router.get("/users", response_model=List[UserInDB])
async def get_all_users(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """
    Fetch all registered users. Restricted to admins.
    """
    users = db.query(User).all()
    return users

@router.get("/users/{user_id}", response_model=UserInDB)
async def get_user_detail(
    user_id: str, 
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """
    Fetch details for a specific user. Restricted to admins.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.put("/users/{user_id}", response_model=UserInDB)
async def update_user(
    user_id: str,
    user_update: AdminUserUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """
    Update user status (active/blocked) or admin privileges.
    """
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    update_data = user_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_user, key, value)
    
    db.commit()
    db.refresh(db_user)
    return db_user

@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """
    Permanently delete a user account.
    """
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    db.delete(db_user)
    db.commit()
    return {"message": "User account deleted successfully"}

@router.get("/feedback", response_model=List[FeedbackSchema])
async def get_all_feedback(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """
    Get all user feedback.
    """
    return db.query(Feedback).all()

@router.get("/transactions", response_model=List[TransactionInDB])
async def get_all_transactions(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """
    Get all transactions across the platform.
    """
    return db.query(Transaction).all()

@router.get("/loans", response_model=List[LoanInDB])
async def get_all_loans(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """
    Get all loan applications and records.
    """
    return db.query(Loan).all()

@router.get("/businesses", response_model=List[BusinessProfileSchema])
async def get_all_businesses(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """
    Get all business profiles.
    """
    return db.query(BusinessProfile).all()

@router.get("/invoices", response_model=List[InvoiceSchema])
async def get_all_invoices(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """
    Get all invoices.
    """
    return db.query(Invoice).all()

@router.post("/notifications/send", response_model=NotificationResponse)
async def send_notifications(
    notification: NotificationSend,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """
    Send push notifications to all users or a specific list.
    """
    success_count = 0
    failure_count = 0
    
    if notification.user_ids:
        # Send to specific users
        tokens = db.query(User.fcm_token).filter(
            User.id.in_(notification.user_ids),
            User.fcm_token.isnot(None)
        ).all()
        token_list = [t[0] for t in tokens if t[0]]
    else:
        # Send to all users
        tokens = db.query(User.fcm_token).filter(User.fcm_token.isnot(None)).all()
        token_list = [t[0] for t in tokens if t[0]]

    if not token_list:
        return NotificationResponse(
            message="No valid FCM tokens found",
            success_count=0,
            failure_count=0
        )

    # Use multicast for efficiency
    success_count = send_multicast_notification(
        tokens=token_list,
        title=notification.title,
        body=notification.body,
        data=notification.data
    )
    failure_count = len(token_list) - success_count

    return {"message": "Notifications processed. Success: {success_count}, Failure: {failure_count}", "success_count": success_count, "failure_count": failure_count}

@router.get("/dashboard")
async def get_dashboard_stats(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """
    Get overview statistics for the admin dashboard.
    """
    # User stats
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active == True).count()
    admin_users = db.query(User).filter(User.is_admin == True).count()
    
    # Financial stats
    total_income = db.query(func.sum(Transaction.amount)).filter(Transaction.type == 'income').scalar() or 0
    total_expense = db.query(func.sum(Transaction.amount)).filter(Transaction.type == 'expense').scalar() or 0
    
    # Business & Product stats
    total_businesses = db.query(BusinessProfile).count()
    total_invoices = db.query(Invoice).count()
    
    # Loans
    total_loans = db.query(Loan).count()
    total_loan_amount = db.query(func.sum(Loan.amount)).scalar() or 0
    
    # Feedback
    total_feedback = db.query(Feedback).count()
    avg_rating = db.query(func.avg(Feedback.rating)).scalar() or 0

    return {
        "users": {
            "total": total_users,
            "active": active_users,
            "admins": admin_users
        },
        "finances": {
            "total_income": total_income,
            "total_expense": total_expense,
            "net_flow": total_income - total_expense
        },
        "platform": {
            "businesses": total_businesses,
            "invoices": total_invoices,
            "loans": total_loans,
            "total_loan_volume": total_loan_amount,
            "feedback_count": total_feedback,
            "average_feedback_rating": round(float(avg_rating), 2)
        }
    }
