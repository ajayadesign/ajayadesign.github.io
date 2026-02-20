"""
Outreach Agent — Telegram command handler & notifier.

Extends the existing notify.py with outreach-specific commands and
an enhanced notification system that supports inline keyboards (via webhook).

Commands:
  /ostatus   — Outreach agent status + current ring + today's stats
  /opause    — Pause the outreach agent
  /oresume   — Resume the outreach agent
  /okill     — Emergency stop
  /odigest   — Force-send daily digest
  /orebuild  — Rebuild Firebase from PostgreSQL
  /ohelp     — Show outreach commands

For Phase 1, commands POST to the local API (localhost:3001).
"""

import logging
import re
from datetime import datetime, timezone

import aiohttp

from api.config import settings

logger = logging.getLogger(__name__)

# ── Markdown escape ─────────────────────────────────────
_MDESC_RE = re.compile(r"([_*\[\]()~`>#+\-=|{}.!\\])")


def _esc(s: str) -> str:
    """Escape MarkdownV2 special characters."""
    return _MDESC_RE.sub(r"\\\1", str(s))


# ── Low-level send ──────────────────────────────────────

async def _tg_post(method: str, payload: dict) -> dict | None:
    """POST to Telegram Bot API. Returns response JSON or None."""
    token = settings.telegram_bot_token
    if not token:
        logger.warning("Telegram not configured — skipping")
        return None
    try:
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            url = f"https://api.telegram.org/bot{token}/{method}"
            async with session.post(url, json=payload) as resp:
                body = await resp.json()
                if resp.status == 200 and body.get("ok"):
                    return body
                logger.error(f"Telegram {method} {resp.status}: {body}")
                return None
    except Exception as e:
        logger.error(f"Telegram {method} failed: {e}")
        return None


async def notify(message: str, reply_markup: dict | None = None) -> bool:
    """
    Send a Telegram notification to the configured chat.
    Supports MarkdownV2 formatting and optional inline keyboards.

    Args:
        message: MarkdownV2-formatted text.
        reply_markup: Optional inline keyboard markup dict.

    Returns True on success.
    """
    chat_id = settings.telegram_chat_id
    if not chat_id:
        logger.warning("TELEGRAM_CHAT_ID not set — skipping notify")
        return False

    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "MarkdownV2",
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup

    result = await _tg_post("sendMessage", payload)
    return result is not None


# ── Convenience notifiers ───────────────────────────────

async def notify_discovery(count: int, ring_name: str) -> bool:
    """Notify: batch of prospects discovered."""
    return await notify(
        f"🔍 *Found {count} new businesses in {_esc(ring_name)}*"
    )


async def notify_audit(business_name: str, score: int, url: str) -> bool:
    """Notify: audit complete for a prospect."""
    score = int(score) if score is not None else 0
    grade = "🟢" if score >= 70 else "🟡" if score >= 40 else "🔴"
    return await notify(
        f"📊 Audited `{_esc(business_name)}`\n"
        f"{grade} Score: *{score}/100*\n"
        f"🔗 {_esc(url)}"
    )


async def notify_email_sent(count: int) -> bool:
    """Notify: batch of emails sent."""
    return await notify(f"📧 *Sent {count} outreach emails today*")


async def notify_open(business_name: str, open_count: int) -> bool:
    """Notify: email opened by prospect."""
    suffix = f" \\({_esc(str(open_count))} times\\)" if open_count > 1 else ""
    return await notify(
        f"👀 *{_esc(business_name)}* opened your email{suffix}"
    )


async def notify_reply(business_name: str, classification: str, preview: str = "") -> bool:
    """Notify: reply received — with inline keyboard for actions."""
    keyboard = {
        "inline_keyboard": [
            [{"text": "💰 Promote to Lead", "callback_data": f"promote_{business_name[:20]}"}],
            [{"text": "⏭ Skip", "callback_data": f"skip_{business_name[:20]}"}],
        ]
    }
    return await notify(
        f"⭐ *REPLY from {_esc(business_name)}\\!*\n"
        f"📋 Classification: `{_esc(classification)}`\n"
        f"💬 _{_esc(preview[:200])}_",
        reply_markup=keyboard,
    )


