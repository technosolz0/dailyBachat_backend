from fastapi import APIRouter, Depends, HTTPException, Header, File, UploadFile
import shutil
import os
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid
from app.core.database import get_db
from app.models.business import BusinessProfile, PaymentDetail
from app.models.user import User
from app.models.customer import Customer
from app.models.invoice import Invoice, InvoiceItem, Payment, Quotation, QuotationItem
from app.schemas import business as schemas
from app.schemas import customer as customer_schemas
from app.schemas import invoice as invoice_schemas
from app.core.security import get_current_user_id

router = APIRouter()


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
async def create_or_update_business_profile(
    profile: schemas.BusinessProfileCreate, 
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    # Ensure user exists in backend to satisfy foreign key constraint
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        # Create a shell user if not exists to avoid 500 IntegrityError
        # This can happen if Firebase registration synced but backend verify didn't create the user yet
        user = User(id=user_id, email=profile.email or "", name=profile.name)
        db.add(user)
        db.flush() 

    db_profile = db.query(BusinessProfile).filter(BusinessProfile.user_id == user_id).first()
    
    if db_profile:
        # UPDATE existing profile
        for key, value in profile.dict(exclude={"payment_details"}).items():
            setattr(db_profile, key, value)
        
        # Simple payment details update: clear and recreate
        db.query(PaymentDetail).filter(PaymentDetail.business_id == db_profile.id).delete()
        for pd in profile.payment_details:
            db_pd = PaymentDetail(
                id=str(uuid.uuid4()),
                business_id=db_profile.id,
                **pd.dict()
            )
            db.add(db_pd)
    else:
        # CREATE new profile
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
    
    try:
        db.commit()
        db.refresh(db_profile)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error during profile save: {str(e)}")
        
    return db_profile
 
@router.put("/profile", response_model=schemas.BusinessProfile)
async def update_business_profile(
    profile: schemas.BusinessProfileCreate, 
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    return await create_or_update_business_profile(profile, db, user_id)

@router.patch("/profile", response_model=schemas.BusinessProfile)
async def patch_business_profile(
    profile_update: dict, 
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    db_profile = db.query(BusinessProfile).filter(BusinessProfile.user_id == user_id).first()
    if not db_profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    for key, value in profile_update.items():
        if hasattr(db_profile, key) and key != "payment_details":
            setattr(db_profile, key, value)
    
    db.commit()
    db.refresh(db_profile)
    return db_profile

@router.post("/profile/logo")
async def upload_business_logo(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id)
):
    try:
        # Define path
        ext = os.path.splitext(file.filename)[1]
        if not ext: ext = ".jpg"
        filename = f"{user_id}{ext}"
        
        upload_folder = "uploads/business_logos"
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)
            
        file_path = os.path.join(upload_folder, filename)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Return the public URL path
        return {"logo_url": f"/uploads/business_logos/{filename}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload logo: {str(e)}")


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

@router.put("/customers/{customer_id}", response_model=customer_schemas.Customer)
async def update_customer(
    customer_id: str,
    customer_update: customer_schemas.CustomerCreate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    profile = db.query(BusinessProfile).filter(BusinessProfile.user_id == user_id).first()
    if not profile:
        raise HTTPException(status_code=400, detail="Create business profile first")
        
    db_customer = db.query(Customer).filter(Customer.id == customer_id, Customer.business_id == profile.id).first()
    if not db_customer:
        raise HTTPException(status_code=404, detail="Customer not found")
        
    for key, value in customer_update.dict().items():
        setattr(db_customer, key, value)
        
    db.commit()
    db.refresh(db_customer)
    return db_customer

@router.patch("/customers/{customer_id}", response_model=customer_schemas.Customer)
async def patch_customer(
    customer_id: str,
    customer_update: dict,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    profile = db.query(BusinessProfile).filter(BusinessProfile.user_id == user_id).first()
    if not profile:
        raise HTTPException(status_code=400, detail="Create business profile first")
        
    db_customer = db.query(Customer).filter(Customer.id == customer_id, Customer.business_id == profile.id).first()
    if not db_customer:
        raise HTTPException(status_code=404, detail="Customer not found")
        
    for key, value in customer_update.items():
        if hasattr(db_customer, key):
            setattr(db_customer, key, value)
            
    db.commit()
    db.refresh(db_customer)
    return db_customer

from fastapi import Response
from app.core.pdf_service import pdf_service
from datetime import datetime

@router.get("/customers/{customer_id}/statement")
async def get_customer_statement(
    customer_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    profile = db.query(BusinessProfile).filter(BusinessProfile.user_id == user_id).first()
    if not profile:
        raise HTTPException(status_code=400, detail="Business profile required")
        
    customer = db.query(Customer).filter(Customer.id == customer_id, Customer.business_id == profile.id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
        
    # Prepare transactions data (invoices)
    transactions = []
    for inv in customer.invoices:
        transactions.append({
            "date": inv.date.strftime("%Y-%m-%d"),
            "number": inv.invoice_number,
            "type": "Invoice",
            "total": inv.total,
            "paid": inv.paid_amount,
            "balance": inv.total - inv.paid_amount
        })
        
    data = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "is_premium": profile.user.is_premium,
        "business": {
            "name": profile.name,
            "address": profile.address,
            "phone": profile.phone,
            "email": profile.email,
            "logo_url": profile.logo_url
        },
        "customer": {
            "name": customer.name,
            "address": customer.address,
            "phone": customer.phone
        },
        "total_sales": customer.total_sales,
        "total_paid": customer.total_paid,
        "balance_due": customer.pending_amount,
        "transactions": transactions
    }
    
    pdf_content = pdf_service.generate_statement_pdf(data)
    
    return Response(
        content=pdf_content,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=statement_{customer.name.replace(' ', '_')}.pdf"}
    )
