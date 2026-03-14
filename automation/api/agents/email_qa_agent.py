"""
Email QA Agent — Quality Assurance for Outreach Emails.

Reviews generated emails before they're sent to prospects.
Checks for factual errors, grammar issues, CAN-SPAM compliance.
Can auto-approve high-quality emails or flag for human review.
"""

import logging
import re
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import async_session
from api.models.prospect import Prospect, OutreachEmail
from api.services.ai import call_ai, extract_json
from api.config import settings

logger = logging.getLogger("agents.email_qa")

# Email QA system prompt
EMAIL_QA_SYSTEM_PROMPT = """You are an email quality assurance expert reviewing outreach emails for a web design agency.

Review the email for:
1. FACTUAL ACCURACY - Are all claims about the prospect verifiable from the data provided?
2. GRAMMAR & SPELLING - Professional writing quality
3. PERSONALIZATION - Does it feel genuinely researched or templated?
4. CAN-SPAM COMPLIANCE - Includes business address, unsubscribe mechanism
5. TONE - Helpful, not salesy or pushy
6. CALL TO ACTION - Clear, single action requested

Return JSON:
{
  "approved": true/false,
  "confidence_score": 0.0-1.0,
  "issues": ["issue 1", "issue 2"],  // empty if approved
  "suggestions": ["suggestion 1"],    // improvements even if approved
  "reasoning": "Why approved or rejected"
}"""


async def execute_email_qa_cycle(
    batch_size: int = 30,
    auto_approve_threshold: float = 0.90,
    ai_provider: str = "github-models",
) -> Dict[str, Any]:
    """
    Execute one Email QA cycle — review queued emails for quality.

    Finds emails with status='queued' (generated but not reviewed),
    runs AI quality check, auto-approves high-quality or flags for human review.

    Args:
        batch_size: Maximum emails to review this cycle
        auto_approve_threshold: Confidence threshold for auto-approval (0.90 = 90%)
        ai_provider: "github-models" or "anthropic"

    Returns:
        {
            "reviewed": int,
            "auto_approved": int,
            "flagged": int,
            "avg_confidence": float,
            "cost": float,
            "log": str,
        }
    """
    logger.info(
        f"[EmailQA] Starting cycle — batch_size={batch_size}, "
        f"auto_approve_threshold={auto_approve_threshold}"
    )

    # Get queued emails
    emails_to_review: List[OutreachEmail] = []

    async with async_session() as session:
        stmt = (
            select(OutreachEmail)
            .where(OutreachEmail.status == "queued")
            .order_by(OutreachEmail.created_at.asc())  # FIFO
            .limit(batch_size)
        )
        result = await session.execute(stmt)
        emails_to_review = list(result.scalars().all())

    if not emails_to_review:
        logger.info("[EmailQA] No emails ready for review")
        return {
            "reviewed": 0,
            "auto_approved": 0,
            "flagged": 0,
            "avg_confidence": 0.0,
            "cost": 0.0,
            "log": "No emails ready for QA review",
        }

    logger.info(f"[EmailQA] Found {len(emails_to_review)} emails to review")

    reviewed = 0
    auto_approved = 0
    flagged = 0
    confidence_scores: List[float] = []
    total_cost = 0.0

    for email in emails_to_review:
        try:
            # Get prospect data for context
            async with async_session() as session:
                prospect = await session.get(Prospect, email.prospect_id)

            if not prospect:
                logger.warning(f"[EmailQA] Prospect {email.prospect_id} not found, skipping email {email.id}")
                continue

            logger.info(f"[EmailQA] Reviewing email to {prospect.business_name}")

            # Build review prompt
            review_prompt = f"""Review this outreach email:

PROSPECT DATA:
- Business: {prospect.business_name}
- Type: {prospect.business_type}
- Website: {prospect.website_url}
- Performance Score: {prospect.performance_score if hasattr(prospect, 'performance_score') else 'N/A'}
- WP Score: {prospect.wp_score}
- Owner Name: {prospect.owner_name or 'Unknown'}

EMAIL:
Subject: {email.subject}

{email.body}

Review for factual accuracy, grammar, personalization, compliance, and tone."""

            # Call AI for review
            messages = [
                {"role": "system", "content": EMAIL_QA_SYSTEM_PROMPT},
                {"role": "user", "content": review_prompt},
            ]

            ai_response = await call_ai(messages, provider=ai_provider)
            review_result = extract_json(ai_response)

            reviewed += 1
            confidence = review_result.get("confidence_score", 0.0)
            confidence_scores.append(confidence)
            approved = review_result.get("approved", False)

            # Calculate cost (rough estimate: 500 tokens input + 150 output = 650 tokens)
            # GPT-4o: $2.50/1M input, $10/1M output ≈ $0.0025 per email
            # Claude Sonnet: $3/1M input, $15/1M output ≈ $0.0030 per email
            email_cost = 0.003 if ai_provider == "anthropic" else 0.0025
            total_cost += email_cost

            # Update email status based on review
            async with async_session() as session:
                email_obj = await session.get(OutreachEmail, email.id)
                if email_obj:
                    email_obj.qa_reviewed = True
                    email_obj.qa_confidence = confidence
                    email_obj.qa_issues = review_result.get("issues", [])
                    email_obj.qa_suggestions = review_result.get("suggestions", [])

                    if approved and confidence >= auto_approve_threshold:
                        # Auto-approve high-quality emails
                        email_obj.status = "approved"
                        auto_approved += 1
                        logger.info(
                            f"[EmailQA] ✅ Auto-approved email to {prospect.business_name} "
                            f"(confidence: {confidence:.2f})"
                        )
                    else:
                        # Flag for human review
                        email_obj.status = "review_flagged"
                        flagged += 1
                        logger.info(
                            f"[EmailQA] ⚠️  Flagged email to {prospect.business_name} "
                            f"(confidence: {confidence:.2f}, issues: {len(review_result.get('issues', []))})"
                        )

                    await session.commit()

        except Exception as e:
            logger.error(f"[EmailQA] Error reviewing email {email.id}: {e}", exc_info=True)

    avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0

    log_output = (
        f"Email QA cycle completed:\n"
        f"  - Emails reviewed: {reviewed}\n"
        f"  - Auto-approved: {auto_approved}\n"
        f"  - Flagged for review: {flagged}\n"
        f"  - Avg confidence: {avg_confidence:.2f}\n"
        f"  - Cost: ${total_cost:.4f}\n"
    )

    logger.info(log_output)

    return {
        "reviewed": reviewed,
        "auto_approved": auto_approved,
        "flagged": flagged,
        "avg_confidence": avg_confidence,
        "cost": total_cost,
        "log": log_output,
    }


