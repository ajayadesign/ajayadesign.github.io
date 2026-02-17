"""
FastAPI Application — entry point.
"""

import asyncio
import uuid
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from api.config import settings
from api.database import init_db, close_db, async_session
from api.models.build import Build
from api.routes import router
from api.services.firebase import (
    init_firebase, get_new_leads, get_all_leads, update_lead_status, is_initialized,
    get_pending_parse_requests, update_parse_request,
    get_pending_signatures, mark_signature_processed,
)
from api.services.queue import BuildQueue

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)

logger = logging.getLogger(__name__)

# Global build queue — one build at a time
build_queue = BuildQueue(max_concurrent=1)


async def _process_build(build_id: str) -> None:
    """Process a single build from the queue through the full pipeline."""
    from api.pipeline.orchestrator import BuildOrchestrator
    from sqlalchemy.orm import selectinload

    async with async_session() as session:
        stmt = (
            select(Build)
            .where(Build.id == build_id)
            .options(
                selectinload(Build.phases),
                selectinload(Build.logs),
                selectinload(Build.pages),
            )
        )
        result = await session.execute(stmt)
        build = result.scalar_one_or_none()

        if not build:
            logger.error("Build %s not found in DB — skipping", build_id)
            return

        orchestrator = BuildOrchestrator(build, session)
        try:
            await orchestrator.run()
        except Exception as e:
            logger.error("Queued build %s failed: %s", build_id, e)


async def reconcile_firebase_leads() -> list[dict]:
    """
    Compare Firebase leads with PostgreSQL builds.
    Create build rows for any unprocessed leads and return them.
    """
    if not is_initialized():
        return []

    leads = get_all_leads()
    if not leads:
        return []

    missed: list[dict] = []

    async with async_session() as session:
        for lead in leads:
            fid = lead.get("firebase_id", "")
            if not fid:
                continue

            # Check if build already exists for this Firebase lead
            existing = await session.execute(
                select(Build).where(Build.firebase_id == fid)
            )
            if existing.scalar_one_or_none():
                continue  # Already tracked

            status = lead.get("status", "")
            if status not in ("new", "contacted"):
                continue  # Not a lead we should auto-process

            # Create build row
            short_id = uuid.uuid4().hex[:8]
            build = Build(
                short_id=short_id,
                firebase_id=fid,
                client_name=lead.get("business_name", lead.get("businessName", "Unknown")),
                niche=lead.get("niche", ""),
                goals=lead.get("goals", ""),
                email=lead.get("email", ""),
                source="firebase-poll",
                status="queued",
            )
            session.add(build)
            await session.commit()
            await session.refresh(build)

            update_lead_status(fid, "queued")
            missed.append({"build_id": str(build.id), "firebase_id": fid})
            logger.info(
                "🔄 Queued missed lead: %s (%s)",
                lead.get("business_name", "unknown"),
                fid,
            )

    return missed


async def periodic_firebase_poll(interval: int = 60) -> None:
    """Poll Firebase for new leads and parse requests every ``interval`` seconds."""
    while True:
        try:
            await asyncio.sleep(interval)
            if not is_initialized():
                continue

            # Poll for new leads
            leads = get_new_leads()
            if leads:
                logger.info("📡 Firebase poll found %d new leads", len(leads))
                missed = await reconcile_firebase_leads()
                for m in missed:
                    await build_queue.enqueue(m["build_id"])

            # Poll for parse requests
            await process_parse_requests()

            # Poll for signatures submitted via Firebase bridge
            await process_firebase_signatures()

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error("Firebase poll error: %s", e)


async def process_parse_requests() -> None:
    """Pick up pending parse_requests from Firebase, run AI extraction, write results back."""
    pending = get_pending_parse_requests()
    if not pending:
        return

    from api.services.ai import call_ai, extract_json
    from api.pipeline.prompts import PARSE_CLIENT_SYSTEM, parse_client_text

    for req in pending:
        rid = req["request_id"]
        raw_text = req.get("rawText", "")
        if len(raw_text) < 10:
            update_parse_request(rid, {
                "status": "failed",
                "error": "Text too short (min 10 chars)",
            })
            continue

        # Mark as processing so the admin sees the spinner update
        update_parse_request(rid, {"status": "processing"})
        logger.info("⚙️ Processing parse request %s (%d chars)", rid, len(raw_text))

        try:
            messages = [
                {"role": "system", "content": PARSE_CLIENT_SYSTEM},
                {"role": "user", "content": parse_client_text(raw_text)},
            ]
            raw_response = await call_ai(messages)
            parsed_data = extract_json(raw_response)
            confidence = parsed_data.pop("confidence", "medium")
            if confidence not in ("high", "medium", "low"):
                confidence = "medium"

            update_parse_request(rid, {
                "status": "complete",
                "result": {
                    "parsed": parsed_data,
                    "confidence": confidence,
                },
            })
            logger.info("✅ Parse request %s complete (confidence=%s)", rid, confidence)

        except Exception as exc:
            logger.error("❌ Parse request %s failed: %s", rid, exc)
            update_parse_request(rid, {
                "status": "failed",
                "error": str(exc),
            })


