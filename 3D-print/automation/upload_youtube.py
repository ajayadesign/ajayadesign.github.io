#!/usr/bin/env python3
"""
Batch YouTube Upload — Upload lesson videos to YouTube Studio via Playwright.
Uses persistent Chrome profile (already logged into Google/YouTube).
"""
import time, json, os, sys, re
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
from tinkercad_helper import get_persistent_context

CHANNEL_ID = "UCUDAzAh-qpKR4z1b9KaHNsg"
STUDIO_URL = f"https://studio.youtube.com/channel/{CHANNEL_ID}"
RESULTS_FILE = os.path.expanduser("~/video-uploads/upload-results.json")

# ── Upload Queue ──────────────────────────────────────────────────────
# (filepath, title, description, lesson_id)
UPLOADS = [
    (
        os.path.expanduser("~/video-uploads/3D-Printer-s-Anatomy.mp4"),
        "3D Print Academy: Lesson 1.1 — Printer Anatomy",
        "Lesson 1.1 of the 3D Print Academy. Learn the complete anatomy of your 3D printer — frame, hotend, extruder, build plate, and every component you need to know.\n\n#3DPrinting #3DPrintAcademy #PrinterAnatomy",
        "1-1",
    ),
    (
        os.path.expanduser("~/video-uploads/Precision-Bed-Leveling.mp4"),
        "3D Print Academy: Lesson 1.2 — Bed Leveling",
        "Lesson 1.2 of the 3D Print Academy. Master bed leveling — the foundation of every successful print.\n\n#3DPrinting #3DPrintAcademy #BedLeveling",
        "1-2",
    ),
    (
        os.path.expanduser("~/video-uploads/Mastering-Cura-for-Frames.mp4"),
        "3D Print Academy: Lesson 1.4 — Slicer Setup Cura",
        "Lesson 1.4 of the 3D Print Academy. Set up Cura slicer optimized for magnet frame printing — layer height, infill, supports, and speed.\n\n#3DPrinting #3DPrintAcademy #Cura #Slicer",
        "1-4",
    ),
    (
        os.path.expanduser("~/video-uploads/Mastering-PrusaSlicer.mp4"),
        "3D Print Academy: Lesson 1.5 — Slicer Setup PrusaSlicer",
        "Lesson 1.5 of the 3D Print Academy. Configure PrusaSlicer for photo frame production — profiles, variable layer height, and batch printing.\n\n#3DPrinting #3DPrintAcademy #PrusaSlicer",
        "1-5",
    ),
    (
        os.path.expanduser("~/video-uploads/Your-First-3D-Print.mp4"),
        "3D Print Academy: Lesson 1.6 — Your First Test Print",
        "Lesson 1.6 of the 3D Print Academy. Print your first test model and learn to evaluate print quality.\n\n#3DPrinting #3DPrintAcademy #FirstPrint",
        "1-6",
    ),
    (
        os.path.expanduser("~/video-uploads/From-Beginner-to-Builder.mp4"),
        "3D Print Academy: Lesson 1.7 — Module 1 Recap",
        "Lesson 1.7 of the 3D Print Academy. Full recap of Module 1 — 3D Printing Fundamentals. Review everything from printer anatomy to your first test print.\n\n#3DPrinting #3DPrintAcademy",
        "1-7",
    ),
    (
        os.path.expanduser("~/video-uploads/Tinkercad-Zero-to-3D-Hero.mp4"),
        "3D Print Academy: Lesson 2.1 — TinkerCAD Introduction",
        "Lesson 2.1 of the 3D Print Academy. Get started with TinkerCAD — the free browser-based CAD tool for designing magnet frames.\n\n#3DPrinting #3DPrintAcademy #TinkerCAD #CAD",
        "2-1",
    ),
    (
        os.path.expanduser("~/video-uploads/lesson-2-2-first-frame-tinkercad.mp4"),
        "3D Print Academy: Lesson 2.2 — Design Your First Magnet Frame",
        "Lesson 2.2 of the 3D Print Academy. Build a complete magnet photo frame in TinkerCAD step-by-step — live screen recording with narration.\n\n#3DPrinting #3DPrintAcademy #TinkerCAD #MagnetFrame",
        "2-2",
    ),
    (
        os.path.expanduser("~/video-uploads/Fusion-360-Parametric-Design.mp4"),
        "3D Print Academy: Lesson 2.3 — Fusion 360 Introduction",
        "Lesson 2.3 of the 3D Print Academy. Introduction to Fusion 360 for parametric frame design — sketches, extrusions, and constraints.\n\n#3DPrinting #3DPrintAcademy #Fusion360",
        "2-3",
    ),
    (
        os.path.expanduser("~/video-uploads/Mastering-3D-Tolerances.mp4"),
        "3D Print Academy: Lesson 2.4 — Tolerances & Photo Insert Sizing",
        "Lesson 2.4 of the 3D Print Academy. Master 3D print tolerances — magnet slot sizing, photo insert clearances, and test-fit methodology.\n\n#3DPrinting #3DPrintAcademy #Tolerances",
        "2-4",
    ),
    (
        os.path.expanduser("~/video-uploads/Snap-Fit-Clip-Design.mp4"),
        "3D Print Academy: Lesson 2.5 — Snap-Fit Clip Design",
        "Lesson 2.5 of the 3D Print Academy. Design snap-fit clips for secure photo and magnet attachment.\n\n#3DPrinting #3DPrintAcademy #SnapFit",
        "2-5",
    ),
    (
        os.path.expanduser("~/video-uploads/Export-STL-&-Test-Slice.mp4"),
        "3D Print Academy: Lesson 2.6 — Export STL & Test Slice",
        "Lesson 2.6 of the 3D Print Academy. Export your TinkerCAD design as STL and run a test slice in your slicer.\n\n#3DPrinting #3DPrintAcademy #STL #Export",
        "2-6",
    ),
    (
        os.path.expanduser("~/video-uploads/3D-Print-a-Magnet-Frame.mp4"),
        "3D Print Academy: Lesson 3.1 — Multi-Piece Magnetic Assemblies",
        "Lesson 3.1 of the 3D Print Academy. Design multi-piece magnetic assemblies — frames that snap together magnetically.\n\n#3DPrinting #3DPrintAcademy #MagnetFrame",
        "3-1",
    ),
    (
        os.path.expanduser("~/video-uploads/Retro-TV-Frame-Design.mp4"),
        "3D Print Academy: Lesson 3.2 — Retro TV Frame Design",
        "Lesson 3.2 of the 3D Print Academy. Design a retro TV-style photo frame in TinkerCAD.\n\n#3DPrinting #3DPrintAcademy #RetroTV #TinkerCAD",
        "3-2",
    ),
    (
        os.path.expanduser("~/video-uploads/lesson-3-3-polaroid-frame.mp4"),
        "3D Print Academy: Lesson 3.3 — Polaroid-Style Frame",
        "Lesson 3.3 of the 3D Print Academy. Build a Polaroid-style photo frame in TinkerCAD — live screen recording with step-by-step narration.\n\n#3DPrinting #3DPrintAcademy #Polaroid #TinkerCAD",
        "3-3",
    ),
    (
        os.path.expanduser("~/video-uploads/lesson-3-4-instax-mini-frame.mp4"),
        "3D Print Academy: Lesson 3.4 — Instax Mini Frame",
        "Lesson 3.4 of the 3D Print Academy. Build an Instax Mini photo frame in TinkerCAD — compact design for instant film photos.\n\n#3DPrinting #3DPrintAcademy #InstaxMini #TinkerCAD",
        "3-4",
    ),
    (
        os.path.expanduser("~/Downloads/CAD-Design-Basics.mp4"),
        "3D Print Academy: Lesson 2.7 — Module 2 Recap",
        "Lesson 2.7 of the 3D Print Academy. Full recap of Module 2 — CAD Design Basics. Review TinkerCAD, Fusion 360, tolerances, and STL export.\n\n#3DPrinting #3DPrintAcademy #CAD",
        "2-7",
    ),
]


