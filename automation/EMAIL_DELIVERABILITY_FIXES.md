# Email Deliverability Crisis — Root Cause Analysis & Fixes

**Date:** 2026-03-30
**Problem:** 0.2% open rate, 0% reply rate, 7.7% bounce rate

## Root Causes Identified

### 1. 🔴 CRITICAL: Sending from Gmail (@gmail.com) for cold outreach
- Gmail SMTP is **not designed for cold email**. Google monitors sending patterns and throttles/blocks accounts doing mass cold outreach.
- **"AjayaDesign" brand name in From header** flags as promotional/spam. Changed to "Ajaya Dahal" (personal name).
- **Fix applied:** Changed `From` header from `AjayaDesign <email>` → `Ajaya Dahal <email>` in both `email_service.py` and `smtp_pool.py`.

### 2. 🔴 CRITICAL: Missing List-Unsubscribe Header
- Gmail and Yahoo **require** `List-Unsubscribe` header since Feb 2024 for bulk senders.
- Without it, emails are silently filed into spam.
- **Fix applied:** Added `List-Unsubscribe` and `List-Unsubscribe-Post` headers.

### 3. 🟡 HIGH: No Custom Sending Domain (SPF/DKIM/DMARC)
- Sending from `@gmail.com` means you're sharing reputation with billions of other Gmail users.
- **YOU NEED A CUSTOM DOMAIN** like `mail@ajayadesign.com` with:
  - SPF record pointing to your SMTP provider
  - DKIM signatures
  - DMARC policy (`p=none` to start)
- **Recommended providers for cold email:**
  - **Google Workspace** ($6/mo) — best deliverability, uses Gmail infrastructure
  - **Instantly.ai** ($30/mo) — built for cold outreach, auto warm-up
  - **Smartlead** ($39/mo) — mailbox rotation, warm-up included
- **Action needed:** Set up a custom domain with proper DNS records.

### 4. 🟡 HIGH: No Warm-up Period
- New sending addresses need 2-4 weeks of gradual sending to build reputation.
- Start with 5-10 emails/day, increase by 5 every few days.
- Send to known contacts first to generate opens/replies.

### 5. 🟢 MODERATE: Subject Line Improvements
- Previous subjects were too generic and lowercase.
- **Fix applied:** New subject variants include first-name personalization and conversational tone.
- Avoid spam trigger words: "free", "guarantee", "act now", "limited time".

### 6. 🟢 MODERATE: Tracking Pixel Detection
- Email tracking pixels can trigger spam filters (especially Gmail).
- Consider making tracking opt-in or removing the pixel for first-touch emails.
- The `<img src="__TRACKING_PIXEL_URL__" width="1" height="1">` pattern is well-known to spam filters.

## Bounce Rate Analysis (7.7%)

Likely causes:
- **Scraped/guessed emails** from Google Maps don't always resolve to real inboxes
- **Catch-all domains** accept delivery but the person never sees it
- The email verification (`email_verify.py`) does MX checks but can't verify Gmail/Yahoo/Outlook recipients (they block RCPT TO probes)

### Fix: Pre-Send Verification Improvements
- Use a service like **ZeroBounce** or **NeverBounce** ($0.008/verification) for high-confidence verification
- Filter out role-based addresses (`info@`, `admin@`, `contact@`) — they rarely belong to decision makers
- Require `email_verified = True` before sending

## Immediate Action Items

1. **[DONE]** Fix From header — personal name instead of brand
2. **[DONE]** Add List-Unsubscribe headers
3. **[DONE]** Improve subject lines with personalization
4. **[TODO]** Set up custom sending domain (ajayadesign.com)
5. **[TODO]** Configure SPF/DKIM/DMARC on sending domain
6. **[TODO]** Implement 2-4 week warm-up before scaling sends
7. **[TODO]** Consider removing tracking pixel from step-1 emails
8. **[TODO]** Add email verification service (ZeroBounce/NeverBounce)
9. **[TODO]** Filter out role-based email addresses from send queue
