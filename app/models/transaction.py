from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.core.database import Base

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(String, primary_key=True, index=True) # UUID or Firestore ID if syncing
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    amount = Column(Float, nullable=False)
    description = Column(String)
    category = Column(String) # For now, keeping it as string to match Firestore logic, but could be a foreign key to Category
    type = Column(String, nullable=False) # 'income' or 'expense'
    date = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", backref="transactions")
