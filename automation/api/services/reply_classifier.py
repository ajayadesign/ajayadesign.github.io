"""
Reply Classifier — Keyword-Based Reply Analysis.

Classifies incoming replies as positive/neutral/negative/unsubscribe
using regex pattern matching. No AI needed — keyword patterns are
sufficient for outreach replies.

Phase 7 of OUTREACH_AGENT_PLAN.md.
"""

import logging
import re
from typing import Optional

from api.database import async_session_factory
from api.models.prospect import Prospect, OutreachEmail

logger = logging.getLogger("outreach.reply_classifier")


# ─── Classification Patterns ──────────────────────────────────────────

POSITIVE_PATTERNS = [
    r"\byes\b",
    r"\bsure\b",
    r"\binterested\b",
    r"\btell me more\b",
    r"\blet'?s (talk|chat|meet|schedule|discuss)\b",
    r"\bsend (it|me|the audit|the report)\b",
    r"\bwould love\b",
    r"\bsounds good\b",
    r"\bsounds great\b",
    r"\bset up a (call|meeting|time)\b",
    r"\bschedule a (call|meeting|time)\b",
    r"\bfree (this|next) week\b",
    r"\bwhat time works\b",
    r"\bi'?d like to\b",
    r"\bwhen (can|are) (you|we)\b",
    r"\bcalendar link\b",
    r"\bbook a time\b",
    r"\bhow much\b",
    r"\bpricing\b",
    r"\bquote\b",
    r"\bcost\b",
    r"\brate\b",
]

NEGATIVE_PATTERNS = [
    r"\bnot interested\b",
    r"\bno thanks\b",
    r"\bno thank you\b",
    r"\bnot right now\b",
    r"\bwe'?re (good|fine|set)\b",
    r"\bwe (already have|have a|just got)\b",
    r"\bdon'?t (need|want|contact)\b",
    r"\bremove me\b",
    r"\bstop (emailing|contacting|sending)\b",
    r"\bleave me alone\b",
    r"\bnot (looking|in the market)\b",
    r"\bwe (use|have|work with) (someone|a guy|our)\b",
    r"\btoo (busy|expensive)\b",
    r"\bbudget\b.*\btight\b",
    r"\bmaybe (later|next year|next quarter)\b",
    r"\bnot a (good|great) time\b",
    r"\bpass\b",
    r"\bdecline\b",
]

UNSUBSCRIBE_PATTERNS = [
    r"\bunsubscribe\b",
    r"\bopt.?out\b",
    r"\bremove (me |my )?(from|off)\b",
    r"\bstop (all |these )?emails?\b",
    r"\bdo not (email|contact|send)\b",
    r"\bdon'?t (email|contact|send)\b",
    r"\bspam\b",
    r"\breport(ing)?\b.*\bspam\b",
    r"\billegal\b",
    r"\bcan.?spam\b",
    r"\bblacklist\b",
    r"\bblock\b",
]

NEUTRAL_PHRASES = [
    r"\bwho (is|are) you\b",
    r"\bhow did you (get|find)\b",
    r"\bmore (info|information|details)\b",
    r"\bwhat (is|are) (you|your)\b",
    r"\bthanks (for reaching|for the)\b",
    r"\bi'?ll (think about|consider)\b",
    r"\blet me (check|think|ask)\b",
    r"\bi'?ll get back\b",
    r"\bforward(ed)? (this|it|your)\b",
    r"\bwho should i\b",
]

# Compile for performance
_POSITIVE = [re.compile(p, re.IGNORECASE) for p in POSITIVE_PATTERNS]
_NEGATIVE = [re.compile(p, re.IGNORECASE) for p in NEGATIVE_PATTERNS]
_UNSUBSCRIBE = [re.compile(p, re.IGNORECASE) for p in UNSUBSCRIBE_PATTERNS]
_NEUTRAL = [re.compile(p, re.IGNORECASE) for p in NEUTRAL_PHRASES]


