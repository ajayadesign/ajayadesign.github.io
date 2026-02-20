"""
Unit Tests for Outreach Engine Pure Functions.

No database or async required — tests pure logic only.
Run: cd automation && python -m pytest tests/outreach/test_unit.py -v
"""

import pytest


# ═══════════════════════════════════════════════════════════
# CRAWL ENGINE
# ═══════════════════════════════════════════════════════════

class TestHaversine:
    """Test haversine distance calculation."""

    def test_same_point_is_zero(self):
        from api.services.crawl_engine import haversine
        assert haversine(30.0, -97.0, 30.0, -97.0) == 0.0

    def test_manor_to_austin(self):
        """Manor TX → Austin TX ≈ 12-20 miles."""
        from api.services.crawl_engine import haversine
        d = haversine(30.3427, -97.5567, 30.2672, -97.7431)
        assert 10 < d < 25

    def test_cross_hemisphere(self):
        """0,0 → 0,180 ≈ half circumference of Earth."""
        from api.services.crawl_engine import haversine
        d = haversine(0, 0, 0, 180)
        assert 12400 < d < 12500


class TestPriorityScore:
    """Test prospect priority scoring."""

    def test_high_value_prospect(self):
        from api.services.crawl_engine import calculate_priority_score
        score = calculate_priority_score(
            score_overall=30, google_rating=4.5, google_reviews=100,
            distance_miles=2.0, business_type="plumber",
            has_email=True, email_verified=True, has_owner_name=True,
        )
        assert isinstance(score, int)
        assert score > 50

    def test_low_value_prospect(self):
        from api.services.crawl_engine import calculate_priority_score
        score = calculate_priority_score(
            score_overall=85, google_rating=2.0, google_reviews=3,
            distance_miles=100.0, business_type="restaurant",
            has_email=False, email_verified=False, has_owner_name=False,
        )
        assert isinstance(score, int)
        assert score < 50

    def test_no_data_returns_score(self):
        from api.services.crawl_engine import calculate_priority_score
        score = calculate_priority_score(
            score_overall=None, google_rating=None, google_reviews=None,
            distance_miles=None, business_type=None,
            has_email=False, email_verified=False, has_owner_name=False,
        )
        assert isinstance(score, int)


# ═══════════════════════════════════════════════════════════
# INTEL ENGINE — DESIGN ERA JUDGE
# ═══════════════════════════════════════════════════════════

class TestDesignEra:
    """Test heuristic design era detection."""

    def test_ancient_table_layout(self):
        from api.services.intel_engine import judge_design_era
        html = """
        <html><body>
        <table><tr><td>Layout in tables</td></tr></table>
        <p>&copy; 2012 My Business</p>
        <script src="jquery-1.7.min.js"></script>
        </body></html>
        """
        result = judge_design_era(html, ["jQuery 1.x"], "http://test.com")
        assert result["score"] < 50
        assert len(result["sins"]) > 0

    def test_modern_site_scores_well(self):
        from api.services.intel_engine import judge_design_era
        html = """
        <html><head><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
        <body>
        <div style="display: grid;">Content</div>
        <link href="https://fonts.googleapis.com/css2?family=Inter" rel="stylesheet">
        <img loading="lazy" src="hero.webp">
        <script type="application/ld+json">{"@type":"LocalBusiness"}</script>
        <picture><source srcset="hero.avif"></picture>
        </body></html>
        """
        result = judge_design_era(html, ["React", "Tailwind CSS"], "https://test.com")
        assert result["score"] > 50


# ═══════════════════════════════════════════════════════════
# INTEL ENGINE — SEO SIGNALS
# ═══════════════════════════════════════════════════════════

class TestSeoSignals:
    """Test SEO signal extraction."""

    def test_well_optimized_page(self):
        from api.services.intel_engine import extract_seo_signals
        html = """
        <html><head>
            <title>Joe's Plumbing - Manor TX</title>
            <meta name="description" content="Best plumber in Manor, TX since 2015">
            <meta property="og:title" content="Joe's Plumbing">
            <link rel="canonical" href="https://joesplumbing.com">
        </head>
        <body><h1>Professional Plumbing Services</h1></body></html>
        """
        result = extract_seo_signals(html, "https://joesplumbing.com")
        assert result["has_title"] is True
        assert result["has_meta_desc"] is True
        assert result["has_h1"] is True
        assert result["has_og_tags"] is True

    def test_bare_bones_page(self):
        from api.services.intel_engine import extract_seo_signals
        html = "<html><body><p>Hello world</p></body></html>"
        result = extract_seo_signals(html, "http://test.com")
        assert result["has_title"] is False
        assert result["has_meta_desc"] is False
        assert result["has_h1"] is False


