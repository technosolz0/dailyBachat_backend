import os
import firebase_admin
from firebase_admin import credentials, messaging, auth as firebase_auth
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
                logger.info(f"Firebase Admin SDK initialized with service account from env: {service_account_path}")
            elif os.path.exists("firebase_key.json"):
                cred = credentials.Certificate("firebase_key.json")
                firebase_admin.initialize_app(cred)
                logger.info("Firebase Admin SDK initialized with local firebase_key.json service account.")
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

def delete_firebase_user_account(user_id: str = None, email: str = None, phone_number: str = None) -> bool:
    """
    Safely deletes a user from Firebase Authentication by UID, Email, or Phone Number.
    """
    deleted = False

    # 1. Attempt deletion by UID
    if user_id:
        try:
            firebase_auth.delete_user(user_id)
            logger.info(f"Successfully deleted Firebase user by UID: {user_id}")
            deleted = True
        except firebase_auth.UserNotFoundError:
            logger.info(f"Firebase user UID {user_id} not found.")
        except Exception as e:
            logger.warning(f"Error deleting Firebase user by UID {user_id}: {e}")

    # 2. Attempt deletion by Email if not deleted yet
    if not deleted and email:
        try:
            fb_user = firebase_auth.get_user_by_email(email)
            if fb_user:
                firebase_auth.delete_user(fb_user.uid)
                logger.info(f"Successfully deleted Firebase user by email: {email} (UID: {fb_user.uid})")
                deleted = True
        except firebase_auth.UserNotFoundError:
            logger.info(f"Firebase user email {email} not found.")
        except Exception as e:
            logger.warning(f"Error deleting Firebase user by email {email}: {e}")

    # 3. Attempt deletion by Phone Number if not deleted yet
    if not deleted and phone_number:
        try:
            formatted_phone = phone_number if phone_number.startswith("+") else f"+91{phone_number}"
            fb_user = firebase_auth.get_user_by_phone_number(formatted_phone)
            if fb_user:
                firebase_auth.delete_user(fb_user.uid)
                logger.info(f"Successfully deleted Firebase user by phone: {formatted_phone} (UID: {fb_user.uid})")
                deleted = True
        except firebase_auth.UserNotFoundError:
            logger.info(f"Firebase user phone {phone_number} not found.")
        except Exception as e:
            logger.warning(f"Error deleting Firebase user by phone {phone_number}: {e}")

    return deleted
