from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, func
from app.core.database import Base

class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    rating = Column(Integer) # 1-5 rating
    category = Column(String) # e.g. "Bug", "Suggestion", "Other"
    message = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
