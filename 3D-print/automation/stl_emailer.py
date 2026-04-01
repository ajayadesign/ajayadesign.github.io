#!/usr/bin/env python3
"""
STL Lead Auto-Emailer
Watches Firebase /leads for new 3d-print-stl submissions and sends a welcome email
with a free STL sample pack download link.

Runs as a polling daemon — checks every 60 seconds for new leads.
Uses Gmail SMTP with aj@ajayadesign.com as sender.
"""

import json
import os
import smtplib
import time
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError

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

# STL download page (public page on the site with the free samples)
STL_DOWNLOAD_URL = "https://ajayadesign.com/3D-print/free-stl-pack"
COURSE_URL = "https://ajayadesign.com/3D-print/#enroll"

# ── State Management ────────────────────────────────────────────
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
    """Fetch all leads from Firebase (public read is blocked, but we use REST shallow query)."""
    try:
        url = f"{FIREBASE_DB}/leads.json"
        req = Request(url, headers={"Accept": "application/json"})
        with urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
            return data if data else {}
    except Exception as e:
        print(f"[ERROR] Firebase fetch failed: {e}", flush=True)
        return {}

# ── Email ───────────────────────────────────────────────────────
def build_email_html(name, email):
    first_name = (name or "there").split()[0]
    return f"""\
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background:#111;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
  <div style="max-width:600px;margin:0 auto;background:#1a1a1a;border:1px solid #333;border-radius:12px;overflow:hidden;">

    <!-- Header -->
    <div style="background:linear-gradient(135deg,#ed1c24 0%,#b91c1c 100%);padding:32px 24px;text-align:center;">
      <h1 style="color:#fff;margin:0;font-size:24px;font-weight:700;">🎉 Your Free STL Pack is Ready!</h1>
      <p style="color:rgba(255,255,255,0.85);margin:8px 0 0;font-size:14px;">3D Print Academy — Magnet Frame Starter Kit</p>
    </div>

    <!-- Body -->
    <div style="padding:32px 24px;color:#e0e0e0;line-height:1.7;">
      <p style="font-size:16px;margin-top:0;">Hey {first_name}! 👋</p>

      <p>Thanks for signing up — here's your <strong>free magnet frame STL starter pack</strong>. These are the same designs we use in the full course, optimized for FDM printing:</p>

      <div style="text-align:center;margin:28px 0;">
        <a href="{STL_DOWNLOAD_URL}" style="display:inline-block;background:#ed1c24;color:#fff;text-decoration:none;padding:14px 32px;border-radius:8px;font-weight:600;font-size:16px;">
          ⬇️ Download Your STL Pack
        </a>
      </div>

      <p><strong>What's included:</strong></p>
      <ul style="color:#ccc;padding-left:20px;">
        <li>Instax Mini magnet frame</li>
        <li>4×6 photo magnet frame</li>
        <li>Heart-shaped magnet frame</li>
        <li>Star magnet frame</li>
        <li>Slicer settings guide (PLA/PETG)</li>
      </ul>

      <p style="margin-top:24px;">These frames are print-ready — just slice and go. Each one is designed to hold standard neodymium magnets (10mm × 2mm).</p>

      <hr style="border:none;border-top:1px solid #333;margin:28px 0;">

      <p><strong>Want the full course?</strong></p>
      <p>The starter pack is just the beginning. The full <a href="{COURSE_URL}" style="color:#ed1c24;text-decoration:none;font-weight:600;">3D Print Academy</a> includes 43 lessons, 15+ STL files with commercial license, live mentorship, and everything you need to start selling magnet frames as a business.</p>

      <div style="text-align:center;margin:24px 0;">
        <a href="{COURSE_URL}" style="display:inline-block;border:1px solid #ed1c24;color:#ed1c24;text-decoration:none;padding:12px 28px;border-radius:8px;font-weight:600;font-size:14px;">
          See Full Course →
        </a>
      </div>

      <p style="color:#888;font-size:13px;margin-top:28px;">Happy printing! 🖨️<br>— AJ, 3D Print Academy</p>
    </div>

    <!-- Footer -->
    <div style="background:#111;padding:20px 24px;text-align:center;border-top:1px solid #333;">
      <p style="color:#666;font-size:12px;margin:0;">
        You're getting this because you signed up at <a href="https://ajayadesign.com/3D-print" style="color:#888;">ajayadesign.com/3D-print</a>
      </p>
    </div>
  </div>
</body>
</html>"""


def send_email(to_email, to_name):
    """Send the STL welcome email."""
    msg = MIMEMultipart("alternative")
    msg["From"] = f"{SENDER_NAME} <{SENDER_EMAIL}>"
    msg["To"] = to_email
    msg["Subject"] = f"Your Free STL Starter Pack is Ready 🎉"
    msg["Reply-To"] = SENDER_EMAIL

    # Plain text fallback
    first_name = (to_name or "there").split()[0]
    plain = f"""Hey {first_name}!

Thanks for signing up for the 3D Print Academy starter pack!

Download your free STL files here:
{STL_DOWNLOAD_URL}

Included: Instax Mini frame, 4x6 frame, heart frame, star frame, and slicer settings.

Want the full course? Check it out: {COURSE_URL}

Happy printing!
— AJ, 3D Print Academy
"""
    msg.attach(MIMEText(plain, "plain"))
    msg.attach(MIMEText(build_email_html(to_name, to_email), "html"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(SENDER_EMAIL, to_email, msg.as_string())

    print(f"[OK] Sent STL email to {to_email} ({to_name})", flush=True)


# ── Main Loop ───────────────────────────────────────────────────
def main():
    print(f"[START] STL Lead Emailer — polling every {POLL_INTERVAL}s", flush=True)
    print(f"[CONFIG] Sender: {SENDER_EMAIL} via {SMTP_USER}", flush=True)

    if not SMTP_PASS:
        print("[FATAL] SMTP_APP_PASSWORD not set!", flush=True)
        sys.exit(1)

    state = load_state()

    while True:
        try:
            leads = fetch_leads()
            new_count = 0

            for key, lead in leads.items():
                # Only process 3d-print-stl leads we haven't emailed yet
                if key in state["sent_keys"]:
                    continue
                if lead.get("source") != "3d-print-stl":
                    state["sent_keys"].append(key)
                    save_state(state)
                    continue

                email = lead.get("email", "").strip()
                name = lead.get("name", "")

                if not email or "@" not in email:
                    print(f"[SKIP] Bad email for key {key}: {email!r}", flush=True)
                    state["sent_keys"].append(key)
                    save_state(state)
                    continue

                # Skip test emails
                if "cbabe-test" in email.lower():
                    print(f"[SKIP] Test email: {email}", flush=True)
                    state["sent_keys"].append(key)
                    save_state(state)
                    continue

                try:
                    send_email(email, name)
                    new_count += 1
                except Exception as e:
                    print(f"[ERROR] Failed to send to {email}: {e}", flush=True)
                    # Don't mark as sent — retry next cycle
                    continue

                state["sent_keys"].append(key)
                save_state(state)

            state["last_check"] = int(time.time())
            save_state(state)

            if new_count:
                print(f"[SUMMARY] Sent {new_count} new email(s)", flush=True)

        except Exception as e:
            print(f"[ERROR] Main loop: {e}", flush=True)

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
