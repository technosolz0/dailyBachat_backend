from sqlalchemy import Column, String, ForeignKey, DateTime, func, Float, Integer, Enum, Boolean
from sqlalchemy.orm import relationship
import enum
from app.core.database import Base

class InvoiceStatus(str, enum.Enum):
    pending = "pending"
    paid = "paid"
    partially_paid = "partially_paid"
    void = "void"

class QuotationStatus(str, enum.Enum):
    draft = "draft"
    sent = "sent"
    converted = "converted"
    expired = "expired"

class Quotation(Base):
    __tablename__ = "quotations"

    id = Column(String, primary_key=True, index=True)
    business_id = Column(String, ForeignKey("business_profiles.id"), nullable=False)
    customer_id = Column(String, ForeignKey("customers.id"), nullable=False)
    quotation_number = Column(String, nullable=False)
    date = Column(DateTime(timezone=True), server_default=func.now())
    expiry_date = Column(DateTime(timezone=True))
    subtotal = Column(Float, default=0.0)
    tax = Column(Float, default=0.0)
    total = Column(Float, default=0.0)
    advance_amount = Column(Float, default=0.0)
    payment_mode = Column(String)
    tax_percent = Column(Float, default=0.0)
    creator_name = Column(String, nullable=True)
    status = Column(String, default=QuotationStatus.draft)
    pdf_url = Column(String)

    business = relationship("BusinessProfile", back_populates="quotations")
    customer = relationship("Customer", back_populates="quotations")
    items = relationship("QuotationItem", back_populates="quotation", cascade="all, delete-orphan")

class QuotationItem(Base):
    __tablename__ = "quotation_items"

    id = Column(String, primary_key=True, index=True)
    quotation_id = Column(String, ForeignKey("quotations.id"), nullable=False)
    description = Column(String, nullable=False)
    quantity = Column(Float, default=1.0)
    unit_price = Column(Float, default=0.0)
    amount = Column(Float, default=0.0)

    quotation = relationship("Quotation", back_populates="items")

class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(String, primary_key=True, index=True)
    business_id = Column(String, ForeignKey("business_profiles.id"), nullable=False)
    customer_id = Column(String, ForeignKey("customers.id"), nullable=False)
    invoice_number = Column(String, nullable=False)
    date = Column(DateTime(timezone=True), server_default=func.now())
    due_date = Column(DateTime(timezone=True))
    subtotal = Column(Float, default=0.0)
    tax = Column(Float, default=0.0)
    total = Column(Float, default=0.0)
    tax_percent = Column(Float, default=0.0)
    paid_amount = Column(Float, default=0.0)
    payment_mode = Column(String)
    creator_name = Column(String, nullable=True)
    status = Column(String, default=InvoiceStatus.pending)
    pdf_url = Column(String)

    business = relationship("BusinessProfile", back_populates="invoices")
    customer = relationship("Customer", back_populates="invoices")
    items = relationship("InvoiceItem", back_populates="invoice", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="invoice", cascade="all, delete-orphan")
    share_tokens = relationship("ShareToken", back_populates="invoice", cascade="all, delete-orphan")

class InvoiceItem(Base):
    __tablename__ = "invoice_items"

    id = Column(String, primary_key=True, index=True)
    invoice_id = Column(String, ForeignKey("invoices.id"), nullable=False)
    description = Column(String, nullable=False)
    quantity = Column(Float, default=1.0)
    unit_price = Column(Float, default=0.0)
    amount = Column(Float, default=0.0)

    invoice = relationship("Invoice", back_populates="items")

class Payment(Base):
    __tablename__ = "payments"

    id = Column(String, primary_key=True, index=True)
    invoice_id = Column(String, ForeignKey("invoices.id"), nullable=False)
    amount = Column(Float, nullable=False)
    date = Column(DateTime(timezone=True), server_default=func.now())
    method = Column(String) # bank, upi, cash
    reference_id = Column(String)

    invoice = relationship("Invoice", back_populates="payments")

class ShareToken(Base):
    __tablename__ = "share_tokens"

    id = Column(String, primary_key=True, index=True)
    invoice_id = Column(String, ForeignKey("invoices.id"), nullable=True)
    quotation_id = Column(String, ForeignKey("quotations.id"), nullable=True)
    token = Column(String, unique=True, index=True)
    expires_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    invoice = relationship("Invoice", back_populates="share_tokens")
