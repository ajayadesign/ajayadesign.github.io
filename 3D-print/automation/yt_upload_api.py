#!/usr/bin/env python3
"""
YouTube Data API v3 — Batch Uploader for 3D Print Academy.
Uses OAuth2 Desktop flow for authentication.
Uploads all videos as Unlisted with proper titles/descriptions.
"""
import os, sys, json, time, pickle, http.client, httplib2, random
from pathlib import Path
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

CLIENT_SECRET = os.path.expanduser("~/client_secret.json")
TOKEN_PICKLE = os.path.expanduser("~/yt_token.pickle")
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

# Retry config
MAX_RETRIES = 10
RETRIABLE_STATUS_CODES = [500, 502, 503, 504]

# ── Video Upload Queue ────────────────────────────────────────────────────
# (filepath, title, description, category_id)
# Category 27 = Education
UPLOADS = [
    # Module 1
    ("~/video-uploads/3D-Printer-s-Anatomy.mp4",
     "3D Print Academy: Lesson 1.1 — 3D Printer Anatomy",
     "Module 1, Lesson 1 — Know your machine: extruder, bed, frame, stepper motors, hotend — every part explained.\n\n🎓 3D Print Academy by AJ Design\nhttps://ajayadesign.github.io/3D-print/"),

    ("~/video-uploads/Precision-Bed-Leveling.mp4",
     "3D Print Academy: Lesson 1.2 — Bed Leveling Mastery",
     "Module 1, Lesson 2 — Foundation of every good print: paper test, mesh leveling, and Z-offset.\n\n🎓 3D Print Academy by AJ Design\nhttps://ajayadesign.github.io/3D-print/"),

    ("~/video-uploads/Mastering-Cura-for-Frames.mp4",
     "3D Print Academy: Lesson 1.4 — Slicer Setup: Cura",
     "Module 1, Lesson 4 — Master Cura slicer settings optimized for magnet frames.\n\n🎓 3D Print Academy by AJ Design\nhttps://ajayadesign.github.io/3D-print/"),

    ("~/video-uploads/Mastering-PrusaSlicer.mp4",
     "3D Print Academy: Lesson 1.5 — Slicer Setup: PrusaSlicer",
     "Module 1, Lesson 5 — PrusaSlicer setup from first install to frame-optimized profiles.\n\n🎓 3D Print Academy by AJ Design\nhttps://ajayadesign.github.io/3D-print/"),

    ("~/video-uploads/Your-First-3D-Print.mp4",
     "3D Print Academy: Lesson 1.6 — Your First Test Print",
     "Module 1, Lesson 6 — Start-to-finish walkthrough: your first 3D print with real troubleshooting tips.\n\n🎓 3D Print Academy by AJ Design\nhttps://ajayadesign.github.io/3D-print/"),

    ("~/video-uploads/From-Beginner-to-Builder.mp4",
     "3D Print Academy: Lesson 1.7 — Module 1 Recap",
     "Module 1, Lesson 7 — Recap of 3D printing fundamentals. Everything you've learned so far.\n\n🎓 3D Print Academy by AJ Design\nhttps://ajayadesign.github.io/3D-print/"),

    # Module 2
    ("~/video-uploads/Tinkercad-Zero-to-3D-Hero.mp4",
     "3D Print Academy: Lesson 2.1 — TinkerCAD Introduction",
     "Module 2, Lesson 1 — Learn TinkerCAD from scratch: interface, shapes panel, workplane, and basic operations.\n\n🎓 3D Print Academy by AJ Design\nhttps://ajayadesign.github.io/3D-print/"),

    ("~/video-uploads/lesson-2-2-first-frame-tinkercad.mp4",
     "3D Print Academy: Lesson 2.2 — Your First Magnet Frame",
     "Module 2, Lesson 2 — Build your first 4×3 photo frame from scratch in TinkerCAD. 112×87mm body with magnet slots.\n\n🎓 3D Print Academy by AJ Design\nhttps://ajayadesign.github.io/3D-print/"),

    ("~/video-uploads/Fusion-360-Parametric-Design.mp4",
     "3D Print Academy: Lesson 2.3 — Fusion 360 Introduction",
     "Module 2, Lesson 3 — Introduction to Fusion 360 for parametric frame design.\n\n🎓 3D Print Academy by AJ Design\nhttps://ajayadesign.github.io/3D-print/"),

    ("~/video-uploads/Mastering-3D-Tolerances.mp4",
     "3D Print Academy: Lesson 2.4 — Magnet Slot Tolerances",
     "Module 2, Lesson 4 — Tolerances for magnet slots, photo inserts, and press-fit joints.\n\n🎓 3D Print Academy by AJ Design\nhttps://ajayadesign.github.io/3D-print/"),

    ("~/video-uploads/Snap-Fit-Clip-Design.mp4",
     "3D Print Academy: Lesson 2.5 — Snap-Fit Clip Design",
     "Module 2, Lesson 5 — Design snap-fit clips for secure photo frames.\n\n🎓 3D Print Academy by AJ Design\nhttps://ajayadesign.github.io/3D-print/"),

    ("~/video-uploads/Export-STL-&-Test-Slice.mp4",
     "3D Print Academy: Lesson 2.6 — Export STL & Test Slice",
     "Module 2, Lesson 6 — Export your frame as STL and test-slice it in Cura.\n\n🎓 3D Print Academy by AJ Design\nhttps://ajayadesign.github.io/3D-print/"),

    # Module 3
    ("~/video-uploads/Retro-TV-Frame-Design.mp4",
     "3D Print Academy: Lesson 3.2 — Retro TV Frame",
     "Module 3, Lesson 2 — Design a fun retro TV-shaped magnet frame.\n\n🎓 3D Print Academy by AJ Design\nhttps://ajayadesign.github.io/3D-print/"),

    ("~/video-uploads/lesson-3-3-polaroid-frame.mp4",
     "3D Print Academy: Lesson 3.3 — Polaroid Frame",
     "Module 3, Lesson 3 — Design a Polaroid-style frame with distinctive wide bottom border. 88×107mm with 72×72mm square opening.\n\n🎓 3D Print Academy by AJ Design\nhttps://ajayadesign.github.io/3D-print/"),

    ("~/video-uploads/lesson-3-4-instax-mini-frame.mp4",
     "3D Print Academy: Lesson 3.4 — Instax Mini Frame",
     "Module 3, Lesson 4 — Design a compact Instax Mini photo frame in TinkerCAD. 72×56mm body, 62×46mm opening.\n\n🎓 3D Print Academy by AJ Design\nhttps://ajayadesign.github.io/3D-print/"),

    ("~/video-uploads/lesson-3-5-multi-photo-collage.mp4",
     "3D Print Academy: Lesson 3.5 — Multi-Photo Collage Frame",
     "Module 3, Lesson 5 — Build a premium 3-photo collage frame in TinkerCAD. 200×80mm body with three 52×52mm openings. Your highest-priced product.\n\n🎓 3D Print Academy by AJ Design\nhttps://ajayadesign.github.io/3D-print/"),

    ("~/video-uploads/lesson-3-6-custom-text-frame.mp4",
     "3D Print Academy: Lesson 3.6 — Custom Text Frame (Personalization)",
     "Module 3, Lesson 6 — Add embossed text to frames for premium personalization. Charge $2-5 more per frame.\n\n🎓 3D Print Academy by AJ Design\nhttps://ajayadesign.github.io/3D-print/"),

    ("~/video-uploads/Shopify-Store-Setup.mp4",
     "3D Print Academy: Lesson 6.3 — Shopify Store Setup",
     "Module 6, Lesson 3 — Complete Shopify walkthrough: Dawn theme, product listings, photography tips, shipping, payments, and abandoned checkout recovery.\n\n🎓 3D Print Academy by AJ Design\nhttps://ajayadesign.github.io/3D-print/"),

    # ── New NotebookLM lesson videos (19) ─────────────────────────────────
    ("~/video-uploads/lesson-2-7-cad-design.mp4",
     "3D Print Academy: Lesson 2.7 — Module 2 Recap: CAD Design",
     "Module 2, Lesson 7 — Recap of CAD design basics: TinkerCAD, Fusion 360, tolerances, snap-fits, and STL export.\n\n🎓 3D Print Academy by AJ Design\nhttps://ajayadesign.github.io/3D-print/"),

    ("~/video-uploads/lesson-3-1-modular-frames.mp4",
     "3D Print Academy: Lesson 3.1 — Multi-Piece Magnetic Assemblies",
     "Module 3, Lesson 1 — Design modular magnetic frames with multi-piece assemblies and interchangeable parts.\n\n🎓 3D Print Academy by AJ Design\nhttps://ajayadesign.github.io/3D-print/"),

    ("~/video-uploads/lesson-3-7-quality-control.mp4",
     "3D Print Academy: Lesson 3.7 — Quality Showcase & Review",
     "Module 3, Lesson 7 — From hobbyist to pro: quality control showcase and review of premium frame designs.\n\n🎓 3D Print Academy by AJ Design\nhttps://ajayadesign.github.io/3D-print/"),

    ("~/video-uploads/lesson-4-1-layer-height.mp4",
     "3D Print Academy: Lesson 4.1 — Layer Height Comparison",
     "Module 4, Lesson 1 — Match layer height to frame design for optimal print quality and speed.\n\n🎓 3D Print Academy by AJ Design\nhttps://ajayadesign.github.io/3D-print/"),

    ("~/video-uploads/lesson-4-3-speed-quality.mp4",
     "3D Print Academy: Lesson 4.3 — Speed vs Quality Tuning",
     "Module 4, Lesson 3 — Find the sweet spot between print speed and quality for production frames.\n\n🎓 3D Print Academy by AJ Design\nhttps://ajayadesign.github.io/3D-print/"),

    ("~/video-uploads/lesson-4-4-temperature-tower.mp4",
     "3D Print Academy: Lesson 4.4 — Temperature Tower Test",
     "Module 4, Lesson 4 — 30-minute fix for perfect prints using temperature tower calibration.\n\n🎓 3D Print Academy by AJ Design\nhttps://ajayadesign.github.io/3D-print/"),

    ("~/video-uploads/lesson-4-5-stringing.mp4",
     "3D Print Academy: Lesson 4.5 — Fix Stringing & Oozing",
     "Module 4, Lesson 5 — Eliminate stringing and oozing with retraction tuning and travel settings.\n\n🎓 3D Print Academy by AJ Design\nhttps://ajayadesign.github.io/3D-print/"),

    ("~/video-uploads/lesson-4-6-bed-adhesion.mp4",
     "3D Print Academy: Lesson 4.6 — Fix Warping & Bed Adhesion",
     "Module 4, Lesson 6 — Solve warping and bed adhesion issues for reliable first layers.\n\n🎓 3D Print Academy by AJ Design\nhttps://ajayadesign.github.io/3D-print/"),

    ("~/video-uploads/lesson-4-7-elephants-foot.mp4",
     "3D Print Academy: Lesson 4.7 — Fix Elephant's Foot",
     "Module 4, Lesson 7 — Diagnose and fix elephant's foot for clean frame bases.\n\n🎓 3D Print Academy by AJ Design\nhttps://ajayadesign.github.io/3D-print/"),

    ("~/video-uploads/lesson-4-8-batch-production.mp4",
     "3D Print Academy: Lesson 4.8 — Batch Printing for Production",
     "Module 4, Lesson 8 — Scale up with batch printing: plate filling, sequential printing, and quality at volume.\n\n🎓 3D Print Academy by AJ Design\nhttps://ajayadesign.github.io/3D-print/"),

    ("~/video-uploads/lesson-5-1-sanding.mp4",
     "3D Print Academy: Lesson 5.1 — Sanding Technique",
     "Module 5, Lesson 1 — Grit progression sanding guide for smooth, retail-ready 3D prints.\n\n🎓 3D Print Academy by AJ Design\nhttps://ajayadesign.github.io/3D-print/"),

    ("~/video-uploads/lesson-5-2-filler-primer.mp4",
     "3D Print Academy: Lesson 5.2 — Filler Primer Application",
     "Module 5, Lesson 2 — Pro finishing with filler primer: hide layer lines and prep for paint.\n\n🎓 3D Print Academy by AJ Design\nhttps://ajayadesign.github.io/3D-print/"),

    ("~/video-uploads/lesson-5-3-spray-painting.mp4",
     "3D Print Academy: Lesson 5.3 — Spray Painting Technique",
     "Module 5, Lesson 3 — Professional spray finishing for 3D printed frames: technique, colors, and coats.\n\n🎓 3D Print Academy by AJ Design\nhttps://ajayadesign.github.io/3D-print/"),

    ("~/video-uploads/lesson-5-4-clear-coat.mp4",
     "3D Print Academy: Lesson 5.4 — Clear Coating for Durability",
     "Module 5, Lesson 4 — Level up your 3D prints with clear coat protection for lasting finish.\n\n🎓 3D Print Academy by AJ Design\nhttps://ajayadesign.github.io/3D-print/"),

    ("~/video-uploads/lesson-5-5-mid-print-magnet.mp4",
     "3D Print Academy: Lesson 5.5 — Magnet Installation: Mid-Print Pause",
     "Module 5, Lesson 5 — The invisible magnet technique: embed magnets during printing with mid-print pause.\n\n🎓 3D Print Academy by AJ Design\nhttps://ajayadesign.github.io/3D-print/"),

    ("~/video-uploads/lesson-5-6-post-glue-magnet.mp4",
     "3D Print Academy: Lesson 5.6 — Magnet Installation: Post-Glue Method",
     "Module 5, Lesson 6 — The post-glue method for secure magnet installation after printing.\n\n🎓 3D Print Academy by AJ Design\nhttps://ajayadesign.github.io/3D-print/"),

    ("~/video-uploads/lesson-6-2-pricing.mp4",
     "3D Print Academy: Lesson 6.2 — Pricing Strategy ($5–$15 Retail)",
     "Module 6, Lesson 2 — Price your 3D printed frames for profit: cost analysis, market positioning, and margin targets.\n\n🎓 3D Print Academy by AJ Design\nhttps://ajayadesign.github.io/3D-print/"),

    ("~/video-uploads/lesson-6-5-product-photography.mp4",
     "3D Print Academy: Lesson 6.5 — Product Photography",
     "Module 6, Lesson 5 — Photos that sell 3D prints: lighting, angles, props, and editing for online listings.\n\n🎓 3D Print Academy by AJ Design\nhttps://ajayadesign.github.io/3D-print/"),

    ("~/video-uploads/lesson-6-6-packaging-shipping.mp4",
     "3D Print Academy: Lesson 6.6 — Packaging & Shipping",
     "Module 6, Lesson 6 — From box to brand: premium packaging and shipping for your magnet frame business.\n\n🎓 3D Print Academy by AJ Design\nhttps://ajayadesign.github.io/3D-print/"),

    # ── Module-level overview videos (from NotebookLM, not yet on YouTube) ──
    ("~/Downloads/CAD-Design-Basics.mp4",
     "3D Print Academy: Module 2 Overview — CAD Design Basics",
     "Module 2 overview — Learn CAD design basics for creating 3D-printed magnet photo frames. TinkerCAD, Fusion 360, tolerances, snap-fits, and STL export.\n\n🎓 3D Print Academy by AJ Design\nhttps://ajayadesign.github.io/3D-print/"),

    ("~/Downloads/3D-Print-Finishing.mp4",
     "3D Print Academy: Module 5 Overview — Post-Processing & Finishing",
     "Module 5 overview — Transform raw prints into retail-ready products: sanding, priming, painting, clear coating, and magnet installation.\n\n🎓 3D Print Academy by AJ Design\nhttps://ajayadesign.github.io/3D-print/"),

    ("~/Downloads/Launch-Your-Magnet-Business.mp4",
     "3D Print Academy: Module 6 Overview — Launch Your Magnet Business",
     "Module 6 overview — Everything you need to launch your magnet frame business: pricing, Shopify, craft fairs, photography, packaging, and scaling.\n\n🎓 3D Print Academy by AJ Design\nhttps://ajayadesign.github.io/3D-print/"),
]


