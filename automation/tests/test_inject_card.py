"""
Tests for inject_portfolio_card — pure-Python replacement for inject_card.js.
"""

import os

import pytest

from api.pipeline.phases.p07_deploy import (
    inject_portfolio_card,
    PORTFOLIO_MARKER,
    _pick_emoji,
)


# ── _pick_emoji ──────────────────────────────────────────


class TestPickEmoji:
    def test_known_keyword(self):
        assert _pick_emoji("Professional Photography") == "📸"

    def test_bakery_keyword(self):
        assert _pick_emoji("French Bakery & Café") == "🍰"

    def test_tech_keyword(self):
        assert _pick_emoji("Software Engineering") == "⚡"

    def test_unknown_falls_back(self):
        assert _pick_emoji("Quantum Physics Lab") == "🌐"

    def test_case_insensitive(self):
        assert _pick_emoji("PET GROOMING") == "🐾"


# ── inject_portfolio_card ────────────────────────────────


@pytest.fixture
def index_html(tmp_path):
    """Create a minimal index.html with the portfolio marker."""
    path = tmp_path / "index.html"
    path.write_text(
        "<html><body>\n"
        f"    <div class=\"portfolio\">\n"
        f"        {PORTFOLIO_MARKER}\n"
        f"    </div>\n"
        "</body></html>\n",
        encoding="utf-8",
    )
    return path


class TestInjectPortfolioCard:
    def test_injects_card(self, index_html):
        ok = inject_portfolio_card(
            str(index_html),
            repo_name="sunrise-bakery",
            client_name="Sunrise Bakery",
            niche="Artisan Bakery",
            goals="Sell more bread online",
            emoji="🍰",
        )
        assert ok is True
        content = index_html.read_text()
        assert 'id="card-sunrise-bakery"' in content
        assert "Sunrise Bakery" in content
        assert "Sell more bread online" in content
        assert "🍰" in content
        assert PORTFOLIO_MARKER in content  # marker preserved for next card

    def test_uses_niche_when_no_goals(self, index_html):
        inject_portfolio_card(
            str(index_html),
            repo_name="test-site",
            client_name="Test",
            niche="Pet Grooming",
            goals="",
        )
        content = index_html.read_text()
        assert "Pet Grooming" in content

    def test_skips_duplicate(self, index_html):
        inject_portfolio_card(
            str(index_html),
            repo_name="dupe-site",
            client_name="Dupe",
        )
        ok = inject_portfolio_card(
            str(index_html),
            repo_name="dupe-site",
            client_name="Dupe",
        )
        assert ok is False  # second call skips

    def test_returns_false_if_file_missing(self, tmp_path):
        ok = inject_portfolio_card(
            str(tmp_path / "nope.html"),
            repo_name="x",
            client_name="X",
        )
        assert ok is False

    def test_returns_false_if_no_marker(self, tmp_path):
        path = tmp_path / "index.html"
        path.write_text("<html><body></body></html>")
        ok = inject_portfolio_card(
            str(path),
            repo_name="x",
            client_name="X",
        )
        assert ok is False

    def test_escapes_html_in_client_name(self, index_html):
        inject_portfolio_card(
            str(index_html),
            repo_name="xss-test",
            client_name='<script>alert("xss")</script>',
            niche="Test",
        )
        content = index_html.read_text()
        assert "<script>" not in content
        assert "&lt;script&gt;" in content

    def test_live_url_format(self, index_html):
        inject_portfolio_card(
            str(index_html),
            repo_name="cool-site",
            client_name="Cool",
        )
        content = index_html.read_text()
        assert "https://ajayadesign.github.io/cool-site/" in content

    def test_multiple_cards_injected_in_order(self, index_html):
        inject_portfolio_card(
            str(index_html),
            repo_name="first",
            client_name="First Client",
        )
        inject_portfolio_card(
            str(index_html),
            repo_name="second",
            client_name="Second Client",
        )
        content = index_html.read_text()
        pos_first = content.index('id="card-first"')
        pos_second = content.index('id="card-second"')
        assert pos_first < pos_second  # first card comes first
