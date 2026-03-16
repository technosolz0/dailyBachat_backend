from fastapi import APIRouter, Depends, HTTPException, Header, Response
from sqlalchemy.orm import Session
from typing import List
import uuid
from datetime import datetime
from app.core.database import get_db
from app.models.business import BusinessProfile
from app.models.invoice import Invoice, InvoiceItem, Quotation, QuotationItem, InvoiceStatus
from app.schemas import invoice as schemas
from app.core.pdf_service import pdf_service

router = APIRouter()

def get_current_user_id(x_user_id: str = Header(...)):
    return x_user_id

@router.post("/invoices", response_model=schemas.Invoice)
async def create_invoice(
    invoice: schemas.InvoiceCreate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    profile = db.query(BusinessProfile).filter(BusinessProfile.user_id == user_id).first()
    if not profile:
        raise HTTPException(status_code=400, detail="Business profile required")
        
    invoice_id = str(uuid.uuid4())
    db_invoice = Invoice(
        id=invoice_id,
        business_id=profile.id,
        **invoice.dict(exclude={"items"})
    )
    db.add(db_invoice)
    
    for item in invoice.items:
        db_item = InvoiceItem(
            id=str(uuid.uuid4()),
            invoice_id=invoice_id,
            **item.dict()
        )
        db.add(db_item)
        
    db.commit()
    db.refresh(db_invoice)
    return db_invoice

@router.get("/invoices", response_model=List[schemas.Invoice])
async def list_invoices(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    profile = db.query(BusinessProfile).filter(BusinessProfile.user_id == user_id).first()
    if not profile:
        return []
    
    invoices = db.query(Invoice).filter(Invoice.business_id == profile.id).order_by(Invoice.date.desc()).all()
    return invoices

@router.get("/invoices/{invoice_id}/pdf")
async def get_invoice_pdf(
    invoice_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
        
    # Check ownership
    if invoice.business.user_id != user_id:
        raise HTTPException(status_code=403, detail="Unauthorized")
        
    # Prepare data for PDF
    data = {
        "invoice_number": invoice.invoice_number,
        "date": invoice.date.strftime("%Y-%m-%d"),
        "due_date": invoice.due_date.strftime("%Y-%m-%d") if invoice.due_date else "N/A",
        "status": invoice.status,
        "business": {
            "name": invoice.business.name,
            "address": invoice.business.address,
            "phone": invoice.business.phone,
            "email": invoice.business.email,
            "gst_number": invoice.business.gst_number
        },
        "customer": {
            "name": invoice.customer.name,
            "address": invoice.customer.address,
            "phone": invoice.customer.phone
        },
        "items": [
            {
                "description": item.description,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "amount": item.amount
            } for item in invoice.items
        ],
        "payment": {
            "upi_id": invoice.business.payment_details[0].upi_id if invoice.business.payment_details else None,
            "bank_name": invoice.business.payment_details[0].bank_name if invoice.business.payment_details else None,
            "account_number": invoice.business.payment_details[0].account_number if invoice.business.payment_details else None,
            "ifsc": invoice.business.payment_details[0].ifsc if invoice.business.payment_details else None,
            "qr_code_url": invoice.business.payment_details[0].qr_code_url if invoice.business.payment_details else None
        },
        "subtotal": invoice.subtotal,
        "tax": invoice.tax,
        "total": invoice.total,
        "paid_amount": invoice.paid_amount
    }
    
    pdf_content = pdf_service.generate_invoice_pdf(data)
    
    return Response(
        content=pdf_content,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=invoice_{invoice.invoice_number}.pdf"}
    )

@router.post("/quotations", response_model=schemas.QuotationCreate)
async def create_quotation(
    quotation: schemas.QuotationCreate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    profile = db.query(BusinessProfile).filter(BusinessProfile.user_id == user_id).first()
    if not profile:
        raise HTTPException(status_code=400, detail="Business profile required")
        
    quotation_id = str(uuid.uuid4())
    db_quotation = Quotation(
        id=quotation_id,
        business_id=profile.id,
        **quotation.dict(exclude={"items"})
    )
    db.add(db_quotation)
    
    for item in quotation.items:
        db_item = QuotationItem(
            id=str(uuid.uuid4()),
            quotation_id=quotation_id,
            **item.dict()
        )
        db.add(db_item)
        
    db.commit()
    db.refresh(db_quotation)
    return db_quotation

@router.get("/quotations")
async def list_quotations(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    profile = db.query(BusinessProfile).filter(BusinessProfile.user_id == user_id).first()
    if not profile:
        return []
    
    quotations = db.query(Quotation).filter(Quotation.business_id == profile.id).order_by(Quotation.created_at.desc()).all()
    # Pydantic is missing full Quotation schema, passing raw or doing manual format depending on system, 
    # Since schemas.Quotation might be missing we are just returning it raw, fastapi handles ORM normally.
    return quotations
