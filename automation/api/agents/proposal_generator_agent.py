"""
Proposal Generator Agent — Autonomous Quote Creation.

Generates professional PDF proposals for qualified leads.
Analyzes project scope, estimates effort, calculates pricing.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import async_session_factory
from api.models.prospect import Prospect
from api.services.ai import call_ai, extract_json
from api.config import settings

logger = logging.getLogger("agents.proposal_generator")

# Proposal generation system prompt
PROPOSAL_SYSTEM_PROMPT = """You are a proposal generation AI for AjayaDesign web design agency.

Generate detailed project proposals based on prospect data and requirements.

OUTPUT FORMAT (JSON):
{
  "executive_summary": "2-3 sentence project overview",
  "deliverables": [
    {"item": "Homepage redesign", "hours": 12, "description": "Modern, mobile-responsive..."},
    {"item": "SEO optimization", "hours": 6, "description": "Meta tags, schema markup..."}
  ],
  "timeline_weeks": 4-12,
  "total_hours": sum of all deliverable hours,
  "recommended_price": total_hours * hourly_rate,
  "payment_schedule": [
    {"milestone": "Design approval", "percentage": 30},
    {"milestone": "Development complete", "percentage": 40},
    {"milestone": "Launch", "percentage": 30}
  ],
  "risks": ["Timeline depends on content provision", "Third-party integrations may add cost"],
  "assumptions": ["Client provides all content", "Hosting is client responsibility"]
}

PRICING GUIDE:
- Basic website (5 pages): 40-60 hours → $4,000-$6,000
- Medium site (10 pages + CMS): 80-120 hours → $8,000-$12,000
- Complex (e-commerce, integrations): 150+ hours → $15,000+
- Hourly rate: $100/hr

ALWAYS recommend payment schedules (not full upfront).
ALWAYS include risks and assumptions.
"""


async def execute_proposal_generator_cycle(
    batch_size: int = 5,
    ai_provider: str = "github-models",
) -> Dict[str, Any]:
    """
    Execute one Proposal Generator cycle — create quotes for qualified leads.

    Finds prospects with status='meeting_scheduled' (ready for proposal),
    generates detailed scope + pricing, creates Quote record.

    Args:
        batch_size: Max proposals to generate this cycle
        ai_provider: "github-models" or "anthropic"

    Returns:
        {
            "generated": int,
            "avg_quote_value": float,
            "cost": float,
            "log": str,
        }
    """
    logger.info(f"[ProposalGen] Starting cycle — batch_size={batch_size}")

    # Get prospects ready for proposals
    prospects_needing_proposals: List[Prospect] = []

    async with async_session() as session:
        stmt = (
            select(Prospect)
            .where(
                Prospect.status == "meeting_scheduled",
                # Don't generate if already have a quote
                ~Prospect.id.in_(
                    select(Quote.prospect_id).where(Quote.status != "declined")
                )
            )
            .order_by(Prospect.wp_score.desc())  # Prioritize high-value leads
            .limit(batch_size)
        )
        result = await session.execute(stmt)
        prospects_needing_proposals = list(result.scalars().all())

    if not prospects_needing_proposals:
        logger.info("[ProposalGen] No prospects ready for proposals")
        return {
            "generated": 0,
            "avg_quote_value": 0.0,
            "cost": 0.0,
            "log": "No prospects ready for proposal generation",
        }

    logger.info(f"[ProposalGen] Found {len(prospects_needing_proposals)} prospects needing proposals")

    generated = 0
    quote_values: List[float] = []
    total_cost = 0.0

    for prospect in prospects_needing_proposals:
        try:
            logger.info(f"[ProposalGen] Generating proposal for {prospect.business_name}")

            # Build proposal prompt
            proposal_prompt = f"""Generate a website proposal for:

PROSPECT:
- Business: {prospect.business_name}
- Type: {prospect.business_type}
- Location: {prospect.city}, {prospect.state}
- Current site: {prospect.website_url}

CURRENT SITE ANALYSIS:
- Performance score: {prospect.performance_score or 'Unknown'}/100
- Mobile-friendly: {'No' if prospect.mobile_friendly == False else 'Yes'}
- SSL: {'No' if prospect.ssl_valid == False else 'Yes'}
- Design era: {prospect.design_era or 'Outdated'}

