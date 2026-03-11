from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from .customer import Customer
from .business import BusinessProfile

class InvoiceItemBase(BaseModel):
    description: str
    quantity: float
    unit_price: float
    amount: float

class InvoiceItemCreate(InvoiceItemBase):
    pass

class InvoiceItem(InvoiceItemBase):
    id: str
    invoice_id: str

    class Config:
        from_attributes = True

class InvoiceBase(BaseModel):
    customer_id: str
    invoice_number: str
    due_date: Optional[datetime] = None
    subtotal: float
    tax: float
    total: float

class InvoiceCreate(InvoiceBase):
    items: List[InvoiceItemCreate]

class Invoice(InvoiceBase):
    id: str
    business_id: str
    date: datetime
    paid_amount: float
    status: str
    pdf_url: Optional[str] = None
    items: List[InvoiceItem] = []

    class Config:
        from_attributes = True

class PaymentCreate(BaseModel):
    amount: float
    method: str
    reference_id: Optional[str] = None

class QuotationItemCreate(BaseModel):
    description: str
    quantity: float
    unit_price: float
    amount: float

class QuotationCreate(BaseModel):
    customer_id: str
    quotation_number: str
    expiry_date: Optional[datetime] = None
    subtotal: float
    tax: float
    total: float
    items: List[QuotationItemCreate]
