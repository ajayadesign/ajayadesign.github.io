// @ts-check
const { test, expect } = require('@playwright/test');
const AxeBuilder = require('@axe-core/playwright').default;

/* ── Helper: stub Firebase ── */
async function stubFirebase(page) {
  await page.evaluate(() => {
    const noop = () => ({
      set: () => Promise.resolve(),
      update: () => Promise.resolve(),
      remove: () => Promise.resolve(),
      push: () => ({ set: () => Promise.resolve(), key: 'test-stub' }),
      on: () => {},
      off: () => {},
      once: () => Promise.resolve({ val: () => null }),
    });
    window.__db = { ref: noop, goOffline: () => {} };
  });
}

/* ═══════════════════════════════════════════════
   PROPOSAL GENERATOR
   ═══════════════════════════════════════════════ */
test.describe('Proposal Generator', () => {

  test('page loads with correct title', async ({ page }) => {
    await page.goto('/tools/proposal-generator.html');
    await expect(page).toHaveTitle(/Proposal Generator/i);
  });

  test('form has all required fields', async ({ page }) => {
    await page.goto('/tools/proposal-generator.html');
    await expect(page.locator('#pg-business-name')).toBeAttached();
    await expect(page.locator('#pg-business-type')).toBeAttached();
    await expect(page.locator('#pg-contact-name')).toBeAttached();
    await expect(page.locator('#pg-email')).toBeAttached();
    await expect(page.locator('#pg-current-site')).toBeAttached();
  });

  test('feature checkboxes are rendered', async ({ page }) => {
    await page.goto('/tools/proposal-generator.html');
    const checks = page.locator('#features-grid input[type="checkbox"]');
    const count = await checks.count();
    expect(count).toBeGreaterThanOrEqual(10);
  });

  test('tier cards are selectable', async ({ page }) => {
    await page.goto('/tools/proposal-generator.html');
    const tiers = page.locator('#tiers-grid .tier-card');
    expect(await tiers.count()).toBe(3);
    // Professional is pre-selected
    await expect(tiers.nth(1)).toHaveAttribute('aria-checked', 'true');
    // Click essential
    await tiers.nth(0).click();
    await expect(tiers.nth(0)).toHaveAttribute('aria-checked', 'true');
    await expect(tiers.nth(1)).toHaveAttribute('aria-checked', 'false');
  });

  test('generates proposal on valid submit', async ({ page }) => {
    await page.goto('/tools/proposal-generator.html');
    await stubFirebase(page);

    // Fill form
    await page.fill('#pg-business-name', 'Test Corp');
    await page.selectOption('#pg-business-type', 'Tech / SaaS');
    await page.fill('#pg-contact-name', 'John Doe');
    await page.fill('#pg-email', 'john@test.com');

    // Check some features
    await page.locator('#features-grid input[value="seo"]').check();
    await page.locator('#features-grid input[value="blog"]').check();

    // Submit
    await page.click('#generate-btn');

    // Proposal should be visible
    await expect(page.locator('#proposal-output')).toBeVisible();
    await expect(page.locator('#prop-business')).toHaveText('Test Corp');
    // Pricing section populated
    await expect(page.locator('#prop-pricing')).toContainText('$2,500');
  });

  test('download PDF button exists after generation', async ({ page }) => {
    await page.goto('/tools/proposal-generator.html');
    await stubFirebase(page);
    await page.fill('#pg-business-name', 'PDF Test');
    await page.selectOption('#pg-business-type', 'Other');
    await page.fill('#pg-contact-name', 'Jane');
    await page.fill('#pg-email', 'jane@test.com');
    await page.click('#generate-btn');
    await expect(page.locator('#download-pdf')).toBeVisible();
  });

  test('edit button hides proposal and returns to form', async ({ page }) => {
    await page.goto('/tools/proposal-generator.html');
    await stubFirebase(page);
    await page.fill('#pg-business-name', 'Edit Test');
    await page.selectOption('#pg-business-type', 'Other');
    await page.fill('#pg-contact-name', 'Jane');
    await page.fill('#pg-email', 'jane@test.com');
    await page.click('#generate-btn');
    await expect(page.locator('#proposal-output')).toBeVisible();
    await page.click('#edit-proposal');
    await expect(page.locator('#proposal-output')).toBeHidden();
  });

  test('email modal opens and closes', async ({ page }) => {
    await page.goto('/tools/proposal-generator.html');
    await stubFirebase(page);
    await page.fill('#pg-business-name', 'Modal Test');
    await page.selectOption('#pg-business-type', 'Other');
    await page.fill('#pg-contact-name', 'Jane');
    await page.fill('#pg-email', 'jane@test.com');
    await page.click('#generate-btn');
    await page.click('#send-email-btn');
    await expect(page.locator('#email-modal')).toBeVisible();
    await page.click('#cancel-send-email');
    await expect(page.locator('#email-modal')).toBeHidden();
  });

  test('axe accessibility audit — proposal generator', async ({ page }) => {
    await page.goto('/tools/proposal-generator.html');
    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'best-practice'])
      .analyze();
    const critical = results.violations.filter(
      v => v.impact === 'critical' || v.impact === 'serious'
    );
    if (critical.length > 0) {
      console.log('\n🔴 Critical/Serious axe violations (proposal):');
      critical.forEach(v => {
        console.log(`  [${v.impact}] ${v.id}: ${v.description}`);
        v.nodes.forEach(n => console.log(`    → ${n.html.substring(0, 150)}`));
      });
    }
    expect(critical).toHaveLength(0);
  });
});

