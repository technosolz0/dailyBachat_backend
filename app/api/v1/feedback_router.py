from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.feedback import Feedback as FeedbackModel
from app.schemas.feedback import FeedbackCreate, Feedback as FeedbackSchema
from typing import List

router = APIRouter()

@router.post("/", response_model=FeedbackSchema)
async def create_feedback(feedback: FeedbackCreate, db: Session = Depends(get_db)):
    db_feedback = FeedbackModel(
        user_id=feedback.user_id,
        rating=feedback.rating,
        category=feedback.category,
        message=feedback.message
    )
    db.add(db_feedback)
    db.commit()
    db.refresh(db_feedback)
    return db_feedback

@router.get("/", response_model=List[FeedbackSchema])
async def get_all_feedback(db: Session = Depends(get_db)):
    """
    Get all feedback. In a real app, this would be restricted to administrators.
    """
    return db.query(FeedbackModel).all()
