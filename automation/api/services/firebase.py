"""
AjayaDesign Automation — Firebase RTDB bridge service.

Reads leads from Firebase, syncs build status back.
Requires firebase-admin SDK and a service account key.
"""

import logging
from datetime import datetime, timezone
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
        # Build the clause list for Firebase (keep it lightweight)
        raw_clauses = contract_data.get("clauses", [])
        fb_clauses = [
            {"title": c.get("title", ""), "body": c.get("body", ""),
             "category": c.get("category", "custom"), "enabled": c.get("enabled", True)}
            for c in (raw_clauses if isinstance(raw_clauses, list) else [])
        ]

        ref.update({
            "client_name": contract_data.get("client_name", ""),
            "client_email": contract_data.get("client_email", ""),
            "project_name": contract_data.get("project_name", ""),
            "project_description": contract_data.get("project_description", ""),
            "total_amount": contract_data.get("total_amount", 0),
            "deposit_amount": contract_data.get("deposit_amount", 0),
            "payment_method": contract_data.get("payment_method", ""),
            "payment_terms": contract_data.get("payment_terms", ""),
            "start_date": contract_data.get("start_date", None),
            "estimated_completion_date": contract_data.get("estimated_completion_date", None),
            "clauses": fb_clauses,
            "custom_notes": contract_data.get("custom_notes", ""),
            "status": contract_data.get("status", "draft"),
            "signed_at": contract_data.get("signed_at", None),
            "signer_name": contract_data.get("signer_name", None),
            "signature_data": contract_data.get("signature_data", None),
            "signer_ip": contract_data.get("signer_ip", None),
            "sign_token": contract_data.get("sign_token", None),
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
        # Build lightweight payment plan for Firebase
        raw_plan = invoice_data.get("payment_plan", [])
        fb_plan = [
            {"id": p.get("id", ""), "due_date": p.get("due_date", ""),
             "amount": p.get("amount", 0), "status": p.get("status", "pending"),
             "paid_at": p.get("paid_at", None)}
            for p in (raw_plan if isinstance(raw_plan, list) else [])
        ]
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
            "items": invoice_data.get("items", []),
            "items_count": invoice_data.get("items_count", 0),
            "notes": invoice_data.get("notes", ""),
            "payment_plan": fb_plan,
            "payment_plan_enabled": invoice_data.get("payment_plan_enabled", "false"),
            "pending_installments": invoice_data.get("pending_installments", 0),
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


# ── Public Contract Signing via Firebase ─────────────────────────


def publish_contract_for_signing(sign_token: str, contract_data: dict) -> bool:
    """
    Publish contract data to Firebase at signing/{sign_token} so the
    public sign.html page can read it without hitting our local API.
    This is the same pattern as leads — Firebase is the public bridge.
    """
    if not _initialized:
        logger.warning("publish_contract_for_signing skipped — Firebase not initialized")
        return False

    try:
        ref = firebase_db.reference(f"signing/{sign_token}")
        ref.set({
            "short_id": contract_data.get("short_id", ""),
            "client_name": contract_data.get("client_name", ""),
            "project_name": contract_data.get("project_name", ""),
            "project_description": contract_data.get("project_description", ""),
            "total_amount": contract_data.get("total_amount", 0),
            "deposit_amount": contract_data.get("deposit_amount", 0),
            "payment_method": contract_data.get("payment_method", ""),
            "payment_terms": contract_data.get("payment_terms", ""),
            "start_date": contract_data.get("start_date", None),
            "estimated_completion_date": contract_data.get("estimated_completion_date", None),
            "clauses": contract_data.get("clauses", []),
            "custom_notes": contract_data.get("custom_notes", ""),
            "provider_name": contract_data.get("provider_name", "AjayaDesign"),
            "provider_email": contract_data.get("provider_email", "ajayadesign@gmail.com"),
            "provider_address": contract_data.get("provider_address", ""),
            "status": "sent",
            "signed_at": None,
            "signer_name": None,
            "signature_data": None,
            "published_at": {'.sv': 'timestamp'},
        })
        logger.info(f"Firebase signing/{sign_token} published for signing")
        return True
    except Exception as e:
        logger.error(f"Firebase publish_contract_for_signing failed: {e}")
        return False


def get_pending_signatures() -> list[dict]:
    """
    Poll Firebase for contracts that have been signed by clients.
    Returns list of signing records where signed_at is set but not yet processed.
    """
    if not _initialized:
        return []

    try:
        ref = firebase_db.reference("signing")
        snapshot = ref.order_by_child("status").equal_to("signed").get()
        if not snapshot:
            return []
        return [{"sign_token": k, **v} for k, v in snapshot.items()]
    except Exception as e:
        logger.error(f"Firebase get_pending_signatures failed: {e}")
        return []


def mark_signature_processed(sign_token: str) -> bool:
    """Mark a signing record as processed after syncing to Postgres."""
    if not _initialized:
        return False
    try:
        firebase_db.reference(f"signing/{sign_token}").update({
            "status": "processed",
            "processed_at": {'.sv': 'timestamp'},
        })
        return True
    except Exception as e:
        logger.error(f"Firebase mark_signature_processed failed: {e}")
        return False


# ── Activity Log Sync ────────────────────────────────────


def sync_activity_to_firebase(activity_data: dict) -> bool:
    """Push an activity log entry to Firebase for real-time admin feed."""
    if not _initialized:
        return False
    try:
        entry_id = activity_data.get("id", "unknown")
        firebase_db.reference(f"activity_logs/{entry_id}").set(activity_data)
        return True
    except Exception as e:
        logger.error(f"Firebase sync_activity failed: {e}")
        return False


def get_pending_retry_commands() -> list[dict]:
    """Fetch pending retry commands from /commands/retry/."""
    if not _initialized:
        return []
    try:
        ref = firebase_db.reference("commands/retry")
        data = ref.get()
        if not data or not isinstance(data, dict):
            return []
        results = []
        for key, val in data.items():
            if isinstance(val, dict) and val.get("status") == "pending":
                val["_key"] = key
                results.append(val)
        return results
    except Exception as e:
        logger.error(f"get_pending_retry_commands failed: {e}")
        return []


def clear_retry_command(key: str, result_status: str = "done", message: str = "") -> bool:
    """Mark a retry command as processed so it isn't picked up again."""
    if not _initialized:
        return False
    try:
        ref = firebase_db.reference(f"commands/retry/{key}")
        ref.update({"status": result_status, "result": message, "processed_at": datetime.now(timezone.utc).isoformat() if True else ""})
        return True
    except Exception as e:
        logger.error(f"clear_retry_command failed: {e}")
        return False


def deploy_database_rules(rules_path: str = "") -> bool:
    """
    Deploy Firebase RTDB security rules using the Admin SDK REST API.
    Falls back to the local firebase-database.rules.json if no path given.
    """
    import json

    if not _initialized:
        logger.warning("deploy_database_rules skipped — Firebase not initialized")
        return False

    if not rules_path:
        import os
        rules_path = os.path.join(os.path.dirname(__file__), "..", "..", "firebase-database.rules.json")

    try:
        with open(rules_path) as f:
            rules = json.load(f)

        from api.config import settings
        db_url = settings.firebase_db_url.rstrip("/")

        # Use the Firebase Admin SDK's own credential for the access token
        app = firebase_admin.get_app()
        credential = app.credential
        access_token = credential.get_access_token().access_token

        import urllib.request
        url = f"{db_url}/.settings/rules.json?access_token={access_token}"
        data = json.dumps(rules).encode("utf-8")
        req = urllib.request.Request(url, data=data, method="PUT")
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req) as resp:
            body = resp.read().decode()
            logger.info(f"✅ Firebase RTDB rules deployed: {body}")
        return True
    except Exception as e:
        logger.error(f"Firebase deploy_database_rules failed: {e}")
        return False
