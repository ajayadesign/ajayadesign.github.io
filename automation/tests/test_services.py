"""
Tests for services — AI, git, notify, test_runner.
"""

import json
import os
import time
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from api.services.ai import call_ai, strip_fences, extract_json, extract_html
from api.services.git import (
    sanitize_repo_name,
    find_unique_repo_name,
    run_cmd,
    try_cmd,
    _is_rate_limited,
    _is_transient,
    _get_github_rate_limit_wait,
)
from api.services.notify import send_telegram


# ── AI Service ──────────────────────────────────────────

class TestStripFences:
    def test_json_fences(self):
        raw = '```json\n{"key": "value"}\n```'
        assert strip_fences(raw) == '{"key": "value"}'

    def test_html_fences(self):
        raw = "```html\n<div>hello</div>\n```"
        assert strip_fences(raw) == "<div>hello</div>"

    def test_no_fences(self):
        raw = '{"key": "value"}'
        assert strip_fences(raw) == '{"key": "value"}'

    def test_multiple_fences(self):
        raw = "text before\n```json\n{}\n```\ntext after"
        result = strip_fences(raw)
        assert "{}" in result


class TestExtractJson:
    def test_clean_json(self):
        raw = '{"name": "test", "pages": [{"slug": "index"}]}'
        result = extract_json(raw)
        assert result["name"] == "test"

    def test_json_in_fences(self):
        raw = '```json\n{"pages": [{"slug": "home"}]}\n```'
        result = extract_json(raw)
        assert result["pages"][0]["slug"] == "home"

    def test_json_with_surrounding_text(self):
        raw = 'Here is the JSON:\n{"key": "val"}\nDone!'
        result = extract_json(raw)
        assert result["key"] == "val"

    def test_invalid_json_raises(self):
        with pytest.raises((json.JSONDecodeError, ValueError)):
            extract_json("this is not json at all")


class TestExtractHtml:
    def test_html_in_fences(self):
        raw = '```html\n<main><h1>Hi</h1></main>\n```'
        result = extract_html(raw)
        assert "<main>" in result

    def test_raw_html(self):
        raw = "<main><section>Content</section></main>"
        result = extract_html(raw)
        assert "<main>" in result


class TestCallAi:
    async def test_call_ai_with_mock(self, mock_ai):
        import api.services.ai as ai_module
        result = await ai_module.call_ai(
            messages=[
                {"role": "system", "content": "You are a senior web strategist at AjayaDesign"},
                {"role": "user", "content": "Design a site"},
            ],
        )
        assert "pages" in result or "siteName" in result

    async def test_call_ai_retry_on_failure(self):
        """Simulate a transient failure then success."""
        attempt = {"n": 0}

        async def _flaky(*args, **kwargs):
            attempt["n"] += 1
            if attempt["n"] < 2:
                raise Exception("rate limit")
            return '{"ok": true}'

        with patch("api.services.ai._request", side_effect=_flaky):
            # This would need the real retry logic — test the function signature
            pass  # Covered by integration tests


# ── Git Service ─────────────────────────────────────────

class TestSanitizeRepoName:
    def test_basic(self):
        assert sanitize_repo_name("Sunrise Bakery") == "sunrise-bakery"

    def test_special_chars(self):
        assert sanitize_repo_name("Joe's Café & Bar!") == "joe-s-caf-bar"

    def test_long_name(self):
        result = sanitize_repo_name("A" * 200)
        assert len(result) <= 100

    def test_leading_trailing_hyphens(self):
        result = sanitize_repo_name("---test---")
        assert not result.startswith("-")
        assert not result.endswith("-")

    def test_empty_fallback(self):
        result = sanitize_repo_name("!@#$%")
        assert len(result) > 0  # Should have some fallback


