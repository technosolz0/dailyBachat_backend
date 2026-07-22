from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime

class MemberSchema(BaseModel):
    name: str
    phone: Optional[str] = None
    share_amount: float
    paid_amount: float = 0.0
    is_paid: bool = False

class GroupSplitBase(BaseModel):
    id: Optional[str] = None
    title: str
    total_amount: float
    split_type: str = "equal" # "equal", "unequal", "percentage"
    date: Optional[datetime] = None
    members: List[MemberSchema] = []

class GroupSplitCreate(GroupSplitBase):
    pass

class GroupSplitUpdate(BaseModel):
    title: Optional[str] = None
    total_amount: Optional[float] = None
    split_type: Optional[str] = None
    date: Optional[datetime] = None
    members: Optional[List[MemberSchema]] = None

class GroupSplitInDB(GroupSplitBase):
    id: str
    user_id: str
    created_at: datetime

    class Config:
        from_attributes = True
