#!/usr/bin/env python3
"""
Upload STL files to Google Drive using Playwright.
Uses persistent browser profile (same as TinkerCAD automation).

Usage:
    python3 upload_stl_drive.py                # Upload all STLs
    python3 upload_stl_drive.py --dry-run      # List files without uploading
    python3 upload_stl_drive.py --folder-only   # Just open the Drive folder
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
from tinkercad_helper import get_persistent_context

# ── Config ───────────────────────────────────────────────────────────────
STL_DIR = Path(__file__).parent.parent / "stl-files"
TMP_STL_DIR = Path("/tmp")
RESULTS_FILE = Path(__file__).parent / "drive_upload_results.json"

# Existing shared folder on Drive (from downloads.html)
DRIVE_FOLDER_ID = "1gVuFT9NDA5DNvZ_AfoTVxALHwpmrWrsr"
DRIVE_FOLDER_URL = f"https://drive.google.com/drive/folders/{DRIVE_FOLDER_ID}"

# ── Files to upload ──────────────────────────────────────────────────────
def get_upload_queue():
    """Build list of (filepath, display_name, category) tuples."""
    files = []

    # Individual STLs from general-frames/
    general_dir = STL_DIR / "general-frames"
    if general_dir.exists():
        for stl in sorted(general_dir.glob("*.stl")):
            files.append((str(stl), stl.name, "general-frames"))

    # Individual STLs from baby-milestones/
    baby_dir = STL_DIR / "baby-milestones"
    if baby_dir.exists():
        for stl in sorted(baby_dir.glob("*.stl")):
            files.append((str(stl), stl.name, "baby-milestones"))

    # ZIP bundles
    for zf in sorted(STL_DIR.glob("*.zip")):
        files.append((str(zf), zf.name, "zip-bundles"))

    # TinkerCAD lesson STLs from /tmp/
    for stl in sorted(TMP_STL_DIR.glob("lesson_*_frame.stl")):
        # Rename for upload: lesson_2-2_frame.stl → lesson-2-2-frame.stl
        display = stl.name.replace("_", "-")
        files.append((str(stl), display, "lesson-exports"))

    return files


def load_results():
    """Load previously uploaded file IDs."""
    if RESULTS_FILE.exists():
        return json.loads(RESULTS_FILE.read_text())
    return {}


def save_results(results):
    """Save upload results."""
    RESULTS_FILE.write_text(json.dumps(results, indent=2))


def upload_file(page, filepath, display_name):
    """Upload a single file to the current Drive folder. Returns True on success."""
    filepath = os.path.expanduser(filepath)
    if not os.path.exists(filepath):
        print(f"    SKIP: {filepath} not found")
        return False

    size_kb = os.path.getsize(filepath) / 1024
    print(f"  Uploading: {display_name} ({size_kb:.0f} KB)")

    try:
        # Use expect_file_chooser to intercept the native file dialog
        with page.expect_file_chooser(timeout=10000) as fc_info:
            # Click "New" button at known coordinates
            page.mouse.click(66, 99)
            time.sleep(2)
            # Click "File upload" menu item at known visible position (center of 16,125 320x32)
            page.mouse.click(176, 141)

        file_chooser = fc_info.value
        file_chooser.set_files(filepath)
        print("    File selected via file chooser")
    except Exception as e:
        print(f"    ERROR: File chooser failed: {e}")
        page.keyboard.press("Escape")
        time.sleep(1)
        return False

    # Wait for upload to complete
    print("    Waiting for upload to complete...")
    for i in range(60):
        complete = page.evaluate("""() => {
            const texts = document.body.innerText;
            if (texts.includes('Upload complete') || texts.includes('1 upload complete'))
                return 'complete';
            if (texts.includes('Uploading') || texts.includes('upload'))
                return 'uploading';
            return 'unknown';
        }""")
        if complete == "complete":
            print("    ✅ Upload complete!")
            break
        if i > 0 and i % 10 == 0:
            print(f"    ... still uploading ({i*2}s)")
        time.sleep(2)
    else:
        print("    ⚠ Upload may not have completed (timeout)")

    # Close the upload notification if present
    try:
        page.locator("[aria-label='Close']").last.click(timeout=2000)
    except Exception:
        pass
    time.sleep(1)

    return True


def main():
    parser = argparse.ArgumentParser(description="Upload STL files to Google Drive")
    parser.add_argument("--dry-run", action="store_true", help="List files without uploading")
    parser.add_argument("--folder-only", action="store_true", help="Just open Drive folder")
    args = parser.parse_args()

    files = get_upload_queue()
    results = load_results()

    if args.dry_run:
        print(f"\n=== STL Upload Queue ({len(files)} files) ===\n")
        for filepath, name, category in files:
            size_kb = os.path.getsize(filepath) / 1024 if os.path.exists(filepath) else 0
            status = "✅ uploaded" if name in results else "⬜ pending"
            print(f"  [{category:15s}] {name:45s} {size_kb:7.0f} KB  {status}")
        print(f"\n  Total: {len(files)} files, {sum(os.path.getsize(f) for f, _, _ in files if os.path.exists(f)) / 1024 / 1024:.1f} MB")
        already = sum(1 for _, n, _ in files if n in results)
        print(f"  Already uploaded: {already}, Remaining: {len(files) - already}")
        return

    # Launch browser
    print("\n=== Google Drive STL Upload ===")
    print(f"  Folder: {DRIVE_FOLDER_URL}")
    p, ctx = get_persistent_context(headless=False)
    page = ctx.pages[0] if ctx.pages else ctx.new_page()

    # Navigate to the shared folder
    page.goto(DRIVE_FOLDER_URL, wait_until="load", timeout=30000)
    time.sleep(5)

    if args.folder_only:
        print("  Folder opened. Press Enter to close browser...")
        input()
        ctx.close()
        p.stop()
        return

    # Upload each file
    uploaded = 0
    skipped = 0
    for filepath, name, category in files:
        if name in results:
            print(f"  SKIP (already uploaded): {name}")
            skipped += 1
            continue

        result = upload_file(page, filepath, name)
        if result:
            results[name] = {
                "status": "uploaded",
                "category": category,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            }
            save_results(results)
            uploaded += 1
        time.sleep(2)

    print(f"\n=== Done: {uploaded} uploaded, {skipped} skipped ===")
    ctx.close()
    p.stop()


if __name__ == "__main__":
    main()
