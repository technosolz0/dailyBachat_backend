from sqlalchemy import Column, String, ForeignKey, Float, DateTime, func
from sqlalchemy.orm import relationship
from app.core.database import Base

class Product(Base):
    __tablename__ = "products"

    id = Column(String, primary_key=True, index=True)
    business_id = Column(String, ForeignKey("business_profiles.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(String)
    price = Column(Float, default=0.0)
    stock_quantity = Column(Float, default=0.0)
    unit = Column(String, default="pcs") # pcs, kg, m, etc.
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    business = relationship("BusinessProfile", backref="products")
