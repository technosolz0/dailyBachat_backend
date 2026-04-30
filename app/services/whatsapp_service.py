"""
WhatsApp Business API Service
------------------------------
Sends WhatsApp Utility template messages using the Meta WhatsApp Cloud API.

Environment variables required (add to .env):
    WHATSAPP_ACCESS_TOKEN   – Permanent / long-lived access token
    WHATSAPP_PHONE_NUMBER_ID – The sender phone number ID from Meta Business
    WHATSAPP_API_VERSION     – (optional) defaults to v19.0

Template names used (create these in Meta Business Manager):
    dailybachat_loan_lent        – when user lends money
    dailybachat_loan_borrowed    – when user borrows money
    dailybachat_invoice_created  – when a new invoice is generated
    dailybachat_reminder_2days   – 2 days before due date
    dailybachat_reminder_1day    – 1 day before due date
    dailybachat_reminder_duedate – on the due date itself

All templates must be of category UTILITY and approved in Meta Business Manager.
"""

import os
import logging
import requests
from typing import Optional, List

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────────────────────────────────────

WHATSAPP_ACCESS_TOKEN: str = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
WHATSAPP_PHONE_NUMBER_ID: str = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
WHATSAPP_API_VERSION: str = os.getenv("WHATSAPP_API_VERSION", "v19.0")

def _api_url() -> str:
    return (
        f"https://graph.facebook.com/{WHATSAPP_API_VERSION}"
        f"/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    )

def _headers() -> dict:
    return {
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }

def _is_configured() -> bool:
    """Return True only when both required env vars are present."""
    if not WHATSAPP_ACCESS_TOKEN or not WHATSAPP_PHONE_NUMBER_ID:
        logger.warning(
            "WhatsApp not configured – set WHATSAPP_ACCESS_TOKEN and "
            "WHATSAPP_PHONE_NUMBER_ID in .env"
        )
        return False
    return True


# ──────────────────────────────────────────────────────────────────────────────
# Low-level send helper
# ──────────────────────────────────────────────────────────────────────────────

def _normalize_phone(phone: str) -> str:
    """
    Ensure the number is in E.164 format without the leading '+'.
    Examples: '+91 98765 43210' → '919876543210'
              '9876543210'      → '919876543210'   (assumes IN country code)
    """
    digits = "".join(ch for ch in phone if ch.isdigit())
    if len(digits) == 10:           # Local Indian number → prepend 91
        digits = "91" + digits
    return digits


def _send_template(
    to_phone: str,
    template_name: str,
    language_code: str = "en",
    components: Optional[List[dict]] = None,
) -> bool:
    """
    Core function: sends one WhatsApp template message.

    :param to_phone:      Recipient's phone number (any reasonable format).
    :param template_name: Approved template name in Meta Business Manager.
    :param language_code: Template language code, default 'en'.
    :param components:    List of template component objects (body params, etc.).
    :return: True on success, False on failure.
    """
    if not _is_configured():
        return False

    normalized = _normalize_phone(to_phone)
    if not normalized:
        logger.warning(f"Invalid phone number supplied: '{to_phone}'")
        return False

    payload: dict = {
        "messaging_product": "whatsapp",
        "to": normalized,
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": language_code},
        },
    }

    if components:
        payload["template"]["components"] = components

    # Log payload for debugging (masking phone number for privacy)
    # logger.debug(f"WhatsApp Payload: {payload}")

    try:
        resp = requests.post(_api_url(), json=payload, headers=_headers(), timeout=10)
        if resp.status_code in (200, 201):
            logger.info(
                f"WhatsApp '{template_name}' sent to {normalized}. "
                f"Response: {resp.json()}"
            )
            return True
        else:
            logger.error(
                f"WhatsApp API error [{resp.status_code}] for '{template_name}' "
                f"to {normalized}: {resp.text}"
            )
            logger.error(f"Failed Payload: {payload}")
            return False
    except requests.RequestException as exc:
        logger.error(f"WhatsApp request failed for '{template_name}': {exc}")
        return False


# ──────────────────────────────────────────────────────────────────────────────
# Public helpers – one per use-case
# ──────────────────────────────────────────────────────────────────────────────

def send_loan_lent_notification(
    to_phone: str,
    lender_name: str,
    borrower_name: str,
    amount: float,
    due_date: Optional[str] = None,
) -> bool:
    """
    Notify *borrower* that someone recorded a 'lent' loan.

    Template: dailybachat_loan_lent
    Body parameters (positional):
        {{1}} – lender's name
        {{2}} – amount (₹)
        {{3}} – borrower's name
        {{4}} – due date (or 'N/A')
    """
    amount_str = f"{amount:,.0f}"
    due_str = due_date if due_date else "Not set"

    components = [
        {
            "type": "body",
            "parameters": [
                {"type": "text", "text": lender_name},
                {"type": "text", "text": amount_str},
                {"type": "text", "text": borrower_name},
                {"type": "text", "text": due_str},
            ],
        }
    ]
    return _send_template(to_phone, "dailybachat_loan_lent", components=components)


