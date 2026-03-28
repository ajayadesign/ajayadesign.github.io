/**
 * 3D Print Academy — Google Apps Script
 * Stripe Webhook + Auto-Approval + Email Onboarding
 *
 * AUTOMATED SETUP (via clasp CLI):
 *   $ cd 3D-print/google-apps-script
 *   $ clasp push
 *   $ clasp deploy --description "v1" 
 *   $ clasp open --webapp   ← copy the Web App URL
 *
 * MANUAL SETUP (alternative):
 *   1. Go to https://script.google.com/home → New Project
 *   2. Paste this entire file into Code.gs
 *   3. Set Script Properties (gear icon → Project Settings → Script Properties):
 *        STRIPE_SECRET_KEY = sk_live_51TFlQz...
 *        FIREBASE_DB_URL   = https://ajayadesign-6d739-default-rtdb.firebaseio.com
 *   4. Deploy → New Deployment → Web App
 *        Execute as: Me (ajayadesign@gmail.com)
 *        Who has access: Anyone
 *   5. Copy the Web App URL
 *   6. Register webhook:
 *        $ stripe webhook_endpoints create --url <WEB_APP_URL> --enabled-events checkout.session.completed
 *
 * TRIGGERS (set once):
 *   Triggers (clock icon) → Add Trigger → processEmailQueue → Hour timer → Every hour
 *
 * VERIFICATION: Events verified by re-fetching from Stripe API (not HMAC — Apps Script limitation)
 *
 * FEATURES:
 *   - Receives Stripe checkout.session.completed webhook
 *   - Maps product → tier, auto-approves in RTDB
 *   - Stores in /pre_approved if user hasn't signed into portal yet
 *   - Sends welcome email via Gmail (Day 0)
 *   - Queues follow-up emails at Day 1, 3, 7, 14 (processed hourly)
 *   - Notifies admin of every purchase
 */

// ─── CONFIG ───────────────────────────────────────────────────────────────────

/** Product ID → tier mapping (LIVE Stripe products) */
var PRODUCT_TIER_MAP = {
  'prod_UEEzw3X7DTYSTO': 'stl',
  'prod_UEEztyshyZQa7E': 'course',
  'prod_UEEz5f7fmMy38f': 'session',
  'prod_UEF0aZrf5nyrxX': 'bundle'
};

/** Tier display names */
var TIER_NAMES = {
  'stl':     'STL Starter Pack',
  'course':  'Full Course',
  'session': '1-on-1 Session',
  'bundle':  'Complete Bundle'
};

/** Tier access descriptions for welcome email */
var TIER_ACCESS_LIST = {
  'stl':     '✅ 15+ ready-to-print STL magnet frame designs\n✅ Slicer profiles for PLA, PETG, ASA\n✅ Commercial license included',
  'course':  '✅ All 6 modules (44+ video lessons)\n✅ 15+ STL files included\n✅ Slicer profiles & settings\n✅ Pricing calculator & business templates\n✅ Lifetime access + updates',
  'session': '✅ 90-minute private video call\n✅ Screen sharing & live CAD help\n✅ Print troubleshooting\n✅ Session recording sent to you',
  'bundle':  '✅ Everything in the Full Course\n✅ All 15+ STL designs\n✅ 2× live 1-on-1 sessions\n✅ Priority scheduling\n✅ Lifetime updates & new STLs'
};

var SENDER_NAME = 'Ajaya — 3D Print Academy';
var PORTAL_URL  = 'https://ajayadesign.github.io/3D-print/portal/';

// ─── HELPERS ──────────────────────────────────────────────────────────────────

function getProps() {
  return PropertiesService.getScriptProperties();
}

function stripeGet(endpoint) {
  var sk = getProps().getProperty('STRIPE_SECRET_KEY');
  var resp = UrlFetchApp.fetch('https://api.stripe.com/v1/' + endpoint, {
    headers: { 'Authorization': 'Basic ' + Utilities.base64Encode(sk + ':') },
    muteHttpExceptions: true
  });
  return JSON.parse(resp.getContentText());
}

/**
 * Firebase RTDB — read a path (returns parsed JSON or null)
 */
function fbRead(path) {
  var url = getProps().getProperty('FIREBASE_DB_URL') + '/' + path + '.json';
  // Use the service account OAuth token for admin access
  var token = ScriptApp.getOAuthToken();
  var resp = UrlFetchApp.fetch(url, {
    headers: { 'Authorization': 'Bearer ' + token },
    muteHttpExceptions: true
  });
  var data = JSON.parse(resp.getContentText());
  return data;
}

