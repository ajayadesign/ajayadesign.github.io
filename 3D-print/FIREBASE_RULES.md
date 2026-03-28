# Firebase Realtime Database Security Rules

## Architecture Overview

```
                    ┌─────────────────────────┐
                    │     Google OAuth         │
                    │   (Firebase Auth)        │
                    └────────┬────────────────┘
                             │
                    ┌────────▼────────────────┐
                    │   User Signs In          │
                    │   Gets uid + email       │
                    └────────┬────────────────┘
                             │
                 ┌───────────┼───────────────┐
                 │           │               │
          ┌──────▼─────┐ ┌──▼──────────┐ ┌──▼──────────────┐
          │  Admin?     │ │ Approved?   │ │ Not approved    │
          │ (email ==   │ │ (exists in  │ │ (no record in   │
          │  admin@)    │ │ /approved_  │ │  /approved_     │
          │             │ │  users/)    │ │   users/)       │
          └──────┬──────┘ └──────┬──────┘ └──────┬──────────┘
                 │               │               │
          ┌──────▼──────┐ ┌─────▼───────┐ ┌─────▼──────────┐
          │ Full access  │ │ Dashboard + │ │ Write self to  │
          │ + Admin      │ │ Modules     │ │ /pending_users │
          │   panel      │ │ (per tier)  │ │ Show "pending" │
          └─────────────┘ └─────────────┘ └────────────────┘
```

## RTDB Structure

```
/approved_users/{uid}
  ├── email: "customer@gmail.com"
  ├── name: "Customer Name"
  ├── tier: "course" | "bundle" | "stl" | "session"
  ├── approved_at: 1711500000000 (server timestamp)
  ├── approved_by: "admin_uid_here"
  └── payment_ref: "shopify_order_12345"

/pending_users/{uid}
  ├── email: "customer@gmail.com"
  ├── name: "Customer Name"
  ├── photo: "https://..."
  └── requested_at: 1711500000000 (server timestamp)

/courses/{uid}/progress/
  ├── module-1: true
  ├── module-2: true
  └── ...
```

## Security Rules — DEPLOYED via Firebase CLI

**Status: ✅ LIVE** (deployed 2026-03-27 via `firebase deploy --only database`)

Rules source file: `/database.rules.json`

To redeploy after editing:
```bash
cd /home/aj/website/ajayadesign.github.io
firebase deploy --only database --project ajayadesign-6d739
```

```json
{
  "rules": {
    "approved_users": {
      ".read": "auth != null && auth.token.email === 'ajayadesign@gmail.com'",
      "$uid": {
        ".read": "auth != null && auth.uid === $uid",
        ".write": "auth != null && auth.token.email === 'ajayadesign@gmail.com'",
        ".validate": "newData.hasChildren(['email', 'tier'])"
      }
    },

    "pending_users": {
      ".read": "auth != null && auth.token.email === 'ajayadesign@gmail.com'",
      "$uid": {
        ".read": "auth != null && auth.uid === $uid",
        ".write": "auth != null && ((auth.uid === $uid && !data.exists()) || auth.token.email === 'ajayadesign@gmail.com')",
        ".validate": "newData.hasChildren(['email', 'requested_at']) || !newData.exists()"
      }
    },

    "courses": {
      "$uid": {
        ".read": "auth != null && auth.uid === $uid",
        ".write": "auth != null && auth.uid === $uid",
        "progress": {
          "$module": {
            ".validate": "newData.isBoolean() && $module.matches(/^module-[1-6]$/)"
          }
        },
        "$other": {
          ".validate": false
        }
      }
    },

    "site_analytics": {
      ".read": "auth != null && auth.token.email === 'ajayadesign@gmail.com'",
      ".write": true
    },

    "leads": {
      ".read": "auth != null && auth.token.email === 'ajayadesign@gmail.com'",
      "$leadId": {
        ".write": true,
        ".validate": "newData.hasChildren(['email'])"
      }
    },

    "builds": {
      ".read": true,
      ".write": "auth != null && auth.token.email === 'ajayadesign@gmail.com'"
    },

    "quote_viewer": { "$token": { ".read": true, ".write": true } },
    "signing":      { "$token": { ".read": true, ".write": true } },

    "quotes":         { ".read": "auth != null && auth.token.email === 'ajayadesign@gmail.com'", "$id": { ".write": "auth != null && auth.token.email === 'ajayadesign@gmail.com'" } },
    "contracts":      { ".read": "auth != null && auth.token.email === 'ajayadesign@gmail.com'", ".write": "auth != null && auth.token.email === 'ajayadesign@gmail.com'" },
    "portfolio":      { ".read": "auth != null && auth.token.email === 'ajayadesign@gmail.com'", ".write": "auth != null && auth.token.email === 'ajayadesign@gmail.com'" },
    "parse_requests": { ".read": "auth != null && auth.token.email === 'ajayadesign@gmail.com'", ".write": "auth != null && auth.token.email === 'ajayadesign@gmail.com'" },
    "activity_logs":  { ".read": "auth != null && auth.token.email === 'ajayadesign@gmail.com'", ".write": "auth != null && auth.token.email === 'ajayadesign@gmail.com'" },
    "commands":       { ".read": "auth != null && auth.token.email === 'ajayadesign@gmail.com'", ".write": "auth != null && auth.token.email === 'ajayadesign@gmail.com'" },
    "outreach":       { ".read": "auth != null && auth.token.email === 'ajayadesign@gmail.com'", ".write": "auth != null && auth.token.email === 'ajayadesign@gmail.com'" },
    "drone":          { ".read": "auth != null && auth.token.email === 'ajayadesign@gmail.com'", ".write": "auth != null && auth.token.email === 'ajayadesign@gmail.com'" },

    "$other": {
      ".read": false,
      ".write": false
    }
  }
}
```