async def get_email_qa_stats() -> Dict[str, Any]:
    """Get Email QA Agent performance statistics."""
    async with async_session() as session:
        # Total reviewed
        stmt = select(func.count(OutreachEmail.id)).where(
            OutreachEmail.qa_reviewed == True
        )
        result = await session.execute(stmt)
        total_reviewed = result.scalar() or 0

        # Auto-approved rate
        stmt = select(func.count(OutreachEmail.id)).where(
            OutreachEmail.status == "approved",
            OutreachEmail.qa_reviewed == True
        )
        result = await session.execute(stmt)
        auto_approved = result.scalar() or 0

        # Flagged for review
        stmt = select(func.count(OutreachEmail.id)).where(
            OutreachEmail.status == "review_flagged"
        )
        result = await session.execute(stmt)
        flagged = result.scalar() or 0

        # Average QA confidence
        stmt = select(func.avg(OutreachEmail.qa_confidence)).where(
            OutreachEmail.qa_confidence.isnot(None)
        )
        result = await session.execute(stmt)
        avg_confidence = result.scalar() or 0.0

    auto_approve_rate = (auto_approved / total_reviewed * 100) if total_reviewed > 0 else 0.0

    return {
        "total_reviewed": total_reviewed,
        "auto_approved": auto_approved,
        "flagged": flagged,
        "avg_confidence": round(float(avg_confidence), 2),
        "auto_approve_rate": round(auto_approve_rate, 1),
    }