/**
 * Firebase RTDB — write (PUT) to a path
 */
function fbWrite(path, data) {
  var url = getProps().getProperty('FIREBASE_DB_URL') + '/' + path + '.json';
  var token = ScriptApp.getOAuthToken();
  UrlFetchApp.fetch(url, {
    method: 'put',
    contentType: 'application/json',
    headers: { 'Authorization': 'Bearer ' + token },
    payload: JSON.stringify(data),
    muteHttpExceptions: true
  });
}

/**
 * Firebase RTDB — push (POST) to a path
 */
function fbPush(path, data) {
  var url = getProps().getProperty('FIREBASE_DB_URL') + '/' + path + '.json';
  var token = ScriptApp.getOAuthToken();
  var resp = UrlFetchApp.fetch(url, {
    method: 'post',
    contentType: 'application/json',
    headers: { 'Authorization': 'Bearer ' + token },
    payload: JSON.stringify(data),
    muteHttpExceptions: true
  });
  return JSON.parse(resp.getContentText());
}

/**
 * Firebase RTDB — delete a path
 */
function fbDelete(path) {
  var url = getProps().getProperty('FIREBASE_DB_URL') + '/' + path + '.json';
  var token = ScriptApp.getOAuthToken();
  UrlFetchApp.fetch(url, {
    method: 'delete',
    headers: { 'Authorization': 'Bearer ' + token },
    muteHttpExceptions: true
  });
}

/**
 * Firebase RTDB — query by child value
 */
function fbQuery(path, orderBy, equalTo) {
  var url = getProps().getProperty('FIREBASE_DB_URL') + '/' + path + '.json'
    + '?orderBy="' + orderBy + '"&equalTo="' + equalTo + '"';
  var token = ScriptApp.getOAuthToken();
  var resp = UrlFetchApp.fetch(url, {
    headers: { 'Authorization': 'Bearer ' + token },
    muteHttpExceptions: true
  });
  return JSON.parse(resp.getContentText());
}

// ─── STRIPE WEBHOOK ───────────────────────────────────────────────────────────

/**
 * Web App entry point — receives Stripe webhook POST
 */
function doPost(e) {
  try {
    var payload = JSON.parse(e.postData.contents);
    var eventId = payload.id;
    var eventType = payload.type;

    // Only handle checkout.session.completed
    if (eventType !== 'checkout.session.completed') {
      return ContentService.createTextOutput(
        JSON.stringify({ received: true, ignored: eventType })
      ).setMimeType(ContentService.MimeType.JSON);
    }

    // Verify event by re-fetching from Stripe API (prevents forged events)
    var verified = stripeGet('events/' + eventId);
    if (!verified || verified.id !== eventId || verified.type !== eventType) {
      console.error('Event verification failed for: ' + eventId);
      return ContentService.createTextOutput(
        JSON.stringify({ error: 'verification_failed' })
      ).setMimeType(ContentService.MimeType.JSON);
    }

    var session = verified.data.object;
    var customerEmail = '';

    // Get email from customer_details
    if (session.customer_details && session.customer_details.email) {
      customerEmail = session.customer_details.email;
    }

    if (!customerEmail) {
      console.error('No customer email in session: ' + session.id);
      return ContentService.createTextOutput(
        JSON.stringify({ error: 'no_email' })
      ).setMimeType(ContentService.MimeType.JSON);
    }

    // Get line items to determine product/tier
    var lineItems = stripeGet('checkout/sessions/' + session.id + '/line_items?expand[]=data.price.product');

    var tier = null;
    if (lineItems && lineItems.data) {
      for (var i = 0; i < lineItems.data.length; i++) {
        var item = lineItems.data[i];
        var productId = typeof item.price.product === 'string'
          ? item.price.product
          : item.price.product.id;
        if (PRODUCT_TIER_MAP[productId]) {
          tier = PRODUCT_TIER_MAP[productId];
          break;
        }
      }
    }

    if (!tier) {
      console.warn('No matching tier for session: ' + session.id);
      return ContentService.createTextOutput(
        JSON.stringify({ received: true, no_tier: true })
      ).setMimeType(ContentService.MimeType.JSON);
    }

    // Process the approval
    var result = processApproval(customerEmail, tier, session.id);

    // Send welcome email
    sendWelcomeEmail(customerEmail, tier, session.customer_details.name || '');

    // Schedule follow-up emails (queue-based, processed hourly)
    scheduleFollowUps(customerEmail, tier, session.customer_details.name || '');

    // Notify admin
    notifyAdmin(customerEmail, tier, session.id);

    return ContentService.createTextOutput(
      JSON.stringify({ received: true, approved: result.approved, tier: tier })
    ).setMimeType(ContentService.MimeType.JSON);

  } catch (err) {
    console.error('Webhook error: ' + err.message + '\n' + err.stack);
    return ContentService.createTextOutput(
      JSON.stringify({ error: err.message })
    ).setMimeType(ContentService.MimeType.JSON);
  }
}

