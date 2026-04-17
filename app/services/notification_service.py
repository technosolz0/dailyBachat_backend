"""
Notification Service
---------------------
Handles:
  1. FCM push notifications (existing behaviour)
  2. WhatsApp utility template messages (new)

WhatsApp is sent in addition to FCM — both channels fire independently so a
failure in one does not block the other.

Reminder schedule (loan & invoice):
  • 2 days before due date  → dailybachat_reminder_2days
  • 1 day before due date   → dailybachat_reminder_1day
  • on the due date itself  → dailybachat_reminder_duedate

Condition: reminders are ONLY sent when the loan/invoice is NOT fully paid.
"""

from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import logging

from app.models.loan import Loan
from app.models.invoice import Invoice
from app.models.user import User
from app.models.customer import Customer
from app.models.business import BusinessProfile
from app.core import firebase_config

# WhatsApp helpers ─────────────────────────────────────────────────────────────
from app.services.whatsapp_service import (
    send_loan_lent_notification,
    send_loan_borrowed_notification,
    send_invoice_created_notification,
    send_quotation_created_notification,
    send_reminder_2days_before,
    send_reminder_1day_before,
    send_reminder_on_due_date,
)

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Utility helpers
# ──────────────────────────────────────────────────────────────────────────────

def get_user_by_phone(db: Session, phone: str):
    if not phone:
        return None
    return db.query(User).filter(User.phone_number == phone).first()


def send_notification_to_user(
    db: Session, user_id: str, title: str, body: str, data: dict = None
):
    user = db.query(User).filter(User.id == user_id).first()
    if user and user.fcm_token:
        return firebase_config.send_push_notification(user.fcm_token, title, body, data)
    return False


def _fmt_date(dt) -> str:
    """Return a human-readable date string or 'Not set'."""
    if dt is None:
        return "Not set"
    return dt.strftime("%d-%m-%Y")


def _is_paid(status: str) -> bool:
    """Return True if the loan/invoice is fully settled."""
    if not status:
        return False
    return status.lower() in ("paid",)


# ──────────────────────────────────────────────────────────────────────────────
# Loan – creation notification
# ──────────────────────────────────────────────────────────────────────────────

def handle_loan_addition_notification(db: Session, loan: Loan):
    """
    Called right after a new loan is saved.

    FCM   → notify the other party (if they are a registered user)
    WhatsApp → notify the person's phone number directly (no account required)

    Logic:
      • type == 'lent'     → owner lent to person_phone's person
                             → WA to person_phone: "You borrowed X from <owner>"
      • type == 'borrowed' → owner borrowed from person_phone's person
                             → WA to person_phone: "DailyBachat user borrowed X from you"
    """
    owner = db.query(User).filter(User.id == loan.user_id).first()
    owner_name = owner.name if owner else "A DailyBachat User"
    due_str = _fmt_date(loan.expected_return_date)

    # ── FCM (existing) ──────────────────────────────────────────────────────
    if loan.person_phone:
        other_user = get_user_by_phone(db, loan.person_phone)
        if other_user and other_user.fcm_token:
            if loan.type == "lent":
                title = "📥 New Loan Recorded"
                body = f"{owner_name} recorded that you borrowed ₹{loan.amount} from them."
            else:
                title = "💸 New Loan Recorded"
                body = f"{owner_name} recorded that they borrowed ₹{loan.amount} from you."
            firebase_config.send_push_notification(
                other_user.fcm_token,
                title,
                body,
                {"loan_id": str(loan.id), "type": "loan_new", "target_screen": "view_loan"},
            )

    # ── WhatsApp ─────────────────────────────────────────────────────────────
    if loan.person_phone:
        try:
            if loan.type == "lent":
                # Owner lent → person borrowed → tell person they owe
                send_loan_lent_notification(
                    to_phone=loan.person_phone,
                    lender_name=owner_name,
                    borrower_name=loan.person_name,
                    amount=loan.amount,
                    due_date=due_str,
                )
            else:
                # Owner borrowed → person lent → tell person their money is out
                send_loan_borrowed_notification(
                    to_phone=loan.person_phone,
                    borrower_name=owner_name,
                    lender_name=loan.person_name,
                    amount=loan.amount,
                    due_date=due_str,
                )
        except Exception as exc:
            logger.error(f"WhatsApp loan notification failed: {exc}")

    # Also notify the owner via FCM (confirmation to self)
    try:
        firebase_config.send_push_notification(
            owner.fcm_token,
            "✅ Loan Recorded",
            f"{'Lent' if loan.type == 'lent' else 'Borrowed'} ₹{loan.amount} "
            f"with {loan.person_name} recorded successfully.",
            {"loan_id": str(loan.id), "type": "loan_new", "target_screen": "view_loan"},
        )
    except Exception as exc:
        logger.error(f"FCM owner loan confirmation failed: {exc}")


