// ═══════════════════════════════════════════════════════════════
//  Phase 8: Notifications — Telegram + future channels
// ═══════════════════════════════════════════════════════════════
const https = require('https');

module.exports = async function notify(clientRequest, repo, orch) {
  const { businessName, niche, goals, email } = clientRequest;
  const { repoFull, liveUrl } = repo;
  const pageCount = orch.state.blueprint?.pages?.length || 1;

  const token = process.env.TELEGRAM_BOT_TOKEN;
  const chatId = process.env.TELEGRAM_CHAT_ID;

  if (!token || !chatId) {
    orch.log('📬 ⚠️ Telegram not configured — skipping notification');
    return;
  }

  orch.log('📬 Sending Telegram notification');

  const message = [
    '✅ *AjayaDesign v2 — New Site Deployed\\!*',
    '',
    `🏢 *Client:* \`${escMD(businessName)}\``,
    `🏷️ *Niche:* ${escMD(niche)}`,
    `🎯 *Goals:* ${escMD(goals)}`,
    `📧 *Email:* ${escMD(email || 'not provided')}`,
    `📄 *Pages:* ${pageCount}`,
    '',
    `🔗 *Live URL:* [${escMD(liveUrl)}](${liveUrl})`,
    `📦 *Repo:* [github\\.com/${escMD(repoFull)}](https://github.com/${repoFull})`,
    '',
    '_Built by AjayaDesign v2 Multi\\-Agent Pipeline_',
  ].join('\n');

  try {
    await sendTelegram(token, chatId, message);
    orch.log('  ✅ Telegram notification sent');
  } catch (err) {
    orch.log(`  ⚠️ Telegram failed: ${err.message}`);
  }
};

// ── Telegram API helper ────────────────────────────────────────

function sendTelegram(token, chatId, text) {
  return new Promise((resolve, reject) => {
    const payload = JSON.stringify({
      chat_id: chatId,
      text,
      parse_mode: 'MarkdownV2',
    });

    const opts = {
      hostname: 'api.telegram.org',
      path: `/bot${token}/sendMessage`,
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(payload),
      },
    };

    const req = https.request(opts, (res) => {
      let body = '';
      res.on('data', (d) => (body += d));
      res.on('end', () => {
        if (res.statusCode === 200) resolve(body);
        else reject(new Error(`Telegram API ${res.statusCode}: ${body.slice(0, 200)}`));
      });
    });

    req.on('error', reject);
    req.setTimeout(10000, () => {
      req.destroy();
      reject(new Error('Telegram timeout'));
    });
    req.write(payload);
    req.end();
  });
}

function escMD(s) {
  return String(s).replace(/([_*\[\]()~`>#+\-=|{}.!\\])/g, '\\$1');
}
