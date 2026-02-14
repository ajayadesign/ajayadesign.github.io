// ═══════════════════════════════════════════════════════════════
//  Phase 7: Deploy to GitHub Pages + Submodule + Portfolio Card
// ═══════════════════════════════════════════════════════════════
const fs = require('fs');
const path = require('path');
const { exec, tryExec } = require('../lib/shell');

module.exports = async function deploy(repo, orch) {
  const { dir: projectDir, repoName, repoFull } = repo;
  const mainSiteDir = orch.config.mainSiteDir;

  orch.log(`🚀 Deploying ${repoFull} to GitHub Pages`);

  // ── Git add, commit, push ─────────────────────────────────
  exec('git add -A', { cwd: projectDir });

  const clientName = orch.state.blueprint?.siteName || repoName;
  const niche = orch.state.blueprint?.tagline || '';
  const pageCount = orch.state.blueprint?.pages?.length || 1;

  tryExec(
    `git commit -m "feat: ${pageCount}-page site for ${clientName}\n\n${niche}\nBuilt by AjayaDesign v2 automation pipeline"`,
    { cwd: projectDir }
  );

  exec('git push -u origin main', { cwd: projectDir });
  orch.log('  ✅ Pushed to GitHub');

  // ── Enable GitHub Pages ───────────────────────────────────
  orch.log('  Enabling GitHub Pages...');
  const pagesPayload = '{"source":{"branch":"main","path":"/"}}';

  let pagesOk = tryExec(
    `gh api -X POST "repos/${repoFull}/pages" --input - <<< '${pagesPayload}'`,
    { cwd: projectDir }
  );
  if (!pagesOk.ok) {
    pagesOk = tryExec(
      `gh api -X PUT "repos/${repoFull}/pages" --input - <<< '${pagesPayload}'`,
      { cwd: projectDir }
    );
  }

  if (pagesOk.ok) {
    orch.log('  ✅ GitHub Pages enabled');
  } else {
    orch.log('  ⚠️ Pages may already be enabled or needs manual setup');
  }

  // ── Add submodule to main site ────────────────────────────
  if (fs.existsSync(mainSiteDir)) {
    orch.log('  Adding submodule to main site...');

    const submodulePath = path.join(mainSiteDir, repoName);

    if (!fs.existsSync(submodulePath)) {
      // Clean up stale git module cache
      tryExec(`rm -rf ".git/modules/${repoName}"`, { cwd: mainSiteDir });

      const subResult = tryExec(
        `git submodule add --force "https://github.com/${repoFull}.git" "${repoName}"`,
        { cwd: mainSiteDir }
      );

      if (subResult.ok) {
        orch.log('    ✅ Submodule added');
      } else {
        orch.log(`    ⚠️ Submodule add failed: ${subResult.output.slice(0, 100)}`);
      }
    } else {
      tryExec(`git submodule update --remote "${repoName}"`, {
        cwd: mainSiteDir,
      });
      orch.log('    ⚠️ Submodule already exists, updated');
    }

    // ── Inject portfolio card ─────────────────────────────
    const injectScript = path.join(mainSiteDir, 'automation', 'inject_card.js');
    const mainIndex = path.join(mainSiteDir, 'index.html');

    if (
      fs.existsSync(injectScript) &&
      fs.existsSync(mainIndex) &&
      fs.readFileSync(mainIndex, 'utf-8').includes('%%PORTFOLIO_INJECT%%')
    ) {
      orch.log('    Injecting portfolio card...');

      const emoji = pickEmoji(orch.state.blueprint?.pages?.[0]?.sections || [], niche);

      const cardData = JSON.stringify({
        repoName,
        clientName,
        niche: niche || 'Professional Services',
        goals: orch.state.blueprint?.siteGoals || '',
        emoji,
        indexPath: mainIndex,
      });

      const injectResult = tryExec(
        `echo '${cardData.replace(/'/g, "\\'")}' | node "${injectScript}"`,
        { cwd: mainSiteDir }
      );

      if (injectResult.ok) {
        orch.log('    ✅ Portfolio card injected');
      } else {
        orch.log(`    ⚠️ Card injection failed: ${injectResult.output.slice(0, 100)}`);
      }
    }

    // Commit + push main site
    tryExec('git add -A', { cwd: mainSiteDir });
    tryExec(
      `git commit -m "feat: add ${clientName} portfolio (submodule + card)"`,
      { cwd: mainSiteDir }
    );
    tryExec('git push', { cwd: mainSiteDir });
    orch.log('  ✅ Main site updated and pushed');
  } else {
    orch.log(`  ⚠️ Main site not found at ${mainSiteDir}, skipping submodule`);
  }

  orch.log(`  🔗 Live URL: ${repo.liveUrl}`);
};

// ── Pick emoji based on niche ──────────────────────────────────

function pickEmoji(sections, niche) {
  const n = (niche || '').toLowerCase();
  if (/photo|camera/.test(n)) return '📸';
  if (/food|bakery|restaurant|cafe|cook/.test(n)) return '🍰';
  if (/tech|engineer|software|dev/.test(n)) return '⚡';
  if (/child|nanny|baby|daycare/.test(n)) return '👶';
  if (/health|fitness|gym|yoga/.test(n)) return '💪';
  if (/music|band|dj/.test(n)) return '🎵';
  if (/art|design|creative/.test(n)) return '🎨';
  if (/shop|store|retail|ecommerce/.test(n)) return '🛍️';
  if (/real.?estate|property/.test(n)) return '🏠';
  if (/law|legal|attorney/.test(n)) return '⚖️';
  if (/pet|animal|vet/.test(n)) return '🐾';
  if (/beauty|salon|spa/.test(n)) return '💅';
  if (/auto|car|mechanic/.test(n)) return '🔧';
  if (/construct|plumb/.test(n)) return '🏗️';
  if (/education|tutor|school/.test(n)) return '📚';
  if (/travel|tour/.test(n)) return '✈️';
  if (/wedding|event/.test(n)) return '💍';
  if (/clean|maid/.test(n)) return '✨';
  if (/garden|landscape|lawn/.test(n)) return '🌿';
  return '🌐';
}
