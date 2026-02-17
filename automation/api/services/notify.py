"""
AjayaDesign Automation — Telegram notification service.
"""

import re
import logging

import aiohttp

from api.config import settings

logger = logging.getLogger(__name__)


def _esc_md(s: str) -> str:
    """Escape MarkdownV2 special characters."""
    return re.sub(r"([_*\[\]()~`>#+\-=|{}.!\\])", r"\\\1", str(s))


async def send_telegram(
    client_name: str,
    niche: str,
    goals: str,
    email: str,
    repo_full: str,
    live_url: str,
    page_count: int,
    verified_live: bool = False,
) -> bool:
    """Send Telegram build-complete notification. Returns True on success."""
    token = settings.telegram_bot_token
    chat_id = settings.telegram_chat_id

    if not token or not chat_id:
        logger.warning("Telegram not configured — skipping notification")
        return False

    live_status = "✅ Verified live" if verified_live else "⏳ Propagating"

    message = "\n".join([
        "✅ *AjayaDesign v2 — New Site Deployed\\!*",
        "",
        f"🏢 *Client:* `{_esc_md(client_name)}`",
        f"🏷️ *Niche:* {_esc_md(niche)}",
        f"🎯 *Goals:* {_esc_md(goals)}",
        f"📧 *Email:* {_esc_md(email or 'not provided')}",
        f"📄 *Pages:* {page_count}",
        f"🌐 *Status:* {_esc_md(live_status)}",
        "",
        f"🔗 *Live URL:* [{_esc_md(live_url)}]({live_url})",
        f"📦 *Repo:* [github\\.com/{_esc_md(repo_full)}](https://github.com/{repo_full})",
        "",
        "_Built by AjayaDesign v2 Multi\\-Agent Pipeline \\(Python\\)_",
    ])

    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "MarkdownV2",
    }

    return await _send_tg_message(payload)


async def send_telegram_contract_signed(
    contract_id: str,
    client_name: str,
    project_name: str,
    total_amount: float,
    signer_name: str,
    signed_at: str,
) -> bool:
    """Send Telegram notification when a contract is signed. Returns True on success."""
    token = settings.telegram_bot_token
    chat_id = settings.telegram_chat_id

    if not token or not chat_id:
        logger.warning("Telegram not configured — skipping signing notification")
        return False

    amount_str = f"${total_amount:,.2f}" if total_amount else "N/A"

    message = "\n".join([
        "✍️ *CONTRACT SIGNED\\!*",
        "",
        f"📝 *Contract:* `{_esc_md(contract_id)}`",
        f"🏢 *Client:* {_esc_md(client_name)}",
        f"📁 *Project:* {_esc_md(project_name)}",
        f"💰 *Amount:* {_esc_md(amount_str)}",
        f"✍️ *Signed by:* {_esc_md(signer_name)}",
        f"🕐 *Signed at:* {_esc_md(signed_at)}",
        "",
        "🎉 _Time to start building\\!_",
    ])

    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "MarkdownV2",
    }

    return await _send_tg_message(payload)


async def _send_tg_message(payload: dict) -> bool:
    """Low-level Telegram sendMessage wrapper."""
    token = settings.telegram_bot_token
    try:
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            async with session.post(url, json=payload) as resp:
                if resp.status == 200:
                    logger.info("Telegram notification sent")
                    return True
                body = await resp.text()
                logger.error(f"Telegram API {resp.status}: {body[:200]}")
                return False
    except Exception as e:
        logger.error(f"Telegram failed: {e}")
        return False
