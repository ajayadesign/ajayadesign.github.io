"""
AjayaDesign Automation — AI API service (GitHub Models / Azure OpenAI).
Async with retry, JSON/HTML extraction.
"""

import json
import re
import asyncio
import logging

import aiohttp

from api.config import settings

logger = logging.getLogger(__name__)

TIMEOUT = aiohttp.ClientTimeout(total=120)


async def call_ai(
    messages: list[dict],
    temperature: float = 0.7,
    max_tokens: int = 8000,
    model: str | None = None,
    retries: int = 2,
) -> str:
    """Call AI chat completion API with retry logic."""
    token = settings.gh_token
    if not token:
        raise RuntimeError("GH_TOKEN not set — cannot call AI API")

    used_model = model or settings.ai_model
    last_err: Exception | None = None

    for attempt in range(1, retries + 2):
        try:
            return await _request(messages, temperature, max_tokens, used_model, token)
        except Exception as err:
            last_err = err
            if attempt <= retries:
                msg = str(err)
                rate_limited = "429" in msg or "RateLimitReached" in msg
                wait_match = re.search(r"wait\s+(\d+)\s+second", msg, re.I)
                if rate_limited:
                    wait = (int(wait_match.group(1)) + 2 if wait_match else 25)
                else:
                    wait = attempt * 2
                logger.warning(
                    f"AI retry {attempt}/{retries} — waiting {wait}s"
                    f"{' (rate limited)' if rate_limited else ''}..."
                )
                await asyncio.sleep(wait)

    raise last_err  # type: ignore[misc]


async def _request(
    messages: list[dict],
    temperature: float,
    max_tokens: int,
    model: str,
    token: str,
) -> str:
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    async with aiohttp.ClientSession(timeout=TIMEOUT) as session:
        async with session.post(
            settings.ai_api_url, json=payload, headers=headers
        ) as resp:
            body = await resp.text()
            if resp.status != 200:
                raise RuntimeError(f"AI API HTTP {resp.status}: {body[:500]}")
            data = json.loads(body)
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            return strip_fences(content)


# ── Parsing helpers ─────────────────────────────────────────────


def strip_fences(text: str) -> str:
    """Remove markdown code fences."""
    text = re.sub(r"^```(?:html|json|javascript|js|css)?\s*\n?", "", text, flags=re.MULTILINE)
    text = re.sub(r"^```\s*$", "", text, flags=re.MULTILINE)
    return text.strip()


def extract_json(text: str) -> dict:
    """Extract JSON object from AI response."""
    cleaned = strip_fences(text)

    # Try full text
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Try outermost { ... }
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(cleaned[start : end + 1])
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Could not extract JSON from AI response:\n{cleaned[:300]}…")


def extract_html(text: str) -> str:
    """Extract HTML from AI response."""
    cleaned = strip_fences(text)
    if any(tag in cleaned for tag in ("<!DOCTYPE", "<html", "<main")):
        return cleaned
    raise ValueError("AI response does not contain valid HTML")
