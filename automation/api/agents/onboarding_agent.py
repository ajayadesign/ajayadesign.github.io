"""
Onboarding Agent — Automated Client Welcome & Project Kickoff.

Welcomes new clients after contract signing, sends welcome packet,
collects requirements, schedules kickoff meeting, sets up project infrastructure.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import async_session_factory
from api.models.prospect import Prospect
from api.config import settings

logger = logging.getLogger("agents.onboarding")


async def execute_onboarding_cycle(
    batch_size: int = 10,
) -> Dict[str, Any]:
    """
    Execute one Onboarding Agent cycle — welcome new clients.

    Finds prospects with status='client' (contract signed, not yet onboarded),
    sends welcome packet, collects requirements, schedules kickoff.

    Args:
        batch_size: Max clients to onboard this cycle

    Returns:
        {
            "onboarded": int,
            "welcome_emails_sent": int,
            "kickoff_meetings_scheduled": int,
            "log": str,
        }
    """
    logger.info(f"[Onboarding] Starting cycle — batch_size={batch_size}")

    # Get new clients needing onboarding
    new_clients: List[Prospect] = []

    async with async_session() as session:
        stmt = (
            select(Prospect)
            .where(
                Prospect.status == "client",
                Prospect.onboarded_at.is_(None),
            )
            .order_by(Prospect.deal_closed_at.desc())
            .limit(batch_size)
        )
        result = await session.execute(stmt)
        new_clients = list(result.scalars().all())

    if not new_clients:
        logger.info("[Onboarding] No new clients to onboard")
        return {
            "onboarded": 0,
            "welcome_emails_sent": 0,
            "kickoff_meetings_scheduled": 0,
            "log": "No new clients ready for onboarding",
        }

    logger.info(f"[Onboarding] Found {len(new_clients)} new clients to onboard")

    onboarded = 0
    welcome_emails_sent = 0
    kickoff_meetings_scheduled = 0

    for client in new_clients:
        try:
            logger.info(f"[Onboarding] Onboarding {client.business_name}")

            async with async_session() as session:
                # Get client's contract
                stmt = select(Contract).where(
                    Contract.prospect_id == client.id,
                    Contract.status == "signed"
                ).order_by(Contract.signed_at.desc())
                result = await session.execute(stmt)
                contract = result.scalar_one_or_none()

                if not contract:
                    continue

                # Step 1: Send welcome email
                await _send_welcome_email(client, contract)
                welcome_emails_sent += 1

                # Step 2: Schedule kickoff meeting (3-5 days out)
                kickoff_scheduled = await _schedule_kickoff_meeting(client)
                if kickoff_scheduled:
                    kickoff_meetings_scheduled += 1

                # Step 3: Create project infrastructure
                await _setup_project_infrastructure(client, contract)

                # Step 4: Send requirement collection form
                await _send_requirement_form(client)

                # Update client status
                client_obj = await session.get(Prospect, client.id)
                if client_obj:
                    client_obj.status = "onboarding"
                    client_obj.onboarded_at = datetime.now(timezone.utc)

                onboarded += 1

                await session.commit()

                logger.info(f"[Onboarding] ✅ Onboarded {client.business_name}")

        except Exception as e:
            logger.error(f"[Onboarding] Error onboarding {client.business_name}: {e}", exc_info=True)

    log_output = (
        f"Onboarding Agent cycle completed:\n"
        f"  - Clients onboarded: {onboarded}\n"
        f"  - Welcome emails sent: {welcome_emails_sent}\n"
        f"  - Kickoff meetings scheduled: {kickoff_meetings_scheduled}\n"
    )

    logger.info(log_output)

    return {
        "onboarded": onboarded,
        "welcome_emails_sent": welcome_emails_sent,
        "kickoff_meetings_scheduled": kickoff_meetings_scheduled,
        "log": log_output,
    }


async def _send_welcome_email(client: Prospect, contract: "Contract"):
    """Send welcome email to new client."""
    from api.services.email_service import send_email

    subject = f"Welcome to AjayaDesign! Let's build your website 🎉"
    body = f"""Hi {client.owner_name},

Welcome aboard! I'm thrilled to work on {client.business_name}'s new website.

Here's what happens next:

📅 KICKOFF MEETING
I'll send a calendar invite for our kickoff meeting this week. We'll discuss:
- Your vision and goals
- Target audience insights
- Design preferences
- Content strategy

📝 REQUIREMENT FORM
Please fill out this quick form (5 minutes):
https://ajayadesign.com/client-intake/{client.id}

This helps me understand your business better before our kickoff.

💰 DEPOSIT INVOICE
I'll send your deposit invoice ({contract.payment_schedule[0]['percentage']}%) shortly.
Once received, I'll officially add you to my schedule.

🛠️ PROJECT PORTAL
I've set up your project portal:
https://ajayadesign.com/projects/{client.id}

You can track progress, review designs, and provide feedback here.

📧 QUESTIONS?
Just reply to this email!

Super excited to build something amazing together.

Best,
Ajaya Dahal
AjayaDesign

P.S. Expected timeline: {contract.timeline_weeks} weeks from deposit to launch.
"""

    await send_email(
        to_email=client.owner_email,
        subject=subject,
        body=body,
    )

    logger.info(f"[Onboarding] Sent welcome email to {client.business_name}")


async def _schedule_kickoff_meeting(client: Prospect) -> bool:
    """Schedule kickoff meeting (Calendly or manual)."""
    from api.services.email_service import send_email

    # Send Calendly link for kickoff
    kickoff_date = datetime.now(timezone.utc) + timedelta(days=3)

    subject = f"Kickoff meeting - {client.business_name} website"
    body = f"""Hi {client.owner_name},

Let's schedule our project kickoff meeting!

I have availability this week. Book a time that works for you:
https://calendly.com/ajayadesign/kickoff-meeting

Or let me know your preferred day/time and I'll send a calendar invite.

Looking forward to it!

Best,
Ajaya
"""

    await send_email(
        to_email=client.owner_email,
        subject=subject,
        body=body,
    )

    logger.info(f"[Onboarding] Sent kickoff scheduling to {client.business_name}")
    return True


async def _setup_project_infrastructure(client: Prospect, contract: "Contract"):
    """Set up project infrastructure (repo, folder, tools)."""
    # Create GitHub repo for client project
    from api.services.git import create_repository

    repo_name = client.business_name.lower().replace(" ", "-")

    try:
        repo_url = await create_repository(
            name=repo_name,
            description=f"Website project for {client.business_name}",
            private=True,
        )

        logger.info(f"[Onboarding] Created repo for {client.business_name}: {repo_url}")
    except Exception as e:
        logger.warning(f"[Onboarding] Could not create repo for {client.business_name}: {e}")

    # Create project folder in file system
    # Create Notion/Trello board (if integrated)
    # Add to project management tool


async def _send_requirement_form(client: Prospect):
    """Send requirement collection form link."""
    from api.services.email_service import send_email

    subject = f"Quick intake form - {client.business_name}"
    body = f"""Hi {client.owner_name},

Before our kickoff, please fill out this quick intake form:
https://ajayadesign.com/client-intake/{client.id}

It covers:
- Business goals and target audience
- Design preferences (colors, fonts, examples you like)
- Content you have ready
- Must-have features

Takes about 5 minutes and helps me come prepared!

Thanks,
Ajaya
"""

    await send_email(
        to_email=client.owner_email,
        subject=subject,
        body=body,
    )


async def get_onboarding_stats() -> Dict[str, Any]:
    """Get Onboarding Agent performance statistics."""
    async with async_session() as session:
        # Total clients onboarded
        stmt = select(func.count(Prospect.id)).where(
            Prospect.onboarded_at.isnot(None)
        )
        result = await session.execute(stmt)
        total_onboarded = result.scalar() or 0

        # Active projects
        stmt = select(func.count(Prospect.id)).where(
            Prospect.status.in_(["onboarding", "in_progress"])
        )
        result = await session.execute(stmt)
        active_projects = result.scalar() or 0

        # Completed projects
        stmt = select(func.count(Prospect.id)).where(
            Prospect.status == "completed"
        )
        result = await session.execute(stmt)
        completed_projects = result.scalar() or 0

    return {
        "total_onboarded": total_onboarded,
        "active_projects": active_projects,
        "completed_projects": completed_projects,
    }