async def process_firebase_signatures() -> None:
    """
    Poll Firebase for contracts that clients signed via the public page.
    Same bridge pattern as leads: Firebase → API → Postgres.
    """
    pending = get_pending_signatures()
    if not pending:
        return

    from api.models.contract import Contract
    from api.services.email_service import (
        send_email, build_signed_notification_email,
    )
    from api.services.firebase import sync_contract_to_firebase

    logger.info("🖊️ Found %d pending signature(s) in Firebase", len(pending))

    async with async_session() as session:
        for sig in pending:
            token = sig.get("sign_token", "")
            signer_name = sig.get("signer_name", "Unknown")
            signature_data = sig.get("signature_data", "")
            signed_at_ts = sig.get("signed_at")  # might be ISO string or timestamp

            if not token or not signature_data:
                logger.warning("Skipping malformed signature record: %s", token)
                mark_signature_processed(token)
                continue

            # Find contract in Postgres
            result = await session.execute(
                select(Contract).where(Contract.sign_token == token)
            )
            contract = result.scalar_one_or_none()
            if not contract:
                logger.warning("Signature for unknown token %s — skipping", token)
                mark_signature_processed(token)
                continue

            if contract.signed_at:
                logger.info("Contract %s already signed — marking processed", contract.short_id)
                mark_signature_processed(token)
                continue

            # Record the signature
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc)
            contract.signed_at = now
            contract.signature_data = signature_data
            contract.signer_name = signer_name
            contract.signer_ip = sig.get("signer_ip", "firebase-bridge")
            contract.status = "signed"

            await session.commit()
            await session.refresh(contract)

            logger.info("✅ Contract %s signed by %s (via Firebase bridge)",
                        contract.short_id, signer_name)

            # Log the signing activity
            from api.routes.activity import log_activity
            await log_activity(
                entity_type="contract", entity_id=contract.short_id,
                action="signed", icon="✍️",
                description=f"Contract signed by {signer_name} (via Firebase bridge)",
                actor=f"client:{signer_name}",
                metadata={"signer_name": signer_name, "signer_ip": sig.get("signer_ip", "firebase-bridge")},
            )

            # Sync back to Firebase contracts node
            try:
                sync_contract_to_firebase({
                    "short_id": contract.short_id,
                    "client_name": contract.client_name,
                    "client_email": contract.client_email,
                    "project_name": contract.project_name,
                    "total_amount": float(contract.total_amount or 0),
                    "status": "signed",
                    "signed_at": now.isoformat(),
                    "signer_name": signer_name,
                })
            except Exception:
                pass

            # Mark Firebase signing record as processed
            mark_signature_processed(token)

            # Send notification to admin
            try:
                subject, html = build_signed_notification_email(
                    contract.short_id,
                    contract.client_name,
                    contract.project_name,
                    now.strftime("%B %d, %Y at %I:%M %p UTC"),
                )
                await send_email(
                    to=contract.provider_email or "ajayadesign@gmail.com",
                    subject=subject,
                    body_html=html,
                )
            except Exception as e:
                logger.warning("Failed to send signing notification: %s", e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown hook."""
    logger.info("🚀 Starting AjayaDesign Automation API v2.0.0-python")
    await init_db()
    logger.info("✅ Database ready")

    # Initialize Firebase bridge (optional — needs service account key)
    fb_ok = init_firebase(
        cred_path=settings.firebase_cred_path,
        db_url=settings.firebase_db_url,
    )
    if fb_ok:
        logger.info("✅ Firebase bridge ready")

        # Reconcile any missed leads
        missed = await reconcile_firebase_leads()
        if missed:
            logger.info("🔄 Found %d unprocessed leads — queueing builds", len(missed))

        # Wire up the queue processor
        build_queue.set_processor(_process_build)

        for m in missed:
            await build_queue.enqueue(m["build_id"])
    else:
        logger.info("ℹ️ Firebase bridge disabled (no credentials)")

    # Start periodic poller
    poller_task = asyncio.create_task(
        periodic_firebase_poll(interval=settings.firebase_poll_interval)
    )

    yield

    # Shutdown
    poller_task.cancel()
    try:
        await poller_task
    except asyncio.CancelledError:
        pass
    await close_db()
    logger.info("👋 Shutdown complete")


app = FastAPI(
    title="AjayaDesign Automation API",
    description=(
        "AI-powered website builder — generates, tests, and deploys "
        "production-ready client sites."
    ),
    version="2.0.0-python",
    lifespan=lifespan,
)

# CORS — allow admin dashboard on GitHub Pages and local dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")

# Contract, Invoice, Email, Portfolio, and Activity routes
from api.routes.contracts import router as contract_router, invoice_router, email_router
from api.routes.portfolio import router as portfolio_router
from api.routes.activity import activity_router

app.include_router(contract_router, prefix="/api/v1")
app.include_router(invoice_router, prefix="/api/v1")
app.include_router(email_router, prefix="/api/v1")
app.include_router(portfolio_router, prefix="/api/v1")
app.include_router(activity_router, prefix="/api/v1")


@app.get("/", include_in_schema=False)
async def root():
    return {
        "service": "AjayaDesign Automation API",
        "version": "2.0.0-python",
        "docs": "/docs",
    }
