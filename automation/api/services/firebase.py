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


def sync_build_to_firebase(build_data: dict) -> bool:
    """
    Sync a build's status to Firebase RTDB so the admin dashboard
    can display builds even when the Python API is offline.

    Args:
        build_data: dict with short_id, client_name, niche, status,
                    created_at, finished_at, live_url, repo_full, etc.

    Returns True on success, False on failure.
    """
    if not _initialized:
        return False

    short_id = build_data.get("short_id", "")
    if not short_id:
        return False

    try:
        ref = firebase_db.reference(f"builds/{short_id}")
        # Only sync fields the admin dashboard needs
        sync_data = {
            "client_name": build_data.get("client_name", ""),
            "niche": build_data.get("niche", ""),
            "email": build_data.get("email", ""),
            "status": build_data.get("status", "queued"),
            "created_at": build_data.get("created_at", ""),
            "started_at": build_data.get("started_at", ""),
            "finished_at": build_data.get("finished_at", ""),
            "live_url": build_data.get("live_url", ""),
            "repo_full": build_data.get("repo_full", ""),
            "pages_count": build_data.get("pages_count", 0),
        }
        ref.update(sync_data)
        logger.info(f"Firebase build {short_id} → status={sync_data['status']}")
        return True
    except Exception as e:
        logger.error(f"Firebase sync_build failed: {e}")
        return False


def sync_build_phase_to_firebase(
    short_id: str, phase_number: int, phase_name: str, status: str
) -> bool:
    """Sync individual phase status to Firebase for real-time dashboard updates."""
    if not _initialized:
        return False

    try:
        ref = firebase_db.reference(f"builds/{short_id}/phases/{phase_number}")
        ref.update({
            "name": phase_name,
            "status": status,
        })
        return True
    except Exception as e:
        logger.error(f"Firebase sync_build_phase failed: {e}")
        return False


# ── Build Logs (sync log lines so admin can show real-time logs via Firebase) ──


def sync_build_log_to_firebase(short_id: str, sequence: int, message: str, category: str = "general", level: str = "info") -> bool:
    """Push a log line to Firebase RTDB for real-time admin dashboard."""
    if not _initialized:
        return False

    try:
        ref = firebase_db.reference(f"builds/{short_id}/log/{sequence}")
        ref.set({
            "seq": sequence,
            "msg": message,
            "cat": category,
            "lvl": level,
            "ts": {'.sv': 'timestamp'},
        })
        return True
    except Exception as e:
        logger.debug(f"Firebase log sync failed (non-critical): {e}")
        return False


# ── Parse Requests (Firebase bridge for AI text extraction) ──────


def get_pending_parse_requests() -> list[dict]:
    """Fetch all parse_requests with status='pending' from Firebase RTDB."""
    if not _initialized:
        return []

    try:
        ref = firebase_db.reference("parse_requests")
        snapshot = ref.order_by_child("status").equal_to("pending").get()
        if not snapshot:
            return []
        return [{"request_id": k, **v} for k, v in snapshot.items()]
    except Exception as e:
        logger.error(f"Firebase get_pending_parse_requests failed: {e}")
        return []


def update_parse_request(request_id: str, updates: dict) -> bool:
    """Update a parse_request node in Firebase RTDB."""
    if not _initialized:
        return False

    try:
        ref = firebase_db.reference(f"parse_requests/{request_id}")
        ref.update(updates)
        return True
    except Exception as e:
        logger.error(f"Firebase update_parse_request failed: {e}")
        return False


# ── Portfolio / Contract / Invoice sync ──────────────────────────


def sync_portfolio_site_to_firebase(build_data: dict) -> bool:
    """
    Sync a portfolio site (Build) to Firebase RTDB under portfolio/{short_id}.
    This keeps Firebase in sync with Postgres for finished sites.
    """
    if not _initialized:
        return False

    short_id = build_data.get("short_id", "")
    if not short_id:
        return False

    try:
        ref = firebase_db.reference(f"portfolio/{short_id}")
        ref.update({
            "client_name": build_data.get("client_name", ""),
            "email": build_data.get("email", ""),
            "phone": build_data.get("phone", ""),
            "niche": build_data.get("niche", ""),
            "goals": build_data.get("goals", ""),
            "location": build_data.get("location", ""),
            "live_url": build_data.get("live_url", ""),
            "repo_name": build_data.get("repo_name", ""),
            "brand_colors": build_data.get("brand_colors", ""),
            "tagline": build_data.get("tagline", ""),
            "status": build_data.get("status", "complete"),
            "updated_at": {'.sv': 'timestamp'},
        })
        logger.info(f"Firebase portfolio/{short_id} synced")
        return True
    except Exception as e:
        logger.error(f"Firebase sync_portfolio_site failed: {e}")
        return False


