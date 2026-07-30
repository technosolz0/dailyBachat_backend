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
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
