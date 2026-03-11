from pydantic import BaseModel
from typing import Optional, List

class PaymentDetailBase(BaseModel):
    bank_name: Optional[str] = None
    account_number: Optional[str] = None
    ifsc: Optional[str] = None
    upi_id: Optional[str] = None
    qr_code_url: Optional[str] = None

class PaymentDetailCreate(PaymentDetailBase):
    pass

class PaymentDetail(PaymentDetailBase):
    id: str
    business_id: str

    class Config:
        from_attributes = True

class BusinessProfileBase(BaseModel):
    name: str
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    gst_number: Optional[str] = None
    logo_url: Optional[str] = None

class BusinessProfileCreate(BusinessProfileBase):
    payment_details: Optional[List[PaymentDetailCreate]] = []

class BusinessProfile(BusinessProfileBase):
    id: str
    user_id: str
    payment_details: List[PaymentDetail] = []

    class Config:
        from_attributes = True
