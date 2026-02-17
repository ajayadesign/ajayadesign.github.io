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
    deploy_database_rules,
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


async def reconcile_contracts_invoices_to_firebase() -> None:
    """
    On startup, re-sync all active contracts, invoices, and portfolio sites
    from Postgres → Firebase.
    This covers the case where the server was down and Firebase mirror is stale.
    Also picks up any pending signatures that arrived while we were offline.
    """
    if not is_initialized():
        return

    from api.models.contract import Contract, Invoice
    from api.services.firebase import sync_contract_to_firebase, sync_invoice_to_firebase, sync_portfolio_site_to_firebase

    synced_contracts = 0
    synced_invoices = 0
    synced_portfolio = 0

    async with async_session() as session:
        # Re-sync all portfolio sites (complete builds)
        result = await session.execute(
            select(Build).where(Build.status.in_(["complete", "success"]))
        )
        builds = result.scalars().all()
        for b in builds:
            try:
                sync_portfolio_site_to_firebase({
                    "short_id": b.short_id,
                    "client_name": b.client_name or "",
                    "email": getattr(b, "email", "") or "",
                    "phone": getattr(b, "phone", "") or "",
                    "niche": b.niche or "",
                    "goals": b.goals or "",
                    "location": getattr(b, "location", "") or "",
                    "live_url": b.live_url or "",
                    "repo_name": b.repo_name or "",
                    "brand_colors": getattr(b, "brand_colors", "") or "",
                    "tagline": getattr(b, "tagline", "") or "",
                    "status": b.status or "complete",
                })
                synced_portfolio += 1
            except Exception as e:
                logger.warning("Failed to sync portfolio %s to Firebase: %s", b.short_id, e)

        # Re-sync all non-cancelled contracts
        result = await session.execute(
            select(Contract).where(Contract.status.notin_(["cancelled"]))
        )
        contracts = result.scalars().all()
        for c in contracts:
            try:
                # Resolve build short_id if linked
                build_short_id = ""
                if c.build_id:
                    b = await session.execute(
                        select(Build.short_id).where(Build.id == c.build_id)
                    )
                    row = b.scalar_one_or_none()
                    if row:
                        build_short_id = row

                sync_contract_to_firebase({
                    "short_id": c.short_id,
                    "client_name": c.client_name,
                    "client_email": c.client_email,
                    "project_name": c.project_name,
                    "total_amount": float(c.total_amount or 0),
                    "deposit_amount": float(c.deposit_amount or 0),
                    "payment_method": c.payment_method or "",
                    "status": c.status,
                    "signed_at": c.signed_at.isoformat() if c.signed_at else None,
                    "signer_name": c.signer_name,
                    "sent_at": c.sent_at.isoformat() if c.sent_at else None,
                    "build_short_id": build_short_id,
                })
                synced_contracts += 1
            except Exception as e:
                logger.warning("Failed to sync contract %s to Firebase: %s", c.short_id, e)

        # Re-sync all non-cancelled invoices
        result = await session.execute(
            select(Invoice).where(Invoice.status.notin_(["cancelled"]))
        )
        invoices = result.scalars().all()
        for inv in invoices:
            try:
                # Resolve contract short_id if linked
                contract_short_id = ""
                if inv.contract_id:
                    cr = await session.execute(
                        select(Contract.short_id).where(Contract.id == inv.contract_id)
                    )
                    row = cr.scalar_one_or_none()
                    if row:
                        contract_short_id = row

                plan = inv.payment_plan or []
                pending_installments = sum(1 for i in plan if i.get("status") in ("pending", "overdue"))
                sync_invoice_to_firebase({
                    "invoice_number": inv.invoice_number,
                    "client_name": inv.client_name,
                    "client_email": inv.client_email,
                    "total_amount": float(inv.total_amount or 0),
                    "subtotal": float(inv.subtotal or 0),
                    "tax_amount": float(inv.tax_amount or 0),
                    "amount_paid": float(inv.amount_paid or 0),
                    "payment_status": inv.payment_status or "unpaid",
                    "payment_method": inv.payment_method or "",
                    "status": inv.status,
                    "due_date": inv.due_date.isoformat() if inv.due_date else None,
                    "paid_at": inv.paid_at.isoformat() if inv.paid_at else None,
                    "contract_short_id": contract_short_id,
                    "items_count": len(inv.items) if inv.items else 0,
                    "payment_plan_enabled": inv.payment_plan_enabled or "false",
                    "pending_installments": pending_installments,
                })
                synced_invoices += 1
            except Exception as e:
                logger.warning("Failed to sync invoice %s to Firebase: %s", inv.invoice_number, e)

    if synced_contracts or synced_invoices or synced_portfolio:
        logger.info(
            "🔄 Synced %d portfolio sites, %d contracts, %d invoices → Firebase",
            synced_portfolio, synced_contracts, synced_invoices,
        )


