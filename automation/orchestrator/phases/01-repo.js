// ═══════════════════════════════════════════════════════════════
//  Phase 1: Create GitHub Repository
// ═══════════════════════════════════════════════════════════════
const fs = require('fs');
const path = require('path');
const { exec, tryExec } = require('../lib/shell');

module.exports = async function createRepo({ businessName, niche, goals, email }, orch) {
  const githubOrg = orch.config.githubOrg;
  const baseDir = orch.config.baseDir;

  // Sanitize name for repo/directory
  const repoName = businessName
    .toLowerCase()
    .replace(/[^a-z0-9-]/g, '-')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '');

  const repoFull = `${githubOrg}/${repoName}`;
  const projectDir = path.join(baseDir, repoName);
  const liveUrl = `https://ajayadesign.github.io/${repoName}`;

  orch.log(`🏗️ Creating GitHub repo: ${repoFull}`);

  // Ensure base directory exists
  if (!fs.existsSync(baseDir)) {
    fs.mkdirSync(baseDir, { recursive: true });
  }

  // Clean up any stale project directory
  if (fs.existsSync(projectDir)) {
    orch.log(`  ⚠️ Directory ${repoName} exists, cleaning...`);
    exec(`rm -rf "${projectDir}"`);
  }

  // Check if repo already exists
  const repoCheck = tryExec(`gh repo view "${repoFull}" 2>/dev/null`);

  if (repoCheck.ok) {
    orch.log(`  Repo ${repoFull} already exists, cloning...`);
    exec(`git clone "https://github.com/${repoFull}.git" "${projectDir}"`);
  } else {
    orch.log(`  Creating repo under org ${githubOrg}...`);
    const createResult = tryExec(
      `gh repo create "${repoFull}" --public --add-readme ` +
        `--description "Client site for ${businessName} — built by AjayaDesign"`
    );

    if (!createResult.ok) {
      throw new Error(
        `Failed to create repo: ${createResult.output}\n` +
          'Check GH_TOKEN permissions (needs Administration: Write for org repos).'
      );
    }

    // Give GitHub API a moment to propagate
    await new Promise((r) => setTimeout(r, 3000));
    exec(`git clone "https://github.com/${repoFull}.git" "${projectDir}"`);
  }

  orch.log(`  ✅ Repo ready: ${repoFull} → ${projectDir}`);

  return { dir: projectDir, repoName, repoFull, liveUrl };
};