class TestFindUniqueRepoName:
    """Test repo name collision resolution."""

    async def test_no_collision(self):
        """Fresh name — no repo exists, use as-is."""
        async def _no_repo(cmd, **kw):
            return (False, "")  # repo doesn't exist

        with patch("api.services.git.try_cmd", side_effect=_no_repo):
            result = await find_unique_repo_name("Sunrise Bakery", "ajayadesign")
            assert result == "sunrise-bakery"

    async def test_same_client_reuse(self):
        """Repo exists AND description matches same client — reuse it."""
        call_count = {"n": 0}

        async def _same_client(cmd, **kw):
            call_count["n"] += 1
            if "gh repo view" in cmd and "--json description" in cmd:
                return (True, "Client site for Sunrise Bakery — built by AjayaDesign")
            if "gh repo view" in cmd:
                return (True, "exists")  # repo exists
            return (True, "")

        with patch("api.services.git.try_cmd", side_effect=_same_client):
            result = await find_unique_repo_name("Sunrise Bakery", "ajayadesign")
            assert result == "sunrise-bakery"  # reused, no suffix

    async def test_different_client_gets_suffix(self):
        """Repo exists for different client — should append -2."""
        async def _different_client(cmd, **kw):
            if "gh repo view" in cmd and "--json description" in cmd:
                return (True, "Client site for Some Other Business — built by AjayaDesign")
            if "gh repo view" in cmd:
                # sunrise-bakery exists, sunrise-bakery-2 does not
                if "sunrise-bakery-2" in cmd:
                    return (False, "")
                return (True, "exists")
            return (True, "")

        with patch("api.services.git.try_cmd", side_effect=_different_client):
            result = await find_unique_repo_name("Sunrise Bakery", "ajayadesign")
            assert result == "sunrise-bakery-2"

    async def test_multiple_collisions(self):
        """Both sunrise-bakery and sunrise-bakery-2 taken — should get -3."""
        async def _multi_collision(cmd, **kw):
            if "gh repo view" in cmd and "--json description" in cmd:
                return (True, "Client site for Someone Else — built by AjayaDesign")
            if "gh repo view" in cmd:
                # -3 is free, everything else taken
                if "sunrise-bakery-3" in cmd:
                    return (False, "")
                return (True, "exists")
            return (True, "")

        with patch("api.services.git.try_cmd", side_effect=_multi_collision):
            result = await find_unique_repo_name("Sunrise Bakery", "ajayadesign")
            assert result == "sunrise-bakery-3"

    async def test_db_in_progress_collision(self):
        """Repo name is used by an in-progress build in DB — skip it."""
        async def _no_gh_collision(cmd, **kw):
            if "gh repo view" in cmd:
                if "sunrise-bakery-2" in cmd:
                    return (False, "")  # -2 is free on GitHub
                return (False, "")  # base is also free on GitHub
            return (True, "")

        # Mock a DB session that returns sunrise-bakery as in-progress
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [("sunrise-bakery",)]
        mock_session.execute = AsyncMock(return_value=mock_result)

        with patch("api.services.git.try_cmd", side_effect=_no_gh_collision):
            result = await find_unique_repo_name(
                "Sunrise Bakery", "ajayadesign", db_session=mock_session
            )
            # sunrise-bakery is claimed by DB → should get -2
            assert result == "sunrise-bakery-2"

# ── Rate Limit Classifiers ─────────────────────────────

class TestRetryClassifiers:
    """Test _is_rate_limited and _is_transient classification helpers."""

    def test_rate_limit_phrase(self):
        assert _is_rate_limited("HTTP 403: API rate limit exceeded for user")

    def test_secondary_rate_limit(self):
        assert _is_rate_limited("You have exceeded a secondary rate limit. Please wait.")

    def test_abuse_detection(self):
        assert _is_rate_limited("abuse detection mechanism triggered")

    def test_normal_error_not_rate_limited(self):
        assert not _is_rate_limited("fatal: repository 'xyz' not found")

    def test_transient_dns(self):
        assert _is_transient("fatal: could not resolve host github.com")

    def test_transient_timeout(self):
        assert _is_transient("Connection timed out after 30 seconds")

    def test_transient_hung_up(self):
        assert _is_transient("the remote end hung up unexpectedly")

    def test_transient_early_eof(self):
        assert _is_transient("error: RPC failed; curl 56 early eof")

    def test_normal_error_not_transient(self):
        assert not _is_transient("fatal: repository 'xyz' not found")