# ──────────────────────────────────────────────────────────────────────────────
# Invoice – creation notification
# ──────────────────────────────────────────────────────────────────────────────

def handle_invoice_addition_notification(db: Session, invoice: Invoice):
    """
    Called right after a new invoice is saved.

    FCM       → notify customer if they are a registered DailyBachat user
    WhatsApp  → notify customer's phone number directly
    """
    customer = db.query(Customer).filter(Customer.id == invoice.customer_id).first()
    if not customer:
        return

    business_name = invoice.business.name if invoice.business else "A Business"
    due_str = _fmt_date(invoice.due_date)

    # ── FCM (existing) ──────────────────────────────────────────────────────
    if customer.phone:
        other_user = get_user_by_phone(db, customer.phone)
        if other_user and other_user.fcm_token:
            title = f"🧾 New Invoice from {business_name}"
            body = (
                f"Invoice {invoice.invoice_number} for ₹{invoice.total} "
                f"has been raised. Due: {due_str}"
            )
            firebase_config.send_push_notification(
                other_user.fcm_token,
                title,
                body,
                {"invoice_id": str(invoice.id), "type": "invoice_new", "target_screen": "invoice_list"},
            )

    # ── WhatsApp ─────────────────────────────────────────────────────────────
    # Only send for premium users
    is_premium = invoice.business.user.is_premium if (invoice.business and invoice.business.user) else False
    
    if customer.phone and is_premium:
        try:
            send_invoice_created_notification(
                to_phone=customer.phone,
                customer_name=customer.name,
                business_name=business_name,
                invoice_number=invoice.invoice_number,
                total=invoice.total,
                due_date=due_str,
            )
        except Exception as exc:
            logger.error(f"WhatsApp invoice notification failed: {exc}")
    elif customer.phone and not is_premium:
        logger.info(f"Skipping WhatsApp invoice notification for non-premium user: {invoice.business.user_id if invoice.business else 'Unknown'}")


# ──────────────────────────────────────────────────────────────────────────────
# Quotation – creation notification
# ──────────────────────────────────────────────────────────────────────────────

def handle_quotation_addition_notification(db: Session, quotation: Quotation):
    """
    Called right after a new quotation is saved.
    
    Checks if the user is premium before sending WhatsApp notification.
    """
    customer = db.query(Customer).filter(Customer.id == quotation.customer_id).first()
    if not customer:
        return

    business_name = quotation.business.name if quotation.business else "A Business"
    expiry_str = _fmt_date(quotation.expiry_date)

    # ── FCM ──────────────────────────────────────────────────────────────────
    if customer.phone:
        other_user = get_user_by_phone(db, customer.phone)
        if other_user and other_user.fcm_token:
            title = f"📄 New Quotation from {business_name}"
            body = (
                f"Quotation {quotation.quotation_number} for ₹{quotation.total} "
                f"has been received. Valid until: {expiry_str}"
            )
            firebase_config.send_push_notification(
                other_user.fcm_token,
                title,
                body,
                {"quotation_id": str(quotation.id), "type": "quotation_new", "target_screen": "quotation_list"},
            )

    # ── WhatsApp ─────────────────────────────────────────────────────────────
    # Only send for premium users
    is_premium = quotation.business.user.is_premium if (quotation.business and quotation.business.user) else False
    
    if customer.phone and is_premium:
        try:
            send_quotation_created_notification(
                to_phone=customer.phone,
                customer_name=customer.name,
                business_name=business_name,
                quotation_number=quotation.quotation_number,
                total=quotation.total,
                expiry_date=expiry_str,
            )
        except Exception as exc:
            logger.error(f"WhatsApp quotation notification failed: {exc}")
    elif customer.phone and not is_premium:
        logger.info(f"Skipping WhatsApp quotation notification for non-premium user: {quotation.business.user_id if quotation.business else 'Unknown'}")


# ──────────────────────────────────────────────────────────────────────────────
# Scheduler job  –  runs every few hours (configured in main.py)
# ──────────────────────────────────────────────────────────────────────────────

def process_reminders(db: Session):
    """
    The heart of the reminder system.
    Runs on a schedule and fires reminders for unpaid/pending loans & invoices.

    Reminder windows checked each run:
        • 2 days before due date   (today == due_date - 2 days)
        • 1 day before due date    (today == due_date - 1 day)
        • on the due date itself   (today == due_date)

    Condition: only sent when status != 'paid' (loan) or status != 'paid' (invoice).
    """
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = now.replace(hour=23, minute=59, second=59, microsecond=999999)

    # Build the three target date windows
    windows = {
        "2days": (
            today_start + timedelta(days=2),
            today_end + timedelta(days=2),
        ),
        "1day": (
            today_start + timedelta(days=1),
            today_end + timedelta(days=1),
        ),
        "duedate": (
            today_start,
            today_end,
        ),
    }

    _process_loan_reminders(db, windows)
    _process_invoice_reminders(db, windows)