# ═══════════════════════════════════════════════════════════
# INTEL ENGINE — TECH STACK
# ═══════════════════════════════════════════════════════════

class TestTechStack:
    """Test technology detection."""

    def test_wordpress_detection(self):
        from api.services.intel_engine import detect_tech_stack
        html = '<link rel="stylesheet" href="/wp-content/themes/theme/style.css">'
        result = detect_tech_stack(html, {"X-Powered-By": "PHP/7.4"})
        assert any("WordPress" in t for t in result)

    def test_wix_detection(self):
        from api.services.intel_engine import detect_tech_stack
        html = '<meta name="generator" content="Wix.com Website Builder">'
        result = detect_tech_stack(html, {})
        assert any("Wix" in t for t in result)

    def test_squarespace_detection(self):
        from api.services.intel_engine import detect_tech_stack
        html = '<link rel="stylesheet" href="https://static1.squarespace.com/static/css/main.css">'
        result = detect_tech_stack(html, {})
        assert any("Squarespace" in t for t in result)

    def test_jquery_version_detection(self):
        from api.services.intel_engine import detect_tech_stack
        html = '<script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>'
        result = detect_tech_stack(html, {})
        assert any("jQuery" in t for t in result)


class TestCmsDetection:
    """Test CMS platform detection."""

    def test_detect_wordpress(self):
        from api.services.intel_engine import detect_cms_platform
        assert detect_cms_platform(["WordPress", "jQuery"]) == "wordpress"

    def test_detect_wix(self):
        from api.services.intel_engine import detect_cms_platform
        assert detect_cms_platform(["Wix"]) == "wix"

    def test_detect_custom(self):
        from api.services.intel_engine import detect_cms_platform
        assert detect_cms_platform(["React", "Tailwind CSS"]) in ("custom", "unknown", "")


# ═══════════════════════════════════════════════════════════
# INTEL ENGINE — SECURITY & COMPOSITE
# ═══════════════════════════════════════════════════════════

class TestSecuritySignals:
    """Test security signal extraction."""

    def test_good_security(self):
        from api.services.intel_engine import extract_security_signals
        headers = {
            "Strict-Transport-Security": "max-age=31536000",
            "X-Frame-Options": "DENY",
            "Content-Security-Policy": "default-src 'self'",
            "X-Content-Type-Options": "nosniff",
        }
        result = extract_security_signals("<html></html>", headers, "https://test.com")
        assert result["ssl_grade"] in ("A", "B")

    def test_no_security(self):
        from api.services.intel_engine import extract_security_signals
        result = extract_security_signals("<html></html>", {}, "http://test.com")
        assert result["ssl_grade"] in ("C", "D", "F")


class TestCompositeScore:
    """Test weighted composite score computation."""

    def test_weighted_calculation(self):
        from api.services.intel_engine import compute_composite_score
        lighthouse = {"performance": 50, "accessibility": 60, "best-practices": 70, "seo": 80}
        design = {"score": 40, "era": "dated-2015"}
        seo = {"seo_score": 45}
        security = {"ssl_grade": "B", "score": 65}
        result = compute_composite_score(lighthouse, design, seo, security)
        assert "composite" in result
        assert 0 <= result["composite"] <= 100


# ═══════════════════════════════════════════════════════════
# RECON ENGINE — EMAIL VALIDATION
# ═══════════════════════════════════════════════════════════

class TestEmailValidation:
    """Test email format validation helpers."""

    def test_valid_emails(self):
        from api.services.recon_engine import is_valid_email_format
        assert is_valid_email_format("joe@joesplumbing.com") is True
        assert is_valid_email_format("jane.doe@company.co.uk") is True

    def test_invalid_emails(self):
        from api.services.recon_engine import is_valid_email_format
        assert is_valid_email_format("not-an-email") is False
        assert is_valid_email_format("@nodomain.com") is False
        assert is_valid_email_format("spaces in@email.com") is False

    def test_role_emails(self):
        from api.services.recon_engine import is_role_email
        assert is_role_email("info@company.com") is True
        assert is_role_email("support@company.com") is True
        assert is_role_email("admin@company.com") is True
        assert is_role_email("joe@company.com") is False

    def test_disposable_domains(self):
        from api.services.recon_engine import is_disposable
        assert is_disposable("user@mailinator.com") is True
        assert is_disposable("user@gmail.com") is False


