import os
import razorpay
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User
from app.models.system_settings import SystemSettings
from app.schemas.payment import (
    RazorpayOrderCreate, RazorpayOrderResponse, 
    PaymentCaptureRequest, PremiumUpdateResponse
)
from app.core.security import get_current_user_id
from dotenv import load_dotenv

load_dotenv()

router = APIRouter()

RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")

client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

@router.post("/initiate-order", response_model=RazorpayOrderResponse)
async def initiate_order(order_data: RazorpayOrderCreate):
    """
    Create a Razorpay order.
    """
    try:
        data = {
            "amount": order_data.amount,
            "currency": order_data.currency,
            "payment_capture": 1  # Auto capture
        }
        order = client.order.create(data=data)
        return {
            "order_id": order['id'],
            "amount": order['amount'],
            "currency": order['currency'],
            "status": order['status']
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/verify-payment", response_model=PremiumUpdateResponse)
async def verify_payment(
    payment_data: PaymentCaptureRequest, 
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Verify Razorpay signature and update user premium status.
    """
    try:
        # Verify signature
        params_dict = {
            'razorpay_order_id': payment_data.razorpay_order_id,
            'razorpay_payment_id': payment_data.razorpay_payment_id,
            'razorpay_signature': payment_data.razorpay_signature
        }
        
        client.utility.verify_payment_signature(params_dict)
        
        # Update user status
        db_user = db.query(User).filter(User.id == user_id).first()
        if not db_user:
            raise HTTPException(status_code=404, detail="User not found")
        
        db_user.is_premium = True
        db.commit()
        
        return {
            "success": True,
            "message": "Payment verified and premium status updated.",
            "is_premium": True
        }
    except razorpay.errors.SignatureVerificationError:
        print(f"Signature verification failed for order {payment_data.razorpay_order_id}")
        raise HTTPException(status_code=400, detail="Invalid payment signature")
    except Exception as e:
        print(f"Payment verification error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Payment verification failed: {str(e)}")

@router.post("/update-premium", response_model=PremiumUpdateResponse)
async def update_premium_value(
    is_premium: bool,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Directly update premium value (Admin or specific use case).
    """
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    db_user.is_premium = is_premium
    db.commit()
    
    return {
        "success": True,
        "message": f"Premium status updated to {is_premium}",
        "is_premium": db_user.is_premium
    }

@router.get("/premium-amount")
async def get_premium_amount(db: Session = Depends(get_db)):
    """
    Fetch the premium feature price.
    """
    setting = db.query(SystemSettings).filter(SystemSettings.key == "premium_amount").first()
    if not setting:
        return {"amount": 499} # Default fallback
    return {"amount": int(setting.value)}
