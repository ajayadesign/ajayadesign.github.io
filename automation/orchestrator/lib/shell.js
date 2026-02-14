// ═══════════════════════════════════════════════════════════════
//  AjayaDesign v2 — Shell Utility
//  Safe exec wrapper for git, gh, npx, etc.
// ═══════════════════════════════════════════════════════════════
const { execSync } = require('child_process');

/**
 * Execute a shell command synchronously.
 * @returns {string} trimmed stdout
 * @throws on non-zero exit
 */
function exec(cmd, opts = {}) {
  const result = execSync(cmd, {
    cwd: opts.cwd,
    env: { ...process.env, HOME: '/root', ...opts.env },
    encoding: 'utf-8',
    maxBuffer: 20 * 1024 * 1024,
    stdio: ['pipe', 'pipe', 'pipe'],
    timeout: opts.timeout || 300_000, // 5 min default
  });
  return result.trim();
}

/**
 * Try executing a command — returns { ok, output } instead of throwing.
 */
function tryExec(cmd, opts = {}) {
  try {
    return { ok: true, output: exec(cmd, opts) };
  } catch (err) {
    const stderr = err.stderr ? err.stderr.toString().trim() : '';
    const stdout = err.stdout ? err.stdout.toString().trim() : '';
    return { ok: false, output: stderr || stdout || err.message };
  }
}

/**
 * Configure git identity (needed inside Docker containers).
 */
function ensureGitIdentity() {
  tryExec('git config --global user.email "ajayadahal1000@gmail.com"');
  tryExec('git config --global user.name "Ajaya Dahal"');
  tryExec("git config --global --add safe.directory '*'");

  const ghToken = process.env.GH_TOKEN;
  if (ghToken) {
    tryExec(
      `git config --global url."https://${ghToken}@github.com/".insteadOf "https://github.com/"`
    );
  }
}

module.exports = { exec, tryExec, ensureGitIdentity };