/**
 * Handle GET requests (health check / test)
 */
function doGet(e) {
  return ContentService.createTextOutput(
    JSON.stringify({ status: 'ok', service: '3D Print Academy Webhook' })
  ).setMimeType(ContentService.MimeType.JSON);
}

// ─── APPROVAL LOGIC ───────────────────────────────────────────────────────────

/**
 * Try to approve the user in Firebase RTDB.
 * If user exists in pending_users (already signed in), approve directly.
 * If not, store in pre_approved for auto-approval on first sign-in.
 */
function processApproval(email, tier, sessionId) {
  var now = Date.now();

  // Check pending_users for this email
  var pending = fbRead('pending_users');
  var uid = null;

  if (pending) {
    var keys = Object.keys(pending);
    for (var i = 0; i < keys.length; i++) {
      if (pending[keys[i]] && pending[keys[i]].email === email) {
        uid = keys[i];
        break;
      }
    }
  }

  if (uid) {
    // User already signed in — approve directly
    fbWrite('approved_users/' + uid, {
      email: email,
      tier: tier,
      stripe_session: sessionId,
      approved_at: now
    });
    fbDelete('pending_users/' + uid);
    console.log('Approved: ' + email + ' (' + uid + ') as ' + tier);
    return { approved: true, method: 'direct' };
  }

  // User hasn't signed in yet — pre-approve
  fbPush('pre_approved', {
    email: email,
    tier: tier,
    stripe_session: sessionId,
    approved_at: now
  });
  console.log('Pre-approved: ' + email + ' as ' + tier);
  return { approved: true, method: 'pre_approved' };
}

// ─── EMAIL AUTOMATION ─────────────────────────────────────────────────────────

/**
 * Send the Day 0 welcome email immediately after purchase
 */
function sendWelcomeEmail(email, tier, fullName) {
  var firstName = (fullName || '').split(' ')[0] || 'there';
  var tierName = TIER_NAMES[tier] || tier;
  var accessList = TIER_ACCESS_LIST[tier] || '';

  var subject = '🎉 You\'re in! Here\'s how to get started';

  var body = 'Hey ' + firstName + ',\n\n'
    + 'Welcome to the 3D Print Academy! You just made a seriously smart move.\n\n'
    + 'Here\'s exactly what to do right now:\n\n'
    + 'STEP 1: Log into your portal\n'
    + '→ ' + PORTAL_URL + '\n'
    + 'Sign in with the same Google account you used to purchase.\n\n'
    + 'STEP 2: Check your tier\n'
    + 'You\'re on the ' + tierName + ' plan. Here\'s what you have access to:\n'
    + accessList + '\n\n'
    + 'STEP 3: Start Module 1\n'
    + 'Don\'t overthink it — just open Module 1, Lesson 1 and press play.\n\n'
    + 'If you hit any issues logging in or accessing content, reply to this email directly. I read every one.\n\n'
    + 'Welcome to the family,\n'
    + 'Ajaya\n\n'
    + 'P.S. Bookmark this link — it\'s your portal: ' + PORTAL_URL;

  var htmlBody = '<div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;color:#333">'
    + '<h2 style="color:#ED1C24">Welcome to 3D Print Academy! 🎉</h2>'
    + '<p>Hey ' + escapeHtml(firstName) + ',</p>'
    + '<p>Welcome to the <strong>3D Print Academy</strong>! You just made a seriously smart move.</p>'
    + '<p>Here\'s exactly what to do right now:</p>'
    + '<h3>Step 1: Log into your portal</h3>'
    + '<p>→ <a href="' + PORTAL_URL + '" style="color:#00D4FF">' + PORTAL_URL + '</a><br>'
    + 'Sign in with the same Google account you used to purchase.</p>'
    + '<h3>Step 2: Check your tier</h3>'
    + '<p>You\'re on the <strong>' + escapeHtml(tierName) + '</strong> plan:</p>'
    + '<pre style="background:#f5f5f5;padding:12px;border-radius:6px;font-size:14px">' + escapeHtml(accessList) + '</pre>'
    + '<h3>Step 3: Start Module 1</h3>'
    + '<p>Don\'t overthink it — just open Module 1, Lesson 1 and press play.</p>'
    + '<p><a href="' + PORTAL_URL + 'module-1.html" style="display:inline-block;padding:12px 24px;background:#ED1C24;color:#fff;border-radius:6px;text-decoration:none;font-weight:bold">Start Module 1 →</a></p>'
    + '<p style="color:#666;font-size:13px">If you hit any issues, reply to this email directly. I read every one.</p>'
    + '<hr style="border:none;border-top:1px solid #eee;margin:24px 0">'
    + '<p>Welcome to the family,<br><strong>Ajaya</strong></p>'
    + '<p style="color:#999;font-size:12px">AjayaDesign — 3D Print Academy<br>' + PORTAL_URL + '</p>'
    + '</div>';

  GmailApp.sendEmail(email, subject, body, {
    name: SENDER_NAME,
    htmlBody: htmlBody,
    replyTo: 'ajayadesign@gmail.com'
  });

  console.log('Welcome email sent to: ' + email);
}