/* ═══════════════════════════════════════════════
   ONBOARDING QUESTIONNAIRE
   ═══════════════════════════════════════════════ */
test.describe('Client Onboarding', () => {

  test('page loads with correct title', async ({ page }) => {
    await page.goto('/onboarding/');
    await expect(page).toHaveTitle(/Onboarding/i);
  });

  test('step 1 is visible by default', async ({ page }) => {
    await page.goto('/onboarding/');
    await expect(page.locator('.step-panel[data-step="1"]')).toBeVisible();
    await expect(page.locator('.step-panel[data-step="2"]')).toBeHidden();
  });

  test('progress bar updates on navigation', async ({ page }) => {
    await page.goto('/onboarding/');
    const bar = page.locator('#progress-bar');
    const initialWidth = await bar.evaluate(el => el.style.width);
    expect(initialWidth).toBe('17%');

    await page.click('#next-btn');
    await expect(page.locator('.step-panel[data-step="2"]')).toBeVisible();
    const newWidth = await bar.evaluate(el => el.style.width);
    expect(parseInt(newWidth)).toBeGreaterThan(17);
  });

  test('can navigate forward and back through all steps', async ({ page }) => {
    await page.goto('/onboarding/');
    for (let i = 2; i <= 7; i++) {
      await page.click('#next-btn');
      await expect(page.locator(`.step-panel[data-step="${i}"]`)).toBeVisible();
    }
    // On last step, submit btn should be visible, next hidden
    await expect(page.locator('#submit-btn')).toBeVisible();
    await expect(page.locator('#next-btn')).toBeHidden();

    // Go back
    await page.click('#prev-btn');
    await expect(page.locator('.step-panel[data-step="6"]')).toBeVisible();
  });

  test('goals checkboxes are rendered', async ({ page }) => {
    await page.goto('/onboarding/');
    // Navigate to step 3
    await page.click('#next-btn');
    await page.click('#next-btn');
    const goals = page.locator('#goals-list input[type="checkbox"]');
    expect(await goals.count()).toBeGreaterThanOrEqual(6);
  });

  test('voice selector works', async ({ page }) => {
    await page.goto('/onboarding/');
    await page.click('#next-btn'); // step 2
    const casual = page.locator('#voice-selector .voice-btn[data-voice="casual"]');
    await casual.click();
    await expect(casual).toHaveAttribute('aria-checked', 'true');
  });

  test('file upload area responds to click', async ({ page }) => {
    await page.goto('/onboarding/');
    await page.click('#next-btn'); // step 2
    // File input exists
    await expect(page.locator('#ob-logo-upload')).toBeAttached();
    // Upload area is visible
    await expect(page.locator('#logo-upload-area')).toBeVisible();
  });

  test('summary step shows collected data', async ({ page }) => {
    await page.goto('/onboarding/');

    // Fill step 1
    await page.fill('#ob-biz-name', 'Summary Test Biz');
    await page.selectOption('#ob-industry', 'Tech / SaaS');
    await page.fill('#ob-target-audience', 'Developers');

    // Navigate to summary (step 7)
    for (let i = 0; i < 6; i++) await page.click('#next-btn');

    await expect(page.locator('#summary-container')).toContainText('Summary Test Biz');
    await expect(page.locator('#summary-container')).toContainText('Tech / SaaS');
  });

  test('submit shows success state', async ({ page }) => {
    await page.goto('/onboarding/');
    await stubFirebase(page);

    // Fill minimum required
    await page.fill('#ob-biz-name', 'Submit Test');
    await page.selectOption('#ob-industry', 'Other');
    await page.fill('#ob-target-audience', 'Everyone');

    // Navigate to step 6 (Timeline & Budget) and fill required fields
    for (let i = 0; i < 5; i++) await page.click('#next-btn');
    // Step 6
    await page.selectOption('#ob-timeline', 'Within 1 month');
    await page.selectOption('#ob-budget', '$1,500 – $2,500');
    await page.fill('#ob-email', 'submit@test.com');

    // Go to summary & submit
    await page.click('#next-btn');
    await page.click('#submit-btn');

    await expect(page.locator('#success-state')).toBeVisible({ timeout: 5000 });
    await expect(page.locator('#success-id')).not.toHaveText('—');
  });

  test('axe accessibility audit — onboarding', async ({ page }) => {
    await page.goto('/onboarding/');
    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'best-practice'])
      .analyze();
    const critical = results.violations.filter(
      v => v.impact === 'critical' || v.impact === 'serious'
    );
    if (critical.length > 0) {
      console.log('\n🔴 Critical/Serious axe violations (onboarding):');
      critical.forEach(v => {
        console.log(`  [${v.impact}] ${v.id}: ${v.description}`);
        v.nodes.forEach(n => console.log(`    → ${n.html.substring(0, 150)}`));
      });
    }
    expect(critical).toHaveLength(0);
  });
});