# ──────────────────────────────────────────────────────────────────────────────
# Loan reminders
# ──────────────────────────────────────────────────────────────────────────────

def _process_loan_reminders(db: Session, windows: dict):
    for window_key, (w_start, w_end) in windows.items():
        unpaid_loans = (
            db.query(Loan)
            .filter(
                Loan.status != "paid",           # ← only unpaid
                Loan.expected_return_date >= w_start,
                Loan.expected_return_date <= w_end,
            )
            .all()
        )

        for loan in unpaid_loans:
            _send_loan_reminder_whatsapp(db, loan, window_key)
            _send_loan_reminder_fcm(db, loan, window_key)


def _send_loan_reminder_fcm(db: Session, loan: Loan, window_key: str):
    """FCM reminders to owner (and other party if registered)."""
    prefixes = {
        "2days": "Reminder: Payment due in 2 days",
        "1day": "Reminder: Payment due tomorrow",
        "duedate": "URGENT: Payment due today",
    }
    prefix = prefixes.get(window_key, "Loan Reminder")

    # Notify owner
    send_notification_to_user(
        db,
        loan.user_id,
        "Loan Reminder",
        f"{prefix}: ₹{loan.amount} with {loan.person_name}",
        {"loan_id": str(loan.id), "type": "loan_reminder", "target_screen": "view_loan"},
    )

    # Notify other party (if registered)
    if loan.person_phone:
        other_user = get_user_by_phone(db, loan.person_phone)
        if other_user:
            owner_name = loan.user.name if loan.user else "DailyBachat User"
            send_notification_to_user(
                db,
                other_user.id,
                "Loan Reminder",
                f"{prefix}: ₹{loan.amount} with {owner_name}",
                {"loan_id": str(loan.id), "type": "loan_reminder", "target_screen": "view_loan"},
            )


def _send_loan_reminder_whatsapp(db: Session, loan: Loan, window_key: str):
    """
    Send WhatsApp reminder to the person's phone.
    Notify both the owner (via owner's phone) and the other party.
    """
    if not loan.person_phone:
        return

    due_str = _fmt_date(loan.expected_return_date)

    # Determine context string
    if loan.type == "lent":
        context_for_person = f"Loan (you owe {loan.user.name if loan.user else 'a DailyBachat user'})"
        context_for_owner = f"Loan lent to {loan.person_name}"
        recipient_name_person = loan.person_name
    else:
        context_for_person = f"Loan ({loan.user.name if loan.user else 'a DailyBachat user'} owes you)"
        context_for_owner = f"Loan borrowed from {loan.person_name}"
        recipient_name_person = loan.person_name

    owner = db.query(User).filter(User.id == loan.user_id).first()

    try:
        # Send to other party's phone number
        if window_key == "2days":
            send_reminder_2days_before(
                to_phone=loan.person_phone,
                recipient_name=recipient_name_person,
                amount=loan.amount,
                due_date=due_str,
                context_info=context_for_person,
            )
        elif window_key == "1day":
            send_reminder_1day_before(
                to_phone=loan.person_phone,
                recipient_name=recipient_name_person,
                amount=loan.amount,
                due_date=due_str,
                context_info=context_for_person,
            )
        elif window_key == "duedate":
            send_reminder_on_due_date(
                to_phone=loan.person_phone,
                recipient_name=recipient_name_person,
                amount=loan.amount,
                due_date=due_str,
                context_info=context_for_person,
            )
    except Exception as exc:
        logger.error(f"WhatsApp loan reminder ({window_key}) to {loan.person_phone}: {exc}")

    # Also send to owner's phone (if available)
    if owner and owner.phone_number:
        try:
            owner_name = owner.name or "You"
            if window_key == "2days":
                send_reminder_2days_before(
                    to_phone=owner.phone_number,
                    recipient_name=owner_name,
                    amount=loan.amount,
                    due_date=due_str,
                    context_info=context_for_owner,
                )
            elif window_key == "1day":
                send_reminder_1day_before(
                    to_phone=owner.phone_number,
                    recipient_name=owner_name,
                    amount=loan.amount,
                    due_date=due_str,
                    context_info=context_for_owner,
                )
            elif window_key == "duedate":
                send_reminder_on_due_date(
                    to_phone=owner.phone_number,
                    recipient_name=owner_name,
                    amount=loan.amount,
                    due_date=due_str,
                    context_info=context_for_owner,
                )
        except Exception as exc:
            logger.error(f"WhatsApp loan reminder ({window_key}) to owner {owner.phone_number}: {exc}")


