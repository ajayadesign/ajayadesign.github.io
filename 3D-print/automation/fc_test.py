#!/usr/bin/env python3
"""Test: Use expect_file_chooser + SELECT FILES button instead of set_input_files."""
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

# Capture console errors
console_msgs = []
page.on("console", lambda msg: console_msgs.append(f"[{msg.type}] {msg.text[:100]}") if msg.type in ('error', 'warning') else None)

try:
    page.goto(STUDIO_URL, wait_until="load", timeout=60000)
    time.sleep(6)
    
    # Close leftover
    try:
        page.locator("#close-button").first.click(force=True, timeout=2000)
        time.sleep(1)
    except:
        pass
    
    # Open upload dialog
    page.locator("[aria-label='Create']").click(force=True, timeout=5000)
    time.sleep(2)
    page.locator("tp-yt-paper-item:has-text('Upload videos'), #text-item-0").first.click(force=True, timeout=3000)
    time.sleep(3)
    
    # Use expect_file_chooser with SELECT FILES button
    print("=== USING FILE CHOOSER API ===")
    with page.expect_file_chooser() as fc_info:
        page.locator("#select-files-button").click(force=True, timeout=5000)
    
    file_chooser = fc_info.value
    file_chooser.set_files(TEST_FILE)
    print(f"  File set via file chooser: {os.path.basename(TEST_FILE)}")
    
    # Monitor upload progress
    print("\n=== MONITORING UPLOAD PROGRESS ===")
    for i in range(60):  # 5 minutes max
        state = page.evaluate("""() => {
            const dialog = document.querySelector('ytcp-uploads-dialog');
            const prog = dialog?.querySelector('tp-yt-paper-progress');
            const label = dialog?.querySelector('.progress-label');
            const next = document.querySelector('#next-button');
            const done = document.querySelector('#done-button');
            
            return {
                progress: prog?.getAttribute('value'),
                progressStyle: prog?.getAttribute('style')?.substring(0, 100),
                label: label?.textContent?.trim() || '',
                nextHidden: next?.hasAttribute('hidden'),
                nextDisabled: next?.hasAttribute('disabled'),
                doneHidden: done?.hasAttribute('hidden'),
                doneDisabled: done?.hasAttribute('disabled'),
            };
        }""")
        
        nhid = state.get('nextHidden', True)
        dhid = state.get('doneHidden', True)
        prog = state.get('progress', '?')
        label = state.get('label', '')
        
        print(f"  [{i*5:3d}s] prog={prog} label='{label}' next_hidden={nhid} done_hidden={dhid}")
        
        # If Next becomes visible, we can proceed
        if not nhid:
            print("  ✅ Next button is visible!")
            break
        if not dhid:
            print("  ✅ Done button is visible!")
            break
            
        time.sleep(5)
    
    page.screenshot(path=f"{SS}/fc_after_wait.png")
    
    # Check if buttons are visible now
    state_final = page.evaluate("""() => {
        const next = document.querySelector('#next-button');
        const done = document.querySelector('#done-button');
        return {
            nextHidden: next?.hasAttribute('hidden'),
            nextVisible: next?.offsetParent !== null,
            doneHidden: done?.hasAttribute('hidden'),
            doneVisible: done?.offsetParent !== null,
        };
    }""")
    print(f"\n  Final button state: {state_final}")
    
    # Console errors
    if console_msgs:
        print(f"\n=== CONSOLE ERRORS ({len(console_msgs)}) ===")
        for msg in console_msgs[:10]:
            print(f"  {msg}")

finally:
    ctx.close()
    pw.stop()
    print("\nDone.")
