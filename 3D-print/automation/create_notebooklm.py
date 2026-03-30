#!/usr/bin/env python3
"""
Automate NotebookLM notebook creation for remaining lessons.
Opens NotebookLM, creates a notebook, pastes lesson content, and queues Video Overview.

Uses persistent Chromium profile with Google account already logged in.
"""
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

CONTENT_DIR = Path("/home/aj/website/ajayadesign.github.io/3D-print/content/lessons")
PROFILE_DIR = Path.home() / ".tinkercad-playwright-profile" / "chromium-profile"

# Lessons that still need NotebookLM videos
LESSONS_NEEDED = [
    ("2-7", "lesson-2-7-module2-recap.txt", "Module 2 Recap: CAD Design"),
    ("3-1", "lesson-3-1-multi-piece-assemblies.txt", "Multi-Piece Frame Assemblies"),
    ("3-7", "lesson-3-7-quality-showcase.txt", "Quality Showcase & Portfolio"),
    ("4-1", "lesson-4-1-layer-height.txt", "Layer Height Optimization"),
    ("4-3", "lesson-4-3-speed-quality.txt", "Speed vs Quality Balance"),
    ("4-4", "lesson-4-4-temperature-tower.txt", "Temperature Tower Calibration"),
    ("4-5", "lesson-4-5-fix-stringing.txt", "Fix Stringing & Oozing"),
    ("4-6", "lesson-4-6-fix-warping.txt", "Fix Warping & Adhesion"),
    ("4-7", "lesson-4-7-fix-elephants-foot.txt", "Fix Elephant's Foot"),
    ("4-8", "lesson-4-8-batch-printing.txt", "Batch Printing Efficiency"),
    ("5-1", "lesson-5-1-sanding-technique.txt", "Sanding & Smoothing"),
    ("5-2", "lesson-5-2-filler-primer.txt", "Filler Primer Application"),
    ("5-3", "lesson-5-3-spray-painting.txt", "Spray Painting Technique"),
    ("5-4", "lesson-5-4-clear-coating.txt", "Clear Coat Protection"),
    ("5-5", "lesson-5-5-magnet-install-pause.txt", "Magnet Install (Pause Method)"),
    ("5-6", "lesson-5-6-magnet-install-glue.txt", "Magnet Install (Glue Method)"),
    ("6-2", "lesson-6-2-pricing-strategy.txt", "Pricing Strategy"),
    ("6-5", "lesson-6-5-product-photography.txt", "Product Photography"),
    ("6-6", "lesson-6-6-packaging-shipping.txt", "Packaging & Shipping"),
]

# NotebookLM accounts: alternate between them
ACCOUNTS = [
    "https://notebooklm.google.com/",                    # ajayadahal1000 (primary)
    "https://notebooklm.google.com/?authuser=1",         # ajayadesign (secondary)
]


def create_notebook(page, lesson_id, content_file, title, account_idx=0):
    """Create a single NotebookLM notebook with lesson content."""
    content_path = CONTENT_DIR / content_file
    content = content_path.read_text()
    
    print(f"\n--- Creating notebook for {lesson_id}: {title} ---")
    
    # Go to NotebookLM
    url = ACCOUNTS[account_idx % 2]
    page.goto(url, wait_until="networkidle", timeout=30000)
    time.sleep(3)
    
    # Click "New notebook" or "+" button
    try:
        new_btn = page.locator("text=New notebook").first
        if new_btn.is_visible(timeout=5000):
            new_btn.click()
            time.sleep(2)
        else:
            # Try the + button
            page.locator("[aria-label='Create new notebook']").first.click()
            time.sleep(2)
    except Exception as e:
        print(f"  Could not find new notebook button: {e}")
        return False
    
    # Look for "Paste text" or "Add source" option
    try:
        paste_btn = page.locator("text=Paste text").first
        if paste_btn.is_visible(timeout=5000):
            paste_btn.click()
            time.sleep(2)
    except:
        # Try "Copied text" or similar
        try:
            page.locator("text=Copied text").first.click()
            time.sleep(2)
        except:
            print("  Could not find paste text option")
            return False
    
    # Paste the content into the text area
    try:
        textarea = page.locator("textarea").first
        if textarea.is_visible(timeout=5000):
            textarea.fill(f"3D Print Academy - Lesson {lesson_id}: {title}\n\n{content}")
            time.sleep(1)
            
            # Click Insert/Add/Submit button
            try:
                page.locator("button:has-text('Insert')").first.click(timeout=5000)
            except:
                try:
                    page.locator("button:has-text('Add')").first.click(timeout=5000)
                except:
                    page.keyboard.press("Enter")
            time.sleep(3)
    except:
        print("  Could not fill textarea")
        return False
    
    # Rename the notebook
    try:
        title_el = page.locator("[contenteditable='true']").first
        if title_el.is_visible(timeout=3000):
            title_el.click()
            page.keyboard.press("Control+a")
            page.keyboard.type(f"3D Print Academy {lesson_id}: {title}", delay=30)
            page.keyboard.press("Tab")
            time.sleep(1)
    except:
        pass
    
    # Try to click "Generate" → "Audio Overview" / "Video Overview"
    try:
        page.locator("text=Generate").first.click(timeout=5000)
        time.sleep(1)
        
        video_btn = page.locator("text=Video Overview").first
        if video_btn.is_visible(timeout=3000):
            video_btn.click()
            time.sleep(2)
            print(f"  ✅ Notebook created and Video Overview queued for {lesson_id}")
            return True
    except:
        print(f"  ⚠️ Notebook created but couldn't auto-queue video for {lesson_id}")
    
    return True


def main():
    # Parse args
    start_idx = 0
    account_idx = 0
    if len(sys.argv) > 1:
        start_idx = int(sys.argv[1])
    if len(sys.argv) > 2:
        account_idx = int(sys.argv[2])
    
    print(f"=== NotebookLM Batch Creator ===")
    print(f"  Starting from lesson index: {start_idx}")
    print(f"  Account: {'primary' if account_idx == 0 else 'secondary'}")
    print(f"  Total lessons needed: {len(LESSONS_NEEDED)}")
    
    p = sync_playwright().start()
    browser = p.chromium.launch_persistent_context(
        str(PROFILE_DIR),
        headless=False,
        viewport={"width": 1920, "height": 1080},
        args=[
            "--no-sandbox",
            "--disable-blink-features=AutomationControlled",
        ],
    )
    page = browser.pages[0] if browser.pages else browser.new_page()
    
    created = 0
    for i, (lesson_id, content_file, title) in enumerate(LESSONS_NEEDED[start_idx:], start=start_idx):
        try:
            result = create_notebook(page, lesson_id, content_file, title, account_idx)
            if result:
                created += 1
            time.sleep(2)
        except Exception as e:
            print(f"  ERROR creating {lesson_id}: {e}")
            continue
        
        # Check if we've hit a limit
        if created >= 10:
            print(f"\n⚠️ Created {created} notebooks. Pausing to avoid rate limits.")
            print(f"  Resume with: python {sys.argv[0]} {i+1} {(account_idx + 1) % 2}")
            break
    
    print(f"\n=== Done. Created {created} notebooks ===")
    browser.close()
    p.stop()


if __name__ == "__main__":
    main()
