from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User
from app.models.feedback import Feedback
from app.models.loan import Loan
from app.models.business import BusinessProfile
from app.models.invoice import Invoice
from app.models.transaction import Transaction
from app.models.system_settings import SystemSettings

from app.schemas.user import UserInDB, AdminUserUpdate, AdminLoginRequest, Token as TokenSchema, UserCreate
from app.schemas.feedback import Feedback as FeedbackSchema
from app.schemas.loan import LoanInDB
from app.schemas.business import BusinessProfile as BusinessProfileSchema
from app.schemas.invoice import Invoice as InvoiceSchema
from app.schemas.transaction import TransactionInDB
from app.schemas.notification import NotificationSend, NotificationResponse
from app.schemas.system_settings import PremiumAmountUpdate, PremiumFeaturesUpdate
from app.core.firebase_config import send_push_notification, send_multicast_notification
from typing import List
from sqlalchemy import func
import os
import json

from app.core.security import create_access_token, verify_password, decrypt_data
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

router = APIRouter()

# Setup HTTP Bearer Auth
security = HTTPBearer()

# Static admin credentials from environment
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@dailybachat.com")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "Admin@123")

def apply_pagination_sorting(query, model, _start, _end, _sort, _order):
    """
    Applies pagination and sorting to a SQLAlchemy query based on React Admin parameters.
    """
    # Total count for header
    total_count = query.count()
    
    # Sorting
    if hasattr(model, _sort):
        col = getattr(model, _sort)
        if _order == "DESC":
            query = query.order_by(col.desc())
        else:
            query = query.order_by(col.asc())
            
    # Pagination
    items = query.offset(_start).limit(_end - _start).all()
    
    return items, total_count

