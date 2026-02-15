"""
AjayaDesign Automation — AI API service.
Multi-provider: GitHub Models (OpenAI) and Anthropic (Claude).
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

# Anthropic API version header
ANTHROPIC_VERSION = "2023-06-01"


async def call_ai(
    messages: list[dict],
    temperature: float = 0.7,
    max_tokens: int = 8000,
    model: str | None = None,
    retries: int = 2,
) -> str:
    """Call AI chat completion API with retry logic.

    Works transparently with both GitHub Models (OpenAI) and Anthropic (Claude).
    Provider is selected via AI_PROVIDER env var.
    """
    token = settings.ai_auth_token
    if not token:
        provider = settings.ai_provider
        if provider == "anthropic":
            raise RuntimeError("ANTHROPIC_API_KEY not set — cannot call Claude API")
        raise RuntimeError("AI_TOKEN or GH_TOKEN not set — cannot call AI API")

    used_model = model or settings.ai_effective_model
    last_err: Exception | None = None

    for attempt in range(1, retries + 2):
        try:
            return await _request(messages, temperature, max_tokens, used_model, token)
        except Exception as err:
            last_err = err
            if attempt <= retries:
                msg = str(err)
                rate_limited = "429" in msg or "RateLimitReached" in msg or "overloaded" in msg.lower()
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
    """Dispatch to the correct provider."""
    if settings.ai_provider == "anthropic":
        return await _request_anthropic(messages, temperature, max_tokens, model, token)
    return await _request_openai(messages, temperature, max_tokens, model, token)


async def _request_openai(
    messages: list[dict],
    temperature: float,
    max_tokens: int,
    model: str,
    token: str,
) -> str:
    """GitHub Models / OpenAI-compatible endpoint."""
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
            settings.ai_effective_url, json=payload, headers=headers
        ) as resp:
            body = await resp.text()
            if resp.status != 200:
                raise RuntimeError(f"AI API HTTP {resp.status}: {body[:500]}")
            data = json.loads(body)
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            return strip_fences(content)


async def _request_anthropic(
    messages: list[dict],
    temperature: float,
    max_tokens: int,
    model: str,
    token: str,
) -> str:
    """Anthropic Messages API (Claude).

    Differences from OpenAI format:
    - system prompt is a top-level field, not in messages
    - header uses x-api-key instead of Authorization Bearer
    - response is content[0].text instead of choices[0].message.content
    """
    # Extract system message(s) → top-level 'system' field
    system_parts: list[str] = []
    user_messages: list[dict] = []
    for msg in messages:
        if msg.get("role") == "system":
            system_parts.append(msg["content"])
        else:
            user_messages.append(msg)

    # Anthropic requires at least one non-system message
    if not user_messages:
        user_messages = [{"role": "user", "content": "Hello"}]

    payload: dict = {
        "model": model,
        "messages": user_messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    if system_parts:
        payload["system"] = "\n\n".join(system_parts)

    headers = {
        "x-api-key": token,
        "anthropic-version": ANTHROPIC_VERSION,
        "Content-Type": "application/json",
    }

    async with aiohttp.ClientSession(timeout=TIMEOUT) as session:
        async with session.post(
            settings.ai_effective_url, json=payload, headers=headers
        ) as resp:
            body = await resp.text()
            if resp.status != 200:
                raise RuntimeError(f"Anthropic API HTTP {resp.status}: {body[:500]}")
            data = json.loads(body)
            # Anthropic response: {"content": [{"type": "text", "text": "..."}], ...}
            blocks = data.get("content", [])
            text_parts = [b["text"] for b in blocks if b.get("type") == "text"]
            content = "\n".join(text_parts)
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
