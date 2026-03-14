"""
Copywriter Agent — Email Generation Wrapper.

Wraps the existing template_engine.py service for Paperclip orchestration.
Generates personalized outreach emails using AI (GPT-4o or Claude).
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import async_session
from api.models.prospect import Prospect, OutreachEmail
from api.services.template_engine import compose_email
from api.config import settings

logger = logging.getLogger("agents.copywriter")


async def execute_copywriter_cycle(
    min_wp_score: int = 60,
    batch_size: int = 20,
    ai_provider: str = "github-models",
    budget_limit: float = 100.0,
) -> Dict[str, Any]:
    """
    Execute one Copywriter Agent cycle — generate personalized emails.

    Finds prospects with status='scored' and wp_score >= min_wp_score,
    generates unique email copy using AI, creates OutreachEmail records.

    Args:
        min_wp_score: Minimum WP score to qualify for outreach (0-100)
        batch_size: Maximum emails to generate this cycle
        ai_provider: "github-models" (GPT-4o) or "anthropic" (Claude)
        budget_limit: Max USD to spend on AI this cycle

    Returns:
        {
            "count": int,               # Emails generated
            "avg_confidence": float,    # Avg AI confidence score
            "tokens": int,              # Total tokens used
            "cost": float,              # USD spent
            "avg_wp_score": float,      # Avg WP score of prospects
            "log": str,                 # Execution summary
        }
    """
    logger.info(
        f"[Copywriter] Starting cycle — min_wp_score={min_wp_score}, "
        f"batch_size={batch_size}, ai_provider={ai_provider}"
    )

    # Find prospects ready for email generation
    prospects_to_email: List[Prospect] = []

    async with async_session() as session:
        # Get prospects that:
        # 1. Have wp_score >= min_wp_score
        # 2. Status = 'scored' (enriched + scored, not yet contacted)
        # 3. Have valid email OR we can generate one
        # 4. Not already in outreach queue
        stmt = (
            select(Prospect)
            .where(
                and_(
                    Prospect.status == "scored",
                    Prospect.wp_score >= min_wp_score,
                    Prospect.owner_email.isnot(None),
                )
            )
            .order_by(Prospect.wp_score.desc())  # Prioritize high scores
            .limit(batch_size)
        )
        result = await session.execute(stmt)
        prospects_to_email = list(result.scalars().all())

    if not prospects_to_email:
        logger.info(f"[Copywriter] No prospects qualify (wp_score >= {min_wp_score})")
        return {
            "count": 0,
            "avg_confidence": 0.0,
            "tokens": 0,
            "cost": 0.0,
            "avg_wp_score": 0.0,
            "log": f"No prospects with wp_score >= {min_wp_score} ready for outreach",
        }

    logger.info(f"[Copywriter] Found {len(prospects_to_email)} prospects to email")

    emails_generated = 0
    total_tokens = 0
    total_cost = 0.0
    confidence_scores: List[float] = []
    wp_scores: List[float] = []

    for prospect in prospects_to_email:
        # Budget check (stop if exceeded)
        if total_cost >= budget_limit:
            logger.warning(f"[Copywriter] Budget limit reached: ${total_cost:.2f}")
            break

        try:
            logger.info(
                f"[Copywriter] Generating email for {prospect.business_name} "
                f"(wp_score: {prospect.wp_score})"
            )

            # Generate email using existing template engine
            email_result = await compose_email(
                prospect_id=str(prospect.id),
                sequence_step=1,  # Initial outreach
            )

            if email_result:
                emails_generated += 1
                # Estimate cost (rough approximation)
                total_cost += 0.01  # Approximate cost per email

                wp_scores.append(prospect.wp_score or 0)

                # Update prospect status
                async with async_session() as session:
                    prospect = await session.get(Prospect, prospect.id)
                    if prospect:
                        prospect.status = "queued"  # Ready for manual approval
                        await session.commit()

            else:
                logger.warning(
                    f"[Copywriter] Failed to generate email for {prospect.business_name}: "
                    f"{email_result.get('error')}"
                )

        except Exception as e:
            logger.error(
                f"[Copywriter] Error generating email for {prospect.business_name}: {e}",
                exc_info=True,
            )

    avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
    avg_wp_score = sum(wp_scores) / len(wp_scores) if wp_scores else 0.0

    log_output = (
        f"Copywriter cycle completed:\n"
        f"  - Prospects processed: {len(prospects_to_email)}\n"
        f"  - Emails generated: {emails_generated}\n"
        f"  - Avg WP score: {avg_wp_score:.1f}\n"
        f"  - Avg confidence: {avg_confidence:.2f}\n"
        f"  - AI provider: {ai_provider}\n"
        f"  - Tokens used: {total_tokens:,}\n"
        f"  - Cost: ${total_cost:.4f}\n"
    )

    logger.info(log_output)

    return {
        "count": emails_generated,
        "avg_confidence": avg_confidence,
        "tokens": total_tokens,
        "cost": total_cost,
        "avg_wp_score": avg_wp_score,
        "log": log_output,
    }


async def get_copywriter_stats() -> Dict[str, Any]:
    """Get Copywriter Agent performance statistics."""
    async with async_session() as session:
        # Total emails generated
        stmt = select(func.count(OutreachEmail.id))
        result = await session.execute(stmt)
        total_emails = result.scalar() or 0

        # Emails generated today
        stmt = select(func.count(OutreachEmail.id)).where(
            OutreachEmail.created_at >= datetime.now(timezone.utc).replace(hour=0, minute=0, second=0)
        )
        result = await session.execute(stmt)
        emails_today = result.scalar() or 0

        # Emails awaiting approval
        stmt = select(func.count(OutreachEmail.id)).where(
            OutreachEmail.status == "queued"
        )
        result = await session.execute(stmt)
        awaiting_approval = result.scalar() or 0

        # Prospects ready for email (scored, not contacted)
        stmt = select(func.count(Prospect.id)).where(
            Prospect.status == "scored",
            Prospect.wp_score >= 60,
            Prospect.owner_email.isnot(None),
        )
        result = await session.execute(stmt)
        prospects_ready = result.scalar() or 0

    return {
        "total_emails_generated": total_emails,
        "emails_today": emails_today,
        "awaiting_approval": awaiting_approval,
        "prospects_ready": prospects_ready,
    }