def get_current_admin(auth: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    """
    Decodes JWT token and verifies admin privileges.
    """
    from jose import jwt, JWTError
    from app.core.security import SECRET_KEY, ALGORITHM
    
    token = auth.credentials
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
    
    if email == ADMIN_EMAIL and password == ADMIN_PASSWORD:
        user_id = email
    else:
        # Check DB
        user = db.query(User).filter(User.email == email).first()
        if user and user.is_admin:
            if user.hashed_password and verify_password(password, user.hashed_password):
                user_id = user.id
    
    if user_id:
        access_token = create_access_token(data={"sub": user_id})
        return {
            "access_token": access_token,
            "token_type": "bearer"
        }
        
    raise HTTPException(status_code=401, detail="Invalid credentials or not an admin")

from fastapi import Response

@router.get("/users", response_model=List[UserInDB])
async def get_all_users(
    response: Response,
    _start: int = 0,
    _end: int = 10,
    _sort: str = "id",
    _order: str = "ASC",
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """
    Fetch all registered users with pagination and sorting.
    """
    query = db.query(User)
    items, total_count = apply_pagination_sorting(query, User, _start, _end, _sort, _order)
    
    result = []
    for u in items:
        u_dict = u.__dict__.copy()
        if u_dict.get("phone_number"):
            try:
                if u_dict["phone_number"].startswith('gAAAAAB'):
                    u_dict["phone_number"] = decrypt_data(u_dict["phone_number"])
            except Exception:
                pass
        else:
            u_dict["phone_number"] = "N/A"
        result.append(u_dict)
    
    response.headers["X-Total-Count"] = str(total_count)
    response.headers["Access-Control-Expose-Headers"] = "X-Total-Count"
    return result

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
        
    user_dict = user.__dict__.copy()
    if user_dict.get("phone_number"):
        try:
            if user_dict["phone_number"].startswith('gAAAAAB'):
                user_dict["phone_number"] = decrypt_data(user_dict["phone_number"])
        except Exception:
            pass
    else:
        user_dict["phone_number"] = "N/A"
        
    return user_dict

@router.put("/users/{user_id}", response_model=UserInDB)
@router.patch("/users/{user_id}", response_model=UserInDB)
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

@router.delete("/users/{user_id}", response_model=UserInDB)
async def delete_user(
    user_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """
    Permanently delete a user account and all related data.
    """
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    from app.models.business import BusinessProfile, PaymentDetail
    from app.models.category import Category
    from app.models.customer import Customer
    from app.models.feedback import Feedback
    from app.models.invoice import Invoice, InvoiceItem, Payment, ShareToken, Quotation, QuotationItem
    from app.models.loan import Loan
    from app.models.product import Product
    from app.models.transaction import Transaction

    # 1. Delete standalone related models
    db.query(Transaction).filter(Transaction.user_id == user_id).delete(synchronize_session=False)
    db.query(Category).filter(Category.user_id == user_id).delete(synchronize_session=False)
    db.query(Feedback).filter(Feedback.user_id == user_id).delete(synchronize_session=False)
    db.query(Loan).filter(Loan.user_id == user_id).delete(synchronize_session=False)

    # 2. Delete business and its cascade
    businesses = db.query(BusinessProfile).filter(BusinessProfile.user_id == user_id).all()
    business_ids = [b.id for b in businesses]

    if business_ids:
        invoices = db.query(Invoice).filter(Invoice.business_id.in_(business_ids)).all()
        invoice_ids = [i.id for i in invoices]
        if invoice_ids:
            db.query(InvoiceItem).filter(InvoiceItem.invoice_id.in_(invoice_ids)).delete(synchronize_session=False)
            db.query(Payment).filter(Payment.invoice_id.in_(invoice_ids)).delete(synchronize_session=False)
            db.query(ShareToken).filter(ShareToken.invoice_id.in_(invoice_ids)).delete(synchronize_session=False)
            db.query(Invoice).filter(Invoice.id.in_(invoice_ids)).delete(synchronize_session=False)

        quotations = db.query(Quotation).filter(Quotation.business_id.in_(business_ids)).all()
        quotation_ids = [q.id for q in quotations]
        if quotation_ids:
            db.query(QuotationItem).filter(QuotationItem.quotation_id.in_(quotation_ids)).delete(synchronize_session=False)
            db.query(Quotation).filter(Quotation.id.in_(quotation_ids)).delete(synchronize_session=False)

        db.query(Product).filter(Product.business_id.in_(business_ids)).delete(synchronize_session=False)
        db.query(Customer).filter(Customer.business_id.in_(business_ids)).delete(synchronize_session=False)
        db.query(PaymentDetail).filter(PaymentDetail.business_id.in_(business_ids)).delete(synchronize_session=False)
        db.query(BusinessProfile).filter(BusinessProfile.id.in_(business_ids)).delete(synchronize_session=False)

    # 3. Delete user
    db.delete(db_user)
    db.commit()
    return db_user

@router.post("/users", response_model=UserInDB)
async def create_user_admin(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """
    Create a new user. Restricted to admins.
    """
    from app.core.security import get_password_hash
    import uuid

    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Generate a unique ID if not provided (though Firebase UID is usually provided)
    user_id = user_data.id if user_data.id else str(uuid.uuid4())
    
    db_user = User(
        id=user_id,
        email=user_data.email,
        name=user_data.name,
        phone_number=user_data.phone_number,
        hashed_password=get_password_hash(user_data.password),
        device_info=user_data.device_info,
        is_active=True
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@router.get("/feedback", response_model=List[FeedbackSchema])
async def get_all_feedback(
    response: Response,
    _start: int = 0,
    _end: int = 10,
    _sort: str = "id",
    _order: str = "ASC",
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """
    Get all user feedback with pagination.
    """
    query = db.query(Feedback)
    items, total_count = apply_pagination_sorting(query, Feedback, _start, _end, _sort, _order)
    response.headers["X-Total-Count"] = str(total_count)
    response.headers["Access-Control-Expose-Headers"] = "X-Total-Count"
    return items

@router.get("/transactions", response_model=List[TransactionInDB])
async def get_all_transactions(
    response: Response,
    _start: int = 0,
    _end: int = 10,
    _sort: str = "id",
    _order: str = "ASC",
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """
    Get all transactions across the platform with pagination.
    """
    query = db.query(Transaction)
    items, total_count = apply_pagination_sorting(query, Transaction, _start, _end, _sort, _order)
    response.headers["X-Total-Count"] = str(total_count)
    response.headers["Access-Control-Expose-Headers"] = "X-Total-Count"
    return items

@router.get("/loans", response_model=List[LoanInDB])
async def get_all_loans(
    response: Response,
    _start: int = 0,
    _end: int = 10,
    _sort: str = "id",
    _order: str = "ASC",
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """
    Get all loan applications and records with pagination.
    """
    query = db.query(Loan)
    items, total_count = apply_pagination_sorting(query, Loan, _start, _end, _sort, _order)
    response.headers["X-Total-Count"] = str(total_count)
    response.headers["Access-Control-Expose-Headers"] = "X-Total-Count"
    return items

@router.get("/businesses", response_model=List[BusinessProfileSchema])
async def get_all_businesses(
    response: Response,
    _start: int = 0,
    _end: int = 10,
    _sort: str = "id",
    _order: str = "ASC",
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """
    Get all business profiles with pagination.
    """
    query = db.query(BusinessProfile)
    items, total_count = apply_pagination_sorting(query, BusinessProfile, _start, _end, _sort, _order)
    response.headers["X-Total-Count"] = str(total_count)
    response.headers["Access-Control-Expose-Headers"] = "X-Total-Count"
    return items

@router.get("/invoices", response_model=List[InvoiceSchema])
async def get_all_invoices(
    response: Response,
    _start: int = 0,
    _end: int = 10,
    _sort: str = "id",
    _order: str = "ASC",
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """
    Get all invoices with pagination.
    """
    query = db.query(Invoice)
    items, total_count = apply_pagination_sorting(query, Invoice, _start, _end, _sort, _order)
    response.headers["X-Total-Count"] = str(total_count)
    response.headers["Access-Control-Expose-Headers"] = "X-Total-Count"
    return items

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

    return {"message": f"Notifications processed. Success: {success_count}, Failure: {failure_count}", "success_count": success_count, "failure_count": failure_count}

@router.get("/dashboard")
async def get_dashboard_stats(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """
    Get overview statistics for the admin dashboard.
    """
    from datetime import datetime, timedelta
    
    # User stats
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active == True).count()
    admin_users = db.query(User).filter(User.is_admin == True).count()
    premium_users = db.query(User).filter(User.is_premium == True).count()
    
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

    # Growth Stats (Last 7 days)
    today = datetime.now()
    growth_data = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        day_str = day.strftime("%Y-%m-%d")
        
        user_count = db.query(User).filter(func.date(User.created_at) == day.date()).count()
        trans_count = db.query(Transaction).filter(func.date(Transaction.created_at) == day.date()).count()
        income = db.query(func.sum(Transaction.amount)).filter(
            func.date(Transaction.created_at) == day.date(),
            Transaction.type == 'income'
        ).scalar() or 0
        
        growth_data.append({
            "date": day_str,
            "new_users": user_count,
            "transactions": trans_count,
            "income": income
        })

    return {
        "summary": {
            "total_users": total_users,
            "active_users": active_users,
            "premium_users": premium_users,
            "admin_users": admin_users,
            "total_income": total_income,
            "total_expense": total_expense,
            "total_businesses": total_businesses,
            "total_invoices": total_invoices,
            "total_loans": total_loans,
            "total_loan_volume": total_loan_amount,
            "feedback_count": total_feedback,
            "average_rating": round(float(avg_rating), 2)
        },
        "growth": growth_data
    }

@router.post("/settings/premium-amount")
async def update_premium_amount(
    data: PremiumAmountUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """
    Update the premium feature price. Restricted to admins.
    """
    setting = db.query(SystemSettings).filter(SystemSettings.key == "premium_amount").first()
    if not setting:
        setting = SystemSettings(key="premium_amount", value=str(data.amount))
        db.add(setting)
    else:
        setting.value = str(data.amount)
    
    db.commit()
    return {"message": "Premium amount updated successfully", "amount": data.amount}

@router.post("/settings/premium-features")
async def update_premium_features(
    data: PremiumFeaturesUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """
    Update the list of premium features. Restricted to admins.
    """
    # Convert list of features to JSON string
    features_json = json.dumps([f.dict() for f in data.features])
    
    setting = db.query(SystemSettings).filter(SystemSettings.key == "premium_features").first()
    if not setting:
        setting = SystemSettings(key="premium_features", value=features_json)
        db.add(setting)
    else:
        setting.value = features_json
    
    db.commit()
    return {"message": "Premium features updated successfully", "features": data.features}