/**
 * Schedule follow-up emails by writing to /email_queue in Firebase RTDB.
 * A time-driven trigger (processEmailQueue, every hour) processes the queue.
 */
function scheduleFollowUps(email, tier, fullName) {
  var now = Date.now();
  var delays = [1, 3, 7, 14]; // Days

  for (var i = 0; i < delays.length; i++) {
    fbPush('email_queue', {
      email: email,
      tier: tier,
      name: fullName,
      day: delays[i],
      send_after: now + (delays[i] * 24 * 60 * 60 * 1000),
      sent: false
    });
  }
  console.log('Email queue entries created for: ' + email);
}

/**
 * Process the email queue — run this hourly via a time-driven trigger.
 * Go to Triggers (clock icon) → Add Trigger → processEmailQueue →
 * Time-driven → Hour timer → Every hour
 */
function processEmailQueue() {
  var queue = fbRead('email_queue');
  if (!queue) return;

  var now = Date.now();
  var keys = Object.keys(queue);

  for (var i = 0; i < keys.length; i++) {
    var entry = queue[keys[i]];
    if (!entry || entry.sent) continue;
    if (entry.send_after > now) continue;

    // Time to send
    try {
      sendFollowUpEmail(entry.email, entry.tier, entry.name, entry.day);
      // Mark as sent
      fbWrite('email_queue/' + keys[i] + '/sent', true);
      console.log('Sent Day ' + entry.day + ' email to: ' + entry.email);
    } catch (err) {
      console.error('Failed to send Day ' + entry.day + ' to ' + entry.email + ': ' + err.message);
    }
  }
}

/**
 * Send a follow-up email based on the day number
 */
function sendFollowUpEmail(email, tier, fullName, dayNum) {
  var firstName = (fullName || '').split(' ')[0] || 'there';

  var subject, body, htmlBody;

  if (dayNum === 1) {
    subject = 'Your first magnet frame — faster than you think';
    body = getDay1Body(firstName);
    htmlBody = getDay1Html(firstName);
  } else if (dayNum === 3) {
    subject = 'The design that sells the most (it\'s not what you\'d guess)';
    body = getDay3Body(firstName);
    htmlBody = getDay3Html(firstName);
  } else if (dayNum === 7) {
    subject = 'Quick check-in (+ a tool you\'ll want)';
    body = getDay7Body(firstName);
    htmlBody = getDay7Html(firstName);
  } else if (dayNum === 14) {
    subject = 'What\'s next for your magnet frame business?';
    body = getDay14Body(firstName, tier);
    htmlBody = getDay14Html(firstName, tier);
  } else {
    return;
  }

  GmailApp.sendEmail(email, subject, body, {
    name: SENDER_NAME,
    htmlBody: htmlBody,
    replyTo: 'ajayadesign@gmail.com'
  });
}

// ─── EMAIL TEMPLATES ──────────────────────────────────────────────────────────

