#!/usr/bin/env python3
"""
STL Lead Auto-Emailer
Watches Firebase /leads for new 3d-print-stl submissions and sends a welcome email
with a free STL sample pack download link.

Runs as a polling daemon — checks every 60 seconds for new leads.
Uses Gmail SMTP with aj@ajayadesign.com as sender.
Uses Google OAuth refresh token for Firebase auth.
"""

import json
import os
import smtplib
import time
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlencode

# ── Config ──────────────────────────────────────────────────────
FIREBASE_DB = "https://ajayadesign-6d739-default-rtdb.firebaseio.com"
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = os.environ.get("SMTP_EMAIL", "ajayadesign@gmail.com")
SMTP_PASS = os.environ.get("SMTP_APP_PASSWORD", "")
SENDER_NAME = "AJ — 3D Print Academy"
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "aj@ajayadesign.com")
POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL", "60"))
STATE_FILE = Path(__file__).parent / "emailer_state.json"

FIREBASE_CONFIG = Path.home() / ".config/configstore/firebase-tools.json"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
FIREBASE_CLIENT_ID = "563584335869-fgrhgmd47bqnekij5i8b5pr03ho849e6.apps.googleusercontent.com"
FIREBASE_CLIENT_SECRET = "j9iVZfS8kkCEFUPaAeJV0sAi"

STL_DOWNLOAD_URL = "https://ajayadesign.com/3D-print/free-stl-pack/"
COURSE_URL = "https://ajayadesign.com/3D-print/#enroll"


# ── Firebase Auth ───────────────────────────────────────────────
def get_refresh_token():
    try:
        with open(FIREBASE_CONFIG) as f:
            data = json.load(f)
        return data.get("tokens", {}).get("refresh_token", "")
    except Exception as e:
        print(f"[ERROR] Can't read firebase config: {e}", flush=True)
        return ""


def get_access_token():
    """Always refresh to avoid stale tokens (called once per poll cycle)."""
    refresh_token = get_refresh_token()
    if not refresh_token:
        return None
    try:
        body = urlencode({
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": FIREBASE_CLIENT_ID,
            "client_secret": FIREBASE_CLIENT_SECRET,
        }).encode()
        req = Request(GOOGLE_TOKEN_URL, data=body, method="POST")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        with urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())["access_token"]
    except Exception as e:
        print(f"[ERROR] Token refresh failed: {e}", flush=True)
        return None


# ── State ───────────────────────────────────────────────────────
def load_state():
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"sent_keys": [], "last_check": 0}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


# ── Firebase ────────────────────────────────────────────────────
def fetch_leads():
    token = get_access_token()
    if not token:
        return {}
    try:
        req = Request(
            f"{FIREBASE_DB}/leads.json",
            headers={"Authorization": f"Bearer {token}"},
        )
        with urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
            return data if data else {}
    except Exception as e:
        print(f"[ERROR] Firebase fetch failed: {e}", flush=True)
        return {}


