"""
AjayaDesign Automation — Firebase RTDB bridge service.

Reads leads from Firebase, syncs build status back.
Requires firebase-admin SDK and a service account key.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# firebase-admin may not be installed in every environment
try:
    import firebase_admin
    from firebase_admin import credentials, db as firebase_db

    _HAS_FIREBASE = True
except ImportError:
    _HAS_FIREBASE = False
    logger.warning("firebase-admin not installed — Firebase bridge disabled")

_initialized = False


def init_firebase(cred_path: str = "", db_url: str = "") -> bool:
    """
    Initialize Firebase Admin SDK.

    Args:
        cred_path: Path to the service account JSON key file.
        db_url: Firebase RTDB URL.

    Returns True if init succeeded, False otherwise.
    """
    global _initialized

    if not _HAS_FIREBASE:
        logger.warning("firebase-admin not installed — skipping init")
        return False

    if _initialized:
        return True

    if not cred_path:
        logger.warning("FIREBASE_CRED_PATH not set — Firebase bridge disabled")
        return False

    try:
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred, {"databaseURL": db_url})
        _initialized = True
        logger.info("✅ Firebase Admin SDK initialized")
        return True
    except Exception as e:
        logger.error(f"Firebase init failed: {e}")
        return False


def is_initialized() -> bool:
    """Check if Firebase Admin SDK is initialized."""
    return _initialized


def get_new_leads() -> list[dict]:
    """Fetch all leads with status='new' from Firebase RTDB."""
    if not _initialized:
        return []

    try:
        ref = firebase_db.reference("leads")
        snapshot = ref.order_by_child("status").equal_to("new").get()
        if not snapshot:
            return []
        return [{"firebase_id": k, **v} for k, v in snapshot.items()]
    except Exception as e:
        logger.error(f"Firebase get_new_leads failed: {e}")
        return []


def get_all_leads() -> list[dict]:
    """Fetch all leads from Firebase RTDB."""
    if not _initialized:
        return []

    try:
        ref = firebase_db.reference("leads")
        snapshot = ref.get()
        if not snapshot:
            return []
        return [{"firebase_id": k, **v} for k, v in snapshot.items()]
    except Exception as e:
        logger.error(f"Firebase get_all_leads failed: {e}")
        return []


def update_lead_status(
    firebase_id: str, status: str, extra: Optional[dict] = None
) -> bool:
    """
    Update a lead's status in Firebase RTDB.

    Returns True on success, False on failure.
    """
    if not _initialized:
        return False

    try:
        ref = firebase_db.reference(f"leads/{firebase_id}")
        update: dict = {"status": status}
        if extra:
            update.update(extra)
        ref.update(update)
        logger.info(f"Firebase lead {firebase_id} → status={status}")
        return True
    except Exception as e:
        logger.error(f"Firebase update_lead_status failed: {e}")
        return False