async def notify_ring_complete(ring_name: str, stats: dict) -> bool:
    """Notify: geo-ring complete — ask to expand."""
    keyboard = {
        "inline_keyboard": [
            [{"text": "✅ Expand to next ring", "callback_data": "expand_next"}],
            [{"text": "⏸ Stay paused", "callback_data": "stay_paused"}],
            [{"text": "🛑 Stop agent", "callback_data": "stop_agent"}],
        ]
    }
    return await notify(
        f"🎯 *Ring Complete: {_esc(ring_name)}*\n\n"
        f"📊 Found: {stats.get('found', 0)}\n"
        f"📧 Contacted: {stats.get('contacted', 0)}\n"
        f"👀 Opened: {stats.get('opened', 0)}\n"
        f"⭐ Replied: {stats.get('replied', 0)}\n\n"
        f"❓ *Expand to next ring\\?*",
        reply_markup=keyboard,
    )


async def notify_error(context: str, error: str) -> bool:
    """Notify: error occurred."""
    return await notify(
        f"⚠️ *Outreach Error*\n"
        f"📍 {_esc(context)}\n"
        f"❌ `{_esc(error[:300])}`"
    )


async def notify_recon(business_name: str, email: str, source: str, verified: bool = False) -> bool:
    """Notify: recon completed — email found for a prospect."""
    v_icon = "✅" if verified else "⚠️"
    return await notify(
        f"🕵️ Recon complete: *{_esc(business_name)}*\n"
        f"📧 {_esc(email)} {v_icon}\n"
        f"🔍 Source: {_esc(source)}"
    )


# Alias used by services that send arbitrary messages
send_message = notify


async def notify_agent_status_change(new_status: str, reason: str = "") -> bool:
    """Notify: agent status changed."""
    icons = {"running": "🟢", "paused": "🟡", "error": "🔴", "idle": "⚪"}
    icon = icons.get(new_status, "❓")
    msg = f"{icon} *Agent {_esc(new_status)}*"
    if reason:
        msg += f"\n📝 {_esc(reason)}"
    return await notify(msg)


# ── Daily Digest ────────────────────────────────────────

async def send_daily_digest(stats: dict) -> bool:
    """
    Send the daily outreach digest.
    Stats dict should contain: discovered, sent, opened, replied, meetings,
    open_rate, ring_summary, agent_status, uptime, hot_leads, issues.
    """
    date_str = datetime.now(timezone.utc).strftime("%b %d, %Y")
    msg = (
        f"📊 *Daily Outreach Digest — {_esc(date_str)}*\n\n"
        f"🔍 Discovered: {stats.get('discovered', 0)}\n"
        f"📧 Sent: {stats.get('sent', 0)}\n"
        f"👀 Opened: {stats.get('opened', 0)}\n"
        f"⭐ Replies: {stats.get('replied', 0)}\n"
        f"📅 Meetings: {stats.get('meetings', 0)}\n"
    )

    hot = stats.get("hot_leads", [])
    if hot:
        msg += "\n🔥 *Hot leads:*\n"
        for lead in hot[:5]:
            msg += f"  • {_esc(lead)}\n"

    issues = stats.get("issues", [])
    if issues:
        msg += f"\n⚠️ Issues: {_esc(', '.join(issues))}\n"

    msg += (
        f"\n📍 Ring: {_esc(stats.get('ring_summary', 'N/A'))}\n"
        f"🔋 Agent: {_esc(stats.get('agent_status', 'unknown'))}"
    )
    return await notify(msg)


# ── Webhook command handler ─────────────────────────────

API_BASE = "http://localhost:3001/api/v1"


async def handle_telegram_update(update: dict) -> dict:
    """
    Process an incoming Telegram update (message or callback_query).
    Called from the FastAPI webhook endpoint.
    Returns {"ok": True} always (Telegram expects 200).
    """
    # Handle callback queries (inline keyboard button presses)
    callback = update.get("callback_query")
    if callback:
        return await _handle_callback(callback)

    # Handle text commands
    message = update.get("message", {})
    text = message.get("text", "").strip()

    # Verify it's from our chat
    chat_id = str(message.get("chat", {}).get("id", ""))
    if chat_id != settings.telegram_chat_id:
        return {"ok": True}

    # Route commands
    if text.startswith("/ostatus"):
        await _cmd_status()
    elif text.startswith("/opause"):
        await _cmd_pause()
    elif text.startswith("/oresume"):
        await _cmd_resume()
    elif text.startswith("/okill"):
        await _cmd_kill()
    elif text.startswith("/odigest"):
        await _cmd_digest()
    elif text.startswith("/orebuild"):
        await _cmd_rebuild()
    elif text.startswith("/ohelp"):
        await _cmd_help()

    return {"ok": True}


