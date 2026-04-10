from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class FeedbackBase(BaseModel):
    rating: Optional[int] = None
    category: Optional[str] = "General"
    message: str

class FeedbackCreate(FeedbackBase):
    user_id: str

class Feedback(FeedbackBase):
    id: int
    user_id: str
    created_at: datetime

    class Config:
        from_attributes = True