def get_authenticated_service():
    """Authenticate via OAuth2 Desktop flow. Returns YouTube API service."""
    creds = None
    if os.path.exists(TOKEN_PICKLE):
        with open(TOKEN_PICKLE, "rb") as f:
            creds = pickle.load(f)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET, SCOPES)
            # Use console flow — paste the auth code manually
            creds = flow.run_local_server(port=0, open_browser=False)
        with open(TOKEN_PICKLE, "wb") as f:
            pickle.dump(creds, f)

    return build("youtube", "v3", credentials=creds)


def upload_video(youtube, filepath, title, description, category="27", privacy="unlisted"):
    """Upload a single video with resumable upload + exponential backoff."""
    filepath = os.path.expanduser(filepath)
    if not os.path.exists(filepath):
        print(f"  SKIP: {filepath} not found")
        return None

    size_mb = os.path.getsize(filepath) / (1024 * 1024)
    print(f"\n{'='*60}")
    print(f"  Uploading: {os.path.basename(filepath)} ({size_mb:.1f} MB)")
    print(f"  Title: {title}")
    print(f"{'='*60}")

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": ["3D printing", "magnet frame", "TinkerCAD", "3D Print Academy", "AJ Design"],
            "categoryId": category,
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(filepath, chunksize=10 * 1024 * 1024, resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    error = None
    retry = 0

    while response is None:
        try:
            status, response = request.next_chunk()
            if status:
                pct = int(status.progress() * 100)
                print(f"  ↑ {pct}%", end="\r")
        except HttpError as e:
            if e.resp.status in RETRIABLE_STATUS_CODES:
                error = f"HTTP {e.resp.status}: {e.content.decode()}"
            else:
                raise
        except Exception as e:
            error = str(e)

        if error:
            retry += 1
            if retry > MAX_RETRIES:
                print(f"  FAILED after {MAX_RETRIES} retries: {error}")
                return None
            wait = random.random() * (2 ** retry)
            print(f"  Retry {retry}/{MAX_RETRIES} in {wait:.1f}s: {error}")
            time.sleep(wait)
            error = None

    video_id = response["id"]
    print(f"  ✓ Uploaded! ID: {video_id}")
    print(f"    https://youtu.be/{video_id}")
    return video_id


def main():
    print("="*60)
    print("  3D Print Academy — YouTube Batch Uploader (API v3)")
    print("="*60)
    print(f"  Videos to upload: {len(UPLOADS)}")
    print()

    # Load previously uploaded results to skip them
    results_file = os.path.expanduser("~/video-uploads/upload_results.json")
    prev_results = {}
    if os.path.exists(results_file):
        with open(results_file) as f:
            prev_results = json.load(f)
        if prev_results:
            print(f"  Skipping {len(prev_results)} already-uploaded videos\n")

    youtube = get_authenticated_service()
    print("  ✓ Authenticated with YouTube API\n")

    results = dict(prev_results)  # preserve previous results
    uploaded_this_run = 0
    for i, (filepath, title, desc) in enumerate(UPLOADS, 1):
        basename = os.path.basename(os.path.expanduser(filepath))
        if basename in prev_results:
            print(f"[{i}/{len(UPLOADS)}] SKIP (already uploaded): {basename} → {prev_results[basename]}")
            continue
        print(f"\n[{i}/{len(UPLOADS)}]")
        try:
            vid = upload_video(youtube, filepath, title, desc)
            if vid:
                results[basename] = vid
                uploaded_this_run += 1
        except HttpError as e:
            err_msg = e.content.decode() if e.content else str(e)
            print(f"  ERROR: {e.resp.status} — {err_msg[:200]}")
            if "exceeded the number of videos" in err_msg or "quotaExceeded" in err_msg:
                print("\n  *** UPLOAD QUOTA EXCEEDED — stopping. Re-run later. ***")
                break
        except Exception as e:
            print(f"  ERROR: {e}")

        # Small delay between uploads
        if i < len(UPLOADS):
            time.sleep(3)

    # ── Summary ───────────────────────────────────────────────────────────
    new_total = len(results) - len(prev_results)
    print(f"\n{'='*60}")
    print(f"  THIS RUN: {uploaded_this_run} uploaded")
    print(f"  TOTAL: {len(results)}/{len(UPLOADS)} done")
    print(f"{'='*60}")
    for filename, vid in results.items():
        marker = " (new)" if filename not in prev_results else ""
        print(f"  {filename} → {vid}{marker}")

    # Save results
    results_file = os.path.expanduser("~/video-uploads/upload_results.json")
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n  Results saved to {results_file}")


if __name__ == "__main__":
    main()
