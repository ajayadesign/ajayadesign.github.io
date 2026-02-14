#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════
#  AjayaDesign — Automated Client Site Builder
#  Triggered by n8n webhook → runner sidecar
#
#  Usage: ./build_and_deploy.sh <CLIENT_NAME> <NICHE> <GOALS> [EMAIL]
# ═══════════════════════════════════════════════════════════════════
set -euo pipefail

# ── Configuration ──────────────────────────────────────────────────
GITHUB_ORG="ajayadesign"
BASE_DIR="/workspace/builds"
TEMPLATE_DIR="/workspace/automation/template"
TELEGRAM_BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-}"
TELEGRAM_CHAT_ID="${TELEGRAM_CHAT_ID:-}"

# ── Input ──────────────────────────────────────────────────────────
CLIENT_NAME="${1:?Error: CLIENT_NAME is required}"
NICHE="${2:?Error: NICHE is required}"
GOALS="${3:?Error: GOALS is required}"
EMAIL="${4:-not-provided}"

# Sanitise client name for use as repo/directory name
REPO_NAME=$(echo "${CLIENT_NAME}" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9-]/-/g' | sed 's/--*/-/g' | sed 's/^-//;s/-$//')
REPO_FULL="${GITHUB_ORG}/${REPO_NAME}"
PROJECT_DIR="${BASE_DIR}/${REPO_NAME}"
LIVE_URL="https://ajayadesign.github.io/${REPO_NAME}"

log() { echo "[$(date '+%H:%M:%S')] $*"; }

# ── Step 1: Create GitHub Repo ─────────────────────────────────────
log "🏗️  Step 1 — Creating GitHub repo: ${REPO_FULL}"

if gh repo view "${REPO_FULL}" &>/dev/null; then
  log "⚠️  Repo ${REPO_FULL} already exists, cloning..."
  git clone "https://github.com/${REPO_FULL}.git" "${PROJECT_DIR}" 2>/dev/null || true
else
  gh repo create "${REPO_FULL}" --public --add-readme --clone --description "Client site for ${CLIENT_NAME} — built by AjayaDesign" -- "${PROJECT_DIR}"
fi

cd "${PROJECT_DIR}"

# ── Step 2: AI Build — Generate Landing Page ───────────────────────
log "🤖  Step 2 — Generating landing page for ${CLIENT_NAME} (${NICHE})"

AI_PROMPT="You are building a professional landing page for a client of AjayaDesign.

Client: ${CLIENT_NAME}
Industry/Niche: ${NICHE}
Goals: ${GOALS}
Contact Email: ${EMAIL}

Requirements:
- Single-page index.html using Tailwind CSS CDN
- Dark, modern, high-performance design matching AjayaDesign's engineering aesthetic
- Sections: Hero, About/Services, Features/Benefits, Contact/CTA
- Mobile-responsive, accessible (WCAG 2 AA), semantic HTML
- JetBrains Mono for headings, Inter for body text (Google Fonts)
- SEO meta tags, Open Graph tags
- Smooth scroll, subtle animations
- Footer crediting 'Built by AjayaDesign'
- All text content tailored to the client's niche and goals
- Do NOT use any placeholder text — write real, compelling copy

Output ONLY the complete index.html file content, nothing else."

# Try opencode first, fall back to writing a template-based page
if command -v opencode &>/dev/null; then
  log "  Using opencode for AI generation..."
  echo "${AI_PROMPT}" | opencode -p "Generate the complete index.html" > "${PROJECT_DIR}/index.html"
elif [ -f "${TEMPLATE_DIR}/index.html" ]; then
  log "  Using template with variable substitution..."
  sed \
    -e "s/{{CLIENT_NAME}}/${CLIENT_NAME}/g" \
    -e "s/{{NICHE}}/${NICHE}/g" \
    -e "s/{{GOALS}}/${GOALS}/g" \
    -e "s/{{EMAIL}}/${EMAIL}/g" \
    "${TEMPLATE_DIR}/index.html" > "${PROJECT_DIR}/index.html"
else
  log "  ⚠️  No AI tool or template found. Generating minimal page..."
  cat > "${PROJECT_DIR}/index.html" << HTMLEOF