# ── Email ───────────────────────────────────────────────────────
def build_html(name):
    first = (name or "there").split()[0]
    return f"""\
<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background:#111;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
<div style="max-width:600px;margin:0 auto;background:#1a1a1a;border:1px solid #333;border-radius:12px;overflow:hidden;">
  <div style="background:linear-gradient(135deg,#ed1c24,#b91c1c);padding:32px 24px;text-align:center;">
    <h1 style="color:#fff;margin:0;font-size:24px;">🎉 Your Free STL Pack is Ready!</h1>
    <p style="color:rgba(255,255,255,.85);margin:8px 0 0;font-size:14px;">3D Print Academy — Magnet Frame Starter Kit</p>
  </div>
  <div style="padding:32px 24px;color:#e0e0e0;line-height:1.7;">
    <p style="font-size:16px;margin-top:0;">Hey {first}! 👋</p>
    <p>Thanks for signing up — here's your <strong>free magnet frame STL starter pack</strong>. These are the same designs we use in the full course, optimized for FDM printing:</p>
    <div style="text-align:center;margin:28px 0;">
      <a href="{STL_DOWNLOAD_URL}" style="display:inline-block;background:#ed1c24;color:#fff;text-decoration:none;padding:14px 32px;border-radius:8px;font-weight:600;font-size:16px;">⬇️ Download Your STL Pack</a>
    </div>
    <p><strong>What's included:</strong></p>
    <ul style="color:#ccc;padding-left:20px;">
      <li>Instax Mini magnet frame</li>
      <li>4×6 photo magnet frame</li>
      <li>Heart-shaped magnet frame</li>
      <li>Star-shaped magnet frame</li>
      <li>Slicer settings guide (PLA/PETG)</li>
    </ul>
    <p style="margin-top:24px;">Print-ready — just slice and go. Each holds standard 10mm × 2mm neodymium magnets.</p>
    <hr style="border:none;border-top:1px solid #333;margin:28px 0;">
    <p><strong>Want the full course?</strong></p>
    <p>The full <a href="{COURSE_URL}" style="color:#ed1c24;text-decoration:none;font-weight:600;">3D Print Academy</a> has 43 lessons, 15+ STL files with commercial license, live mentorship, and business launch training.</p>
    <div style="text-align:center;margin:24px 0;">
      <a href="{COURSE_URL}" style="display:inline-block;border:1px solid #ed1c24;color:#ed1c24;text-decoration:none;padding:12px 28px;border-radius:8px;font-weight:600;font-size:14px;">See Full Course →</a>
    </div>
    <p style="color:#888;font-size:13px;margin-top:28px;">Happy printing! 🖨️<br>— AJ, 3D Print Academy</p>
  </div>
  <div style="background:#111;padding:20px 24px;text-align:center;border-top:1px solid #333;">
    <p style="color:#666;font-size:12px;margin:0;">You signed up at <a href="https://ajayadesign.com/3D-print" style="color:#888;">ajayadesign.com/3D-print</a></p>
  </div>
</div></body></html>"""


def send_email(to_email, to_name):
    msg = MIMEMultipart("alternative")
    msg["From"] = f"{SENDER_NAME} <{SENDER_EMAIL}>"
    msg["To"] = to_email
    msg["Subject"] = "Your Free STL Starter Pack is Ready 🎉"
    msg["Reply-To"] = SENDER_EMAIL

    first = (to_name or "there").split()[0]
    plain = f"Hey {first}!\n\nDownload your free STL files: {STL_DOWNLOAD_URL}\n\nIncludes: Instax Mini, 4x6, heart, star frames + slicer settings.\n\nFull course: {COURSE_URL}\n\n— AJ, 3D Print Academy"

    msg.attach(MIMEText(plain, "plain"))
    msg.attach(MIMEText(build_html(to_name), "html"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as s:
        s.starttls()
        s.login(SMTP_USER, SMTP_PASS)
        s.sendmail(SENDER_EMAIL, to_email, msg.as_string())

    print(f"[OK] Sent to {to_email} ({to_name})", flush=True)


# ── Main ────────────────────────────────────────────────────────
def main():
    print(f"[START] STL Lead Emailer — polling every {POLL_INTERVAL}s", flush=True)
    print(f"[CONFIG] From: {SENDER_EMAIL} via {SMTP_USER}", flush=True)

    if not SMTP_PASS:
        print("[FATAL] SMTP_APP_PASSWORD not set!", flush=True)
        sys.exit(1)

    token = get_access_token()
    print(f"[{'OK' if token else 'WARN'}] Firebase auth {'working' if token else 'failed — will retry'}", flush=True)

    state = load_state()

    while True:
        try:
            leads = fetch_leads()
            new_count = 0

            for key, lead in leads.items():
                if key in state["sent_keys"]:
                    continue
                if lead.get("source") != "3d-print-stl":
                    state["sent_keys"].append(key)
                    save_state(state)
                    continue

                email = lead.get("email", "").strip()
                name = lead.get("name", "")

                if not email or "@" not in email:
                    print(f"[SKIP] Bad email: {email!r}", flush=True)
                    state["sent_keys"].append(key)
                    save_state(state)
                    continue

                if "cbabe-test" in email.lower():
                    print(f"[SKIP] Test: {email}", flush=True)
                    state["sent_keys"].append(key)
                    save_state(state)
                    continue

                try:
                    send_email(email, name)
                    new_count += 1
                except Exception as e:
                    print(f"[ERROR] Send failed for {email}: {e}", flush=True)
                    continue

                state["sent_keys"].append(key)
                save_state(state)

            state["last_check"] = int(time.time())
            save_state(state)
            if new_count:
                print(f"[SUMMARY] Sent {new_count} email(s)", flush=True)

        except Exception as e:
            print(f"[ERROR] Loop: {e}", flush=True)

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