class TestEmailGuesses:
    """Test email pattern generation."""

    def test_full_name_guesses(self):
        from api.services.recon_engine import generate_email_guesses
        guesses = generate_email_guesses("Joe Smith", "joesplumbing.com")
        assert len(guesses) >= 5
        emails = [g.lower() for g in guesses]
        assert "joe@joesplumbing.com" in emails
        assert "joe.smith@joesplumbing.com" in emails
        assert "jsmith@joesplumbing.com" in emails

    def test_single_name_guesses(self):
        from api.services.recon_engine import generate_email_guesses
        guesses = generate_email_guesses("Joe", "test.com")
        assert len(guesses) >= 1
        assert "joe@test.com" in [g.lower() for g in guesses]


# ═══════════════════════════════════════════════════════════
# REPLY CLASSIFIER
# ═══════════════════════════════════════════════════════════

class TestReplyClassifier:
    """Test regex-based reply classification."""

    def test_positive_interest(self):
        from api.services.reply_classifier import classify_reply
        result = classify_reply("Yes, I'm interested! When can we schedule a call?")
        assert result["classification"] == "positive"
        assert result["confidence"] > 0.3

    def test_positive_meeting_request(self):
        from api.services.reply_classifier import classify_reply
        result = classify_reply("Sure, let's set up a meeting. How about Tuesday at 2pm?")
        assert result["classification"] == "positive"

    def test_negative_not_interested(self):
        from api.services.reply_classifier import classify_reply
        result = classify_reply("Not interested, we already have a web developer.")
        assert result["classification"] == "negative"

    def test_unsubscribe_request(self):
        from api.services.reply_classifier import classify_reply
        result = classify_reply("Please remove me from your mailing list immediately.")
        assert result["classification"] == "unsubscribe"

    def test_unsubscribe_stop(self):
        from api.services.reply_classifier import classify_reply
        result = classify_reply("Stop emailing me.")
        assert result["classification"] in ("unsubscribe", "negative")

    def test_neutral_ooo(self):
        from api.services.reply_classifier import classify_reply
        result = classify_reply("I am currently out of the office and will return on Monday.")
        assert result["classification"] in ("neutral", "unknown")

    def test_empty_text(self):
        from api.services.reply_classifier import classify_reply
        result = classify_reply("")
        assert result["classification"] in ("unknown", "neutral")


# ═══════════════════════════════════════════════════════════
# TEMPLATE ENGINE — HELPERS
# ═══════════════════════════════════════════════════════════

class TestTemplateHelpers:
    """Test template engine helper functions."""

    def test_score_to_grade(self):
        from api.services.template_engine import score_to_grade
        assert score_to_grade(95) == "A"
        assert score_to_grade(85) == "B"
        assert score_to_grade(75) in ("B", "C")
        assert score_to_grade(65) in ("C", "D")
        assert score_to_grade(45) in ("D", "F")
        assert score_to_grade(25) == "F"
        assert score_to_grade(None) == "N/A"

    def test_estimate_bounce_rate(self):
        from api.services.template_engine import estimate_bounce_rate
        fast = estimate_bounce_rate(1500)
        slow = estimate_bounce_rate(8000)
        assert isinstance(fast, str) and len(fast) > 0
        assert isinstance(slow, str) and len(slow) > 0

    def test_estimate_monthly_loss(self):
        from api.services.template_engine import estimate_monthly_loss
        result = estimate_monthly_loss("restaurant", 40)
        assert isinstance(result, str) and len(result) > 0

    def test_simple_render(self):
        from api.services.template_engine import simple_render
        result = simple_render(
            "Hello {{name}}, your score is {{score}}",
            {"name": "Joe", "score": "42"},
        )
        assert "Joe" in result
        assert "42" in result


# ═══════════════════════════════════════════════════════════
# EMAIL TRACKER — URL BUILDERS + INJECTION
# ═══════════════════════════════════════════════════════════

