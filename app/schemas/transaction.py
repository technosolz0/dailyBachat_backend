from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class TransactionBase(BaseModel):
    id: str # Can be provided by client or generated
    amount: float
    description: Optional[str] = None
    category: str
    type: str # 'income' or 'expense'
    date: datetime

class TransactionCreate(TransactionBase):
    pass

class TransactionUpdate(BaseModel):
    amount: Optional[float] = None
    description: Optional[str] = None
    category: Optional[str] = None
    type: Optional[str] = None
    date: Optional[datetime] = None

class TransactionInDB(TransactionBase):
    user_id: str
    created_at: datetime

    class Config:
        orm_mode = True