function getDay1Body(name) {
  return 'Hey ' + name + ',\n\n'
    + 'Quick question: have you opened Module 1 yet?\n\n'
    + 'Most students print their first magnet frame within 48 hours of starting.\n\n'
    + 'That\'s not weeks of theory. It\'s:\n'
    + '- Day 1: Learn your printer + slice your first file\n'
    + '- Day 2: Print, drop in magnets, stick it on your fridge\n\n'
    + 'Start Module 1: ' + PORTAL_URL + 'module-1.html\n'
    + 'Pricing Calculator: https://ajayadesign.github.io/3D-print/tools/calculator.html\n\n'
    + 'Go get that first print done.\n\n— Ajaya';
}

function getDay1Html(name) {
  return wrapEmail(
    '<p>Hey ' + escapeHtml(name) + ',</p>'
    + '<p>Quick question: have you opened Module 1 yet?</p>'
    + '<p><strong>Most students print their first magnet frame within 48 hours of starting.</strong></p>'
    + '<p>That\'s not weeks of theory:</p>'
    + '<ul><li>Day 1: Learn your printer + slice your first file</li>'
    + '<li>Day 2: Print, drop in magnets, stick it on your fridge</li></ul>'
    + '<p><a href="' + PORTAL_URL + 'module-1.html" style="display:inline-block;padding:12px 24px;background:#ED1C24;color:#fff;border-radius:6px;text-decoration:none;font-weight:bold">Start Module 1 →</a></p>'
    + '<p>Also — I made you a <a href="https://ajayadesign.github.io/3D-print/tools/calculator.html" style="color:#00D4FF">Pricing Calculator</a> so you can figure out what to charge.</p>'
    + '<p>— Ajaya</p>'
  );
}

function getDay3Body(name) {
  return 'Hey ' + name + ',\n\n'
    + 'Here\'s something I learned the hard way:\n\n'
    + 'The #1 selling magnet frame isn\'t fancy. It\'s the simple rectangle with rounded corners.\n\n'
    + 'Why?\n'
    + '- It fits every photo size\n'
    + '- It prints in under 45 minutes\n'
    + '- The clean look matches any kitchen\n'
    + '- Customers buy 3-4 at a time\n\n'
    + 'Module 2 teaches you to design both simple and complex frames.\n'
    + '→ ' + PORTAL_URL + 'module-2.html\n\n'
    + 'Pro tip: Use the STL files in Module 3 to start selling immediately while you learn to design your own.\n\n'
    + '— Ajaya';
}

function getDay3Html(name) {
  return wrapEmail(
    '<p>Hey ' + escapeHtml(name) + ',</p>'
    + '<p>Here\'s something I learned the hard way:</p>'
    + '<p><strong>The #1 selling magnet frame isn\'t fancy. It\'s the simple rectangle with rounded corners.</strong></p>'
    + '<ul><li>It fits every photo size</li><li>Prints in under 45 minutes</li>'
    + '<li>Clean look matches any kitchen</li><li>Customers buy 3-4 at a time</li></ul>'
    + '<p><a href="' + PORTAL_URL + 'module-2.html" style="display:inline-block;padding:12px 24px;background:#ED1C24;color:#fff;border-radius:6px;text-decoration:none;font-weight:bold">Start Module 2: Design →</a></p>'
    + '<p><strong>Pro tip:</strong> Use the STL files in Module 3 to start selling <em>immediately</em> while you learn to design your own.</p>'
    + '<p>— Ajaya</p>'
  );
}

function getDay7Body(name) {
  return 'Hey ' + name + ',\n\n'
    + 'It\'s been a week. How\'s it going?\n\n'
    + 'Most students fall into one of three buckets:\n\n'
    + '🟢 Crushing it — Printed several frames\n'
    + '🟡 Started but stuck — Hit a print issue\n'
    + '🔴 Haven\'t started yet — Life happened\n\n'
    + 'If you\'re stuck, Module 4 covers every common problem:\n'
    + '→ ' + PORTAL_URL + 'module-4.html\n\n'
    + 'QC Checklist: https://ajayadesign.github.io/3D-print/tools/checklist.html\n\n'
    + 'Reply if you need help. Seriously.\n\n— Ajaya';
}