class TestEmailTrackerUrls:
    """Test tracking URL generation."""

    def test_pixel_url(self):
        from api.services.email_tracker import get_tracking_pixel_url
        url = get_tracking_pixel_url("abc-123")
        assert "abc-123" in url
        assert ".png" in url

    def test_click_url(self):
        from api.services.email_tracker import get_click_tracking_url
        url = get_click_tracking_url("abc-123", "https://example.com")
        assert "abc-123" in url
        assert "example.com" in url

    def test_unsubscribe_url(self):
        from api.services.email_tracker import get_unsubscribe_url
        url = get_unsubscribe_url("abc-123")
        assert "abc-123" in url
        assert "unsubscribe" in url

    def test_inject_tracking_replaces_placeholders(self):
        from api.services.email_tracker import inject_tracking
        html = """<html><body>
        <a href="https://example.com">Visit</a>
        <img src="{{ tracking_pixel_url }}" />
        <a href="{{ unsubscribe_url }}">Unsubscribe</a>
        </body></html>"""
        result = inject_tracking(html, "track-id-1")
        assert "{{ tracking_pixel_url }}" not in result
        assert "{{ unsubscribe_url }}" not in result
        assert "track-id-1" in result

    def test_inject_tracking_rewrites_links(self):
        from api.services.email_tracker import inject_tracking
        html = '<a href="https://example.com">Click here</a>'
        result = inject_tracking(html, "track-id-1")
        assert "track/click/track-id-1" in result

    def test_inject_tracking_skips_mailto(self):
        from api.services.email_tracker import inject_tracking
        html = '<a href="mailto:joe@test.com">Email</a>'
        result = inject_tracking(html, "track-id-1")
        assert "mailto:joe@test.com" in result


# ═══════════════════════════════════════════════════════════
# ADVANCED FEATURES
# ═══════════════════════════════════════════════════════════

class TestSeasonalHooks:
    """Test industry seasonal hooks."""

    def test_known_industry_returns_string_or_none(self):
        from api.services.advanced_features import get_seasonal_hook
        hook = get_seasonal_hook("restaurant", "Manor")
        # Might be None if current month has no hook for restaurants
        if hook:
            assert isinstance(hook, str)
            assert len(hook) > 5

    def test_unknown_industry_returns_none(self):
        from api.services.advanced_features import get_seasonal_hook
        assert get_seasonal_hook("basket_weaving", "Manor") is None


class TestCompetitorComparison:
    """Test competitor comparison builder."""

    def test_with_competitors(self):
        from api.services.advanced_features import build_competitor_comparison
        competitors = [
            {"name": "Competitor A", "score": 75, "url": "https://a.com"},
            {"name": "Competitor B", "score": 82, "url": "https://b.com"},
        ]
        result = build_competitor_comparison(45, competitors)
        assert isinstance(result, dict)

    def test_empty_competitors(self):
        from api.services.advanced_features import build_competitor_comparison
        result = build_competitor_comparison(45, [])
        assert isinstance(result, dict)


class TestReviewThemes:
    """Test review theme analysis."""

    def test_mixed_complaints(self):
        from api.services.advanced_features import analyze_review_themes
        reviews = [
            "The website is so slow and hard to use on my phone",
            "I couldn't find their hours or menu online",
            "Great food but their website looks like it's from 2010",
        ]
        result = analyze_review_themes(reviews)
        assert isinstance(result, dict)


class TestBrokenThings:
    """Test broken things detection from audit data."""

    def test_detect_slow_site(self):
        from api.services.advanced_features import detect_broken_things
        from unittest.mock import MagicMock

        audit = MagicMock()
        audit.perf_score = 35
        audit.page_size_kb = 3000
        audit.request_count = 120
        audit.mobile_friendly = False
        audit.has_meta_desc = False
        audit.has_schema = False
        audit.ssl_valid = False
        audit.design_sins = ["copyright 2017", "lorem ipsum"]
        audit.fcp_ms = 4500
        audit.lcp_ms = 7000
        audit.cms_platform = "wordpress"
        audit.tech_stack = ["WordPress", "jQuery"]

        result = detect_broken_things(audit)
        assert isinstance(result, list)
        assert len(result) > 0  # should find multiple issues
