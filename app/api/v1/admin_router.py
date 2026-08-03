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
from app.models.website import WebsiteContent, ContactSubmission, Testimonial, BlogPostModel
from app.schemas.website import (
    WebsiteContentResponse,
    WebsiteContentUpdate,
    WebsiteContentCreate,
    ContactSubmissionResponse,
    ContactSubmissionUpdateStatus,
    TestimonialResponse,
    TestimonialCreate,
    TestimonialUpdate,
    BlogPostResponse,
    BlogPostCreate,
    BlogPostUpdate
)
from firebase_admin import auth as firebase_auth

from app.schemas.user import UserInDB, AdminUserUpdate, AdminLoginRequest, Token as TokenSchema, UserCreate
from app.schemas.feedback import Feedback as FeedbackSchema
from app.schemas.loan import LoanInDB
from app.schemas.business import BusinessProfile as BusinessProfileSchema
from app.schemas.invoice import Invoice as InvoiceSchema
from app.schemas.transaction import TransactionInDB
from app.schemas.notification import NotificationSend, NotificationResponse
from app.schemas.system_settings import PremiumAmountUpdate, PremiumFeaturesUpdate, AppConfigUpdate
from app.core.firebase_config import send_push_notification, send_multicast_notification, delete_firebase_user_account
from typing import List
from sqlalchemy import func
import os
import json

from app.core.security import create_access_token, verify_password, decrypt_data, encrypt_data
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
    if _sort and hasattr(model, _sort):
        col = getattr(model, _sort)
        if _order == "DESC":
            query = query.order_by(col.desc())
        else:
            query = query.order_by(col.asc())
            
    # Pagination
    limit_val = max(1, _end - _start)
    items = query.offset(_start).limit(limit_val).all()
    
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

from fastapi import Response

def _format_user(user):
    if not user:
        return None
    phone_val = "N/A"
    if user.phone_number:
        try:
            phone_val = decrypt_data(user.phone_number)
        except Exception:
            phone_val = "N/A"

    # Fallback: If phone is missing/N/A or a residual Fernet token starting with "gAAAAA"
    if not phone_val or phone_val == "N/A" or phone_val.startswith("gAAAAA"):
        if user.email and "@dailybachat.com" in user.email:
            prefix = user.email.split("@")[0]
            if prefix.isdigit():
                phone_val = f"+{prefix}"
            elif prefix.startswith("+") and prefix[1:].isdigit():
                phone_val = prefix
            else:
                phone_val = "N/A"
        else:
            phone_val = "N/A"

    return {
        "id": str(user.id),
        "email": user.email,
        "name": user.name or "User",
        "phone_number": phone_val,
        "device_info": user.device_info,
        "fcm_token": user.fcm_token,
        "is_admin": user.is_admin if user.is_admin is not None else False,
        "is_premium": user.is_premium if user.is_premium is not None else False,
        "premium_expiry": user.premium_expiry,
        "is_active": user.is_active if user.is_active is not None else True,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
        "last_login": user.last_login
    }

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
    
    result = [_format_user(u) for u in items]
    
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
        
    return _format_user(user)

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
    return _format_user(db_user)

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
    
    # Prepare response data before deletion
    user_dict = _format_user(db_user)

    try:
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
            # Handle Invoices
            invoices = db.query(Invoice).filter(Invoice.business_id.in_(business_ids)).all()
            invoice_ids = [i.id for i in invoices]
            if invoice_ids:
                db.query(InvoiceItem).filter(InvoiceItem.invoice_id.in_(invoice_ids)).delete(synchronize_session=False)
                db.query(Payment).filter(Payment.invoice_id.in_(invoice_ids)).delete(synchronize_session=False)
                db.query(ShareToken).filter(ShareToken.invoice_id.in_(invoice_ids)).delete(synchronize_session=False)
                db.query(Invoice).filter(Invoice.id.in_(invoice_ids)).delete(synchronize_session=False)

            # Handle Quotations
            quotations = db.query(Quotation).filter(Quotation.business_id.in_(business_ids)).all()
            quotation_ids = [q.id for q in quotations]
            if quotation_ids:
                db.query(ShareToken).filter(ShareToken.quotation_id.in_(quotation_ids)).delete(synchronize_session=False)
                db.query(QuotationItem).filter(QuotationItem.quotation_id.in_(quotation_ids)).delete(synchronize_session=False)
                db.query(Quotation).filter(Quotation.id.in_(quotation_ids)).delete(synchronize_session=False)

            # Delete remaining business-related data
            db.query(Product).filter(Product.business_id.in_(business_ids)).delete(synchronize_session=False)
            db.query(Customer).filter(Customer.business_id.in_(business_ids)).delete(synchronize_session=False)
            db.query(PaymentDetail).filter(PaymentDetail.business_id.in_(business_ids)).delete(synchronize_session=False)
            db.query(BusinessProfile).filter(BusinessProfile.id.in_(business_ids)).delete(synchronize_session=False)

        user_email = db_user.email
        user_phone = db_user.phone_number

        # 3. Delete user record
        db.delete(db_user)
        db.commit()

        # 4. Permanently delete from Firebase Auth (by UID, Email, or Phone)
        try:
            delete_firebase_user_account(user_id=user_id, email=user_email, phone_number=user_phone)
        except Exception as fe:
            print(f"Firebase deletion warning for {user_id}: {str(fe)}")

        return user_dict

    except Exception as e:
        db.rollback()
        import traceback
        print(f"Error deleting user {user_id}: {str(e)}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete user and related data: {str(e)}"
        )

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
        phone_number=encrypt_data(user_data.phone_number) if user_data.phone_number else None,
        hashed_password=get_password_hash(user_data.password),
        device_info=user_data.device_info,
        is_active=True
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return _format_user(db_user)

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

