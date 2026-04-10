from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User
from app.schemas.notification import NotificationSend, NotificationResponse
from app.core import firebase_config
from typing import List

router = APIRouter()

@router.post("/broadcast", response_model=NotificationResponse)
async def broadcast_notification(payload: NotificationSend, db: Session = Depends(get_db)):
    """
    Sends a push notification to specific users or all users.
    In a real app, this endpoint should be protected by Admin roles.
    """
    query = db.query(User).filter(User.fcm_token != None)
    
    if payload.user_ids:
        query = query.filter(User.id.in_(payload.user_ids))
    
    users = query.all()
    tokens = [user.fcm_token for user in users if user.fcm_token]
    
    if not tokens:
        return NotificationResponse(
            message="No registered devices found.",
            success_count=0,
            failure_count=0
        )
    
    # Firebase messaging has a limit of 500 tokens per multicast message
    success_count = 0
    failure_count = 0
    
    for i in range(0, len(tokens), 500):
        batch = tokens[i:i+500]
        results = firebase_config.send_multicast_notification(
            tokens=batch,
            title=payload.title,
            body=payload.body,
            data=payload.data
        )
        success_count += results
        failure_count += (len(batch) - results)
        
    return NotificationResponse(
        message=f"Broadcast complete.",
        success_count=success_count,
        failure_count=failure_count
    )
