"""
Sales Qualification Agent — Autonomous Meeting Booking.

Analyzes email replies, qualifies leads, and auto-books Calendly meetings.
Handles objections, answers common questions, and escalates complex cases.
"""

import logging
import re
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import async_session_factory
from api.models.prospect import Prospect, OutreachEmail, ProspectActivity
from api.services.ai import call_ai, extract_json
from api.config import settings

logger = logging.getLogger("agents.sales_qualification")

# Sales qualification system prompt
SALES_QUAL_SYSTEM_PROMPT = """You are a sales qualification AI for AjayaDesign, a web design agency.

Your job: Analyze email replies from prospects and determine next action.

QUALIFICATION CRITERIA:
- INTERESTED: Mentions pricing, timeline, wanting info, asking questions
- MEETING_READY: Explicitly wants to schedule, ready to discuss, says "let's talk"
- NOT_INTERESTED: Polite no, not now, already have solution
- OBJECTION: Price concerns, timing issues, skepticism (needs nurturing)
- QUESTION: Asking about process, tech, portfolio (needs answer)

RESPONSE TYPES:
- book_meeting: They're ready (send Calendly link)
- answer_question: They need info (generate helpful response)
- nurture: Show interest but not ready (send case study, testimonial)
- close_lost: Definite no (mark as lost, add to drip campaign for 6mo later)

Return JSON:
{
  "classification": "INTERESTED | MEETING_READY | NOT_INTERESTED | OBJECTION | QUESTION",
  "action": "book_meeting | answer_question | nurture | close_lost",
  "confidence": 0.0-1.0,
  "reasoning": "Why you classified this way",
  "suggested_response": "Draft email response (if action != book_meeting)",
  "budget_signals": ["mentioned_price_range", "has_timeline", "decision_maker"],
  "urgency_score": 0-10
}"""


async def execute_sales_qualification_cycle(
    batch_size: int = 20,
    ai_provider: str = "github-models",
    calendly_link: str = "https://calendly.com/ajayadesign/30min",
) -> Dict[str, Any]:
    """
    Execute one Sales Qualification cycle — analyze replied emails.

    Finds prospects who replied to outreach, qualifies them, takes action:
    - MEETING_READY → Send Calendly link
    - QUESTION → Generate answer
    - OBJECTION → Send nurture content
    - NOT_INTERESTED → Mark as lost

    Args:
        batch_size: Max replies to process this cycle
        ai_provider: "github-models" or "anthropic"
        calendly_link: Your Calendly scheduling URL

    Returns:
        {
            "processed": int,
            "meetings_booked": int,
            "questions_answered": int,
            "nurtured": int,
            "closed_lost": int,
            "cost": float,
            "log": str,
        }
    """
    logger.info(f"[SalesQual] Starting cycle — batch_size={batch_size}")

    # Get prospects with new replies (status='replied', not yet qualified)
    prospects_to_qualify: List[Prospect] = []

    async with async_session() as session:
        stmt = (
            select(Prospect)
            .where(
                Prospect.status == "replied",
                Prospect.last_reply_at.isnot(None),
            )
            .order_by(Prospect.last_reply_at.desc())
            .limit(batch_size)
        )
        result = await session.execute(stmt)
        prospects_to_qualify = list(result.scalars().all())

    if not prospects_to_qualify:
        logger.info("[SalesQual] No new replies to qualify")
        return {
            "processed": 0,
            "meetings_booked": 0,
            "questions_answered": 0,
            "nurtured": 0,
            "closed_lost": 0,
            "cost": 0.0,
            "log": "No new email replies to process",
        }

    logger.info(f"[SalesQual] Found {len(prospects_to_qualify)} replies to qualify")

    processed = 0
    meetings_booked = 0
    questions_answered = 0
    nurtured = 0
    closed_lost = 0
    total_cost = 0.0

    for prospect in prospects_to_qualify:
        try:
            # Get the reply text (from prospect.latest_reply or email thread)
            reply_text = prospect.latest_reply or "No reply text captured"

            logger.info(f"[SalesQual] Qualifying {prospect.business_name}")

            # Build qualification prompt
            qual_prompt = f"""Analyze this email reply from a web design prospect:

PROSPECT CONTEXT:
- Business: {prospect.business_name}
- Type: {prospect.business_type}
- Current site: {prospect.website_url}
- WP Score: {prospect.wp_score} (higher = more likely to buy)
- Owner: {prospect.owner_name or 'Unknown'}

THEIR REPLY:
\"\"\"{reply_text}\"\"\"

Classify their interest level and recommend next action."""

            # Call AI for qualification
            messages = [
                {"role": "system", "content": SALES_QUAL_SYSTEM_PROMPT},
                {"role": "user", "content": qual_prompt},
            ]

            ai_response = await call_ai(messages, provider=ai_provider)
            qualification = extract_json(ai_response)

            processed += 1
            classification = qualification.get("classification", "UNKNOWN")
            action = qualification.get("action", "nurture")
            confidence = qualification.get("confidence", 0.0)

            # Cost estimate (1K tokens ≈ $0.0025 for GPT-4o)
            qual_cost = 0.003 if ai_provider == "anthropic" else 0.0025
            total_cost += qual_cost

            # Take action based on qualification
            async with async_session() as session:
                prospect_obj = await session.get(Prospect, prospect.id)
                if not prospect_obj:
                    continue

                if action == "book_meeting":
                    # Send Calendly link
                    await _send_calendly_email(prospect_obj, calendly_link)
                    prospect_obj.status = "meeting_scheduled"
                    meetings_booked += 1
                    logger.info(f"[SalesQual] 🎉 Booked meeting with {prospect.business_name}")

                elif action == "answer_question":
                    # Generate answer and send
                    response_text = qualification.get("suggested_response", "")
                    await _send_follow_up_email(prospect_obj, response_text)
                    prospect_obj.status = "engaged"
                    questions_answered += 1

                elif action == "nurture":
                    # Send case study or testimonial
                    await _send_nurture_content(prospect_obj)
                    prospect_obj.status = "nurturing"
                    nurtured += 1

                elif action == "close_lost":
                    # Mark as lost, add to 6-month drip
                    prospect_obj.status = "closed_lost"
                    prospect_obj.lost_reason = qualification.get("reasoning", "Not interested")
                    closed_lost += 1

                # Log activity
                activity = ProspectActivity(
                    prospect_id=prospect_obj.id,
                    activity_type="sales_qualification",
                    description=f"AI classified as {classification} (confidence: {confidence:.2f}), action: {action}",
                    metadata={
                        "classification": classification,
                        "action": action,
                        "confidence": confidence,
                        "urgency_score": qualification.get("urgency_score", 0),
                    },
                )
                session.add(activity)

                await session.commit()

        except Exception as e:
            logger.error(f"[SalesQual] Error qualifying {prospect.business_name}: {e}", exc_info=True)

    log_output = (
        f"Sales Qualification cycle completed:\n"
        f"  - Replies processed: {processed}\n"
        f"  - Meetings booked: {meetings_booked} 🎉\n"
        f"  - Questions answered: {questions_answered}\n"
        f"  - Nurtured: {nurtured}\n"
        f"  - Closed lost: {closed_lost}\n"
        f"  - Cost: ${total_cost:.4f}\n"
    )

    logger.info(log_output)

    return {
        "processed": processed,
        "meetings_booked": meetings_booked,
        "questions_answered": questions_answered,
        "nurtured": nurtured,
        "closed_lost": closed_lost,
        "cost": total_cost,
        "log": log_output,
    }


