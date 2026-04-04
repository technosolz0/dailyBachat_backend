from fastapi import APIRouter, Depends, HTTPException, Header, Response
from sqlalchemy.orm import Session, joinedload
from typing import List
import uuid
from datetime import datetime
from app.core.database import get_db
from app.models.business import BusinessProfile
from app.models.invoice import Invoice, InvoiceItem, Quotation, QuotationItem, InvoiceStatus, QuotationStatus, Payment

from app.schemas import invoice as schemas
from app.core.pdf_service import pdf_service

router = APIRouter()

def get_current_user_id(x_user_id: str = Header(...)):
    return x_user_id

@router.post("/quotations/{quotation_id}/convert-to-invoice", response_model=schemas.Invoice)
async def convert_quotation_to_invoice(
    quotation_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    quotation = db.query(Quotation).filter(Quotation.id == quotation_id).first()
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")
        
    if quotation.business.user_id != user_id:
        raise HTTPException(status_code=403, detail="Unauthorized")
        
    if quotation.status == QuotationStatus.converted:
        raise HTTPException(status_code=400, detail="Quotation already converted")
        
    invoice_id = str(uuid.uuid4())
    invoice_number = quotation.quotation_number.replace("QUO", "INV")
    
    db_invoice = Invoice(
        id=invoice_id,
        business_id=quotation.business_id,
        customer_id=quotation.customer_id,
        invoice_number=invoice_number,
        subtotal=quotation.subtotal,
        tax=quotation.tax,
        tax_percent=quotation.tax_percent,
        total=quotation.total,
        paid_amount=quotation.advance_amount,
        status=InvoiceStatus.paid if quotation.advance_amount >= quotation.total else (InvoiceStatus.partially_paid if quotation.advance_amount > 0 else InvoiceStatus.pending)
    )
    db.add(db_invoice)
    
    for item in quotation.items:
        db_item = InvoiceItem(
            id=str(uuid.uuid4()),
            invoice_id=invoice_id,
            description=item.description,
            quantity=item.quantity,
            unit_price=item.unit_price,
            amount=item.amount
        )
        db.add(db_item)
        
    quotation.status = QuotationStatus.converted
    db.commit()
    db.refresh(db_invoice)
    return db_invoice

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
    invoice_data = invoice.dict(exclude={"items"})
    if invoice_data.get("date") is None:
        invoice_data.pop("date", None)
        
    db_invoice = Invoice(
        id=invoice_id,
        business_id=profile.id,
        **invoice_data
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
    
    invoices = db.query(Invoice).options(joinedload(Invoice.customer)).filter(Invoice.business_id == profile.id).order_by(Invoice.date.desc()).all()
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
        "tax_percent": invoice.tax_percent,
        "total": invoice.total,
        "paid_amount": invoice.paid_amount
    }
    
    pdf_content = pdf_service.generate_invoice_pdf(data)
    
    return Response(
        content=pdf_content,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=invoice_{invoice.invoice_number}.pdf"}
    )

@router.post("/quotations", response_model=schemas.Quotation)
async def create_quotation(
    quotation: schemas.QuotationCreate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    profile = db.query(BusinessProfile).filter(BusinessProfile.user_id == user_id).first()
    if not profile:
        raise HTTPException(status_code=400, detail="Business profile required")
        
    quotation_id = str(uuid.uuid4())
    quotation_data = quotation.dict(exclude={"items"})
    if quotation_data.get("date") is None:
        quotation_data.pop("date", None)

    db_quotation = Quotation(
        id=quotation_id,
        business_id=profile.id,
        **quotation_data
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

@router.get("/quotations", response_model=List[schemas.Quotation])
async def list_quotations(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    profile = db.query(BusinessProfile).filter(BusinessProfile.user_id == user_id).first()
    if not profile:
        return []
    
    quotations = db.query(Quotation).options(joinedload(Quotation.customer)).filter(Quotation.business_id == profile.id).order_by(Quotation.date.desc()).all()
    return quotations
@router.get("/quotations/{quotation_id}/pdf")
async def get_quotation_pdf(
    quotation_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    quotation = db.query(Quotation).filter(Quotation.id == quotation_id).first()
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")
        
    if quotation.business.user_id != user_id:
        raise HTTPException(status_code=403, detail="Unauthorized")
        
    data = {
        "quotation_number": quotation.quotation_number,
        "date": quotation.date.strftime("%Y-%m-%d"),
        "expiry_date": quotation.expiry_date.strftime("%Y-%m-%d") if quotation.expiry_date else "N/A",
        "status": quotation.status,
        "business": {
            "name": quotation.business.name,
            "address": quotation.business.address,
            "phone": quotation.business.phone,
            "email": quotation.business.email,
            "gst_number": quotation.business.gst_number
        },
        "customer": {
            "name": quotation.customer.name,
            "address": quotation.customer.address,
            "phone": quotation.customer.phone
        },
        "payment": {
            "upi_id": quotation.business.payment_details[0].upi_id if quotation.business.payment_details else None,
            "bank_name": quotation.business.payment_details[0].bank_name if quotation.business.payment_details else None,
            "account_number": quotation.business.payment_details[0].account_number if quotation.business.payment_details else None,
            "ifsc": quotation.business.payment_details[0].ifsc if quotation.business.payment_details else None,
            "qr_code_url": quotation.business.payment_details[0].qr_code_url if quotation.business.payment_details else None
        },
        "items": [
            {
                "description": item.description,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "amount": item.amount
            } for item in quotation.items
        ],
        "subtotal": quotation.subtotal,
        "tax": quotation.tax,
        "tax_percent": quotation.tax_percent,
        "total": quotation.total,
        "advance_amount": quotation.advance_amount
    }
    
    pdf_content = pdf_service.generate_quotation_pdf(data)
    
    return Response(
        content=pdf_content,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=quotation_{quotation.quotation_number}.pdf"}
    )

@router.put("/invoices/{invoice_id}", response_model=schemas.Invoice)
async def update_invoice(
    invoice_id: str,
    invoice_update: schemas.InvoiceCreate, # Reusing create schema if update is similar
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    db_invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not db_invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
        
    if db_invoice.business.user_id != user_id:
        raise HTTPException(status_code=403, detail="Unauthorized")
        
    # Update fields
    for key, value in invoice_update.dict(exclude={"items"}).items():
        setattr(db_invoice, key, value)
        
    # Recreate items
    db.query(InvoiceItem).filter(InvoiceItem.invoice_id == invoice_id).delete()
    for item in invoice_update.items:
        db_item = InvoiceItem(
            id=str(uuid.uuid4()),
            invoice_id=invoice_id,
            **item.dict()
        )
        db.add(db_item)
        
    db.commit()
    db.refresh(db_invoice)
    return db_invoice

@router.put("/quotations/{quotation_id}", response_model=schemas.Quotation)
async def update_quotation(
    quotation_id: str,
    quotation_update: schemas.QuotationCreate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    db_quotation = db.query(Quotation).filter(Quotation.id == quotation_id).first()
    if not db_quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")
        
    if db_quotation.business.user_id != user_id:
        raise HTTPException(status_code=403, detail="Unauthorized")
        
    # Update fields
    for key, value in quotation_update.dict(exclude={"items"}).items():
        setattr(db_quotation, key, value)
        
    # Recreate items
    db.query(QuotationItem).filter(QuotationItem.quotation_id == quotation_id).delete()
    for item in quotation_update.items:
        db_item = QuotationItem(
            id=str(uuid.uuid4()),
            quotation_id=quotation_id,
            **item.dict()
        )
        db.add(db_item)
        
    db.commit()
    db.refresh(db_quotation)
    return db_quotation

@router.post("/invoices/{invoice_id}/payments", response_model=schemas.Invoice)
async def add_invoice_payment(
    invoice_id: str,
    payment: schemas.PaymentCreate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
        
    if invoice.business.user_id != user_id:
        raise HTTPException(status_code=403, detail="Unauthorized")
        
    # Record payment
    db_payment = Payment(
        id=str(uuid.uuid4()),
        invoice_id=invoice_id,
        amount=payment.amount,
        method=payment.method,
        reference_id=payment.reference_id
    )
    db.add(db_payment)
    
    invoice.paid_amount += payment.amount
    if invoice.paid_amount >= invoice.total:
        invoice.status = InvoiceStatus.paid
    else:
        invoice.status = InvoiceStatus.partially_paid
        
    db.commit()
    db.refresh(invoice)
    return invoice

@router.post("/invoices/{invoice_id}/mark-paid", response_model=schemas.Invoice)
async def mark_invoice_paid(
    invoice_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
        
    if invoice.business.user_id != user_id:
        raise HTTPException(status_code=403, detail="Unauthorized")
        
    invoice.paid_amount = invoice.total
    invoice.status = InvoiceStatus.paid
    
    db.commit()
    db.refresh(invoice)
    return invoice