def delete_portfolio_site_from_firebase(short_id: str) -> bool:
    """Remove a portfolio site from Firebase."""
    if not _initialized:
        return False
    try:
        firebase_db.reference(f"portfolio/{short_id}").delete()
        return True
    except Exception as e:
        logger.error(f"Firebase delete portfolio/{short_id} failed: {e}")
        return False


def sync_contract_to_firebase(contract_data: dict) -> bool:
    """
    Sync a contract to Firebase RTDB under contracts/{short_id}.
    """
    if not _initialized:
        return False

    short_id = contract_data.get("short_id", "")
    if not short_id:
        return False

    try:
        ref = firebase_db.reference(f"contracts/{short_id}")
        ref.update({
            "client_name": contract_data.get("client_name", ""),
            "client_email": contract_data.get("client_email", ""),
            "project_name": contract_data.get("project_name", ""),
            "total_amount": contract_data.get("total_amount", 0),
            "deposit_amount": contract_data.get("deposit_amount", 0),
            "payment_method": contract_data.get("payment_method", ""),
            "status": contract_data.get("status", "draft"),
            "signed_at": contract_data.get("signed_at", None),
            "signer_name": contract_data.get("signer_name", None),
            "sent_at": contract_data.get("sent_at", None),
            "build_short_id": contract_data.get("build_short_id", ""),
            "updated_at": {'.sv': 'timestamp'},
        })
        logger.info(f"Firebase contracts/{short_id} synced → {contract_data.get('status')}")
        return True
    except Exception as e:
        logger.error(f"Firebase sync_contract failed: {e}")
        return False


def delete_contract_from_firebase(short_id: str) -> bool:
    """Remove a contract from Firebase."""
    if not _initialized:
        return False
    try:
        firebase_db.reference(f"contracts/{short_id}").delete()
        return True
    except Exception as e:
        logger.error(f"Firebase delete contracts/{short_id} failed: {e}")
        return False


def sync_invoice_to_firebase(invoice_data: dict) -> bool:
    """
    Sync an invoice to Firebase RTDB under invoices/{invoice_number}.
    """
    if not _initialized:
        return False

    inv_num = invoice_data.get("invoice_number", "")
    if not inv_num:
        return False

    try:
        ref = firebase_db.reference(f"invoices/{inv_num}")
        ref.update({
            "client_name": invoice_data.get("client_name", ""),
            "client_email": invoice_data.get("client_email", ""),
            "total_amount": invoice_data.get("total_amount", 0),
            "subtotal": invoice_data.get("subtotal", 0),
            "tax_amount": invoice_data.get("tax_amount", 0),
            "amount_paid": invoice_data.get("amount_paid", 0),
            "payment_status": invoice_data.get("payment_status", "unpaid"),
            "payment_method": invoice_data.get("payment_method", ""),
            "status": invoice_data.get("status", "draft"),
            "due_date": invoice_data.get("due_date", None),
            "paid_at": invoice_data.get("paid_at", None),
            "contract_short_id": invoice_data.get("contract_short_id", ""),
            "items_count": invoice_data.get("items_count", 0),
            "updated_at": {'.sv': 'timestamp'},
        })
        logger.info(f"Firebase invoices/{inv_num} synced → {invoice_data.get('status')}")
        return True
    except Exception as e:
        logger.error(f"Firebase sync_invoice failed: {e}")
        return False


def delete_invoice_from_firebase(invoice_number: str) -> bool:
    """Remove an invoice from Firebase."""
    if not _initialized:
        return False
    try:
        firebase_db.reference(f"invoices/{invoice_number}").delete()
        return True
    except Exception as e:
        logger.error(f"Firebase delete invoices/{invoice_number} failed: {e}")
        return False
