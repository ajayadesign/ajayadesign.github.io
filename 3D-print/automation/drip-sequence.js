#!/usr/bin/env node
/**
 * drip-sequence.js — Email drip automation for 3D Print Academy free course signups
 *
 * Reads signups from Firebase RTDB /free-course-signups/
 * Queues drip emails to /drip-queue/ based on days since signup
 * Tracks sent status in /drip-status/{email_key}
 *
 * Usage:
 *   node drip-sequence.js              # Process all signups
 *   node drip-sequence.js --dry-run    # Preview without writing to Firebase
 *
 * Requires: FIREBASE_SERVICE_ACCOUNT_PATH or FIREBASE_DATABASE_URL env vars
 * Falls back to ajayadesign-6d739 default config.
 */

const { initializeApp, cert } = require('firebase-admin/app');
const { getDatabase } = require('firebase-admin/database');
const fs = require('fs');
const path = require('path');

// ── Config ──────────────────────────────────────────────────────────
const DATABASE_URL = process.env.FIREBASE_DATABASE_URL || 'https://ajayadesign-6d739-default-rtdb.firebaseio.com';
const DRY_RUN = process.argv.includes('--dry-run');

const DRIP_SCHEDULE = [
  { day: 0,  key: 'welcome',           template: 'welcome.html',           subject: 'Welcome to 3D Print Academy! 🎉' },
  { day: 2,  key: 'lesson-2',          template: 'lesson-2.html',          subject: "How's it going? Lesson 2 is ready 🖨️" },
  { day: 4,  key: 'lesson-3',          template: 'lesson-3.html',          subject: 'Ready for Lesson 3? ⚡' },
  { day: 7,  key: 'full-course-offer', template: 'full-course-offer.html', subject: 'You finished the free course! Here\'s 10% off the full academy 🏆' },
  { day: 14, key: 'last-chance',       template: 'last-chance.html',       subject: 'Still thinking about it? Let\'s do the math 🧮' },
];

const TEMPLATES_DIR = path.join(__dirname, 'templates');

// ── Firebase Init ───────────────────────────────────────────────────
function initFirebase() {
  const saPath = process.env.FIREBASE_SERVICE_ACCOUNT_PATH;
  const opts = { databaseURL: DATABASE_URL };

  if (saPath && fs.existsSync(saPath)) {
    opts.credential = cert(JSON.parse(fs.readFileSync(saPath, 'utf8')));
  }
  // If no service account, uses GOOGLE_APPLICATION_CREDENTIALS or default creds

  initializeApp(opts);
  return getDatabase();
}

// ── Helpers ─────────────────────────────────────────────────────────
function daysSince(isoDate) {
  const signup = new Date(isoDate);
  const now = new Date();
  return Math.floor((now - signup) / (1000 * 60 * 60 * 24));
}

function loadTemplate(filename) {
  return fs.readFileSync(path.join(TEMPLATES_DIR, filename), 'utf8');
}

function renderTemplate(html, vars) {
  let out = html;
  for (const [k, v] of Object.entries(vars)) {
    out = out.replaceAll(`{{${k}}}`, v);
  }
  return out;
}

function emailKeyFromEmail(email) {
  return email.replace(/[.#$[\]]/g, '_');
}

// ── Main ────────────────────────────────────────────────────────────
async function main() {
  console.log(`🚀 Drip Sequence Processor ${DRY_RUN ? '(DRY RUN)' : ''}`);
  console.log(`   Database: ${DATABASE_URL}\n`);

  const db = initFirebase();

  // Fetch signups
  const signupsSnap = await db.ref('free-course-signups').once('value');
  const signups = signupsSnap.val();

  if (!signups) {
    console.log('No signups found. Exiting.');
    return;
  }

  // Fetch existing drip status
  const statusSnap = await db.ref('drip-status').once('value');
  const allStatus = statusSnap.val() || {};

  let queued = 0;
  let skipped = 0;

  for (const [emailKey, signup] of Object.entries(signups)) {
    const { email, signup_date } = signup;
    if (!email || !signup_date) {
      console.log(`  ⚠ Skipping ${emailKey} — missing email or signup_date`);
      continue;
    }

    const days = daysSince(signup_date);
    const status = allStatus[emailKey] || {};
    const name = signup.name || email.split('@')[0];

    console.log(`  📧 ${email} — signed up ${days}d ago`);

    for (const drip of DRIP_SCHEDULE) {
      if (days < drip.day) continue;          // Not time yet
      if (status[drip.key]) {                  // Already sent
        skipped++;
        continue;
      }

      // Load and render template
      const html = renderTemplate(loadTemplate(drip.template), {
        NAME: name,
        EMAIL: email,
        UNSUBSCRIBE_URL: `https://ajayadesign.github.io/3D-print/unsubscribe?email=${encodeURIComponent(email)}`,
      });

      const queueEntry = {
        to: email,
        subject: drip.subject,
        html,
        drip_key: drip.key,
        status: 'pending',
        created_at: new Date().toISOString(),
        signup_key: emailKey,
      };

      if (DRY_RUN) {
        console.log(`    ✉ [DRY RUN] Would queue "${drip.key}" — ${drip.subject}`);
      } else {
        // Push to queue
        const queueRef = db.ref('drip-queue').push();
        await queueRef.set(queueEntry);

        // Mark as sent in status
        await db.ref(`drip-status/${emailKey}/${drip.key}`).set({
          queued_at: new Date().toISOString(),
          queue_id: queueRef.key,
        });

        console.log(`    ✉ Queued "${drip.key}" — ${drip.subject}`);
      }
      queued++;
    }
  }

  console.log(`\n✅ Done. Queued: ${queued} | Skipped (already sent): ${skipped}`);
}

main().catch((err) => {
  console.error('❌ Error:', err.message);
  process.exit(1);
});
