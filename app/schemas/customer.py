from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class CustomerBase(BaseModel):
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None

class CustomerCreate(CustomerBase):
    pass

class Customer(CustomerBase):
    id: str
    business_id: str
    created_at: Optional[datetime] = None
    total_sales: float = 0.0
    total_paid: float = 0.0
    pending_amount: float = 0.0

    class Config:
        from_attributes = True