@router.delete("/feedback/{feedback_id}")
async def delete_feedback(
    feedback_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Delete a feedback entry."""
    fb = db.query(Feedback).filter(Feedback.id == feedback_id).first()
    if not fb:
        raise HTTPException(status_code=404, detail="Feedback not found")
    db.delete(fb)
    db.commit()
    return {"message": "Feedback deleted successfully"}

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

@router.delete("/transactions/{transaction_id}")
async def delete_transaction(
    transaction_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Delete a transaction record."""
    tx = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    db.delete(tx)
    db.commit()
    return {"message": "Transaction deleted successfully"}

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

@router.delete("/loans/{loan_id}")
async def delete_loan(
    loan_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Delete a loan record."""
    ln = db.query(Loan).filter(Loan.id == loan_id).first()
    if not ln:
        raise HTTPException(status_code=404, detail="Loan record not found")
    db.delete(ln)
    db.commit()
    return {"message": "Loan record deleted successfully"}

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

@router.delete("/businesses/{business_id}")
async def delete_business(
    business_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Delete a business profile and its cascade records."""
    biz = db.query(BusinessProfile).filter(BusinessProfile.id == business_id).first()
    if not biz:
        raise HTTPException(status_code=404, detail="Business profile not found")
    
    try:
        from app.models.customer import Customer
        from app.models.invoice import Invoice, InvoiceItem, Payment, ShareToken, Quotation, QuotationItem
        from app.models.product import Product
        from app.models.business import PaymentDetail

        invoices = db.query(Invoice).filter(Invoice.business_id == business_id).all()
        inv_ids = [i.id for i in invoices]
        if inv_ids:
            db.query(InvoiceItem).filter(InvoiceItem.invoice_id.in_(inv_ids)).delete(synchronize_session=False)
            db.query(Payment).filter(Payment.invoice_id.in_(inv_ids)).delete(synchronize_session=False)
            db.query(ShareToken).filter(ShareToken.invoice_id.in_(inv_ids)).delete(synchronize_session=False)
            db.query(Invoice).filter(Invoice.id.in_(inv_ids)).delete(synchronize_session=False)

        quotations = db.query(Quotation).filter(Quotation.business_id == business_id).all()
        q_ids = [q.id for q in quotations]
        if q_ids:
            db.query(ShareToken).filter(ShareToken.quotation_id.in_(q_ids)).delete(synchronize_session=False)
            db.query(QuotationItem).filter(QuotationItem.quotation_id.in_(q_ids)).delete(synchronize_session=False)
            db.query(Quotation).filter(Quotation.id.in_(q_ids)).delete(synchronize_session=False)

        db.query(Product).filter(Product.business_id == business_id).delete(synchronize_session=False)
        db.query(Customer).filter(Customer.business_id == business_id).delete(synchronize_session=False)
        db.query(PaymentDetail).filter(PaymentDetail.business_id == business_id).delete(synchronize_session=False)
        
        db.delete(biz)
        db.commit()
        return {"message": "Business profile deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete business: {str(e)}")

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

@router.delete("/invoices/{invoice_id}")
async def delete_invoice(
    invoice_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Delete an invoice and its items."""
    inv = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")

    try:
        from app.models.invoice import InvoiceItem, Payment, ShareToken
        db.query(InvoiceItem).filter(InvoiceItem.invoice_id == invoice_id).delete(synchronize_session=False)
        db.query(Payment).filter(Payment.invoice_id == invoice_id).delete(synchronize_session=False)
        db.query(ShareToken).filter(ShareToken.invoice_id == invoice_id).delete(synchronize_session=False)
        db.delete(inv)
        db.commit()
        return {"message": "Invoice deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete invoice: {str(e)}")

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

@router.get("/settings/app-config")
async def get_admin_app_config(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """
    Get app config settings for admin.
    """
    min_version_setting = db.query(SystemSettings).filter(SystemSettings.key == "app_min_version").first()
    store_url_setting = db.query(SystemSettings).filter(SystemSettings.key == "app_store_url").first()
    force_update_setting = db.query(SystemSettings).filter(SystemSettings.key == "app_force_update").first()

    return {
        "min_version": min_version_setting.value if min_version_setting else "1.0.0",
        "store_url": store_url_setting.value if store_url_setting else "https://play.google.com/store/apps/details?id=com.technosolz.dailybachat",
        "force_update": force_update_setting.value.lower() == "true" if force_update_setting else True
    }

@router.post("/settings/app-config")
async def update_app_config(
    data: AppConfigUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """
    Update app config settings. Restricted to admins.
    """
    settings = {
        "app_min_version": data.min_version,
        "app_store_url": data.store_url,
        "app_force_update": str(data.force_update).lower()
    }

    for key, val in settings.items():
        setting = db.query(SystemSettings).filter(SystemSettings.key == key).first()
        if not setting:
            setting = SystemSettings(key=key, value=val)
            db.add(setting)
        else:
            setting.value = val

    db.commit()
    return {"message": "App configuration updated successfully", "config": data}

@router.get("/settings/premium-amount")
async def get_premium_amount(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """
    Get the premium feature price. Restricted to admins.
    """
    setting = db.query(SystemSettings).filter(SystemSettings.key == "premium_amount").first()
    return {"amount": int(setting.value) if setting else 999}

@router.get("/settings/premium-features")
async def get_premium_features(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """
    Get the premium features list. Restricted to admins.
    """
    setting = db.query(SystemSettings).filter(SystemSettings.key == "premium_features").first()
    if setting:
        return {"features": json.loads(setting.value)}
    return {"features": []}

# --- Website Content & Contact Submissions Admin Endpoints ---

@router.get("/website/content", response_model=List[WebsiteContentResponse])
def admin_get_website_contents(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """
    List all custom website sections stored in database.
    """
    return db.query(WebsiteContent).all()

@router.post("/website/content", response_model=WebsiteContentResponse)
def admin_create_or_update_website_content(
    data: WebsiteContentCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """
    Create or update website dynamic section content (e.g. hero, features, contact_info).
    """
    existing = db.query(WebsiteContent).filter(WebsiteContent.section_key == data.section_key).first()
    if existing:
        if data.title is not None:
            existing.title = data.title
        if data.subtitle is not None:
            existing.subtitle = data.subtitle
        if data.content_json is not None:
            existing.content_json = data.content_json
        db.commit()
        db.refresh(existing)
        return existing

    new_content = WebsiteContent(
        section_key=data.section_key,
        title=data.title,
        subtitle=data.subtitle,
        content_json=data.content_json
    )
    db.add(new_content)
    db.commit()
    db.refresh(new_content)
    return new_content

@router.put("/website/content/{section_key}", response_model=WebsiteContentResponse)
def admin_update_website_content_by_key(
    section_key: str,
    data: WebsiteContentUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """
    Update a specific website section by section_key.
    """
    existing = db.query(WebsiteContent).filter(WebsiteContent.section_key == section_key).first()
    if not existing:
        existing = WebsiteContent(
            section_key=section_key,
            title=data.title,
            subtitle=data.subtitle,
            content_json=data.content_json
        )
        db.add(existing)
    else:
        if data.title is not None:
            existing.title = data.title
        if data.subtitle is not None:
            existing.subtitle = data.subtitle
        if data.content_json is not None:
            existing.content_json = data.content_json
    
    db.commit()
    db.refresh(existing)
    return existing

@router.get("/website/contacts", response_model=List[ContactSubmissionResponse])
def admin_get_contact_submissions(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
    status: str = None
):
    """
    Fetch submitted contact form inquiries from website visitors.
    """
    query = db.query(ContactSubmission)
    if status:
        query = query.filter(ContactSubmission.status == status)
    return query.order_by(ContactSubmission.created_at.desc()).all()

@router.put("/website/contacts/{contact_id}", response_model=ContactSubmissionResponse)
def admin_update_contact_submission_status(
    contact_id: int,
    payload: ContactSubmissionUpdateStatus,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """
    Update contact submission status (pending, read, replied, resolved).
    """
    submission = db.query(ContactSubmission).filter(ContactSubmission.id == contact_id).first()
    if not submission:
        raise HTTPException(status_code=404, detail="Contact submission not found")
    submission.status = payload.status
    db.commit()
    db.refresh(submission)
    return submission

@router.delete("/website/contacts/{contact_id}")
def admin_delete_contact_submission(
    contact_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """
    Delete a contact submission entry.
    """
    submission = db.query(ContactSubmission).filter(ContactSubmission.id == contact_id).first()
    if not submission:
        raise HTTPException(status_code=404, detail="Contact submission not found")
    db.delete(submission)
    db.commit()
    return {"message": "Contact submission deleted successfully"}

# --- Testimonials Management ---

@router.get("/website/testimonials", response_model=List[TestimonialResponse])
def admin_get_testimonials(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    return db.query(Testimonial).order_by(Testimonial.id.desc()).all()

@router.post("/website/testimonials", response_model=TestimonialResponse)
def admin_create_testimonial(
    data: TestimonialCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    testimonial = Testimonial(
        author_name=data.author_name,
        author_role=data.author_role,
        avatar_url=data.avatar_url,
        quote=data.quote,
        rating=data.rating or 5,
        is_active=data.is_active if data.is_active is not None else 1
    )
    db.add(testimonial)
    db.commit()
    db.refresh(testimonial)
    return testimonial

@router.put("/website/testimonials/{testimonial_id}", response_model=TestimonialResponse)
def admin_update_testimonial(
    testimonial_id: int,
    data: TestimonialUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    t = db.query(Testimonial).filter(Testimonial.id == testimonial_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Testimonial not found")
    if data.author_name is not None: t.author_name = data.author_name
    if data.author_role is not None: t.author_role = data.author_role
    if data.quote is not None: t.quote = data.quote
    if data.rating is not None: t.rating = data.rating
    if data.is_active is not None: t.is_active = data.is_active
    db.commit()
    db.refresh(t)
    return t

@router.delete("/website/testimonials/{testimonial_id}")
def admin_delete_testimonial(
    testimonial_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    t = db.query(Testimonial).filter(Testimonial.id == testimonial_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Testimonial not found")
    db.delete(t)
    db.commit()
    return {"message": "Testimonial deleted"}

# --- Blog Posts Management ---

@router.get("/website/blogs", response_model=List[BlogPostResponse])
def admin_get_blogs(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    return db.query(BlogPostModel).order_by(BlogPostModel.id.desc()).all()

@router.post("/website/blogs", response_model=BlogPostResponse)
def admin_create_blog(
    data: BlogPostCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    existing = db.query(BlogPostModel).filter(BlogPostModel.slug == data.slug).first()
    if existing:
        raise HTTPException(status_code=400, detail="Blog post with this slug already exists")
    
    post = BlogPostModel(
        title=data.title,
        slug=data.slug,
        excerpt=data.excerpt,
        category=data.category or "General",
        read_time=data.read_time or "5 min read",
        author_name=data.author_name or "DailyBachat Team",
        author_role=data.author_role or "Financial Writer",
        content=data.content,
        is_published=data.is_published if data.is_published is not None else 1,
        published_date=data.published_date
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    return post

@router.put("/website/blogs/{blog_id}", response_model=BlogPostResponse)
def admin_update_blog(
    blog_id: int,
    data: BlogPostUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    b = db.query(BlogPostModel).filter(BlogPostModel.id == blog_id).first()
    if not b:
        raise HTTPException(status_code=404, detail="Blog post not found")
    
    if data.title is not None: b.title = data.title
    if data.slug is not None: b.slug = data.slug
    if data.excerpt is not None: b.excerpt = data.excerpt
    if data.category is not None: b.category = data.category
    if data.read_time is not None: b.read_time = data.read_time
    if data.author_name is not None: b.author_name = data.author_name
    if data.author_role is not None: b.author_role = data.author_role
    if data.content is not None: b.content = data.content
    if data.is_published is not None: b.is_published = data.is_published
    if data.published_date is not None: b.published_date = data.published_date
    
    db.commit()
    db.refresh(b)
    return b

@router.delete("/website/blogs/{blog_id}")
def admin_delete_blog(
    blog_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    b = db.query(BlogPostModel).filter(BlogPostModel.id == blog_id).first()
    if not b:
        raise HTTPException(status_code=404, detail="Blog post not found")
    db.delete(b)
    db.commit()
    return {"message": "Blog post deleted"}