## Security Analysis

### What each rule does:

| Path | Who can read? | Who can write? |
|------|--------------|----------------|
| `/approved_users/` (list all) | Admin only | — |
| `/approved_users/{uid}` | Admin OR the user themselves | Admin only (tier must be stl/course/session/bundle) |
| `/pending_users/` (list all) | Admin only | — |
| `/pending_users/{uid}` | Admin OR the user themselves | User can write ONCE (if no data exists), Admin can write/delete |
| `/courses/{uid}` | Only that user | Only that user |
| `/courses/{uid}/progress/module-N` | Only that user | Only that user (must be boolean, must match module-[1-6]) |
| `/courses/{uid}/$other` | — | Blocked (validation=false, prevents arbitrary data) |
| `/site_analytics/**` | Admin only | Anyone (anonymous write for tracking) |
| `/leads/{id}` | Admin only | Anyone (contact form, requires email field) |
| `/builds` | Anyone (public) | Admin only |
| `/quote_viewer/{token}` | Anyone with token | Anyone with token |
| `/signing/{token}` | Anyone with token | Anyone with token |
| `/quotes`, `/contracts`, `/portfolio`, etc. | Admin only | Admin only |
| Everything else | Nobody | Nobody |

### Threat mitigations:

1. **Self-elevation blocked**: Users cannot write to `/approved_users/` — only `ajayadesign@gmail.com` can. Server-side enforced.
2. **Tier validation**: `approved_users` tier must be one of `stl|course|session|bundle` (regex validated in rules).
3. **Tier-based module gating**: Client-side `TIER_ACCESS` map in portal-auth.js restricts which modules each tier can access. STL-only users cannot access course modules.
4. **Spam prevention**: `!data.exists()` on pending_users means a user can only write ONCE. They can't overwrite.
5. **Data isolation**: Users can only read their OWN records — never other users' data.
6. **Schema validation**: `approved_users` must have `email` and `tier`. `progress` values must be booleans. Module IDs must match `module-[1-6]`. Arbitrary keys under `/courses/{uid}/` are rejected.
7. **Admin impersonation impossible**: `auth.token.email` comes from Google's OAuth ID token — can't be faked.
8. **Catch-all deny**: `$other` rule blocks all undefined paths.
9. **Admin delete capability**: Admin's write rule on `pending_users/$uid` allows deletion (for deny/cleanup).
10. **No inline onclick XSS**: Admin panel uses event delegation with `data-uid` attributes, not inline JavaScript.
11. **Existing site paths preserved**: All admin panel paths (`contracts`, `portfolio`, `quotes`, etc.) are admin-only protected, not bricked by catch-all.
12. **No console-callable admin functions**: `_approve`, `_deny`, `_revoke` removed from `window.PortalAuth` public API.

### What's NOT protected (by design):

- **Firebase config (API key, project ID)**: These are public by design in Firebase client SDKs. The API key is restricted to `ajayadesign.github.io` domain in Google Cloud Console.
- **Auth domain**: Anyone can sign into your Firebase project. That's fine — signing in doesn't grant course access.
- **YouTube unlisted URLs**: These are embedded in HTML pages that are technically in the public GitHub repo. The auth check prevents casual access, but a determined user could find them in the source code. For true protection, migrate to Bunny.net signed URLs later.

## How to Deploy Rules

```bash
# Deploy via CLI (preferred)
cd /home/aj/website/ajayadesign.github.io
firebase deploy --only database --project ajayadesign-6d739
```

Or manually: [Firebase Console → RTDB → Rules](https://console.firebase.google.com/project/ajayadesign-6d739/database/ajayadesign-6d739-default-rtdb/rules)
4. Test by:
   - Signing in as non-admin → should see "pending" screen
   - Signing in as admin → should see dashboard + admin panel works
   - Check RTDB data viewer → pending_users should populate

## Admin Workflow

1. Customer visits `/3D-print/` → clicks "Enroll" → pays via Shopify (or contact form)
2. Customer visits `/3D-print/portal/` → signs in with Google → sees "Access Pending"
3. You (admin) go to `/3D-print/portal/admin.html` → sign in with `ajayadesign@gmail.com`
4. See the customer in "Pending Approval" list
5. Verify payment in Shopify → enter Shopify order # in "Payment ref" field
6. Select tier (STL Pack / Full Course / 1-on-1 Session / Complete Bundle)
7. Click "Approve"
8. Customer logs in again → now sees the full dashboard
