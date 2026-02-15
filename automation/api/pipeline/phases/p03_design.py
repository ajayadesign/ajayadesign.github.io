"""
Phase 3: Design System Generation — Tailwind config + shared nav/footer.
"""

import re
import logging
from datetime import datetime

from api.services.ai import call_ai, extract_json
from api.pipeline.prompts import DESIGNER_SYSTEM, designer_create

logger = logging.getLogger(__name__)


async def generate_design_system(blueprint: dict, *, creative_spec: dict | None = None, log_fn=None) -> dict:
    """Call AI to produce design system, validate WCAG, build sharedHead."""
    _log(log_fn, "🎨 Generating design system (Tailwind config + shared nav/footer)")

    raw = await call_ai(
        messages=[
            {"role": "system", "content": DESIGNER_SYSTEM},
            {"role": "user", "content": designer_create(blueprint)},
        ],
        temperature=0.5,
        max_tokens=6000,
    )

    ds = extract_json(raw)

    # Validate required keys
    for key in ("tailwindConfig", "googleFontsUrl", "navHtml", "footerHtml"):
        if not ds.get(key):
            raise ValueError(f"Design system missing required key: {key}")

    # Defaults
    ds.setdefault("bodyClass", "bg-surface text-textMain font-body antialiased")
    ds.setdefault("activeNavClass", "text-primary font-bold")
    ds.setdefault("inactiveNavClass", "text-textMuted hover:text-primary transition")
    ds.setdefault("mobileMenuJs", "")
    ds["siteName"] = blueprint.get("siteName", "")

    # ── WCAG contrast validation & auto-fix ──
    cta_colors = _extract_colors(ds["tailwindConfig"], ["cta", "primary", "accent"])
    for name, hex_val in cta_colors.items():
        if hex_val and not _passes_contrast(hex_val, "#ffffff", 4.5):
            darkened = _darken_until_contrast(hex_val, "#ffffff", 4.5)
            _log(log_fn, f"    ⚠️ {name} ({hex_val}) fails WCAG AA vs white → fixed to {darkened}")
            ds["tailwindConfig"] = re.sub(
                rf"(['\"]?){re.escape(hex_val)}\1",
                f"'{darkened}'",
                ds["tailwindConfig"],
                flags=re.IGNORECASE,
            )

    # Build shared <head>
    ds["sharedHead"] = _build_shared_head(ds, blueprint)

    _log(log_fn, "  ✅ Design system ready")
    _log(log_fn, f"    Nav: {len(ds['navHtml'])} chars, Footer: {len(ds['footerHtml'])} chars")

    return ds


# ── WCAG Contrast Utilities ─────────────────────────────────


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = h[0] * 2 + h[1] * 2 + h[2] * 2
    n = int(h[:6], 16)
    return (n >> 16) & 255, (n >> 8) & 255, n & 255


def _luminance(rgb: tuple[int, int, int]) -> float:
    channels = []
    for c in rgb:
        s = c / 255
        channels.append(s / 12.92 if s <= 0.03928 else ((s + 0.055) / 1.055) ** 2.4)
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def _contrast_ratio(hex1: str, hex2: str) -> float:
    l1 = _luminance(_hex_to_rgb(hex1))
    l2 = _luminance(_hex_to_rgb(hex2))
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def _passes_contrast(fg: str, bg: str, ratio: float) -> bool:
    return _contrast_ratio(fg, bg) >= ratio


def _darken_until_contrast(hex_color: str, against: str, target: float) -> str:
    r, g, b = _hex_to_rgb(hex_color)
    for _ in range(100):
        candidate = f"#{r:02x}{g:02x}{b:02x}"
        if _contrast_ratio(candidate, against) >= target:
            return candidate
        r = max(0, r - 5)
        g = max(0, g - 5)
        b = max(0, b - 5)
    return "#1a1a1a"


def _extract_colors(config_str: str, names: list[str]) -> dict[str, str]:
    colors = {}
    for name in names:
        match = re.search(
            rf"['\"]?{name}['\"]?\s*:\s*['\"]?(#[0-9A-Fa-f]{{3,8}})['\"]?", config_str
        )
        if match:
            colors[name] = match.group(1)
    return colors


def _build_shared_head(ds: dict, blueprint: dict) -> str:
    if ds.get("sharedHead") and "tailwindcss" in ds["sharedHead"]:
        return ds["sharedHead"]

    return f"""  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <script src="https://cdn.tailwindcss.com"></script>
  <link href="{ds['googleFontsUrl']}" rel="stylesheet">
  <link href="https://unpkg.com/aos@2.3.4/dist/aos.css" rel="stylesheet">
  <script>
    {ds['tailwindConfig']}
  </script>
  <style>
    html {{ scroll-behavior: smooth; }}
    body {{ overflow-x: hidden; }}
    ::-webkit-scrollbar {{ width: 6px; }}
    ::-webkit-scrollbar-track {{ background: transparent; }}
    ::-webkit-scrollbar-thumb {{ background: #333; border-radius: 3px; }}
    .gradient-text {{
      background: linear-gradient(135deg, var(--tw-gradient-from, #fff), var(--tw-gradient-to, #ccc));
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
    }}
    .glass {{
      background: rgba(255,255,255,0.05);
      backdrop-filter: blur(16px);
      -webkit-backdrop-filter: blur(16px);
      border: 1px solid rgba(255,255,255,0.08);
    }}
    .noise::before {{
      content: '';
      position: absolute;
      inset: 0;
      background: url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.03'/%3E%3C/svg%3E");
      pointer-events: none;
      z-index: 0;
    }}
    .counter {{ display: inline-block; }}
  </style>
  <script src="https://unpkg.com/aos@2.3.4/dist/aos.js"></script>"""


def _log(fn, msg):
    if fn:
        fn(msg)
    logger.info(msg)
