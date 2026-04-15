"""
WhatsApp Trigger Router
-----------------------
Provides manual trigger endpoints so the Flutter app can directly request
a WhatsApp message be sent (e.g. from the loan/invoice creation flow).

These endpoints are thin wrappers — all business logic stays in
`app/services/whatsapp_service.py`.

Routes:
  POST /api/v1/whatsapp/loan     – send loan addition WA message
  POST /api/v1/whatsapp/invoice  – send invoice creation WA message
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from app.core.security import get_current_user_id
from app.services.whatsapp_service import (
    send_loan_lent_notification,
    send_loan_borrowed_notification,
    send_invoice_created_notification,
)

router = APIRouter()


# ── Request schemas ────────────────────────────────────────────────────────────

class LoanWARequest(BaseModel):
    phone: str
    lender_name: str
    borrower_name: str
    amount: float
    type: str               # 'lent' or 'borrowed'
    due_date: Optional[str] = None


class InvoiceWARequest(BaseModel):
    phone: str
    customer_name: str
    business_name: str
    invoice_number: str
    total: float
    due_date: Optional[str] = None


# ── Routes ─────────────────────────────────────────────────────────────────────

@router.post("/loan")
async def trigger_loan_whatsapp(
    payload: LoanWARequest,
    user_id: str = Depends(get_current_user_id),  # must be authenticated
):
    """
    Send a WhatsApp utility template when a loan is recorded.
    The Flutter app calls this after successfully creating a loan.
    """
    success = False
    if payload.type == "lent":
        success = send_loan_lent_notification(
            to_phone=payload.phone,
            lender_name=payload.lender_name,
            borrower_name=payload.borrower_name,
            amount=payload.amount,
            due_date=payload.due_date,
        )
    else:
        success = send_loan_borrowed_notification(
            to_phone=payload.phone,
            borrower_name=payload.borrower_name,
            lender_name=payload.lender_name,
            amount=payload.amount,
            due_date=payload.due_date,
        )

    return {"success": success, "type": payload.type}


@router.post("/invoice")
async def trigger_invoice_whatsapp(
    payload: InvoiceWARequest,
    user_id: str = Depends(get_current_user_id),
):
    """
    Send a WhatsApp utility template when an invoice is created.
    The Flutter app calls this after successfully creating an invoice.
    """
    success = send_invoice_created_notification(
        to_phone=payload.phone,
        customer_name=payload.customer_name,
        business_name=payload.business_name,
        invoice_number=payload.invoice_number,
        total=payload.total,
        due_date=payload.due_date,
    )
    return {"success": success}