def send_loan_borrowed_notification(
    to_phone: str,
    borrower_name: str,
    lender_name: str,
    amount: float,
    due_date: Optional[str] = None,
) -> bool:
    """
    Notify *lender* that someone recorded a 'borrowed' loan.

    Template: dailybachat_loan_borrowed
    Body parameters:
        {{1}} – borrower's name
        {{2}} – amount (₹)
        {{3}} – lender's name
        {{4}} – due date (or 'N/A')
    """
    amount_str = f"{amount:,.0f}"
    due_str = due_date if due_date else "Not set"

    components = [
        {
            "type": "body",
            "parameters": [
                {"type": "text", "text": borrower_name},
                {"type": "text", "text": amount_str},
                {"type": "text", "text": lender_name},
                {"type": "text", "text": due_str},
            ],
        }
    ]
    return _send_template(to_phone, "dailybachat_loan_borrowed", components=components)


def send_invoice_created_notification(
    to_phone: str,
    customer_name: str,
    business_name: str,
    invoice_number: str,
    total: float,
    due_date: Optional[str] = None,
    pdf_url: Optional[str] = None,
) -> bool:
    """
    Notify customer when a new invoice is raised for them.

    Template: dailybachat_invoice_created
    Body parameters:
        {{1}} – customer name
        {{2}} – business name
        {{3}} – invoice number
        {{4}} – total (₹)
        {{5}} – due date (or 'N/A')
    """
    amount_str = f"{total:,.0f}"
    due_str = due_date if due_date else "N/A"

    # Template 'dailybachat_invoice_created' REQUIRES a DOCUMENT header.
    # If pdf_url is missing, we must provide a fallback or Meta will reject the request.
    if not pdf_url:
        logger.warning(f"WhatsApp: No pdf_url for invoice {invoice_number}. Using placeholder to avoid API error.")
        pdf_url = "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf"

    components = [
        {
            "type": "header",
            "parameters": [
                {
                    "type": "document",
                    "document": {
                        "link": pdf_url,
                        "filename": f"Invoice_{invoice_number}.pdf"
                    }
                }
            ]
        },
        {
            "type": "body",
            "parameters": [
                {"type": "text", "text": customer_name},
                {"type": "text", "text": business_name},
                {"type": "text", "text": invoice_number},
                {"type": "text", "text": amount_str},
                {"type": "text", "text": due_str},
            ],
        }
    ]
    
    return _send_template(to_phone, "dailybachat_invoice_created", components=components)


def send_quotation_created_notification(
    to_phone: str,
    customer_name: str,
    business_name: str,
    quotation_number: str,
    total: float,
    expiry_date: Optional[str] = None,
    pdf_url: Optional[str] = None,
) -> bool:
    """
    Notify customer when a new quotation is sent to them.

    Template: dailybachat_quotation_created
    Body parameters:
        {{1}} – customer name
        {{2}} – business name
        {{3}} – quotation number
        {{4}} – estimated total (₹)
        {{5}} – expiry date (or 'N/A')
    """
    amount_str = f"{total:,.0f}"
    expiry_str = expiry_date if expiry_date else "N/A"

    # Template 'dailybachat_quotation_created' REQUIRES a DOCUMENT header.
    if not pdf_url:
        logger.warning(f"WhatsApp: No pdf_url for quotation {quotation_number}. Using placeholder.")
        pdf_url = "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf"

    components = [
        {
            "type": "header",
            "parameters": [
                {
                    "type": "document",
                    "document": {
                        "link": pdf_url,
                        "filename": f"Quotation_{quotation_number}.pdf"
                    }
                }
            ]
        },
        {
            "type": "body",
            "parameters": [
                {"type": "text", "text": customer_name},
                {"type": "text", "text": business_name},
                {"type": "text", "text": quotation_number},
                {"type": "text", "text": amount_str},
                {"type": "text", "text": expiry_str},
            ],
        }
    ]
    
    return _send_template(to_phone, "dailybachat_quotation_created", components=components)



# ──────────────────────────────────────────────────────
# Reminder templates
# ──────────────────────────────────────────────────────

def send_reminder_2days_before(
    to_phone: str,
    recipient_name: str,
    amount: float,
    due_date: str,
    context_info: str,          # e.g. "Loan with Rahul" or "Invoice INV-001"
) -> bool:
    """
    2-day-before reminder.
    Template: dailybachat_reminder_2days
    """
    components = [
        {
            "type": "body",
            "parameters": [
                {"type": "text", "text": recipient_name},
                {"type": "text", "text": context_info},
                {"type": "text", "text": f"{amount:,.0f}"},
                {"type": "text", "text": due_date},
            ],
        }
    ]
    return _send_template(to_phone, "dailybachat_reminder_2days", components=components)


def send_reminder_1day_before(
    to_phone: str,
    recipient_name: str,
    amount: float,
    due_date: str,
    context_info: str,
) -> bool:
    """
    1-day-before reminder.
    Template: dailybachat_reminder_1day
    """
    components = [
        {
            "type": "body",
            "parameters": [
                {"type": "text", "text": recipient_name},
                {"type": "text", "text": context_info},
                {"type": "text", "text": f"{amount:,.0f}"},
                {"type": "text", "text": due_date},
            ],
        }
    ]
    return _send_template(to_phone, "dailybachat_reminder_1day", components=components)


def send_reminder_on_due_date(
    to_phone: str,
    recipient_name: str,
    amount: float,
    due_date: str,
    context_info: str,
) -> bool:
    """
    Due-date reminder.
    Template: dailybachat_reminder_duedate
    """
    components = [
        {
            "type": "body",
            "parameters": [
                {"type": "text", "text": recipient_name},
                {"type": "text", "text": context_info},
                {"type": "text", "text": f"{amount:,.0f}"},
                {"type": "text", "text": due_date},
            ],
        }
    ]
    return _send_template(to_phone, "dailybachat_reminder_duedate", components=components)
