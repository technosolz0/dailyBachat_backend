import os
import uuid
from sqlalchemy.orm import Session
from app.models.invoice import Invoice, Quotation
from app.core.pdf_service import pdf_service
import logging

logger = logging.getLogger(__name__)

# Base URL for static files - should be configured in .env
BASE_URL = os.getenv("BASE_URL", "https://dailybachatapi.serwex.in").strip()

def generate_invoice_pdf_url(db: Session, invoice: Invoice) -> str:
    """
    Generates a PDF for the invoice, saves it to disk, and returns the public URL.
    """
    logger.info(f"Generating PDF URL for invoice {invoice.invoice_number}")
    try:
        # Ensure relationships are loaded
        if not invoice.business:
            logger.info("Refreshing invoice to load business relationship")
            db.refresh(invoice)
            
        if invoice.business and not invoice.business.user:
            logger.info("Refreshing business to load user relationship")
            db.refresh(invoice.business)
            
        # 1. Prepare data (Logic copied from invoice_router.py)
        is_premium = False
        if invoice.business and invoice.business.user:
            is_premium = getattr(invoice.business.user, 'is_premium', False)
            
        data = {
            "invoice_number": invoice.invoice_number or "N/A",
            "date": invoice.date.strftime("%Y-%m-%d") if invoice.date else "N/A",
            "due_date": invoice.due_date.strftime("%Y-%m-%d") if invoice.due_date else "N/A",
            "status": invoice.status or "pending",
            "business": {
                "name": invoice.business.name if invoice.business else "A Business",
                "address": invoice.business.address if invoice.business else "",
                "phone": invoice.business.phone if invoice.business else "",
                "email": invoice.business.email if invoice.business else "",
                "gst_number": invoice.business.gst_number if invoice.business else "",
                "logo_url": invoice.business.logo_url if invoice.business else None
            },
            "customer": {
                "name": invoice.customer.name if invoice.customer else "Valued Customer",
                "address": invoice.customer.address if invoice.customer else "",
                "phone": invoice.customer.phone if invoice.customer else ""
            },
            "items": [
                {
                    "description": item.description,
                    "quantity": item.quantity,
                    "unit_price": item.unit_price,
                    "amount": item.amount
                } for item in (invoice.items or [])
            ],
            "payment": {
                "upi_id": invoice.business.payment_details[0].upi_id if (invoice.business and invoice.business.payment_details) else None,
                "bank_name": invoice.business.payment_details[0].bank_name if (invoice.business and invoice.business.payment_details) else None,
                "account_number": invoice.business.payment_details[0].account_number if (invoice.business and invoice.business.payment_details) else None,
                "ifsc": invoice.business.payment_details[0].ifsc if (invoice.business and invoice.business.payment_details) else None,
                "qr_code_url": invoice.business.payment_details[0].qr_code_url if (invoice.business and invoice.business.payment_details) else None
            },
            "subtotal": invoice.subtotal or 0.0,
            "tax": invoice.tax or 0.0,
            "tax_percent": invoice.tax_percent or 0.0,
            "total": invoice.total or 0.0,
            "paid_amount": invoice.paid_amount or 0.0,
            "is_premium": is_premium
        }

        # 2. Generate PDF bytes
        logger.info(f"Rendering PDF template for invoice {invoice.invoice_number}")
        pdf_bytes = pdf_service.generate_invoice_pdf(data)

        # 3. Save to disk
        filename = f"invoice_{invoice.invoice_number}_{uuid.uuid4().hex[:8]}.pdf"
        directory = "uploads/pdfs"
        if not os.path.exists(directory):
            logger.info(f"Creating directory {directory}")
            os.makedirs(directory)
        
        filepath = os.path.join(directory, filename)
        logger.info(f"Saving PDF to {filepath}")
        with open(filepath, "wb") as f:
            f.write(pdf_bytes)

        # 4. Construct URL
        url = f"{BASE_URL}/uploads/pdfs/{filename}"
        logger.info(f"Generated URL: {url}")
        
        # 5. Update invoice in DB
        invoice.pdf_url = url
        db.add(invoice)
        db.commit()
        db.refresh(invoice)
        
        return url
    except Exception as e:
        logger.exception(f"Failed to generate invoice PDF URL for {invoice.invoice_number}: {e}")
        return ""

def generate_quotation_pdf_url(db: Session, quotation: Quotation) -> str:
    """
    Generates a PDF for the quotation, saves it to disk, and returns the public URL.
    """
    try:
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
                "gst_number": quotation.business.gst_number,
                "logo_url": quotation.business.logo_url
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
            "advance_amount": quotation.advance_amount,
            "is_premium": quotation.business.user.is_premium if quotation.business and quotation.business.user else False
        }

        pdf_bytes = pdf_service.generate_quotation_pdf(data)

        filename = f"quotation_{quotation.quotation_number}_{uuid.uuid4().hex[:8]}.pdf"
        directory = "uploads/pdfs"
        if not os.path.exists(directory):
            os.makedirs(directory)
        
        filepath = os.path.join(directory, filename)
        with open(filepath, "wb") as f:
            f.write(pdf_bytes)

        url = f"{BASE_URL}/uploads/pdfs/{filename}"
        
        quotation.pdf_url = url
        db.add(quotation)
        db.commit()
        
        return url
    except Exception as e:
        logger.error(f"Failed to generate quotation PDF URL: {e}")
        return ""