def load_results():
    if os.path.exists(RESULTS_FILE):
        with open(RESULTS_FILE) as f:
            return json.load(f)
    return {}


def save_results(results):
    with open(RESULTS_FILE, "w") as f:
        json.dump(results, f, indent=2)
    print(f"  Results saved to {RESULTS_FILE}")


def upload_one_video(page, filepath, title, description):
    """Upload a single video to YouTube Studio. Returns YouTube video ID."""
    print(f"\n{'='*60}")
    print(f"  Uploading: {os.path.basename(filepath)}")
    print(f"  Title: {title}")
    print(f"{'='*60}")

    # Navigate to YouTube Studio dashboard
    page.goto(f"{STUDIO_URL}", wait_until="load", timeout=60000)
    time.sleep(6)

    # Dismiss any leftover dialogs
    for _ in range(3):
        try:
            close_btns = page.locator("#close-button, [aria-label='Close']")
            if close_btns.first.is_visible(timeout=1000):
                close_btns.first.click(force=True)
                time.sleep(1)
        except:
            break

    # Click "Upload videos" button (direct on dashboard)
    upload_btn = page.locator("#upload-button")
    create_btn = page.locator("[aria-label='Create']")

    if upload_btn.is_visible(timeout=3000):
        upload_btn.click(force=True)
        time.sleep(4)
    elif create_btn.is_visible(timeout=3000):
        create_btn.click(force=True)
        time.sleep(2)
        page.locator("text=Upload videos").first.click(force=True)
        time.sleep(4)
    else:
        raise Exception("Could not find Upload or CREATE button")

    # Set file on the hidden file input
    file_input = page.locator("input[type='file']")
    file_input.set_input_files(filepath)
    print("  File queued for upload")

    # Wait for file upload to complete (30MB file = ~30-120s)
    # The scrim overlay blocks interactions until upload finishes
    print("  Waiting for upload to complete...")
    for attempt in range(90):  # up to ~7.5 minutes
        progress = page.evaluate(r"""() => {
            // Check progress spans
            const all = document.body?.innerText || '';
            const lines = all.split('\n');
            for (const line of lines) {
                const l = line.trim();
                if (l.includes('% of') || l.includes('Uploading') || l.includes('Processing will begin')) return l;
                if (l.includes('Processing') && l.includes('complete')) return 'DONE';
                if (l.includes('Checks complete')) return 'DONE';
            }
            // Check if title box is editable (scrim gone)
            const box = document.querySelector('#textbox[aria-label*="title"]');
            if (box) {
                const scrim = document.querySelector('.dialog-scrim');
                if (!scrim) return 'DONE';
                const style = getComputedStyle(scrim);
                if (style.display === 'none' || style.pointerEvents === 'none') return 'DONE';
            }
            return '';
        }""")
        if progress == 'DONE':
            print("  Upload complete!")
            break
        if progress:
            print(f"  {progress[:70]:70s}", end="\r")
        time.sleep(5)
    print()

    time.sleep(3)

    # --- ALL INTERACTIONS VIA JAVASCRIPT (bypasses any overlay) ---

    # Set title
    page.evaluate("""(title) => {
        const boxes = document.querySelectorAll('#textbox');
        const titleBox = boxes[0];
        if (titleBox) {
            titleBox.textContent = '';
            titleBox.focus();
            document.execCommand('selectAll', false, null);
            document.execCommand('insertText', false, title);
        }
    }""", title)
    time.sleep(1)
    print(f"  Title set via JS")

    # Set description
    page.evaluate("""(desc) => {
        const boxes = document.querySelectorAll('#textbox');
        if (boxes.length >= 2) {
            const descBox = boxes[1];
            descBox.focus();
            document.execCommand('insertText', false, desc);
        }
    }""", description)
    time.sleep(1)
    print("  Description set via JS")

    # Set "Not made for kids"
    page.evaluate("""() => {
        const r = document.querySelector("tp-yt-paper-radio-button[name='VIDEO_MADE_FOR_KIDS_NOT_MFK']");
        if (r) { r.scrollIntoView(); r.click(); }
    }""")
    time.sleep(1)
    print("  Set: Not made for kids")

    # Click NEXT through wizard (3 times: Details→Elements→Checks→Visibility)
    for step_name in ["Video elements", "Checks", "Visibility"]:
        time.sleep(2)
        page.evaluate("""() => {
            const btn = document.querySelector('#next-button');
            if (btn) btn.click();
        }""")
        print(f"  → {step_name}")
        time.sleep(2)

    # Set visibility to Unlisted
    time.sleep(2)
    page.evaluate("""() => {
        const r = document.querySelector("tp-yt-paper-radio-button[name='UNLISTED']");
        if (r) { r.scrollIntoView(); r.click(); }
    }""")
    time.sleep(2)
    print("  Set visibility: Unlisted")

    # Wait for any remaining processing
    for _ in range(30):
        done_enabled = page.evaluate("""() => {
            const btn = document.querySelector('#done-button');
            return btn && !btn.hasAttribute('disabled');
        }""")
        if done_enabled:
            break
        time.sleep(3)

    # Click SAVE
    page.evaluate("""() => {
        const btn = document.querySelector('#done-button');
        if (btn) btn.click();
    }""")
    print("  Clicked SAVE")
    time.sleep(10)

    # Extract video ID from confirmation dialog
    video_id = page.evaluate(r"""() => {
        // Look for youtu.be links
        const links = document.querySelectorAll('a[href*="youtu"]');
        for (const a of links) {
            const m = a.href.match(/youtu\.be\/([a-zA-Z0-9_-]{11})/);
            if (m) return m[1];
            const m2 = a.href.match(/watch\?v=([a-zA-Z0-9_-]{11})/);
            if (m2) return m2[1];
        }
        // Check page URL
        const m3 = location.href.match(/\/video\/([a-zA-Z0-9_-]{11})/);
        if (m3) return m3[1];
        // Search all text
        const text = document.body?.innerText || '';
        const m4 = text.match(/youtu\.be\/([a-zA-Z0-9_-]{11})/);
        if (m4) return m4[1];
        return null;
    }""") or "UNKNOWN"

    print(f"  ✅ Video ID: {video_id}")

    # Close dialog
    time.sleep(2)
    page.evaluate("""() => {
        const btn = document.querySelector('#close-button');
        if (btn) btn.click();
    }""")
    time.sleep(3)

    return video_id