function getDay7Html(name) {
  return wrapEmail(
    '<p>Hey ' + escapeHtml(name) + ',</p>'
    + '<p>It\'s been a week. How\'s it going?</p>'
    + '<p>Most students fall into one of three buckets:</p>'
    + '<p>🟢 <strong>Crushing it</strong> — Printed several frames<br>'
    + '🟡 <strong>Started but stuck</strong> — Hit a print issue<br>'
    + '🔴 <strong>Haven\'t started yet</strong> — Life happened</p>'
    + '<p>If you\'re stuck, <strong>Module 4</strong> covers every common problem:</p>'
    + '<p><a href="' + PORTAL_URL + 'module-4.html" style="display:inline-block;padding:12px 24px;background:#ED1C24;color:#fff;border-radius:6px;text-decoration:none;font-weight:bold">Module 4: Troubleshooting →</a></p>'
    + '<p>Here\'s the <a href="https://ajayadesign.github.io/3D-print/tools/checklist.html" style="color:#00D4FF">QC Checklist</a> — use it before shipping any frame.</p>'
    + '<p>Reply to this email if you need help. Seriously.</p>'
    + '<p>— Ajaya</p>'
  );
}

function getDay14Body(name, tier) {
  var upsell = '';
  if (tier === 'stl') {
    upsell = '\n\nWant to level up? You\'re on the STL-only plan. Upgrade to the Full Course ($97):\n→ https://ajayadesign.github.io/contact/?ref=3d-course-upgrade';
  } else if (tier === 'course') {
    upsell = '\n\nWant personal guidance? Book a 1-on-1 live session ($149):\n→ https://ajayadesign.github.io/contact/?ref=3d-mentorship-upgrade';
  }

  return 'Hey ' + name + ',\n\n'
    + 'Two weeks in. Let\'s talk about where you go from here.\n\n'
    + 'The students who turn this into a side hustle do three things:\n'
    + '1. They batch-print (4-8 frames per plate, overnight)\n'
    + '2. They pick ONE platform (Shopify or craft fairs)\n'
    + '3. They price with confidence (use the calculator)\n\n'
    + 'Module 6 covers all of this:\n'
    + '→ ' + PORTAL_URL + 'module-6.html'
    + upsell + '\n\n'
    + 'Go print something today.\n\n'
    + '— Ajaya\n\n'
    + 'Toolkit:\n'
    + '📊 Pricing Calculator: https://ajayadesign.github.io/3D-print/tools/calculator.html\n'
    + '✅ QC Checklist: https://ajayadesign.github.io/3D-print/tools/checklist.html\n'
    + '🛒 Materials List: https://ajayadesign.github.io/3D-print/tools/materials.html';
}

function getDay14Html(name, tier) {
  var upsell = '';
  if (tier === 'stl') {
    upsell = '<div style="background:#f0f9ff;border-left:4px solid #00D4FF;padding:16px;margin:16px 0;border-radius:4px">'
      + '<strong>Want to level up?</strong> You\'re on the STL-only plan. Get the full video course with all 44 lessons:'
      + '<br><a href="https://ajayadesign.github.io/contact/?ref=3d-course-upgrade" style="color:#ED1C24;font-weight:bold">Upgrade to Full Course ($97) →</a></div>';
  } else if (tier === 'course') {
    upsell = '<div style="background:#f0f9ff;border-left:4px solid #00D4FF;padding:16px;margin:16px 0;border-radius:4px">'
      + '<strong>Want personal guidance?</strong> Get a 1-on-1 live session — print audit, slicer tuning, Shopify setup:'
      + '<br><a href="https://ajayadesign.github.io/contact/?ref=3d-mentorship-upgrade" style="color:#ED1C24;font-weight:bold">Book 1-on-1 Session ($149) →</a></div>';
  }

  return wrapEmail(
    '<p>Hey ' + escapeHtml(name) + ',</p>'
    + '<p>Two weeks in. Let\'s talk about where you go from here.</p>'
    + '<p><strong>The students who turn this into a side hustle do three things:</strong></p>'
    + '<ol><li>They batch-print (4-8 frames per plate, overnight)</li>'
    + '<li>They pick ONE platform (Shopify or craft fairs)</li>'
    + '<li>They price with confidence (use the calculator)</li></ol>'
    + '<p><a href="' + PORTAL_URL + 'module-6.html" style="display:inline-block;padding:12px 24px;background:#ED1C24;color:#fff;border-radius:6px;text-decoration:none;font-weight:bold">Module 6: Build Your Business →</a></p>'
    + upsell
    + '<hr style="border:none;border-top:1px solid #eee;margin:24px 0">'
    + '<p><strong>Your Toolkit:</strong></p>'
    + '<p>📊 <a href="https://ajayadesign.github.io/3D-print/tools/calculator.html" style="color:#00D4FF">Pricing Calculator</a><br>'
    + '✅ <a href="https://ajayadesign.github.io/3D-print/tools/checklist.html" style="color:#00D4FF">QC Checklist</a><br>'
    + '🛒 <a href="https://ajayadesign.github.io/3D-print/tools/materials.html" style="color:#00D4FF">Materials List</a></p>'
    + '<p>Go print something today.</p>'
    + '<p>— <strong>Ajaya</strong></p>'
  );
}

