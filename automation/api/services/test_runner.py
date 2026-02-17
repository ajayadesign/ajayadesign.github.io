"""
AjayaDesign Automation — Playwright test runner service.
Generates test files, runs them via subprocess, parses results.
"""

import os
import re
import logging

from api.services.git import run_cmd, try_cmd

logger = logging.getLogger(__name__)

PLAYWRIGHT_CONFIG = """const { defineConfig, devices } = require('@playwright/test');
module.exports = defineConfig({
  testDir: './tests',
  fullyParallel: true,
  retries: 0,
  reporter: [['list'], ['json', { outputFile: 'test-results.json' }]],
  use: { baseURL: 'http://localhost:9333' },
  webServer: {
    command: 'npx serve . -l 9333 -s',
    port: 9333,
    reuseExistingServer: false,
  },
  projects: [
    { name: 'Desktop', use: { ...devices['Desktop Chrome'] } },
    { name: 'Mobile', use: { ...devices['Pixel 5'] } },
  ],
});
"""


def generate_page_test(slug: str, title: str, route: str) -> str:
    """Generate a Playwright test file for a single page."""
    return f"""const {{ test, expect }} = require('@playwright/test');
const AxeBuilder = require('@axe-core/playwright').default;

test.describe('{title} page ({slug})', () => {{
  test('loads and has content', async ({{ page }}) => {{
    await page.goto('{route}');
    await expect(page.locator('body')).not.toBeEmpty();
    const h1 = page.locator('h1').first();
    if (await h1.count()) await expect(h1).toBeVisible();
  }});

  test('no horizontal overflow', async ({{ page }}) => {{
    await page.goto('{route}');
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth > document.documentElement.clientWidth
    );
    expect(overflow).toBe(false);
  }});

  test('axe accessibility — zero critical/serious violations', async ({{ page }}) => {{
    await page.goto('{route}');
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
    await page.waitForTimeout(500);
    const results = await new AxeBuilder({{ page }})
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'best-practice'])
      .analyze();
    const critical = results.violations.filter(
      (v) => v.impact === 'critical' || v.impact === 'serious'
    );
    if (critical.length > 0) {{
      console.log('\\n🔴 Critical/Serious violations on {route}:');
      critical.forEach((v) => {{
        console.log('  [' + v.impact + '] ' + v.id + ': ' + v.description);
        v.nodes.forEach((n) => console.log('    → ' + n.html.substring(0, 120)));
      }});
    }}
    expect(critical).toHaveLength(0);
  }});

  test('all links have valid href', async ({{ page }}) => {{
    await page.goto('{route}');
    const links = page.locator('a[href]');
    const count = await links.count();
    for (let i = 0; i < count; i++) {{
      const href = await links.nth(i).getAttribute('href');
      expect(href).toBeTruthy();
      expect(href).not.toBe('#');
    }}
  }});

  test('SEO: exactly one h1 tag', async ({{ page }}) => {{
    await page.goto('{route}');
    const h1Count = await page.locator('h1').count();
    expect(h1Count, 'Page must have exactly 1 <h1> tag, found ' + h1Count).toBe(1);
  }});

  test('SEO: heading hierarchy (no skipped levels)', async ({{ page }}) => {{
    await page.goto('{route}');
    const headings = await page.evaluate(() => {{
      const els = document.querySelectorAll('h1, h2, h3, h4, h5, h6');
      return Array.from(els).map(el => parseInt(el.tagName[1]));
    }});
    for (let i = 1; i < headings.length; i++) {{
      const gap = headings[i] - headings[i - 1];
      expect(gap, 'Heading level skipped: h' + headings[i-1] + ' → h' + headings[i]).toBeLessThanOrEqual(1);
    }}
  }});

  test('SEO: all images have descriptive alt text', async ({{ page }}) => {{
    await page.goto('{route}');
    const images = page.locator('img');
    const count = await images.count();
    for (let i = 0; i < count; i++) {{
      const alt = await images.nth(i).getAttribute('alt');
      expect(alt, 'Image missing alt text').toBeTruthy();
      expect(alt.length, 'Alt text too short: "' + alt + '"').toBeGreaterThan(4);
    }}
  }});

  test('SEO: page has a title tag', async ({{ page }}) => {{
    await page.goto('{route}');
    const title = await page.title();
    expect(title, 'Page must have a <title> tag').toBeTruthy();
    expect(title.length, 'Title too short: "' + title + '"').toBeGreaterThan(10);
    expect(title.length, 'Title too long (' + title.length + ' chars)').toBeLessThan(65);
  }});
}});
"""