<!DOCTYPE html>
<html lang="en" class="scroll-smooth">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${CLIENT_NAME} — Professional ${NICHE} Services</title>
  <meta name="description" content="${GOALS}">
  <script src="https://cdn.tailwindcss.com"></script>
  <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
  <script>
    tailwind.config = {
      theme: {
        extend: {
          fontFamily: { mono: ['JetBrains Mono', 'monospace'], sans: ['Inter', 'sans-serif'] },
          colors: { brand: '#ED1C24', surface: '#0A0A0F', 'surface-alt': '#111118' }
        }
      }
    }
  </script>
</head>
<body class="bg-surface text-gray-200 font-sans antialiased">

  <!-- Hero -->
  <section class="min-h-screen flex items-center justify-center px-6">
    <div class="text-center max-w-3xl">
      <h1 class="font-mono text-4xl md:text-6xl font-bold text-white mb-6">${CLIENT_NAME}</h1>
      <p class="text-xl text-gray-400 mb-8">${GOALS}</p>
      <a href="#contact" class="inline-block px-8 py-3 bg-brand text-white font-mono font-bold rounded hover:opacity-90 transition">Get Started</a>
    </div>
  </section>

  <!-- About -->
  <section class="py-24 px-6 bg-surface-alt">
    <div class="max-w-4xl mx-auto text-center">
      <h2 class="font-mono text-3xl font-bold text-white mb-6">Professional ${NICHE} Services</h2>
      <p class="text-gray-400 text-lg leading-relaxed">${GOALS}</p>
    </div>
  </section>

  <!-- Contact -->
  <section id="contact" class="py-24 px-6">
    <div class="max-w-xl mx-auto text-center">
      <h2 class="font-mono text-3xl font-bold text-white mb-6">Get in Touch</h2>
      <p class="text-gray-400 mb-8">Ready to work together? Reach out today.</p>
      <a href="mailto:${EMAIL}" class="inline-block px-8 py-3 bg-brand text-white font-mono font-bold rounded hover:opacity-90 transition">${EMAIL}</a>
    </div>
  </section>

  <!-- Footer -->
  <footer class="py-8 border-t border-gray-800 text-center">
    <p class="text-gray-500 text-sm font-mono">
      &copy; $(date +%Y) ${CLIENT_NAME} &middot;
      Built by <a href="https://ajayadesign.github.io" class="text-brand hover:underline">AjayaDesign</a>
    </p>
  </footer>

</body>
</html>
HTMLEOF
fi

log "  ✅ index.html generated ($(wc -c < "${PROJECT_DIR}/index.html") bytes)"

# ── Step 3: Engineering Checklist (QA) ─────────────────────────────
log "🧪  Step 3 — Running Playwright + axe accessibility tests"

cd "${PROJECT_DIR}"

# Initialize package.json and install test deps
npm init -y --silent
npm install --save-dev @playwright/test @axe-core/playwright --silent
npx playwright install --with-deps chromium --silent

# Create Playwright config
cat > "${PROJECT_DIR}/playwright.config.js" << 'PWCONFIG'
const { defineConfig, devices } = require('@playwright/test');
module.exports = defineConfig({
  testDir: './tests',
  fullyParallel: true,
  retries: 0,
  reporter: 'list',
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
PWCONFIG

# Create accessibility test suite
mkdir -p "${PROJECT_DIR}/tests"
cat > "${PROJECT_DIR}/tests/a11y.spec.js" << 'TESTEOF'
const { test, expect } = require('@playwright/test');
const AxeBuilder = require('@axe-core/playwright').default;

test('page loads and has content', async ({ page }) => {
  await page.goto('/');
  await expect(page.locator('h1')).toBeVisible();
  await expect(page.locator('body')).not.toBeEmpty();
});

test('no horizontal overflow on any viewport', async ({ page }) => {
  await page.goto('/');
  const overflow = await page.evaluate(() =>
    document.documentElement.scrollWidth > document.documentElement.clientWidth
  );
  expect(overflow).toBe(false);
});

test('axe accessibility audit — zero critical or serious violations', async ({ page }) => {
  await page.goto('/');
  await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
  await page.waitForTimeout(500);

  const results = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'best-practice'])
    .analyze();

  const critical = results.violations.filter(
    v => v.impact === 'critical' || v.impact === 'serious'
  );

  if (critical.length > 0) {
    console.log('\n🔴 Critical/Serious violations:');
    critical.forEach(v => {
      console.log(`  [${v.impact}] ${v.id}: ${v.description}`);
      v.nodes.forEach(n => console.log(`    → ${n.html.substring(0, 120)}`));
    });
  }

  expect(critical).toHaveLength(0);
});

