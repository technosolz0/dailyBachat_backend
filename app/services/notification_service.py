from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import logging
from app.models.loan import Loan
from app.models.invoice import Invoice
from app.models.user import User
from app.models.customer import Customer
from app.core import firebase_config

logger = logging.getLogger(__name__)

def get_user_by_phone(db: Session, phone: str):
    if not phone:
        return None
    # Assuming phone numbers might have +91 or other prefixes, we might need fuzzy matching
    # but for now, exact match
    return db.query(User).filter(User.phone_number == phone).first()

def send_notification_to_user(db: Session, user_id: str, title: str, body: str, data: dict = None):
    user = db.query(User).filter(User.id == user_id).first()
    if user and user.fcm_token:
        return firebase_config.send_push_notification(user.fcm_token, title, body, data)
    return False

def handle_loan_addition_notification(db: Session, loan: Loan):
    """
    Sends an immediate notification to the other party when a loan is added.
    """
    if not loan.person_phone:
        return
        
    other_user = get_user_by_phone(db, loan.person_phone)
    if not other_user or not other_user.fcm_token:
        logger.info(f"Target user with phone {loan.person_phone} not found or has no FCM token.")
        return

    owner = db.query(User).filter(User.id == loan.user_id).first()
    owner_name = owner.name if owner else "Someone"

    if loan.type == 'lent':
        # Owner lent to Other -> Other borrowed from Owner
        title = "📥 New Loan Recorded"
        body = f"{owner_name} recorded that you borrowed ₹{loan.amount} from them."
    else:
        # Owner borrowed from Other -> Other lent to Owner
        title = "💸 New Loan Recorded"
        body = f"{owner_name} recorded that they borrowed ₹{loan.amount} from you."

    firebase_config.send_push_notification(other_user.fcm_token, title, body, {"loan_id": str(loan.id), "type": "loan_new"})

def handle_invoice_addition_notification(db: Session, invoice: Invoice):
    """
    Sends an immediate notification to the customer if they are a registered user.
    """
    customer = db.query(Customer).filter(Customer.id == invoice.customer_id).first()
    if not customer or not customer.phone:
        return

    other_user = get_user_by_phone(db, customer.phone)
    if not other_user or not other_user.fcm_token:
        return

    business_name = invoice.business.name if invoice.business else "A business"
    title = f"🧾 New Invoice from {business_name}"
    body = f"An invoice for ₹{invoice.total} has been generated for you. Due date: {invoice.due_date.strftime('%d-%m-%Y') if invoice.due_date else 'N/A'}"

    firebase_config.send_push_notification(other_user.fcm_token, title, body, {"invoice_id": str(invoice.id), "type": "invoice_new"})

def process_reminders(db: Session):
    """
    The heart of the reminder system. Checks for due dates and sends notifications.
    """
    now = datetime.utcnow()
    tomorrow = now + timedelta(days=1)
    
    # 1. LOAN REMINDERS
    # Due tomorrow
    loans_due_tomorrow = db.query(Loan).filter(
        Loan.status != 'paid',
        Loan.expected_return_date >= tomorrow.replace(hour=0, minute=0, second=0),
        Loan.expected_return_date <= tomorrow.replace(hour=23, minute=59, second=59)
    ).all()
    
    for loan in loans_due_tomorrow:
        _send_loan_reminder(db, loan, "Reminder: Payment due tomorrow")

    # Due today
    loans_due_today = db.query(Loan).filter(
        Loan.status != 'paid',
        Loan.expected_return_date >= now.replace(hour=0, minute=0, second=0),
        Loan.expected_return_date <= now.replace(hour=23, minute=59, second=59)
    ).all()
    
    for loan in loans_due_today:
        _send_loan_reminder(db, loan, "URGENT: Payment due today")

    # 2. INVOICE REMINDERS
    # Due tomorrow
    invoices_due_tomorrow = db.query(Invoice).filter(
        Invoice.status != 'paid',
        Invoice.due_date >= tomorrow.replace(hour=0, minute=0, second=0),
        Invoice.due_date <= tomorrow.replace(hour=23, minute=59, second=59)
    ).all()
    
    for inv in invoices_due_tomorrow:
        _send_invoice_reminder(db, inv, "Reminder: Invoice payment due tomorrow")

    # Due today
    invoices_due_today = db.query(Invoice).filter(
        Invoice.status != 'paid',
        Invoice.due_date >= now.replace(hour=0, minute=0, second=0),
        Invoice.due_date <= now.replace(hour=23, minute=59, second=59)
    ).all()
    
    for inv in invoices_due_today:
        _send_invoice_reminder(db, inv, "URGENT: Invoice payment due today")

def _send_loan_reminder(db: Session, loan: Loan, message_prefix: str):
    # Notify Owner
    send_notification_to_user(db, loan.user_id, "Loan Reminder", f"{message_prefix}: ₹{loan.amount} with {loan.person_name}")
    
    # Notify Other Party
    if loan.person_phone:
        other_user = get_user_by_phone(db, loan.person_phone)
        if other_user:
            send_notification_to_user(db, other_user.id, "Loan Reminder", f"{message_prefix}: ₹{loan.amount} with {loan.user.name if loan.user else 'DailyBachat User'}")

def _send_invoice_reminder(db: Session, inv: Invoice, message_prefix: str):
    # Notify Business Owner
    owner_user_id = inv.business.user_id
    send_notification_to_user(db, owner_user_id, "Invoice Reminder", f"{message_prefix}: Invoice {inv.invoice_number} for ₹{inv.total}")
    
    # Notify Customer
    if inv.customer and inv.customer.phone:
        other_user = get_user_by_phone(db, inv.customer.phone)
        if other_user:
            send_notification_to_user(db, other_user.id, "Invoice Reminder", f"{message_prefix}: Invoice {inv.invoice_number} from {inv.business.name}")
