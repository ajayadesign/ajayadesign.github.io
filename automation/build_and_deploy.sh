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
TEMPLATE_DIR="/workspace/ajayadesign.github.io/automation/template"
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

# Ensure git identity is set (needed inside Docker containers)
git config --global user.email "ajayadahal1000@gmail.com"
git config --global user.name "Ajaya Dahal"
git config --global --add safe.directory '*'

# Configure git to use GH_TOKEN for HTTPS auth
if [ -n "${GH_TOKEN}" ]; then
  git config --global url."https://${GH_TOKEN}@github.com/".insteadOf "https://github.com/"
fi

# Ensure builds directory exists
mkdir -p "${BASE_DIR}"

# ── Step 1: Create GitHub Repo ─────────────────────────────────────
log "[STEP:1:6:repo] 🏗️ Creating GitHub repo: ${REPO_FULL}"

if gh repo view "${REPO_FULL}" &>/dev/null; then
  log "⚠️  Repo ${REPO_FULL} already exists, cloning..."
  git clone "https://github.com/${REPO_FULL}.git" "${PROJECT_DIR}" 2>/dev/null || true
else
  log "Creating repo under org ${GITHUB_ORG}..."
  gh repo create "${REPO_FULL}" --public --add-readme \
    --description "Client site for ${CLIENT_NAME} — built by AjayaDesign" || {
    log "❌ Failed to create repo. Check GH_TOKEN permissions (needs Administration: Write for org repos)."
    exit 1
  }
  sleep 3  # Give GitHub API a moment
  git clone "https://github.com/${REPO_FULL}.git" "${PROJECT_DIR}"
fi

cd "${PROJECT_DIR}"

# ── Step 2: AI Build — Generate Landing Page ───────────────────────
log "[STEP:2:6:generate] 🤖 Generating landing page for ${CLIENT_NAME} (${NICHE})"

GH_TOKEN="${GH_TOKEN:-}"
AI_MODEL="${AI_MODEL:-gpt-4o}"
AI_API="https://models.inference.ai.azure.com/chat/completions"

SYSTEM_PROMPT='You are the Lead Web Designer at AjayaDesign, a web design studio known for high-performance, dark-themed, engineering-precision sites.

You output ONLY raw HTML. No markdown fences, no explanations, no commentary.

