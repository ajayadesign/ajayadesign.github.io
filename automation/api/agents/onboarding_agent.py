"""
Onboarding Agent — Automated Client Welcome & Project Kickoff.

Welcomes new clients after contract signing. Currently a lightweight
implementation that logs onboarding readiness — full automation
(welcome emails, kickoff scheduling) pending service integrations.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, List

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import async_session_factory, async_session_factory as async_session
from api.models.prospect import Prospect
from api.models.contract import Contract
from api.config import settings

logger = logging.getLogger("agents.onboarding")


async def execute_onboarding_cycle(
    batch_size: int = 10,
) -> Dict[str, Any]:
    """
    Execute one Onboarding Agent cycle — check for signed contracts.

    Finds signed contracts and logs clients ready for onboarding.
    Full onboarding automation (emails, kickoff) pending service setup.
    """
    logger.info(f"[Onboarding] Starting cycle — batch_size={batch_size}")

    # Get signed contracts where prospect hasn't been moved to 'onboarding' yet
    signed_contracts: List[Contract] = []

    async with async_session() as session:
        stmt = (
            select(Contract)
            .where(
                Contract.status == "signed",
            )
            .limit(batch_size)
        )
        result = await session.execute(stmt)
        signed_contracts = list(result.scalars().all())

    if not signed_contracts:
        logger.info("[Onboarding] No signed contracts to process")
        return {
            "onboarded": 0,
            "welcome_emails_sent": 0,
            "kickoff_meetings_scheduled": 0,
            "log": "No new clients ready for onboarding",
        }

    logger.info(f"[Onboarding] Found {len(signed_contracts)} signed contracts")

    onboarded = 0

    for contract in signed_contracts:
        try:
            logger.info(
                f"[Onboarding] Client ready for onboarding: "
                f"{contract.client_name} ({contract.client_email}) "
                f"— ${float(contract.total_amount or 0):,.0f}"
            )
            onboarded += 1

        except Exception as e:
            logger.error(f"[Onboarding] Error processing {contract.client_name}: {e}", exc_info=True)

    log_output = (
        f"Onboarding Agent cycle completed:\n"
        f"  - Clients ready for onboarding: {onboarded}\n"
    )

    logger.info(log_output)

    return {
        "onboarded": onboarded,
        "welcome_emails_sent": 0,
        "kickoff_meetings_scheduled": 0,
        "log": log_output,
    }


async def get_onboarding_stats() -> Dict[str, Any]:
    """Get Onboarding Agent performance statistics."""
    async with async_session() as session:
        # Signed contracts (clients)
        stmt = select(func.count(Contract.id)).where(
            Contract.status == "signed"
        )
        result = await session.execute(stmt)
        total_signed = result.scalar() or 0

        # Active prospects in pipeline
        stmt = select(func.count(Prospect.id)).where(
            Prospect.status.in_(["replied", "meeting_scheduled"])
        )
        result = await session.execute(stmt)
        active_pipeline = result.scalar() or 0

    return {
        "total_clients": total_signed,
        "active_pipeline": active_pipeline,
    }
