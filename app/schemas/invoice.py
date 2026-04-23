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
    tax_percent: Optional[float] = 0.0
    total: float
    creator_name: Optional[str] = None
    date: Optional[datetime] = None

class InvoiceCreate(InvoiceBase):
    items: List[InvoiceItemCreate]

class Invoice(InvoiceBase):
    id: str
    business_id: str
    date: Optional[datetime] = None
    paid_amount: float
    status: str
    pdf_url: Optional[str] = None
    items: List[InvoiceItem] = []
    customer: Optional[Customer] = None

    class Config:
        from_attributes = True

class PaymentCreate(BaseModel):
    amount: float
    method: str
    reference_id: Optional[str] = None

# Quotations
class QuotationItemBase(BaseModel):
    description: str
    quantity: float
    unit_price: float
    amount: float

class QuotationItemCreate(QuotationItemBase):
    pass

class QuotationItem(QuotationItemBase):
    id: str
    quotation_id: str

    class Config:
        from_attributes = True

class QuotationBase(BaseModel):
    customer_id: str
    quotation_number: str
    expiry_date: Optional[datetime] = None
    subtotal: float
    tax: float
    tax_percent: Optional[float] = 0.0
    total: float
    creator_name: Optional[str] = None
    date: Optional[datetime] = None
    status: Optional[str] = "draft"
    advance_amount: Optional[float] = 0.0

class QuotationCreate(QuotationBase):
    items: List[QuotationItemCreate]

class Quotation(QuotationBase):
    id: str
    business_id: str
    date: Optional[datetime] = None
    status: str
    pdf_url: Optional[str] = None
    items: List[QuotationItem] = []
    customer: Optional[Customer] = None

    class Config:
        from_attributes = True
