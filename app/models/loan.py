from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, func, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base

class Loan(Base):
    __tablename__ = "loans"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    person_name = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    paid_amount = Column(Float, default=0.0)
    status = Column(String) # 'unpaid', 'partially paid', 'paid'
    type = Column(String) # 'lent' or 'borrowed'
    reason = Column(String)
    date = Column(DateTime(timezone=True), server_default=func.now())
    expected_return_date = Column(DateTime(timezone=True))
    payment_history = Column(JSON, default=[]) # Storing history as JSON for simplicity, matching Firestore

    user = relationship("User", backref="loans")
