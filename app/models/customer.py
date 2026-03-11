from sqlalchemy import Column, String, ForeignKey, DateTime, func, Float
from sqlalchemy.orm import relationship
from app.core.database import Base

class Customer(Base):
    __tablename__ = "customers"

    id = Column(String, primary_key=True, index=True)
    business_id = Column(String, ForeignKey("business_profiles.id"), nullable=False)
    name = Column(String, nullable=False)
    phone = Column(String, index=True)
    email = Column(String)
    address = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    business = relationship("BusinessProfile", back_populates="customers")
    invoices = relationship("Invoice", back_populates="customer")
    quotations = relationship("Quotation", back_populates="customer")

    @property
    def total_sales(self):
        return sum(inv.total for inv in self.invoices if inv.status != 'void')

    @property
    def total_paid(self):
        return sum(inv.paid_amount for inv in self.invoices if inv.status != 'void')

    @property
    def pending_amount(self):
        return self.total_sales - self.total_paid
