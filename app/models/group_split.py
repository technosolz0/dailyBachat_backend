from sqlalchemy import Column, String, Float, DateTime, ForeignKey, func, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base

class GroupSplit(Base):
    __tablename__ = "group_splits"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    total_amount = Column(Float, nullable=False)
    split_type = Column(String, default="equal") # "equal", "unequal", "percentage"
    date = Column(DateTime(timezone=True), server_default=func.now())
    members = Column(JSON, default=[]) # list of member objects
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", backref="group_splits")
