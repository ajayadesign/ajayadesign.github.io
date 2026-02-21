/**
 * Insight Dashboard — Chart Utilities
 * Wrappers around Chart.js with consistent dark-theme styling.
 */

// ── Default Chart.js configuration ──────────────────────────────────
Chart.defaults.color = '#808098';
Chart.defaults.borderColor = '#1A1A24';
Chart.defaults.font.family = "'Inter', system-ui, sans-serif";
Chart.defaults.font.size = 11;
Chart.defaults.plugins.legend.labels.usePointStyle = true;
Chart.defaults.plugins.legend.labels.pointStyleWidth = 8;
Chart.defaults.plugins.legend.labels.padding = 16;
Chart.defaults.plugins.tooltip.backgroundColor = '#12121A';
Chart.defaults.plugins.tooltip.borderColor = '#2A2A3A';
Chart.defaults.plugins.tooltip.borderWidth = 1;
Chart.defaults.plugins.tooltip.padding = 10;
Chart.defaults.plugins.tooltip.cornerRadius = 8;
Chart.defaults.plugins.tooltip.titleFont = { weight: '600', size: 12 };
Chart.defaults.plugins.tooltip.bodyFont = { size: 11 };
Chart.defaults.animation.duration = 800;
Chart.defaults.animation.easing = 'easeOutCubic';

// ── Color Palettes ──────────────────────────────────────────────────
const COLORS = {
  electric:   '#00D4FF',
  green:      '#00FF88',
  purple:     '#A855F7',
  orange:     '#FF8A00',
  red:        '#ef4444',
  yellow:     '#FFD600',
  pink:       '#ec4899',
  teal:       '#14b8a6',
  indigo:     '#6366f1',
  lime:       '#84cc16',
  cyan:       '#06b6d4',
  amber:      '#f59e0b',
};

const PALETTE = [
  '#00D4FF', '#A855F7', '#FF8A00', '#00FF88', '#ef4444',
  '#FFD600', '#ec4899', '#14b8a6', '#6366f1', '#84cc16',
  '#06b6d4', '#f59e0b', '#8b5cf6', '#f97316', '#22d3ee',
];

const TIER_COLORS = {
  hot: '#ef4444',
  warm: '#FF8A00',
  cool: '#00D4FF',
  cold: '#808098',
  unscored: '#4a4a5a',
};

// ── Chart registry (for cleanup) ────────────────────────────────────
const _charts = {};

function destroyChart(id) {
  if (_charts[id]) { _charts[id].destroy(); delete _charts[id]; }
}

// ── Chart Builders ──────────────────────────────────────────────────

/** Bar chart. */
function createBarChart(canvasId, labels, datasets, options = {}) {
  destroyChart(canvasId);
  const ctx = document.getElementById(canvasId)?.getContext('2d');
  if (!ctx) return null;
  const chart = new Chart(ctx, {
    type: 'bar',
    data: { labels, datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: datasets.length > 1, position: 'top' },
        ...(options.plugins || {}),
      },
      scales: {
        x: {
          grid: { display: false },
          ticks: { maxRotation: 45, font: { size: 10 } },
          ...(options.x || {}),
        },
        y: {
          grid: { color: 'rgba(42,42,58,0.3)' },
          beginAtZero: true,
          ...(options.y || {}),
        },
      },
    },
  });
  _charts[canvasId] = chart;
  return chart;
}

/** Horizontal bar chart. */
function createHBarChart(canvasId, labels, data, colors, options = {}) {
  destroyChart(canvasId);
  const ctx = document.getElementById(canvasId)?.getContext('2d');
  if (!ctx) return null;
  const chart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        data,
        backgroundColor: colors || PALETTE.slice(0, data.length),
        borderRadius: 4,
        barThickness: 18,
      }],
    },
    options: {
      indexAxis: 'y',
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false }, ...(options.plugins || {}) },
      scales: {
        x: { grid: { color: 'rgba(42,42,58,0.3)' }, beginAtZero: true },
        y: { grid: { display: false }, ticks: { font: { size: 10 } } },
      },
    },
  });
  _charts[canvasId] = chart;
  return chart;
}

/** Doughnut / Pie chart. */
function createDoughnut(canvasId, labels, data, colors, options = {}) {
  destroyChart(canvasId);
  const ctx = document.getElementById(canvasId)?.getContext('2d');
  if (!ctx) return null;
  const chart = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels,
      datasets: [{
        data,
        backgroundColor: colors || PALETTE.slice(0, data.length),
        borderWidth: 0,
        hoverOffset: 6,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: options.cutout || '65%',
      plugins: {
        legend: {
          position: 'right',
          labels: { padding: 12, font: { size: 10 } },
        },
        ...(options.plugins || {}),
      },
    },
  });
  _charts[canvasId] = chart;
  return chart;
}

/** Radar chart. */
function createRadar(canvasId, labels, datasets, options = {}) {
  destroyChart(canvasId);
  const ctx = document.getElementById(canvasId)?.getContext('2d');
  if (!ctx) return null;
  const chart = new Chart(ctx, {
    type: 'radar',
    data: { labels, datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        r: {
          beginAtZero: true,
          grid: { color: 'rgba(42,42,58,0.4)' },
          angleLines: { color: 'rgba(42,42,58,0.3)' },
          pointLabels: { font: { size: 10 } },
          ticks: { display: false },
          ...options.r,
        },
      },
      plugins: {
        legend: { position: 'top' },
        ...(options.plugins || {}),
      },
    },
  });
  _charts[canvasId] = chart;
  return chart;
}

/** Scatter chart. */
function createScatter(canvasId, datasets, options = {}) {
  destroyChart(canvasId);
  const ctx = document.getElementById(canvasId)?.getContext('2d');
  if (!ctx) return null;
  const chart = new Chart(ctx, {
    type: 'scatter',
    data: { datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: 'top' },
        tooltip: {
          callbacks: {
            label: (ctx) => {
              const p = ctx.raw;
              return `${p.label || ''} (${p.x}, ${p.y})`;
            },
          },
        },
        ...(options.plugins || {}),
      },
      scales: {
        x: { grid: { color: 'rgba(42,42,58,0.3)' }, ...(options.x || {}) },
        y: { grid: { color: 'rgba(42,42,58,0.3)' }, ...(options.y || {}) },
      },
    },
  });
  _charts[canvasId] = chart;
  return chart;
}

/** Line chart. */
function createLineChart(canvasId, labels, datasets, options = {}) {
  destroyChart(canvasId);
  const ctx = document.getElementById(canvasId)?.getContext('2d');
  if (!ctx) return null;
  const chart = new Chart(ctx, {
    type: 'line',
    data: { labels, datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: 'top' },
        ...(options.plugins || {}),
      },
      scales: {
        x: { grid: { display: false }, ...(options.x || {}) },
        y: { grid: { color: 'rgba(42,42,58,0.3)' }, beginAtZero: true, ...(options.y || {}) },
      },
    },
  });
  _charts[canvasId] = chart;
  return chart;
}
