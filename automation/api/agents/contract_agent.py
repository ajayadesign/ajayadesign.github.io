"""
Contract Agent — Autonomous Contract Generation & Signing.

Generates contracts for accepted proposals, sends signing links,
tracks signatures, and notifies when deals are closed.
"""

import logging
import secrets as _secrets
from datetime import datetime, timezone
from typing import Dict, Any, List

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import async_session_factory, async_session_factory as async_session
from api.models.prospect import Prospect
from api.models.quote import Quote
from api.models.contract import Contract
from api.config import settings

logger = logging.getLogger("agents.contract")


async def execute_contract_cycle(
    batch_size: int = 10,
    use_docusign: bool = False,  # Reserved for future DocuSign integration
) -> Dict[str, Any]:
    """
    Execute one Contract Agent cycle — send contracts for accepted/approved quotes.

    Finds approved quotes and creates Contract records.
    """
    logger.info(f"[Contract] Starting cycle — batch_size={batch_size}")

    # Get approved quotes that don't already have a contract
    quotes_needing_contracts: List[Quote] = []

    async with async_session() as session:
        # Find quotes with status='approved' that don't have a matching contract yet
        existing_contracts_emails = select(Contract.client_email).where(
            Contract.status != "cancelled"
        )
        stmt = (
            select(Quote)
            .where(
                Quote.status == "approved",
                ~Quote.client_email.in_(existing_contracts_emails),
            )
            .limit(batch_size)
        )
        result = await session.execute(stmt)
        quotes_needing_contracts = list(result.scalars().all())

    if not quotes_needing_contracts:
        logger.info("[Contract] No approved quotes ready for contracts")
        return {
            "contracts_sent": 0,
            "contracts_signed": 0,
            "deals_closed": 0,
            "total_deal_value": 0.0,
            "log": "No accepted proposals ready for contract",
        }

    logger.info(f"[Contract] Found {len(quotes_needing_contracts)} quotes needing contracts")

    contracts_sent = 0
    total_deal_value = 0.0

    for quote in quotes_needing_contracts:
        try:
            logger.info(f"[Contract] Processing contract for {quote.client_name}")

            async with async_session() as session:
                short_id = _secrets.token_hex(4)[:8]

                contract = Contract(
                    short_id=short_id,
                    client_name=quote.client_name,
                    client_email=quote.client_email,
                    project_name=quote.project_name,
                    project_description=quote.project_description or "",
                    total_amount=quote.total_amount,
                    payment_terms=quote.payment_schedule or "",
                    status="draft",
                )
                session.add(contract)
                await session.commit()

                contracts_sent += 1
                total_deal_value += float(quote.total_amount or 0)

                logger.info(f"[Contract] ✅ Created contract for {quote.client_name}")

        except Exception as e:
            logger.error(f"[Contract] Error processing contract for {quote.client_name}: {e}", exc_info=True)

    # Check for newly signed contracts
    contracts_signed = 0
    deals_closed = 0

    async with async_session() as session:
        stmt = select(Contract).where(
            Contract.status == "signed",
        )
        result = await session.execute(stmt)
        signed_contracts = list(result.scalars().all())

        for contract in signed_contracts:
            contracts_signed += 1
            deals_closed += 1
            total_deal_value += float(contract.total_amount or 0)
            logger.info(f"[Contract] 🎉 Deal signed: {contract.client_name} - ${float(contract.total_amount):,.0f}")

    log_output = (
        f"Contract Agent cycle completed:\n"
        f"  - Contracts created: {contracts_sent}\n"
        f"  - Contracts signed: {contracts_signed}\n"
        f"  - Deals closed: {deals_closed}\n"
        f"  - Total deal value: ${total_deal_value:,.0f}\n"
    )

    logger.info(log_output)

    return {
        "contracts_sent": contracts_sent,
        "contracts_signed": contracts_signed,
        "deals_closed": deals_closed,
        "total_deal_value": total_deal_value,
        "log": log_output,
    }


async def get_contract_stats() -> Dict[str, Any]:
    """Get Contract Agent performance statistics."""
    async with async_session() as session:
        # Total contracts
        stmt = select(func.count(Contract.id))
        result = await session.execute(stmt)
        total_contracts = result.scalar() or 0

        # Signed contracts
        stmt = select(func.count(Contract.id)).where(
            Contract.status == "signed"
        )
        result = await session.execute(stmt)
        signed = result.scalar() or 0

        # Total deal value from signed
        stmt = select(func.sum(Contract.total_amount)).where(
            Contract.status == "signed"
        )
        result = await session.execute(stmt)
        total_closed_value = result.scalar() or 0.0

        signing_rate = (signed / total_contracts * 100) if total_contracts > 0 else 0.0

    return {
        "total_contracts_sent": total_contracts,
        "signed_contracts": signed,
        "signing_rate": round(signing_rate, 1),
        "total_closed_value": round(float(total_closed_value), 0),
    }