# ──────────────────────────────────────────────────────────────────────────────
# Invoice reminders
# ──────────────────────────────────────────────────────────────────────────────

def _process_invoice_reminders(db: Session, windows: dict):
    for window_key, (w_start, w_end) in windows.items():
        pending_invoices = (
            db.query(Invoice)
            .filter(
                Invoice.status != "paid",        # ← only unpaid / partially paid
                Invoice.due_date >= w_start,
                Invoice.due_date <= w_end,
            )
            .all()
        )

        for inv in pending_invoices:
            _send_invoice_reminder_whatsapp(db, inv, window_key)
            _send_invoice_reminder_fcm(db, inv, window_key)


def _send_invoice_reminder_fcm(db: Session, inv: Invoice, window_key: str):
    """FCM reminders for invoice – owner and customer."""
    prefixes = {
        "2days": "Reminder: Invoice payment due in 2 days",
        "1day": "Reminder: Invoice payment due tomorrow",
        "duedate": "URGENT: Invoice payment due today",
    }
    prefix = prefixes.get(window_key, "Invoice Reminder")

    # Notify business owner
    if inv.business:
        send_notification_to_user(
            db,
            inv.business.user_id,
            "Invoice Reminder",
            f"{prefix}: Invoice {inv.invoice_number} for ₹{inv.total}",
            {"invoice_id": str(inv.id), "type": "invoice_reminder", "target_screen": "invoice_list"},
        )

    # Notify customer (if registered user)
    if inv.customer and inv.customer.phone:
        other_user = get_user_by_phone(db, inv.customer.phone)
        if other_user:
            send_notification_to_user(
                db,
                other_user.id,
                "Invoice Reminder",
                f"{prefix}: Invoice from {inv.business.name if inv.business else 'Business'}",
                {"invoice_id": str(inv.id), "type": "invoice_reminder", "target_screen": "invoice_list"},
            )


def _send_invoice_reminder_whatsapp(db: Session, inv: Invoice, window_key: str):
    """
    Send WhatsApp reminder to customer's phone number.
    Only fires when amount is still due (status != 'paid').
    """
    if not inv.customer or not inv.customer.phone:
        return

    due_str = _fmt_date(inv.due_date)
    customer_name = inv.customer.name or "Customer"
    biz_name = inv.business.name if inv.business else "Business"
    context_info = f"Invoice {inv.invoice_number} from {biz_name}"
    remaining = inv.total - inv.paid_amount  # actual outstanding amount

    if remaining <= 0:
        # Edge case: amount is zero or negative – skip
        return

    try:
        if window_key == "2days":
            send_reminder_2days_before(
                to_phone=inv.customer.phone,
                recipient_name=customer_name,
                amount=remaining,
                due_date=due_str,
                context_info=context_info,
            )
        elif window_key == "1day":
            send_reminder_1day_before(
                to_phone=inv.customer.phone,
                recipient_name=customer_name,
                amount=remaining,
                due_date=due_str,
                context_info=context_info,
            )
        elif window_key == "duedate":
            send_reminder_on_due_date(
                to_phone=inv.customer.phone,
                recipient_name=customer_name,
                amount=remaining,
                due_date=due_str,
                context_info=context_info,
            )
    except Exception as exc:
        logger.error(
            f"WhatsApp invoice reminder ({window_key}) to {inv.customer.phone}: {exc}"
        )

    # Also remind business owner via their phone
    if inv.business and inv.business.user:
        owner = inv.business.user
        if owner.phone_number:
            owner_context = f"Invoice {inv.invoice_number} – {customer_name}"
            try:
                if window_key == "2days":
                    send_reminder_2days_before(
                        to_phone=owner.phone_number,
                        recipient_name=owner.name or "You",
                        amount=remaining,
                        due_date=due_str,
                        context_info=owner_context,
                    )
                elif window_key == "1day":
                    send_reminder_1day_before(
                        to_phone=owner.phone_number,
                        recipient_name=owner.name or "You",
                        amount=remaining,
                        due_date=due_str,
                        context_info=owner_context,
                    )
                elif window_key == "duedate":
                    send_reminder_on_due_date(
                        to_phone=owner.phone_number,
                        recipient_name=owner.name or "You",
                        amount=remaining,
                        due_date=due_str,
                        context_info=owner_context,
                    )
            except Exception as exc:
                logger.error(
                    f"WhatsApp invoice reminder ({window_key}) to owner "
                    f"{owner.phone_number}: {exc}"
                )
