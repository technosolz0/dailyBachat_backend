from pydantic import BaseModel
from typing import Optional, List, Dict

class NotificationSend(BaseModel):
    title: str
    body: str
    user_ids: Optional[List[str]] = None  # Send to specific users, if None send to all
    data: Optional[Dict[str, str]] = None

class NotificationResponse(BaseModel):
    message: str
    success_count: int
    failure_count: int
