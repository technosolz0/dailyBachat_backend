from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class FeedbackBase(BaseModel):
    rating: Optional[int] = None
    category: Optional[str] = "General"
    message: Optional[str] = ""

class FeedbackCreate(FeedbackBase):
    user_id: str

class Feedback(FeedbackBase):
    id: int
    user_id: str
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    user_phone: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
