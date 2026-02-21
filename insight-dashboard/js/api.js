/**
 * Insight Dashboard — API Client
 * Fetches analytics data from the outreach API at localhost:3001.
 */

const API_BASE = 'http://localhost:3001/api/v1/outreach';

/** Cache for analytics data (refreshed on demand) */
let _cache = { data: null, ts: 0 };
const CACHE_TTL = 60_000; // 1 minute

/**
 * Fetch all prospect analytics data.
 * Returns cached data if fresh, otherwise fetches from API.
 */
async function fetchAnalytics(forceRefresh = false) {
  if (!forceRefresh && _cache.data && Date.now() - _cache.ts < CACHE_TTL) {
    return _cache.data;
  }
  const res = await fetch(`${API_BASE}/insights/analytics`);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  const data = await res.json();
  _cache = { data, ts: Date.now() };
  return data;
}

/** Fetch WP score stats (aggregated). */
async function fetchScoreStats() {
  const res = await fetch(`${API_BASE}/wp-score-stats`);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

/** Fetch pipeline status. */
async function fetchPipelineStatus() {
  const res = await fetch(`${API_BASE}/pipeline/status`);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

/** Fetch outreach stats. */
async function fetchOutreachStats() {
  const res = await fetch(`${API_BASE}/stats`);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

// ── Utility Helpers ──────────────────────────────────────────────────

/** Group an array by a key function. */
function groupBy(arr, keyFn) {
  const groups = {};
  for (const item of arr) {
    const key = keyFn(item) || 'Unknown';
    (groups[key] ??= []).push(item);
  }
  return groups;
}

/** Count occurrences by a key function. */
function countBy(arr, keyFn) {
  const counts = {};
  for (const item of arr) {
    const key = keyFn(item) || 'Unknown';
    counts[key] = (counts[key] || 0) + 1;
  }
  return counts;
}

/** Sort object entries by value descending. */
function sortEntries(obj, desc = true) {
  return Object.entries(obj).sort((a, b) => desc ? b[1] - a[1] : a[1] - b[1]);
}

/** Average of numeric values, ignoring nulls. */
function avg(arr, keyFn) {
  const vals = arr.map(keyFn).filter(v => v != null && !isNaN(v));
  if (!vals.length) return 0;
  return vals.reduce((a, b) => a + b, 0) / vals.length;
}

/** Median of numeric values. */
function median(arr, keyFn) {
  const vals = arr.map(keyFn).filter(v => v != null && !isNaN(v)).sort((a,b) => a - b);
  if (!vals.length) return 0;
  const mid = Math.floor(vals.length / 2);
  return vals.length % 2 ? vals[mid] : (vals[mid-1] + vals[mid]) / 2;
}

/** Format a number with commas. */
function fmt(n, decimals = 0) {
  if (n == null || isNaN(n)) return '—';
  return Number(n).toLocaleString('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

/** Format business type for display. */
function fmtType(type) {
  if (!type) return 'Unknown';
  return type.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

/** Get tier from wp_score. */
function getTier(score) {
  if (score == null) return 'unscored';
  if (score >= 80) return 'hot';
  if (score >= 60) return 'warm';
  if (score >= 40) return 'cool';
  return 'cold';
}

/** Get tier color. */
function tierColor(tier) {
  return { hot: '#ef4444', warm: '#FF8A00', cool: '#00D4FF', cold: '#808098', unscored: '#4a4a5a' }[tier] || '#808098';
}

/** Percent with 1 decimal. */
function pct(num, total) {
  if (!total) return '0%';
  return (num / total * 100).toFixed(1) + '%';
}

/**
 * Normalize design_era from API values like '2022-modern' to simple labels.
 * API returns: '2022-modern', '2018-recent', '2015-dated', '2010-ancient', 'pre-2010-prehistoric'
 */
function normalizeEra(era) {
  if (!era) return 'unknown';
  if (era.includes('modern')) return 'modern';
  if (era.includes('recent')) return 'dated';      // recent ≈ dated (not modern)
  if (era.includes('dated')) return 'dated';
  if (era.includes('ancient')) return 'ancient';
  if (era.includes('prehistoric')) return 'ancient'; // prehistoric ≈ ancient
  return 'unknown';
}

/** Check if a design_era value represents an outdated design. */
function isOutdatedDesign(era) {
  const n = normalizeEra(era);
  return n === 'ancient' || n === 'dated';
}

/** Build a score bar HTML string. */
function scoreBarHTML(value, max, color = '#00D4FF') {
  const width = max > 0 ? Math.min(100, (value / max) * 100) : 0;
  return `<div class="score-bar"><div class="score-bar-fill" style="width:${width}%;background:${color}"></div></div>`;
}

/** Show a toast notification. */
function showToast(msg, duration = 3000) {
  const el = document.createElement('div');
  el.className = 'toast';
  el.textContent = msg;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), duration);
}