PROJECT REQUIREMENTS (from meeting notes):
{prospect.project_notes or 'General website redesign'}

Generate a detailed proposal with scope, deliverables, timeline, and pricing."""

            # Call AI
            messages = [
                {"role": "system", "content": PROPOSAL_SYSTEM_PROMPT},
                {"role": "user", "content": proposal_prompt},
            ]

            ai_response = await call_ai(messages, provider=ai_provider)
            proposal_data = extract_json(ai_response)

            # Cost estimate (larger prompt, ~2K tokens)
            prop_cost = 0.006 if ai_provider == "anthropic" else 0.005
            total_cost += prop_cost

            # Create Quote record
            async with async_session() as session:
                from api.models.quote import Quote, QuoteItem

                quote = Quote(
                    prospect_id=prospect.id,
                    business_name=prospect.business_name,
                    contact_name=prospect.owner_name,
                    contact_email=prospect.owner_email,
                    title=f"Website Redesign Proposal - {prospect.business_name}",
                    executive_summary=proposal_data.get("executive_summary", ""),
                    total_price=proposal_data.get("recommended_price", 5000.00),
                    timeline_weeks=proposal_data.get("timeline_weeks", 8),
                    payment_schedule=proposal_data.get("payment_schedule", []),
                    risks=proposal_data.get("risks", []),
                    assumptions=proposal_data.get("assumptions", []),
                    status="draft",
                    generated_by="ai_agent",
                )
                session.add(quote)
                await session.flush()  # Get quote.id

                # Add deliverable line items
                for deliverable in proposal_data.get("deliverables", []):
                    item = QuoteItem(
                        quote_id=quote.id,
                        item_name=deliverable.get("item", ""),
                        description=deliverable.get("description", ""),
                        hours=deliverable.get("hours", 0),
                        rate=100.00,  # $100/hr
                        total=deliverable.get("hours", 0) * 100.00,
                    )
                    session.add(item)

                # Update prospect
                prospect_obj = await session.get(Prospect, prospect.id)
                if prospect_obj:
                    prospect_obj.status = "proposal_sent"
                    prospect_obj.last_proposal_at = datetime.now(timezone.utc)

                await session.commit()

            generated += 1
            quote_values.append(proposal_data.get("recommended_price", 0))

            logger.info(
                f"[ProposalGen] ✅ Generated ${proposal_data.get('recommended_price'):,.0f} "
                f"proposal for {prospect.business_name}"
            )

        except Exception as e:
            logger.error(f"[ProposalGen] Error generating proposal for {prospect.business_name}: {e}", exc_info=True)

    avg_quote_value = sum(quote_values) / len(quote_values) if quote_values else 0.0

    log_output = (
        f"Proposal Generator cycle completed:\n"
        f"  - Proposals generated: {generated}\n"
        f"  - Avg quote value: ${avg_quote_value:,.0f}\n"
        f"  - Total pipeline value: ${sum(quote_values):,.0f}\n"
        f"  - Cost: ${total_cost:.4f}\n"
    )

    logger.info(log_output)

    return {
        "generated": generated,
        "avg_quote_value": avg_quote_value,
        "cost": total_cost,
        "log": log_output,
    }


async def get_proposal_generator_stats() -> Dict[str, Any]:
    """Get Proposal Generator performance statistics."""
    async with async_session() as session:
        # Total proposals generated
        stmt = select(func.count(Quote.id)).where(
            Quote.generated_by == "ai_agent"
        )
        result = await session.execute(stmt)
        total_generated = result.scalar() or 0

        # Average quote value
        stmt = select(func.avg(Quote.total_price)).where(
            Quote.generated_by == "ai_agent"
        )
        result = await session.execute(stmt)
        avg_value = result.scalar() or 0.0

        # Acceptance rate
        stmt = select(func.count(Quote.id)).where(
            Quote.generated_by == "ai_agent",
            Quote.status == "accepted"
        )
        result = await session.execute(stmt)
        accepted = result.scalar() or 0

        acceptance_rate = (accepted / total_generated * 100) if total_generated > 0 else 0.0

    return {
        "total_proposals_generated": total_generated,
        "avg_quote_value": round(float(avg_value), 0),
        "acceptance_rate": round(acceptance_rate, 1),
    }
