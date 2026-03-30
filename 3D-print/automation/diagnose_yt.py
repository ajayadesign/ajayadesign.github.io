#!/usr/bin/env python3
"""Diagnostic: Open YT Studio upload, set file, walk through wizard, dump DOM at each step."""
import time, sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
from tinkercad_helper import get_persistent_context

CHANNEL_ID = "UCUDAzAh-qpKR4z1b9KaHNsg"
STUDIO_URL = f"https://studio.youtube.com/channel/{CHANNEL_ID}"
TEST_FILE = os.path.expanduser("~/video-uploads/lesson-3-4-instax-mini-frame.mp4")
SS = "/tmp/yt_upload"
os.makedirs(SS, exist_ok=True)

pw, ctx = get_persistent_context(headless=False)
page = ctx.pages[0] if ctx.pages else ctx.new_page()

try:
    # Navigate
    page.goto(STUDIO_URL, wait_until="load", timeout=60000)
    time.sleep(6)
    
    # Close leftover
    try:
        page.locator("#close-button").first.click(force=True, timeout=2000)
        time.sleep(1)
    except:
        pass
    
    # Create → Upload
    try:
        page.locator("[aria-label='Create']").click(force=True, timeout=3000)
        time.sleep(2)
        page.locator("tp-yt-paper-item:has-text('Upload videos'), #text-item-0").first.click(force=True, timeout=3000)
        time.sleep(3)
    except:
        page.locator("#upload-button").click(force=True, timeout=5000)
        time.sleep(3)
    
    # Set file
    page.locator("input[type='file']").set_input_files(TEST_FILE)
    time.sleep(5)
    
    # Wait for title box
    for _ in range(30):
        if page.evaluate("!!document.querySelector('#textbox')"):
            break
        time.sleep(2)
    time.sleep(2)
    
    # ── DUMP DETAILS PAGE ──
    print("\n=== DETAILS PAGE ===")
    details = page.evaluate("""() => {
        const result = {};
        // All radio buttons
        const radios = document.querySelectorAll('tp-yt-paper-radio-button');
        result.radioButtons = Array.from(radios).map((r, i) => ({
            index: i,
            name: r.getAttribute('name'),
            checked: r.getAttribute('aria-checked'),
            hasCheckedAttr: r.hasAttribute('checked'),
            text: r.textContent?.trim()?.substring(0, 80),
            tagName: r.tagName,
        }));
        
        // All radio groups
        const groups = document.querySelectorAll('tp-yt-paper-radio-group');
        result.radioGroups = Array.from(groups).map((g, i) => ({
            index: i,
            selected: g.getAttribute('selected'),
            ariaLabel: g.getAttribute('aria-label'),
        }));
        
        return result;
    }""")
    print(json.dumps(details, indent=2))
    page.screenshot(path=f"{SS}/diag_details.png")
    
    # Try to click MFK using the radio GROUP's selected attribute
    print("\n=== TRYING MFK CLICK METHODS ===")
    
    # Method 1: Click inner #radioContainer
    result1 = page.evaluate("""() => {
        const r = document.querySelector("tp-yt-paper-radio-button[name='VIDEO_MADE_FOR_KIDS_NOT_MFK']");
        if (!r) return 'NOT FOUND';
        const inner = r.querySelector('#radioContainer') || r.querySelector('#offRadio') || r;
        inner.click();
        return {method: 'innerClick', ariaChecked: r.getAttribute('aria-checked')};
    }""")
    print(f"Method 1 (inner click): {result1}")
    time.sleep(1)
    
    # Method 2: Use Polymer's fire method
    result2 = page.evaluate("""() => {
        const r = document.querySelector("tp-yt-paper-radio-button[name='VIDEO_MADE_FOR_KIDS_NOT_MFK']");
        if (!r) return 'NOT FOUND';
        if (typeof r.fire === 'function') {
            r.fire('click');
            return {method: 'fire', ariaChecked: r.getAttribute('aria-checked')};
        }
        return 'no fire method';
    }""")
    print(f"Method 2 (Polymer fire): {result2}")
    time.sleep(1)
    
    # Method 3: Dispatch proper events
    result3 = page.evaluate("""() => {
        const r = document.querySelector("tp-yt-paper-radio-button[name='VIDEO_MADE_FOR_KIDS_NOT_MFK']");
        if (!r) return 'NOT FOUND';
        r.dispatchEvent(new MouseEvent('mousedown', {bubbles: true, cancelable: true}));
        r.dispatchEvent(new MouseEvent('mouseup', {bubbles: true, cancelable: true}));
        r.dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true}));
        return {method: 'dispatchEvent', ariaChecked: r.getAttribute('aria-checked')};
    }""")
    print(f"Method 3 (dispatchEvent): {result3}")
    time.sleep(1)
    
    # Method 4: Set selected on the radio group
    result4 = page.evaluate("""() => {
        const groups = document.querySelectorAll('tp-yt-paper-radio-group');
        const results = [];
        for (const g of groups) {
            const mfk = g.querySelector("[name='VIDEO_MADE_FOR_KIDS_NOT_MFK']");
            if (mfk) {
                g.setAttribute('selected', 'VIDEO_MADE_FOR_KIDS_NOT_MFK');
                g.selected = 'VIDEO_MADE_FOR_KIDS_NOT_MFK';
                // Try both
                const r = g.querySelector("[name='VIDEO_MADE_FOR_KIDS_NOT_MFK']");
                results.push({
                    method: 'group.selected', 
                    groupSelected: g.selected,
                    ariaChecked: r?.getAttribute('aria-checked')
                });
            }
        }
        return results;
    }""")
    print(f"Method 4 (radio group selected): {result4}")
    time.sleep(2)
    
    # Final state check
    final_mfk = page.evaluate("""() => {
        const r = document.querySelector("tp-yt-paper-radio-button[name='VIDEO_MADE_FOR_KIDS_NOT_MFK']");
        if (!r) return 'NOT FOUND';
        return {
            ariaChecked: r.getAttribute('aria-checked'),
            checked: r.hasAttribute('checked'),
            active: r.hasAttribute('active'),
            className: r.className,
        };
    }""")
    print(f"\nFinal MFK state: {final_mfk}")
    
    # Now click Next x3 to get to Visibility
    print("\n=== NAVIGATING TO VISIBILITY PAGE ===")
    for step in range(3):
        try:
            page.locator("#next-button").click(force=True, timeout=5000)
        except:
            page.evaluate("document.querySelector('#next-button')?.click()")
        time.sleep(3)
        print(f"  Next click {step+1}")
    
    time.sleep(3)
    page.screenshot(path=f"{SS}/diag_visibility.png")
    
    # ── DUMP VISIBILITY PAGE ──
    print("\n=== VISIBILITY PAGE ===")
    vis = page.evaluate("""() => {
        const result = {};
        // All radio buttons on visibility page
        const radios = document.querySelectorAll('tp-yt-paper-radio-button');
        result.radioButtons = Array.from(radios).map((r, i) => ({
            index: i,
            name: r.getAttribute('name'),
            ariaChecked: r.getAttribute('aria-checked'),
            text: r.textContent?.trim()?.substring(0, 80),
            visible: r.offsetParent !== null,
        }));
        
        // All radio groups
        const groups = document.querySelectorAll('tp-yt-paper-radio-group');
        result.radioGroups = Array.from(groups).map((g, i) => ({
            index: i,
            selected: g.getAttribute('selected'),
        }));
        
        // Any elements with "Unlisted" text
        const allElements = document.querySelectorAll('*');
        result.unlistedElements = [];
        for (const el of allElements) {
            if (el.children.length === 0 && el.textContent?.includes('Unlisted')) {
                result.unlistedElements.push({
                    tag: el.tagName,
                    text: el.textContent.trim().substring(0, 50),
                    parentTag: el.parentElement?.tagName,
                    parentName: el.parentElement?.getAttribute('name'),
                });
            }
        }
        
        // Done button state
        const done = document.querySelector('#done-button');
        result.doneButton = {
            exists: !!done,
            disabled: done?.hasAttribute('disabled'),
            text: done?.textContent?.trim(),
        };
        
        return result;
    }""")
    print(json.dumps(vis, indent=2))

finally:
    ctx.close()
    pw.stop()
    print("\nDone.")