def classify_reply(text: str) -> dict:
    """
    Classify a reply text into sentiment categories.
    Returns {'classification': str, 'confidence': float, 'matched_patterns': list}.
    
    Priority order: unsubscribe > positive > negative > neutral > unknown.
    Unsubscribe always wins because it's a legal requirement (CAN-SPAM).
    """
    if not text:
        return {"classification": "unknown", "confidence": 0.0, "matched_patterns": []}

    text = text.strip()
    matches = {
        "positive": [],
        "negative": [],
        "unsubscribe": [],
        "neutral": [],
    }

    # Check all patterns
    for pattern in _UNSUBSCRIBE:
        m = pattern.search(text)
        if m:
            matches["unsubscribe"].append(m.group())

    for pattern in _POSITIVE:
        m = pattern.search(text)
        if m:
            matches["positive"].append(m.group())

    for pattern in _NEGATIVE:
        m = pattern.search(text)
        if m:
            matches["negative"].append(m.group())

    for pattern in _NEUTRAL:
        m = pattern.search(text)
        if m:
            matches["neutral"].append(m.group())

    # Determine classification (priority order)
    if matches["unsubscribe"]:
        return {
            "classification": "unsubscribe",
            "confidence": 0.95,
            "matched_patterns": matches["unsubscribe"],
        }

    if matches["positive"] and not matches["negative"]:
        confidence = min(0.95, 0.5 + len(matches["positive"]) * 0.15)
        return {
            "classification": "positive",
            "confidence": confidence,
            "matched_patterns": matches["positive"],
        }

    if matches["negative"] and not matches["positive"]:
        confidence = min(0.95, 0.5 + len(matches["negative"]) * 0.15)
        return {
            "classification": "negative",
            "confidence": confidence,
            "matched_patterns": matches["negative"],
        }

    # Mixed signals — positive + negative
    if matches["positive"] and matches["negative"]:
        # More positive → neutral-positive, more negative → negative
        if len(matches["positive"]) > len(matches["negative"]):
            return {
                "classification": "neutral",
                "confidence": 0.4,
                "matched_patterns": matches["positive"] + matches["negative"],
            }
        return {
            "classification": "negative",
            "confidence": 0.5,
            "matched_patterns": matches["positive"] + matches["negative"],
        }

    if matches["neutral"]:
        return {
            "classification": "neutral",
            "confidence": 0.6,
            "matched_patterns": matches["neutral"],
        }

    # Very short replies (< 20 chars) that match none → likely auto-reply or ack
    if len(text) < 20:
        return {"classification": "neutral", "confidence": 0.3, "matched_patterns": []}

    return {"classification": "unknown", "confidence": 0.0, "matched_patterns": []}


async def process_reply(email_tracking_id: str, reply_text: str) -> Optional[dict]:
    """
    Process an incoming reply: classify, update records, notify, take action.
    Returns classification dict or None.
    """
    from api.services.telegram_outreach import send_message
    from api.services.cadence_engine import handle_unsubscribe
    from api.services.firebase_summarizer import _safe_set
    from sqlalchemy import select
    import time as _time

    classification = classify_reply(reply_text)

    async with async_session_factory() as db:
        result = await db.execute(
            select(OutreachEmail).where(OutreachEmail.tracking_id == email_tracking_id)
        )
        email = result.scalar_one_or_none()
        if not email:
            return classification

        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)

        email.replied_at = now
        email.reply_body = reply_text[:2000]
        email.reply_sentiment = classification["classification"]
        email.status = "replied"

        prospect = await db.get(Prospect, email.prospect_id)
        if prospect:
            prospect.replied_at = now
            prospect.reply_sentiment = classification["classification"]
            prospect.status = "replied"

        await db.commit()

        # Notify via Telegram with action buttons
        sentiment_emoji = {
            "positive": "⭐",
            "negative": "👎",
            "neutral": "🤔",
            "unsubscribe": "🚫",
            "unknown": "❓",
        }
        emoji = sentiment_emoji.get(classification["classification"], "❓")
        biz_name = prospect.business_name if prospect else "Unknown"

        await send_message(
            f"{emoji} *Reply from {biz_name}!*\n"
            f"📋 Classification: `{classification['classification']}` "
            f"({classification['confidence']:.0%} confidence)\n"
            f"📧 Step {email.sequence_step}\n\n"
            f"💬 _{reply_text[:300]}_"
        )

        await _safe_set("outreach/stats/last_reply", {
            "name": biz_name,
            "sentiment": classification["classification"],
            "ts": int(_time.time()),
        })

    # Handle unsubscribe automatically
    if classification["classification"] == "unsubscribe" and prospect:
        await handle_unsubscribe(str(prospect.id))

    return classification