def main():
    # Load any previously saved results to resume
    results = load_results()
    already_done = set(results.keys())

    # Filter uploads to only those not yet done
    pending = [(f, t, d, lid) for f, t, d, lid in UPLOADS if lid not in already_done]

    if not pending:
        print("All videos already uploaded! Results:")
        for lid, vid in sorted(results.items()):
            print(f"  {lid}: {vid}")
        return

    print(f"\n{'='*60}")
    print(f"  YouTube Batch Upload")
    print(f"  Total: {len(UPLOADS)} | Already done: {len(already_done)} | Pending: {len(pending)}")
    print(f"{'='*60}")

    # Verify all files exist
    for filepath, title, desc, lid in pending:
        if not os.path.exists(filepath):
            print(f"  ❌ File not found: {filepath}")
            sys.exit(1)

    # Launch browser
    pw, context = get_persistent_context(headless=False)
    page = context.pages[0] if context.pages else context.new_page()

    try:
        for i, (filepath, title, desc, lid) in enumerate(pending):
            print(f"\n[{i+1}/{len(pending)}] Uploading lesson {lid}...")
            try:
                video_id = upload_one_video(page, filepath, title, desc)
                results[lid] = video_id
                save_results(results)

                if video_id == "UNKNOWN":
                    print(f"  ⚠️  Could not extract video ID for {lid}")
                    # Take screenshot for debugging
                    page.screenshot(path=os.path.expanduser(f"~/video-uploads/debug-{lid}.png"))

                # Delay between uploads
                if i < len(pending) - 1:
                    print("  Waiting 10s before next upload...")
                    time.sleep(10)

            except Exception as e:
                print(f"  ❌ Error uploading {lid}: {e}")
                page.screenshot(path=os.path.expanduser(f"~/video-uploads/error-{lid}.png"))
                results[lid] = f"ERROR: {e}"
                save_results(results)
                continue

    finally:
        print(f"\n{'='*60}")
        print("  FINAL RESULTS:")
        for lid, vid in sorted(results.items()):
            print(f"  lesson-{lid}: '{vid}'")
        print(f"{'='*60}")
        save_results(results)
        context.close()
        pw.stop()


if __name__ == "__main__":
    main()