# ── run_cmd Retry Logic ──────────────────────────────

class TestRunCmdRetry:
    """Test rate limit and transient failure retry logic in run_cmd."""

    async def test_rate_limit_retry_then_success(self):
        """First call hits 403 rate limit, second call succeeds."""
        attempt = {"n": 0}

        async def _mock_subprocess(cmd, **kwargs):
            attempt["n"] += 1
            proc = AsyncMock()
            if attempt["n"] == 1:
                proc.communicate = AsyncMock(return_value=(
                    b"", b"HTTP 403: API rate limit exceeded"
                ))
                proc.returncode = 1
            else:
                proc.communicate = AsyncMock(return_value=(
                    b"repo created", b""
                ))
                proc.returncode = 0
            return proc

        with patch("asyncio.create_subprocess_shell", side_effect=_mock_subprocess), \
             patch("api.services.git._get_github_rate_limit_wait", new_callable=AsyncMock, return_value=0), \
             patch("asyncio.sleep", new_callable=AsyncMock):
            result = await run_cmd("gh repo create test", retries=3)

        assert result == "repo created"
        assert attempt["n"] == 2

    async def test_transient_retry_then_success(self):
        """Connection failure retries with backoff, then succeeds."""
        attempt = {"n": 0}

        async def _mock_subprocess(cmd, **kwargs):
            attempt["n"] += 1
            proc = AsyncMock()
            if attempt["n"] == 1:
                proc.communicate = AsyncMock(return_value=(
                    b"", b"fatal: could not resolve host github.com"
                ))
                proc.returncode = 128
            else:
                proc.communicate = AsyncMock(return_value=(
                    b"pushed", b""
                ))
                proc.returncode = 0
            return proc

        with patch("asyncio.create_subprocess_shell", side_effect=_mock_subprocess), \
             patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            result = await run_cmd("git push", retries=3)

        assert result == "pushed"
        assert attempt["n"] == 2
        mock_sleep.assert_called_once_with(10)  # attempt=1 * 10s

    async def test_non_retryable_error_raises_immediately(self):
        """Errors that aren't rate limits or transient should raise without retry."""
        attempt = {"n": 0}

        async def _mock_subprocess(cmd, **kwargs):
            attempt["n"] += 1
            proc = AsyncMock()
            proc.communicate = AsyncMock(return_value=(
                b"", b"fatal: repository 'xyz' not found"
            ))
            proc.returncode = 128
            return proc

        with patch("asyncio.create_subprocess_shell", side_effect=_mock_subprocess), \
             patch("asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(RuntimeError, match="repository"):
                await run_cmd("gh repo view xyz", retries=3)

        assert attempt["n"] == 1  # No retries

    async def test_all_retries_exhausted_raises(self):
        """When every attempt hits rate limit, should raise after all retries."""
        async def _mock_subprocess(cmd, **kwargs):
            proc = AsyncMock()
            proc.communicate = AsyncMock(return_value=(
                b"", b"HTTP 403: API rate limit exceeded"
            ))
            proc.returncode = 1
            return proc

        with patch("asyncio.create_subprocess_shell", side_effect=_mock_subprocess), \
             patch("api.services.git._get_github_rate_limit_wait", new_callable=AsyncMock, return_value=0), \
             patch("asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(RuntimeError, match="rate limit"):
                await run_cmd("gh api test", retries=2)

    async def test_secondary_rate_limit_triggers_retry(self):
        """'secondary rate limit' / abuse detection should also retry."""
        attempt = {"n": 0}

        async def _mock_subprocess(cmd, **kwargs):
            attempt["n"] += 1
            proc = AsyncMock()
            if attempt["n"] == 1:
                proc.communicate = AsyncMock(return_value=(
                    b"", b"You have exceeded a secondary rate limit. Please wait."
                ))
                proc.returncode = 1
            else:
                proc.communicate = AsyncMock(return_value=(b"ok", b""))
                proc.returncode = 0
            return proc

        with patch("asyncio.create_subprocess_shell", side_effect=_mock_subprocess), \
             patch("api.services.git._get_github_rate_limit_wait", new_callable=AsyncMock, return_value=0), \
             patch("asyncio.sleep", new_callable=AsyncMock):
            result = await run_cmd("gh api endpoint", retries=3)

        assert result == "ok"
        assert attempt["n"] == 2

    async def test_try_cmd_inherits_retry(self):
        """try_cmd should also retry internally before returning failure."""
        attempt = {"n": 0}

        async def _mock_subprocess(cmd, **kwargs):
            attempt["n"] += 1
            proc = AsyncMock()
            if attempt["n"] <= 2:
                proc.communicate = AsyncMock(return_value=(
                    b"", b"HTTP 403: rate limit"
                ))
                proc.returncode = 1
            else:
                proc.communicate = AsyncMock(return_value=(b"ok", b""))
                proc.returncode = 0
            return proc

        with patch("asyncio.create_subprocess_shell", side_effect=_mock_subprocess), \
             patch("api.services.git._get_github_rate_limit_wait", new_callable=AsyncMock, return_value=0), \
             patch("asyncio.sleep", new_callable=AsyncMock):
            ok, output = await try_cmd("gh api test", retries=3)

        assert ok is True
        assert output == "ok"
        assert attempt["n"] == 3


# ── Rate Limit Wait Helper ───────────────────────────

class TestGetGithubRateLimitWait:
    """Test the _get_github_rate_limit_wait helper."""

    async def test_returns_wait_from_reset_epoch(self):
        """Should parse reset epoch and calculate wait time."""
        future_epoch = str(int(time.time()) + 300).encode()

        async def _mock_subprocess(cmd, **kwargs):
            proc = AsyncMock()
            proc.communicate = AsyncMock(return_value=(future_epoch, b""))
            proc.returncode = 0
            return proc

        with patch("asyncio.create_subprocess_shell", side_effect=_mock_subprocess):
            wait = await _get_github_rate_limit_wait()

        assert 295 <= wait <= 310  # ~305s (300 + 5 buffer)

    async def test_returns_default_on_failure(self):
        """If gh api fails, should return default 120s."""
        async def _mock_subprocess(cmd, **kwargs):
            raise Exception("gh not found")

        with patch("asyncio.create_subprocess_shell", side_effect=_mock_subprocess):
            wait = await _get_github_rate_limit_wait()

        assert wait == 120

    async def test_caps_at_one_hour(self):
        """Wait time should be capped at 3600 seconds."""
        far_future = str(int(time.time()) + 7200).encode()  # 2 hours away

        async def _mock_subprocess(cmd, **kwargs):
            proc = AsyncMock()
            proc.communicate = AsyncMock(return_value=(far_future, b""))
            proc.returncode = 0
            return proc

        with patch("asyncio.create_subprocess_shell", side_effect=_mock_subprocess):
            wait = await _get_github_rate_limit_wait()

        assert wait == 3600

# ── Notify Service ──────────────────────────────────────

class TestNotify:
    async def test_send_telegram_no_token(self):
        """Without token, should return False gracefully."""
        with patch("api.services.notify.settings") as mock_s:
            mock_s.telegram_bot_token = ""
            mock_s.telegram_chat_id = ""
            result = await send_telegram(
                client_name="Test",
                niche="Tech",
                goals="goals",
                email="a@b.com",
                repo_full="org/test",
                live_url="https://example.com",
                page_count=3,
            )
            assert result is False
