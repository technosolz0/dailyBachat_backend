from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class TransactionBase(BaseModel):
    amount: float
    category_id: str
    date: datetime
    description: Optional[str] = None
    transaction_type: str # 'income' or 'expense'

class TransactionCreate(TransactionBase):
    pass

class TransactionInDB(TransactionBase):
    id: str
    user_id: str
    created_at: datetime