async def _handle_callback(callback: dict) -> dict:
    """Handle inline keyboard callbacks."""
    data = callback.get("data", "")
    callback_id = callback.get("id")

    # Acknowledge the callback to remove the loading spinner
    if callback_id:
        await _tg_post("answerCallbackQuery", {"callback_query_id": callback_id})

    if data == "expand_next":
        await notify("✅ *Ring expansion approved* — agent resuming")
        try:
            async with aiohttp.ClientSession() as session:
                await session.post(f"{API_BASE}/outreach/agent/start")
        except Exception:
            pass
    elif data == "stay_paused":
        await notify("⏸ *Staying paused* — use /oresume when ready")
    elif data == "stop_agent":
        await notify("🛑 *Agent stopped*")
        try:
            async with aiohttp.ClientSession() as session:
                await session.post(f"{API_BASE}/outreach/agent/kill")
        except Exception:
            pass
    elif data.startswith("promote_"):
        name = data[8:]
        await notify(f"💰 *Promoting {_esc(name)} to lead*")
        # TODO: Call promote API when prospect ID is available

    return {"ok": True}


async def _api_get(path: str) -> dict | None:
    """GET from the local API."""
    try:
        timeout = aiohttp.ClientTimeout(total=5)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(f"{API_BASE}{path}") as resp:
                if resp.status == 200:
                    return await resp.json()
                return None
    except Exception:
        return None


async def _api_post(path: str) -> dict | None:
    """POST to the local API."""
    try:
        timeout = aiohttp.ClientTimeout(total=5)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(f"{API_BASE}{path}") as resp:
                if resp.status == 200:
                    return await resp.json()
                return None
    except Exception:
        return None


async def _cmd_status():
    """Handle /ostatus command."""
    agent = await _api_get("/outreach/agent/status")
    stats = await _api_get("/outreach/stats")

    if not agent or not stats:
        await notify("⚠️ *API unreachable* — is Docker running\\?")
        return

    icons = {"running": "🟢", "paused": "🟡", "error": "🔴", "idle": "⚪"}
    icon = icons.get(agent.get("status", ""), "❓")
    st = agent.get("status", "unknown")

    msg = (
        f"{icon} *Outreach Agent: {_esc(st)}*\n\n"
        f"📊 Prospects: {stats.get('total_prospects', 0)}\n"
        f"📧 Sent: {stats.get('total_sent', 0)}\n"
        f"👀 Opened: {stats.get('total_opened', 0)} "
        f"\\({stats.get('open_rate', 0)}%\\)\n"
        f"⭐ Replied: {stats.get('total_replied', 0)} "
        f"\\({stats.get('reply_rate', 0)}%\\)\n"
        f"📅 Meetings: {stats.get('total_meetings', 0)}"
    )
    await notify(msg)


async def _cmd_pause():
    result = await _api_post("/outreach/agent/pause")
    if result:
        await notify("⏸ *Agent paused*")
    else:
        await notify("⚠️ Failed to pause — API unreachable")


async def _cmd_resume():
    result = await _api_post("/outreach/agent/start")
    if result:
        await notify("🟢 *Agent resumed*")
    else:
        await notify("⚠️ Failed to resume — API unreachable")


async def _cmd_kill():
    result = await _api_post("/outreach/agent/kill")
    if result:
        await notify("🛑 *Agent killed*")
    else:
        await notify("⚠️ Failed to kill — API unreachable")


async def _cmd_digest():
    stats = await _api_get("/outreach/stats")
    if stats:
        await send_daily_digest(stats)
    else:
        await notify("⚠️ Could not fetch stats — API unreachable")


async def _cmd_rebuild():
    """Trigger Firebase rebuild from PostgreSQL."""
    await notify("🔄 *Rebuilding Firebase from PostgreSQL\\.\\.\\.*")
    # Will be implemented by firebase_summarizer.rebuild_firebase_from_postgres()
    try:
        from api.services.firebase_summarizer import rebuild_firebase_from_postgres
        await rebuild_firebase_from_postgres()
        await notify("✅ *Firebase rebuild complete*")
    except Exception as e:
        await notify(f"❌ *Rebuild failed:* `{_esc(str(e)[:200])}`")


async def _cmd_help():
    await notify(
        "🎯 *Outreach Agent Commands*\n\n"
        "`/ostatus`  — Agent status \\+ stats\n"
        "`/opause`   — Pause the agent\n"
        "`/oresume`  — Resume the agent\n"
        "`/okill`    — Emergency stop\n"
        "`/odigest`  — Force daily digest\n"
        "`/orebuild` — Rebuild Firebase from PG\n"
        "`/ohelp`    — Show this help"
    )