async def check_payment_plan_reminders() -> None:
    """
    Check all invoices with active payment plans for installments that are
    due today or overdue, and send reminder emails if not already sent recently.
    Runs every ~5 min as part of the periodic poller.
    """
    from datetime import date, timedelta
    from api.models.contract import Invoice
    from api.services.email_service import send_email, build_payment_reminder_email
    from api.routes.activity import log_activity

    today = date.today()

    async with async_session() as session:
        # Get all invoices with payment plans that aren't fully paid
        result = await session.execute(
            select(Invoice).where(
                Invoice.payment_plan_enabled == "true",
                Invoice.payment_status.notin_(["paid"]),
                Invoice.status.notin_(["cancelled", "paid"]),
            )
        )
        invoices = result.scalars().all()

        if not invoices:
            return

        reminders_sent = 0

        for inv in invoices:
            plan = list(inv.payment_plan or [])
            if not plan:
                continue

            plan_changed = False
            for inst in plan:
                if inst.get("status") != "pending":
                    continue

                # Parse due_date
                try:
                    due = date.fromisoformat(inst["due_date"])
                except (ValueError, KeyError):
                    continue

                # Mark overdue if past due
                if due < today and inst.get("status") == "pending":
                    inst["status"] = "overdue"
                    plan_changed = True

                # Check if reminder is needed: due today, or overdue
                # Skip if reminder was sent in the last 3 days
                if due <= today:
                    last_reminder = inst.get("reminder_sent_at")
                    if last_reminder:
                        try:
                            from datetime import datetime as _dt
                            lr = _dt.fromisoformat(last_reminder.replace("Z", "+00:00"))
                            if (datetime.now(timezone.utc) - lr).days < 3:
                                continue  # Reminder sent recently
                        except Exception:
                            pass

                    # Send reminder
                    inst_amount = float(inst.get("amount", 0))
                    remaining = float(inv.total_amount or 0) - float(inv.amount_paid or 0)

                    try:
                        subject, html = build_payment_reminder_email(
                            client_name=inv.client_name,
                            invoice_number=inv.invoice_number,
                            installment_amount=f"{inst_amount:.2f}",
                            due_date=inst.get("due_date", ""),
                            remaining_balance=f"{remaining:.2f}",
                            payment_method=inv.payment_method or "",
                        )
                        email_result = await send_email(
                            to=inv.client_email,
                            subject=subject,
                            body_html=html,
                        )
                        if email_result["success"]:
                            inst["reminder_sent_at"] = datetime.now(timezone.utc).isoformat()
                            plan_changed = True
                            reminders_sent += 1

                            await log_activity(
                                entity_type="invoice", entity_id=inv.invoice_number,
                                action="auto_reminder_sent", icon="🤖🔔",
                                description=f"Auto-reminder sent to {inv.client_email} — ${inst_amount:.2f} due {inst.get('due_date', '')}",
                                metadata={
                                    "installment_id": inst.get("id"),
                                    "amount": inst_amount,
                                    "due_date": inst.get("due_date"),
                                    "auto": True,
                                },
                            )
                    except Exception as e:
                        logger.warning("Failed to send auto-reminder for %s: %s", inv.invoice_number, e)

                    break  # Only send one reminder per invoice per cycle

            if plan_changed:
                inv.payment_plan = plan
                await session.commit()

        if reminders_sent:
            logger.info("🔔 Sent %d automatic payment reminder(s)", reminders_sent)


async def periodic_firebase_poll(interval: int = 60) -> None:
    """Poll Firebase for new leads, parse requests, and signatures every ``interval`` seconds.
    Every 5th cycle (~5 min) also re-syncs contracts/invoices Postgres → Firebase
    and checks for overdue payment plan installments that need reminders."""
    cycle = 0
    RESYNC_EVERY = 5  # cycles — re-sync contracts/invoices every ~5 min

    while True:
        try:
            await asyncio.sleep(interval)
            if not is_initialized():
                continue

            cycle += 1

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

            # Periodically re-sync contracts & invoices → Firebase mirror
            # and check for payment reminders
            if cycle % RESYNC_EVERY == 0:
                await reconcile_contracts_invoices_to_firebase()
                await check_payment_plan_reminders()

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
    from api.services.notify import send_telegram_contract_signed

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

            # Send notification to admin (email + Telegram)
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
                logger.warning("Failed to send signing email notification: %s", e)

            try:
                from datetime import timezone, timedelta
                cst = timezone(timedelta(hours=-6))
                now_cst = now.replace(tzinfo=timezone.utc).astimezone(cst)
                await send_telegram_contract_signed(
                    contract_id=contract.short_id,
                    client_name=contract.client_name,
                    project_name=contract.project_name,
                    total_amount=float(contract.total_amount or 0),
                    signer_name=signer_name,
                    signed_at=now_cst.strftime("%B %d, %Y at %I:%M %p CST"),
                )
            except Exception as e:
                logger.warning("Failed to send signing Telegram notification: %s", e)


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

        # Deploy RTDB security rules (idempotent)
        deploy_database_rules()

        # Reconcile any missed leads
        missed = await reconcile_firebase_leads()
        if missed:
            logger.info("🔄 Found %d unprocessed leads — queueing builds", len(missed))

        # Pick up any signatures submitted while we were offline
        await process_firebase_signatures()

        # Re-sync active contracts & invoices → Firebase mirror
        await reconcile_contracts_invoices_to_firebase()

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
