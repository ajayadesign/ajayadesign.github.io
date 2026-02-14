// ═══════════════════════════════════════════════════════════════
//  AjayaDesign v2 — AI API Wrapper
//  GitHub Models API with retry, JSON/HTML extraction
// ═══════════════════════════════════════════════════════════════
const https = require('https');

const API_URL = new URL(
  process.env.AI_API || 'https://models.inference.ai.azure.com/chat/completions'
);
const DEFAULT_MODEL = process.env.AI_MODEL || 'gpt-4o';
const TIMEOUT_MS = 120_000;

// ── Main AI call ───────────────────────────────────────────────
async function callAI({ messages, temperature = 0.7, maxTokens = 8000, model, retries = 2 }) {
  const token = process.env.GH_TOKEN;
  if (!token) throw new Error('GH_TOKEN not set — cannot call AI API');

  let lastErr;
  for (let attempt = 1; attempt <= retries + 1; attempt++) {
    try {
      return await _request({ messages, temperature, maxTokens, model, token });
    } catch (err) {
      lastErr = err;
      if (attempt <= retries) {
        const wait = attempt * 2000;
        await new Promise(r => setTimeout(r, wait));
      }
    }
  }
  throw lastErr;
}

function _request({ messages, temperature, maxTokens, model, token }) {
  const payload = JSON.stringify({
    model: model || DEFAULT_MODEL,
    messages,
    max_tokens: maxTokens,
    temperature,
  });

  return new Promise((resolve, reject) => {
    const opts = {
      hostname: API_URL.hostname,
      path: API_URL.pathname,
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(payload),
      },
    };

    const req = https.request(opts, (res) => {
      let body = '';
      res.on('data', (d) => (body += d));
      res.on('end', () => {
        if (res.statusCode !== 200) {
          return reject(
            new Error(`AI API HTTP ${res.statusCode}: ${body.slice(0, 500)}`)
          );
        }
        try {
          const data = JSON.parse(body);
          const content = data.choices?.[0]?.message?.content || '';
          resolve(stripFences(content));
        } catch (err) {
          reject(new Error(`Failed to parse AI response: ${err.message}`));
        }
      });
    });

    req.on('error', reject);
    req.setTimeout(TIMEOUT_MS, () => {
      req.destroy();
      reject(new Error(`AI API timeout (${TIMEOUT_MS / 1000}s)`));
    });
    req.write(payload);
    req.end();
  });
}

// ── Parsing helpers ────────────────────────────────────────────

function stripFences(text) {
  return text
    .replace(/^```(?:html|json|javascript|js|css)?\s*\n?/gm, '')
    .replace(/^```\s*$/gm, '')
    .trim();
}

function extractJSON(text) {
  const cleaned = stripFences(text);

  // Try full text
  try {
    return JSON.parse(cleaned);
  } catch {}

  // Try outermost { ... }
  const start = cleaned.indexOf('{');
  const end = cleaned.lastIndexOf('}');
  if (start !== -1 && end > start) {
    try {
      return JSON.parse(cleaned.slice(start, end + 1));
    } catch {}
  }

  throw new Error(
    `Could not extract JSON from AI response:\n${cleaned.slice(0, 300)}…`
  );
}

function extractHTML(text) {
  const cleaned = stripFences(text);
  if (cleaned.includes('<!DOCTYPE') || cleaned.includes('<html') || cleaned.includes('<main')) {
    return cleaned;
  }
  throw new Error('AI response does not contain valid HTML');
}

module.exports = { callAI, extractJSON, extractHTML, stripFences };