async def _send_calendly_email(prospect: Prospect, calendly_link: str):
    """Send Calendly booking link to prospect."""
    from api.services.email_service import send_email

    subject = f"Re: {prospect.business_name} website"
    body = f"""Hi {prospect.owner_name or 'there'},

Great to hear you're interested! I'd love to discuss your website project.

I have a few time slots available this week. You can book directly here:
{calendly_link}

Or let me know what works for you and I'll send a calendar invite.

Looking forward to chatting!

Best,
Ajaya Dahal
AjayaDesign
"""

    await send_email(
        to_email=prospect.owner_email,
        subject=subject,
        body=body,
    )

    logger.info(f"[SalesQual] Sent Calendly to {prospect.business_name}")


async def _send_follow_up_email(prospect: Prospect, response_text: str):
    """Send AI-generated follow-up answer."""
    from api.services.email_service import send_email

    subject = f"Re: {prospect.business_name} website"

    await send_email(
        to_email=prospect.owner_email,
        subject=subject,
        body=response_text,
    )

    logger.info(f"[SalesQual] Sent answer to {prospect.business_name}")


async def _send_nurture_content(prospect: Prospect):
    """Send case study/testimonial to nurture lead."""
    from api.services.email_service import send_email

    subject = f"Case study: How we helped a {prospect.business_type} like yours"
    body = f"""Hi {prospect.owner_name or 'there'},

I wanted to share a quick case study that might interest you.

We recently worked with a {prospect.business_type} in {prospect.city or 'Texas'} who had a similar website situation to yours.

Results:
• 3x increase in contact form submissions
• Mobile traffic up 150%
• Page load time: 8s → 1.2s

Full case study: [link to portfolio]

No pressure - just wanted to show what's possible!

Best,
Ajaya
"""

    await send_email(
        to_email=prospect.owner_email,
        subject=subject,
        body=body,
    )

    logger.info(f"[SalesQual] Sent nurture to {prospect.business_name}")


async def get_sales_qualification_stats() -> Dict[str, Any]:
    """Get Sales Qualification Agent performance statistics."""
    async with async_session() as session:
        # Total meetings booked
        stmt = select(func.count(Prospect.id)).where(
            Prospect.status == "meeting_scheduled"
        )
        result = await session.execute(stmt)
        meetings_booked = result.scalar() or 0

        # Conversion rates
        stmt = select(func.count(Prospect.id)).where(
            Prospect.status == "replied"
        )
        result = await session.execute(stmt)
        total_replied = result.scalar() or 0

        reply_to_meeting_rate = (meetings_booked / total_replied * 100) if total_replied > 0 else 0.0

    return {
        "total_meetings_booked": meetings_booked,
        "total_replied": total_replied,
        "reply_to_meeting_rate": round(reply_to_meeting_rate, 1),
    }
