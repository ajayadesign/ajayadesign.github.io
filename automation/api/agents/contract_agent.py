"""
Contract Agent — Autonomous Contract Generation & Signing.

Generates contracts for accepted proposals, sends DocuSign links,
tracks signatures, and notifies when deals are closed.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import async_session_factory
from api.models.prospect import Prospect
from api.config import settings

logger = logging.getLogger("agents.contract")

async def execute_contract_cycle(
    batch_size: int = 10,
    use_docusign: bool = False,  # Set to True when DocuSign configured
) -> Dict[str, Any]:
    """
    Execute one Contract Agent cycle — send contracts for accepted quotes.

    Finds prospects with status='proposal_accepted' (quote approved),
    generates contract, sends for signature (DocuSign or email).

    Args:
        batch_size: Max contracts to process this cycle
        use_docusign: Use DocuSign API (requires configuration)

    Returns:
        {
            "contracts_sent": int,
            "contracts_signed": int,
            "deals_closed": int,
            "total_deal_value": float,
            "log": str,
        }
    """
    logger.info(f"[Contract] Starting cycle — batch_size={batch_size}")

    # Get prospects with accepted proposals
    prospects_needing_contracts: List[Prospect] = []

    async with async_session() as session:
        stmt = (
            select(Prospect)
            .join(Quote, Prospect.id == Quote.prospect_id)
            .where(
                Quote.status == "accepted",
                Prospect.status == "proposal_accepted",
            )
            .limit(batch_size)
        )
        result = await session.execute(stmt)
        prospects_needing_contracts = list(result.scalars().all())

    if not prospects_needing_contracts:
        logger.info("[Contract] No prospects ready for contracts")
        return {
            "contracts_sent": 0,
            "contracts_signed": 0,
            "deals_closed": 0,
            "total_deal_value": 0.0,
            "log": "No accepted proposals ready for contract",
        }

    logger.info(f"[Contract] Found {len(prospects_needing_contracts)} prospects needing contracts")

    contracts_sent = 0
    contracts_signed = 0
    deals_closed = 0
    total_deal_value = 0.0

    for prospect in prospects_needing_contracts:
        try:
            logger.info(f"[Contract] Processing contract for {prospect.business_name}")

            # Get the accepted quote
            async with async_session() as session:
                stmt = select(Quote).where(
                    Quote.prospect_id == prospect.id,
                    Quote.status == "accepted"
                ).order_by(Quote.created_at.desc())
                result = await session.execute(stmt)
                quote = result.scalar_one_or_none()

                if not quote:
                    continue

                # Create contract from existing template
                from api.models.contract import Contract

                contract = Contract(
                    prospect_id=prospect.id,
                    quote_id=quote.id,
                    business_name=prospect.business_name,
                    contact_name=prospect.owner_name,
                    contact_email=prospect.owner_email,
                    project_scope=quote.executive_summary,
                    total_value=quote.total_price,
                    payment_schedule=quote.payment_schedule,
                    deliverables=quote.deliverables,
                    timeline_weeks=quote.timeline_weeks,
                    status="pending_signature",
                    generated_by="ai_agent",
                )
                session.add(contract)
                await session.flush()

                # Send contract for signature
                if use_docusign:
                    # DocuSign integration (requires setup)
                    docusign_url = await _send_docusign(contract)
                    contract.docusign_envelope_id = docusign_url
                else:
                    # Email-based signature (existing flow)
                    await _send_contract_email(contract)

                contracts_sent += 1

                # Update prospect status
                prospect_obj = await session.get(Prospect, prospect.id)
                if prospect_obj:
                    prospect_obj.status = "contract_sent"

                await session.commit()

                logger.info(f"[Contract] ✅ Sent contract to {prospect.business_name}")

        except Exception as e:
            logger.error(f"[Contract] Error processing contract for {prospect.business_name}: {e}", exc_info=True)

    # Check for newly signed contracts (separate query)
    async with async_session() as session:
        stmt = select(Contract).where(
            Contract.status == "signed",
            Contract.deal_closed_at.is_(None),  # Not yet processed
        )
        result = await session.execute(stmt)
        signed_contracts = list(result.scalars().all())

        for contract in signed_contracts:
            # Mark deal as closed
            contract.deal_closed_at = datetime.now(timezone.utc)
            total_deal_value += contract.total_value
            contracts_signed += 1
            deals_closed += 1

            # Update prospect
            prospect = await session.get(Prospect, contract.prospect_id)
            if prospect:
                prospect.status = "client"
                prospect.deal_value = contract.total_value
                prospect.deal_closed_at = datetime.now(timezone.utc)

            # Send to Onboarding Agent (Phase 3)
            logger.info(f"[Contract] 🎉 Deal closed: {contract.business_name} - ${contract.total_value:,.0f}")

        await session.commit()

    log_output = (
        f"Contract Agent cycle completed:\n"
        f"  - Contracts sent: {contracts_sent}\n"
        f"  - Contracts signed: {contracts_signed}\n"
        f"  - Deals closed: {deals_closed} 🎉\n"
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


async def _send_docusign(contract: "Contract") -> str:
    """Send contract via DocuSign API (requires setup)."""
    # Placeholder for DocuSign integration
    # Requires: DOCUSIGN_API_KEY, DOCUSIGN_ACCOUNT_ID in settings
    logger.warning("[Contract] DocuSign not configured, using email fallback")
    return ""


async def _send_contract_email(contract: "Contract"):
    """Send contract via email with signing link."""
    from api.services.email_service import send_email

    subject = f"Contract for {contract.business_name} website project"
    body = f"""Hi {contract.contact_name},

Excited to work together! I've prepared your project contract.

Project: {contract.project_scope}
Investment: ${contract.total_value:,.0f}
Timeline: {contract.timeline_weeks} weeks

Please review and sign here:
https://ajayadesign.com/sign/{contract.id}

Once signed, I'll send deposit invoice and we'll get started!

Best,
Ajaya Dahal
AjayaDesign
"""

    await send_email(
        to_email=contract.contact_email,
        subject=subject,
        body=body,
    )

    logger.info(f"[Contract] Sent contract email to {contract.business_name}")


async def get_contract_stats() -> Dict[str, Any]:
    """Get Contract Agent performance statistics."""
    async with async_session() as session:
        # Total contracts generated
        stmt = select(func.count(Contract.id)).where(
            Contract.generated_by == "ai_agent"
        )
        result = await session.execute(stmt)
        total_contracts = result.scalar() or 0

        # Signed contracts
        stmt = select(func.count(Contract.id)).where(
            Contract.generated_by == "ai_agent",
            Contract.status == "signed"
        )
        result = await session.execute(stmt)
        signed = result.scalar() or 0

        # Total deal value closed
        stmt = select(func.sum(Contract.total_value)).where(
            Contract.status == "signed",
            Contract.deal_closed_at.isnot(None)
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