Design rules you MUST follow:
- Single complete index.html file using Tailwind CSS CDN (<script src="https://cdn.tailwindcss.com"></script>)
- Inline Tailwind config with custom colors: brand-btn (#991B1B), brand-link (#FF6B6B), surface (#0A0A0F), surface-alt (#111118), electric-blue (#00D4FF)
- Google Fonts: JetBrains Mono for headings/mono, Inter for body
- Dark background (bg-surface), light text (text-gray-200)
- WCAG 2 AA accessible: contrast ratios ≥ 4.5:1 for normal text, ≥ 3:1 for large text
- CRITICAL: buttons and CTA links MUST use bg-brand-btn (#991B1B) with text-white — NEVER use #ED1C24 as a background with light text (it fails contrast)
- Do NOT use text-gray-600 or text-gray-500 on dark backgrounds — use text-gray-400 minimum
- CRITICAL: NEVER use href="#" — all links must have meaningful destinations (use section IDs like href="#about", href="#services", href="#contact", or real URLs like mailto: links)
- All interactive elements must have visible focus states
- Mobile-responsive with proper viewport meta tag
- Smooth scroll (class="scroll-smooth" on html)
- Semantic HTML5 (header, main, section, footer)
- SEO: title, meta description, Open Graph tags
- Sections: Hero with CTA, About/Services, Features/Benefits (3-column grid), Contact/CTA, Footer
- Every section must have an id attribute matching its nav links (e.g. id="about", id="services", id="contact")
- Footer must include: "Built by <a href=https://ajayadesign.github.io>AjayaDesign</a>"
- All copy must be real, compelling, tailored to the client — NO placeholder text like Lorem ipsum
- Subtle CSS animations for visual polish'

USER_PROMPT="Build a professional landing page for this client:

Business Name: ${CLIENT_NAME}
Industry/Niche: ${NICHE}
Goals: ${GOALS}
Contact Email: ${EMAIL}

Output the complete index.html file. Nothing else."

ai_generated=false

# ── Method 1: GitHub Models API (free with GH_TOKEN) ──
if [ -n "${GH_TOKEN}" ]; then
  log "[AI:CALL] Calling GitHub Models API (${AI_MODEL})..."

  # Build JSON payload with jq to handle escaping safely
  PAYLOAD=$(jq -n \
    --arg model "${AI_MODEL}" \
    --arg system "${SYSTEM_PROMPT}" \
    --arg user "${USER_PROMPT}" \
    '{
      model: $model,
      messages: [
        { role: "system", content: $system },
        { role: "user", content: $user }
      ],
      max_tokens: 8000,
      temperature: 0.7
    }')

  HTTP_CODE=$(curl -s -w "%{http_code}" -o /tmp/ai_response.json \
    -X POST "${AI_API}" \
    -H "Authorization: Bearer ${GH_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "${PAYLOAD}")

  if [ "${HTTP_CODE}" = "200" ]; then
    # Extract HTML content, strip any markdown fences the model might add
    jq -r '.choices[0].message.content' /tmp/ai_response.json \
      | sed '/^```html$/d' | sed '/^```$/d' \
      > "${PROJECT_DIR}/index.html"

    # Verify we got valid HTML
    if grep -q '<!DOCTYPE\|<html' "${PROJECT_DIR}/index.html"; then
      FILESIZE=$(wc -c < "${PROJECT_DIR}/index.html")
      log "[AI:DONE] ✅ AI generated index.html (${FILESIZE} bytes)"
      ai_generated=true
    else
      log "[AI:ERROR] ⚠️ AI response didn't contain valid HTML, falling back..."
    fi
  else
    log "[AI:ERROR] ⚠️ GitHub Models API returned HTTP ${HTTP_CODE}, falling back..."
    [ -f /tmp/ai_response.json ] && cat /tmp/ai_response.json | head -5
  fi
fi

# ── Method 2: Template fallback ──
if [ "${ai_generated}" = false ] && [ -f "${TEMPLATE_DIR}/index.html" ]; then
  log "[AI:FALLBACK] Using template with variable substitution..."
  sed \
    -e "s/{{CLIENT_NAME}}/${CLIENT_NAME}/g" \
    -e "s/{{NICHE}}/${NICHE}/g" \
    -e "s/{{GOALS}}/${GOALS}/g" \
    -e "s/{{EMAIL}}/${EMAIL}/g" \
    "${TEMPLATE_DIR}/index.html" > "${PROJECT_DIR}/index.html"
  ai_generated=true
fi

# ── Method 3: Inline fallback (always works) ──
if [ "${ai_generated}" = false ]; then
  log "[AI:FALLBACK] ⚠️ Using inline fallback page..."
  YEAR=$(date +%Y)
  cat > "${PROJECT_DIR}/index.html" << HTMLEOF
<!DOCTYPE html>
<html lang="en" class="scroll-smooth">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${CLIENT_NAME} — Professional ${NICHE} Services</title>
  <meta name="description" content="${GOALS}">
  <meta property="og:title" content="${CLIENT_NAME}">
  <meta property="og:description" content="${GOALS}">
  <meta property="og:type" content="website">
  <script src="https://cdn.tailwindcss.com"></script>
  <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
  <script>
    tailwind.config = {
      theme: {
        extend: {
          fontFamily: { mono: ['JetBrains Mono', 'monospace'], sans: ['Inter', 'sans-serif'] },
          colors: { brand: '#ED1C24', 'brand-btn': '#991B1B', 'brand-link': '#FF6B6B', surface: '#0A0A0F', 'surface-alt': '#111118' }
        }
      }
    }
  </script>
</head>
<body class="bg-surface text-gray-200 font-sans antialiased">
  <header class="fixed top-0 w-full bg-surface/80 backdrop-blur border-b border-gray-800 z-50">
    <nav class="max-w-6xl mx-auto px-6 py-4 flex justify-between items-center">
      <span class="font-mono font-bold text-white">${CLIENT_NAME}</span>
      <a href="#contact" class="px-4 py-2 bg-brand-btn text-white font-mono text-sm rounded hover:opacity-90 transition">Contact</a>
    </nav>
  </header>
  <main>
    <section class="min-h-screen flex items-center justify-center px-6 pt-20">
      <div class="text-center max-w-3xl">
        <h1 class="font-mono text-4xl md:text-6xl font-bold text-white mb-6">${CLIENT_NAME}</h1>
        <p class="text-xl text-gray-400 mb-8">${GOALS}</p>
        <a href="#contact" class="inline-block px-8 py-3 bg-brand-btn text-white font-mono font-bold rounded hover:opacity-90 transition">Get Started</a>
      </div>
    </section>
    <section class="py-24 px-6 bg-surface-alt">
      <div class="max-w-4xl mx-auto text-center">
        <h2 class="font-mono text-3xl font-bold text-white mb-6">Professional ${NICHE} Services</h2>
        <p class="text-gray-400 text-lg leading-relaxed">${GOALS}</p>
      </div>
    </section>
    <section class="py-24 px-6">
      <div class="max-w-6xl mx-auto">
        <h2 class="font-mono text-3xl font-bold text-white text-center mb-12">Why Choose Us</h2>
        <div class="grid md:grid-cols-3 gap-8">
          <div class="p-6 bg-surface-alt rounded-xl border border-gray-800">
            <div class="text-3xl mb-4">⚡</div>
            <h3 class="font-mono text-lg font-bold text-white mb-2">Fast &amp; Reliable</h3>
            <p class="text-gray-400">Built for performance from the ground up.</p>
          </div>
          <div class="p-6 bg-surface-alt rounded-xl border border-gray-800">
            <div class="text-3xl mb-4">🎯</div>
            <h3 class="font-mono text-lg font-bold text-white mb-2">Results Driven</h3>
            <p class="text-gray-400">Every decision focused on your goals.</p>
          </div>
          <div class="p-6 bg-surface-alt rounded-xl border border-gray-800">
            <div class="text-3xl mb-4">🛡️</div>
            <h3 class="font-mono text-lg font-bold text-white mb-2">Trusted Quality</h3>
            <p class="text-gray-400">Professional standards, every time.</p>
          </div>
        </div>
      </div>
    </section>
    <section id="contact" class="py-24 px-6 bg-surface-alt">
      <div class="max-w-xl mx-auto text-center">
        <h2 class="font-mono text-3xl font-bold text-white mb-6">Get in Touch</h2>
        <p class="text-gray-400 mb-8">Ready to work together? Reach out today.</p>
        <a href="mailto:${EMAIL}" class="inline-block px-8 py-3 bg-brand-btn text-white font-mono font-bold rounded hover:opacity-90 transition">${EMAIL}</a>
      </div>
    </section>
  </main>
  <footer class="py-8 border-t border-gray-800 text-center">
    <p class="text-gray-400 text-sm font-mono">
      &copy; ${YEAR} ${CLIENT_NAME} &middot;
      Built by <a href="https://ajayadesign.github.io" class="text-brand-link underline hover:text-white">AjayaDesign</a>
    </p>
  </footer>
</body>
</html>
HTMLEOF
fi

log "  ✅ index.html generated ($(wc -c < "${PROJECT_DIR}/index.html") bytes)"

# ── Step 3: Engineering Checklist (QA) ─────────────────────────────
log "[STEP:3:6:test] 🧪 Running Playwright + axe accessibility tests"

cd "${PROJECT_DIR}"

# Initialize package.json and install test deps
npm init -y > /dev/null 2>&1

# Use globally pre-installed playwright & axe from the Docker image
# Only install serve locally for the webServer config
npm install --save-dev serve --loglevel=silent

# Link global packages so they resolve in this project
npm link @playwright/test @axe-core/playwright 2>/dev/null || {
  log "  Global link failed, installing locally..."
  npm install --save-dev @playwright/test @axe-core/playwright --loglevel=silent
  npx playwright install --with-deps chromium 2>/dev/null
}

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

# ── GATEKEEPER: Run tests with agentic retry loop ──
MAX_ATTEMPTS=3
ATTEMPT=1

while [ ${ATTEMPT} -le ${MAX_ATTEMPTS} ]; do
  log "[TEST:RUN:${ATTEMPT}] ▶ Attempt ${ATTEMPT}/${MAX_ATTEMPTS} — running tests..."

  TEST_OUTPUT=$(npx playwright test 2>&1) || true
  TEST_EXIT=$?

  if echo "${TEST_OUTPUT}" | grep -q "failed"; then
    TEST_EXIT=1
  fi

  if [ ${TEST_EXIT} -eq 0 ] && ! echo "${TEST_OUTPUT}" | grep -q "failed"; then
    log "[TEST:PASS:${ATTEMPT}] ✅ All tests passed on attempt ${ATTEMPT}!"
    break
  fi

  log "[TEST:FAIL:${ATTEMPT}] ⚠️ Tests failed on attempt ${ATTEMPT}"

  # If we've exhausted retries, abort
  if [ ${ATTEMPT} -ge ${MAX_ATTEMPTS} ]; then
    log "❌ TESTS FAILED after ${MAX_ATTEMPTS} attempts — aborting deployment."
    echo "${TEST_OUTPUT}" | tail -30
    if [ -n "${TELEGRAM_BOT_TOKEN}" ] && [ -n "${TELEGRAM_CHAT_ID}" ]; then
      curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
        -d chat_id="${TELEGRAM_CHAT_ID}" \
        -d parse_mode="Markdown" \
        -d text="❌ *AjayaDesign Build Failed*%0A%0AClient: \`${CLIENT_NAME}\`%0ANiche: ${NICHE}%0A%0ATests failed after ${MAX_ATTEMPTS} AI fix attempts — deployment blocked." \
        > /dev/null 2>&1
    fi
    exit 1
  fi

  # ── Agentic fix: send errors back to AI ──
  if [ -n "${GH_TOKEN}" ]; then
    log "[AI:FIX:$((ATTEMPT + 1))] 🔄 Sending errors to AI for auto-fix..."

    CURRENT_HTML=$(cat "${PROJECT_DIR}/index.html")

    # Extract just the meaningful error lines
    ERROR_SUMMARY=$(echo "${TEST_OUTPUT}" | grep -E "color-contrast|href.*#|Error:|serious\]|critical\]|Expected|Received|overflow" | head -20)

    FIX_PROMPT="The following HTML page has test failures. Fix ALL issues and return the complete corrected index.html.

ERRORS:
${ERROR_SUMMARY}

RULES:
- Buttons/CTA links: use bg-[#991B1B] with text-white (NEVER #ED1C24 bg with light text — fails WCAG contrast)
- All text on dark backgrounds: minimum text-gray-400 (#9CA3AF) for contrast ratio ≥ 4.5:1
- NEVER use href=\"#\" — use real section IDs (href=\"#about\", href=\"#contact\") or real URLs (mailto:, https://)
- Every section needs an id attribute matching its nav links
- No horizontal overflow

CURRENT HTML:
${CURRENT_HTML}

Output ONLY the fixed, complete HTML. No explanations, no markdown fences."

    FIX_PAYLOAD=$(jq -n \
      --arg model "${AI_MODEL}" \
      --arg system "You are an expert web developer. Fix accessibility and test failures in HTML. Output ONLY the corrected raw HTML, nothing else." \
      --arg user "${FIX_PROMPT}" \
      '{
        model: $model,
        messages: [
          { role: "system", content: $system },
          { role: "user", content: $user }
        ],
        max_tokens: 8000,
        temperature: 0.3
      }')

    FIX_HTTP=$(curl -s -w "%{http_code}" -o /tmp/ai_fix_response.json \
      -X POST "${AI_API}" \
      -H "Authorization: Bearer ${GH_TOKEN}" \
      -H "Content-Type: application/json" \
      -d "${FIX_PAYLOAD}")

    if [ "${FIX_HTTP}" = "200" ]; then
      jq -r '.choices[0].message.content' /tmp/ai_fix_response.json \
        | sed '/^```html$/d' | sed '/^```$/d' \
        > "${PROJECT_DIR}/index.html"

      if grep -q '<!DOCTYPE\|<html' "${PROJECT_DIR}/index.html"; then
        FILESIZE=$(wc -c < "${PROJECT_DIR}/index.html")
        log "  ✅ AI fix applied (${FILESIZE} bytes) — re-testing..."
      else
        log "  ⚠️  AI fix response was not valid HTML, keeping previous version"
      fi
    else
      log "  ⚠️  AI fix API returned HTTP ${FIX_HTTP}, cannot auto-fix"
      # Still increment to try again or fail
    fi
  else
    log "  ⚠️  No GH_TOKEN — cannot auto-fix, aborting"
    exit 1
  fi

  ATTEMPT=$((ATTEMPT + 1))
done

# ── Step 4: Deploy ─────────────────────────────────────────────────
log "[STEP:4:6:deploy] 🚀 Deploying to GitHub Pages"

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
log "[DEPLOY] Pushed to GitHub"

# Enable GitHub Pages on main branch
log "[DEPLOY] Enabling GitHub Pages..."
gh api -X POST "repos/${REPO_FULL}/pages" \
  --input - <<< '{"source":{"branch":"main","path":"/"}}' \
  2>/dev/null || \
gh api -X PUT "repos/${REPO_FULL}/pages" \
  --input - <<< '{"source":{"branch":"main","path":"/"}}' \
  2>/dev/null || \
log "  ⚠️  Pages may already be enabled or needs manual setup"

# ── Step 5: Add as submodule + portfolio card to main site ─────────
log "[STEP:5:6:integrate] 📎 Adding to ajayadesign.github.io (submodule + portfolio card)"

MAIN_SITE="/workspace/ajayadesign.github.io"
INJECT_SCRIPT="${MAIN_SITE}/automation/inject_card.js"

if [ -d "${MAIN_SITE}" ]; then
  cd "${MAIN_SITE}"

  # 5a: Add submodule (--force handles stale cached git dirs from previous runs)
  if [ ! -d "${REPO_NAME}" ]; then
    rm -rf ".git/modules/${REPO_NAME}" 2>/dev/null || true
    git submodule add --force "https://github.com/${REPO_FULL}.git" "${REPO_NAME}"
    log "  ✅ Submodule added"
  else
    log "  ⚠️  Submodule ${REPO_NAME} already exists, updating..."
    git submodule update --remote "${REPO_NAME}" || true
  fi

  # 5b: Pick emoji based on niche
  NICHE_LOWER=$(echo "${NICHE}" | tr '[:upper:]' '[:lower:]')
  case "${NICHE_LOWER}" in
    *photo*|*camera*)                          EMOJI="📸" ;;
    *food*|*bakery*|*restaurant*|*cafe*|*cook*) EMOJI="🍰" ;;
    *tech*|*engineer*|*software*|*dev*)         EMOJI="⚡" ;;
    *child*|*nanny*|*baby*|*daycare*)           EMOJI="👶" ;;
    *health*|*fitness*|*gym*|*yoga*)            EMOJI="💪" ;;
    *music*|*band*|*dj*)                        EMOJI="🎵" ;;
    *art*|*design*|*creative*)                  EMOJI="🎨" ;;
    *shop*|*store*|*retail*|*ecommerce*)        EMOJI="🛍️" ;;
    *real?estate*|*property*)                   EMOJI="🏠" ;;
    *law*|*legal*|*attorney*)                   EMOJI="⚖️" ;;
    *pet*|*animal*|*vet*)                       EMOJI="🐾" ;;
    *beauty*|*salon*|*spa*)                     EMOJI="💅" ;;
    *auto*|*car*|*mechanic*)                    EMOJI="🔧" ;;
    *construct*|*plumb*)                        EMOJI="🏗️" ;;
    *education*|*tutor*|*school*)               EMOJI="📚" ;;
    *travel*|*tour*)                            EMOJI="✈️" ;;
    *wedding*|*event*)                          EMOJI="💍" ;;
    *clean*|*maid*)                             EMOJI="✨" ;;
    *garden*|*landscape*|*lawn*)                EMOJI="🌿" ;;
    *)                                          EMOJI="🌐" ;;
  esac

  # 5c: Inject portfolio card into index.html
  if [ -f "${INJECT_SCRIPT}" ] && grep -q "%%PORTFOLIO_INJECT%%" "${MAIN_SITE}/index.html"; then
    log "  Injecting portfolio card into index.html..."
    jq -n \
      --arg repoName "${REPO_NAME}" \
      --arg clientName "${CLIENT_NAME}" \
      --arg niche "${NICHE}" \
      --arg goals "${GOALS}" \
      --arg emoji "${EMOJI}" \
      --arg indexPath "${MAIN_SITE}/index.html" \
      '{repoName:$repoName,clientName:$clientName,niche:$niche,goals:$goals,emoji:$emoji,indexPath:$indexPath}' \
      | node "${INJECT_SCRIPT}"
    log "  ✅ Portfolio card injected"
  else
    log "  ⚠️  inject_card.js or portfolio marker not found, skipping card injection"
  fi

  git add -A
  git commit -m "feat: add ${CLIENT_NAME} portfolio (submodule + card)"
  git push
  log "  ✅ Main site updated and pushed"
else
  log "  ⚠️  Main site not found at ${MAIN_SITE}, skipping submodule step"
fi

# ── Step 6: Notification ──────────────────────────────────────────
log "[STEP:6:6:notify] 📬 Sending Telegram notification"

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