def generate_integration_test(pages: list[dict]) -> str:
    """Generate cross-page integration test."""
    page_checks = "\n\n".join([
        f"    await page.goto('{_route(p)}');\n"
        f"    await expect(page.locator('nav')).toBeVisible();\n"
        f"    await expect(page.locator('footer')).toBeVisible();"
        for p in pages
    ])

    nav_checks = "\n".join([
        f"    const link_{p['slug'].replace('-', '_')} = page.locator('nav a[href=\"{_nav_href(p)}\"]');\n"
        f"    if (await link_{p['slug'].replace('-', '_')}.count()) "
        f"await expect(link_{p['slug'].replace('-', '_')}).toBeVisible();"
        for p in pages
    ])

    return f"""const {{ test, expect }} = require('@playwright/test');

test.describe('Site Integration', () => {{
  test('nav and footer present on all pages', async ({{ page }}) => {{
{page_checks}
  }});

  test('nav links are present on homepage', async ({{ page }}) => {{
    await page.goto('/');
{nav_checks}
  }});
}});
"""


def setup_tests(project_dir: str, pages: list[dict]) -> None:
    """Write Playwright config and test files to project directory (sync)."""
    # package.json
    pkg_path = os.path.join(project_dir, "package.json")
    if not os.path.exists(pkg_path):
        with open(pkg_path, "w") as f:
            f.write('{"name": "client-site", "private": true}')

    # Playwright config
    with open(os.path.join(project_dir, "playwright.config.js"), "w") as f:
        f.write(PLAYWRIGHT_CONFIG)

    # Test directory
    test_dir = os.path.join(project_dir, "tests")
    os.makedirs(test_dir, exist_ok=True)

    # Per-page tests
    for page in pages:
        slug = page["slug"]
        title = page.get("title", slug)
        route = "/" if slug == "index" else f"/{slug}.html"
        spec_path = os.path.join(test_dir, f"{slug}.spec.js")
        with open(spec_path, "w") as f:
            f.write(generate_page_test(slug, title, route))

    # Integration test
    with open(os.path.join(test_dir, "integration.spec.js"), "w") as f:
        f.write(generate_integration_test(pages))


async def run_tests(project_dir: str) -> dict:
    """Run all Playwright tests, return structured results."""
    ok, output = await try_cmd(
        "npx playwright test 2>&1", cwd=project_dir, timeout=120
    )

    passed = ok and "failed" not in output
    failures = _extract_failures(output) if not passed else []
    failed_pages = _extract_failed_pages(output) if not passed else []

    return {
        "passed": passed,
        "output": output,
        "failures": failures,
        "failed_pages": failed_pages,
    }


async def run_page_test(project_dir: str, slug: str) -> dict:
    """Run tests for a single page."""
    ok, output = await try_cmd(
        f"npx playwright test tests/{slug}.spec.js 2>&1",
        cwd=project_dir,
        timeout=90,
    )

    passed = ok and "failed" not in output
    failures = _extract_failures(output) if not passed else []

    return {"passed": passed, "output": output, "failures": failures}


def _extract_failures(output: str) -> list[str]:
    failures = []
    for line in output.split("\n"):
        trimmed = line.strip()
        if not trimmed or trimmed.startswith("✓") or trimmed.startswith("·"):
            continue
        if re.search(
            r"color-contrast|\[serious\]|\[critical\]|href=\"#\"|Error:|Expected.*Received|scrollWidth",
            trimmed,
            re.I,
        ):
            failures.append(trimmed)
    return failures


def _extract_failed_pages(output: str) -> list[str]:
    """Extract page slugs from failed test output."""
    slugs = set()
    for m in re.finditer(r"(?:tests/|/)(\w[\w-]*)\.spec\.js", output):
        slugs.add(m.group(1))
    return list(slugs)


def _route(page: dict) -> str:
    return "/" if page["slug"] == "index" else f"/{page['slug']}.html"


def _nav_href(page: dict) -> str:
    """Return the relative href as it appears in nav HTML (after link rewriting)."""
    return "index.html" if page["slug"] == "index" else f"{page['slug']}.html"
