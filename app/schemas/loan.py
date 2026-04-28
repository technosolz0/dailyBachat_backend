from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime

class LoanBase(BaseModel):
    id: Optional[str] = None
    user_id: str
    person_name: str
    person_phone: Optional[str] = None # Added for notifications
    amount: float
    paid_amount: float = 0.0
    status: Optional[str] = "unpaid"
    type: str # 'lent' or 'borrowed'
    payment_mode: Optional[str] = None
    creator_name: Optional[str] = None
    reason: Optional[str] = None
    date: datetime
    expected_return_date: Optional[datetime] = None
    payment_history: List[Any] = []

class LoanCreate(LoanBase):
    pass

class LoanUpdate(BaseModel):
    person_name: Optional[str] = None
    person_phone: Optional[str] = None
    amount: Optional[float] = None
    paid_amount: Optional[float] = None
    status: Optional[str] = None
    type: Optional[str] = None
    payment_mode: Optional[str] = None
    reason: Optional[str] = None
    date: Optional[datetime] = None
    expected_return_date: Optional[datetime] = None
    payment_history: Optional[List[Any]] = None

class LoanInDB(LoanBase):
    id: str # Required in DB

    class Config:
        from_attributes = True

class LoanPayment(BaseModel):
    amount: float
    date: datetime
