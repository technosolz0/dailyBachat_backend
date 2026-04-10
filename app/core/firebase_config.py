import os
import firebase_admin
from firebase_admin import credentials, messaging
import logging

logger = logging.getLogger(__name__)

def initialize_firebase():
    """
    Initializes Firebase Admin SDK using service account credentials.
    Priority:
    1. FIREBASE_SERVICE_ACCOUNT_JSON environment variable (path to file)
    2. Default credentials (GOOGLE_APPLICATION_CREDENTIALS or metadata server)
    """
    try:
        # Check if already initialized
        if not firebase_admin._apps:
            service_account_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
            
            if service_account_path and os.path.exists(service_account_path):
                cred = credentials.Certificate(service_account_path)
                firebase_admin.initialize_app(cred)
                logger.info("Firebase Admin SDK initialized with service account.")
            else:
                # Try default credentials
                firebase_admin.initialize_app()
                logger.info("Firebase Admin SDK initialized with default credentials.")
    except Exception as e:
        logger.error(f"Failed to initialize Firebase Admin SDK: {e}")

def send_push_notification(token: str, title: str, body: str, data: dict = None):
    """
    Sends a push notification to a specific device.
    """
    try:
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            data=data or {},
            token=token,
        )
        response = messaging.send(message)
        logger.info(f"Successfully sent message: {response}")
        return True
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        return False

def send_multicast_notification(tokens: list, title: str, body: str, data: dict = None):
    """
    Sends a push notification to multiple devices.
    """
    try:
        if not tokens:
            return 0
            
        message = messaging.MulticastMessage(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            data=data or {},
            tokens=tokens,
        )
        response = messaging.send_multicast(message)
        logger.info(f"Successfully sent {response.success_count} messages; "
                    f"failed to send {response.failure_count} messages.")
        return response.success_count
    except Exception as e:
        logger.error(f"Error sending multicast message: {e}")
        return 0