test('all links have valid href', async ({ page }) => {
  await page.goto('/');
  const links = page.locator('a[href]');
  const count = await links.count();
  for (let i = 0; i < count; i++) {
    const href = await links.nth(i).getAttribute('href');
    expect(href).toBeTruthy();
    expect(href).not.toBe('#');
  }
});
TESTEOF

# Install serve for the test web server
npm install --save-dev serve --silent

# ── GATEKEEPER: Run tests ──
log "  Running tests..."
if ! npx playwright test; then
  log "❌ TESTS FAILED — aborting deployment. Site will NOT be pushed."
  # Notify failure via Telegram
  if [ -n "${TELEGRAM_BOT_TOKEN}" ] && [ -n "${TELEGRAM_CHAT_ID}" ]; then
    curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
      -d chat_id="${TELEGRAM_CHAT_ID}" \
      -d parse_mode="Markdown" \
      -d text="❌ *AjayaDesign Build Failed*%0A%0AClient: \`${CLIENT_NAME}\`%0ANiche: ${NICHE}%0A%0ATests failed — deployment blocked." \
      > /dev/null 2>&1
  fi
  exit 1
fi

log "  ✅ All tests passed!"

# ── Step 4: Deploy ─────────────────────────────────────────────────
log "🚀  Step 4 — Deploying to GitHub Pages"

cd "${PROJECT_DIR}"

# Create .gitignore
cat > .gitignore << 'GIEOF'
node_modules/
test-results/
playwright-report/
GIEOF

git add -A
git commit -m "feat: initial site build for ${CLIENT_NAME}

Niche: ${NICHE}
Goals: ${GOALS}
Built by AjayaDesign automation pipeline"

git push -u origin main

# Enable GitHub Pages on main branch
log "  Enabling GitHub Pages..."
gh api -X POST "repos/${REPO_FULL}/pages" \
  -f source='{"branch":"main","path":"/"}' \
  --silent 2>/dev/null || \
gh api -X PUT "repos/${REPO_FULL}/pages" \
  -f source='{"branch":"main","path":"/"}' \
  --silent 2>/dev/null || \
log "  ⚠️  Pages may already be enabled or needs manual setup"

# ── Step 5: Add as submodule to main AjayaDesign site ──────────────
log "📎  Step 5 — Adding as submodule to ajayadesign.github.io"

MAIN_SITE="/workspace/ajayadesign.github.io"
if [ -d "${MAIN_SITE}" ]; then
  cd "${MAIN_SITE}"
  if [ ! -d "${REPO_NAME}" ]; then
    git submodule add "https://github.com/${REPO_FULL}.git" "${REPO_NAME}"
    git add -A
    git commit -m "feat: add ${CLIENT_NAME} portfolio as submodule"
    git push
    log "  ✅ Submodule added to main site"
  else
    log "  ⚠️  Submodule ${REPO_NAME} already exists"
  fi
fi

# ── Step 6: Notification ──────────────────────────────────────────
log "📬  Step 6 — Sending Telegram notification"

if [ -n "${TELEGRAM_BOT_TOKEN}" ] && [ -n "${TELEGRAM_CHAT_ID}" ]; then
  MESSAGE="✅ *AjayaDesign — New Site Deployed!*

🏢 *Client:* \`${CLIENT_NAME}\`
🏷️ *Niche:* ${NICHE}
🎯 *Goals:* ${GOALS}
📧 *Email:* ${EMAIL}

🔗 *Live URL:* [${LIVE_URL}](${LIVE_URL})
📦 *Repo:* [github.com/${REPO_FULL}](https://github.com/${REPO_FULL})

_Automated by AjayaDesign Pipeline_"

  curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
    -d chat_id="${TELEGRAM_CHAT_ID}" \
    -d parse_mode="Markdown" \
    -d text="${MESSAGE}" \
    > /dev/null 2>&1

  log "  ✅ Telegram notification sent"
else
  log "  ⚠️  TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set, skipping notification"
fi

# ── Done ───────────────────────────────────────────────────────────
log "═══════════════════════════════════════════════════════"
log "✅  BUILD COMPLETE: ${CLIENT_NAME}"
log "   Live: ${LIVE_URL}"
log "   Repo: https://github.com/${REPO_FULL}"
log "═══════════════════════════════════════════════════════"