// ─── ADMIN NOTIFICATION ───────────────────────────────────────────────────────

/**
 * Notify admin of new purchase via email
 */
function notifyAdmin(customerEmail, tier, sessionId) {
  var subject = '💰 New 3D Academy Purchase: ' + TIER_NAMES[tier];
  var body = 'New student:\n'
    + 'Email: ' + customerEmail + '\n'
    + 'Tier: ' + tier + ' (' + TIER_NAMES[tier] + ')\n'
    + 'Session: ' + sessionId + '\n'
    + 'Time: ' + new Date().toISOString() + '\n\n'
    + 'Admin panel: https://ajayadesign.github.io/3D-print/portal/admin.html';

  GmailApp.sendEmail('ajayadesign@gmail.com', subject, body, {
    name: '3D Print Academy Bot'
  });
}

// ─── UTILITIES ────────────────────────────────────────────────────────────────

function escapeHtml(str) {
  return (str || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function wrapEmail(content) {
  return '<div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;color:#333">'
    + content
    + '<hr style="border:none;border-top:1px solid #eee;margin:24px 0">'
    + '<p style="color:#999;font-size:12px">AjayaDesign — 3D Print Academy<br>'
    + '<a href="' + PORTAL_URL + '" style="color:#999">' + PORTAL_URL + '</a></p>'
    + '</div>';
}

// ─── MANUAL FUNCTIONS ─────────────────────────────────────────────────────────

/**
 * Test the webhook locally — run this to verify everything works
 */
function testWebhook() {
  var result = processApproval('test@example.com', 'course', 'ses_test_123');
  console.log(JSON.stringify(result));
  // Clean up test data
  // fbDelete('pre_approved/...');
}

/**
 * Check pending_users who might have pre_approved entries
 * Run manually to reconcile any missed auto-approvals
 */
function reconcilePendingUsers() {
  var pending = fbRead('pending_users');
  if (!pending) { console.log('No pending users'); return; }

  var preApproved = fbRead('pre_approved');
  if (!preApproved) { console.log('No pre-approved entries'); return; }

  // Build email → pre_approved key+entry map
  var preMap = {};
  var preKeys = Object.keys(preApproved);
  for (var i = 0; i < preKeys.length; i++) {
    var entry = preApproved[preKeys[i]];
    if (entry && entry.email) {
      preMap[entry.email] = { key: preKeys[i], entry: entry };
    }
  }

  // Check each pending user
  var pendingKeys = Object.keys(pending);
  for (var j = 0; j < pendingKeys.length; j++) {
    var pUser = pending[pendingKeys[j]];
    if (!pUser || !pUser.email) continue;

    var match = preMap[pUser.email];
    if (match) {
      // Auto-approve
      fbWrite('approved_users/' + pendingKeys[j], {
        email: pUser.email,
        tier: match.entry.tier,
        stripe_session: match.entry.stripe_session || '',
        approved_at: Date.now()
      });
      fbDelete('pending_users/' + pendingKeys[j]);
      fbDelete('pre_approved/' + match.key);
      console.log('Reconciled: ' + pUser.email + ' → ' + match.entry.tier);
    }
  }
}

/**
 * Clean up old sent emails from the queue (older than 30 days)
 */
function cleanupEmailQueue() {
  var queue = fbRead('email_queue');
  if (!queue) return;

  var cutoff = Date.now() - (30 * 24 * 60 * 60 * 1000);
  var keys = Object.keys(queue);

  for (var i = 0; i < keys.length; i++) {
    var entry = queue[keys[i]];
    if (entry && entry.sent && entry.send_after < cutoff) {
      fbDelete('email_queue/' + keys[i]);
    }
  }
  console.log('Email queue cleanup complete');
}
