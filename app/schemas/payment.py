from pydantic import BaseModel
from typing import Optional

class RazorpayOrderCreate(BaseModel):
    amount: int  # in paise
    currency: str = "INR"

class RazorpayOrderResponse(BaseModel):
    order_id: str
    amount: int
    currency: str
    status: str

class PaymentCaptureRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str

class PremiumUpdateResponse(BaseModel):
    success: bool
    message: str
    is_premium: bool
