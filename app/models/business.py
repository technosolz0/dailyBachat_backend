from sqlalchemy import Column, String, ForeignKey, DateTime, func, Integer
from sqlalchemy.orm import relationship
from app.core.database import Base

class BusinessProfile(Base):
    __tablename__ = "business_profiles"

    id = Column(String, primary_key=True, index=True) # UUID
    user_id = Column(String, ForeignKey("users.id"), unique=True, nullable=False)
    name = Column(String, nullable=False)
    address = Column(String)
    phone = Column(String)
    email = Column(String)
    gst_number = Column(String)
    logo_url = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", backref="business_profile")
    payment_details = relationship("PaymentDetail", back_populates="business", cascade="all, delete-orphan")
    customers = relationship("Customer", back_populates="business")
    invoices = relationship("Invoice", back_populates="business")
    quotations = relationship("Quotation", back_populates="business")

class PaymentDetail(Base):
    __tablename__ = "payment_details"

    id = Column(String, primary_key=True, index=True)
    business_id = Column(String, ForeignKey("business_profiles.id"), nullable=False)
    bank_name = Column(String)
    account_number = Column(String)
    ifsc = Column(String)
    upi_id = Column(String)
    qr_code_url = Column(String)
    
    business = relationship("BusinessProfile", back_populates="payment_details")
