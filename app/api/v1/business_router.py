from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid
from app.core.database import get_db
from app.models.business import BusinessProfile, PaymentDetail
from app.models.customer import Customer
from app.models.invoice import Invoice, InvoiceItem, Payment, Quotation, QuotationItem
from app.schemas import business as schemas
from app.schemas import customer as customer_schemas
from app.schemas import invoice as invoice_schemas

router = APIRouter()

# Simple dependency to get user_id from Header for now
def get_current_user_id(x_user_id: str = Header(...)):
    return x_user_id

@router.get("/banks", response_model=List[str])
async def get_banks():
    return [
        "State Bank of India (SBI)",
        "HDFC Bank",
        "ICICI Bank",
        "Punjab National Bank (PNB)",
        "Axis Bank",
        "Kotak Mahindra Bank",
        "Bank of Baroda (BoB)",
        "Canara Bank",
        "Union Bank of India",
        "Bank of India (BOI)",
        "IndusInd Bank",
        "Yes Bank",
        "IDFC FIRST Bank",
        "Other"
    ]

@router.post("/profile", response_model=schemas.BusinessProfile)
async def create_business_profile(
    profile: schemas.BusinessProfileCreate, 
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    db_profile = db.query(BusinessProfile).filter(BusinessProfile.user_id == user_id).first()
    if db_profile:
        raise HTTPException(status_code=400, detail="Business profile already exists")
    
    business_id = str(uuid.uuid4())
    db_profile = BusinessProfile(
        id=business_id,
        user_id=user_id,
        **profile.dict(exclude={"payment_details"})
    )
    db.add(db_profile)
    
    for pd in profile.payment_details:
        db_pd = PaymentDetail(
            id=str(uuid.uuid4()),
            business_id=business_id,
            **pd.dict()
        )
        db.add(db_pd)
    
    db.commit()
    db.refresh(db_profile)
    return db_profile

@router.get("/profile", response_model=schemas.BusinessProfile)
async def get_business_profile(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    profile = db.query(BusinessProfile).filter(BusinessProfile.user_id == user_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile

# Customers
@router.post("/customers", response_model=customer_schemas.Customer)
async def add_customer(
    customer: customer_schemas.CustomerCreate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    profile = db.query(BusinessProfile).filter(BusinessProfile.user_id == user_id).first()
    if not profile:
        raise HTTPException(status_code=400, detail="Create business profile first")
        
    db_customer = Customer(
        id=str(uuid.uuid4()),
        business_id=profile.id,
        **customer.dict()
    )
    db.add(db_customer)
    db.commit()
    db.refresh(db_customer)
    return db_customer

@router.get("/customers", response_model=List[customer_schemas.Customer])
async def list_customers(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    profile = db.query(BusinessProfile).filter(BusinessProfile.user_id == user_id).first()
    if not profile:
        return []
    return db.query(Customer).filter(Customer.business_id == profile.id).all()
