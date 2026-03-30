#!/usr/bin/env python3
"""Quick diagnostic: explore YouTube Studio upload page DOM."""
import time, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from tinkercad_helper import get_persistent_context

CHANNEL_ID = "UCUDAzAh-qpKR4z1b9KaHNsg"

pw, context = get_persistent_context(headless=False)
page = context.pages[0] if context.pages else context.new_page()

# Go to YouTube Studio videos page
print("Navigating to YouTube Studio...")
page.goto(f"https://studio.youtube.com/channel/{CHANNEL_ID}/videos", wait_until="networkidle")
time.sleep(5)
page.screenshot(path=os.path.expanduser("~/video-uploads/diag-1-videos-page.png"))
print("Screenshot 1: videos page")

# Try the direct upload URL
print("Navigating to upload URL...")
page.goto(f"https://studio.youtube.com/channel/{CHANNEL_ID}/videos/upload", wait_until="networkidle")
time.sleep(5)
page.screenshot(path=os.path.expanduser("~/video-uploads/diag-2-upload-url.png"))
print("Screenshot 2: upload URL")

# Check for upload dialog / file inputs
result = page.evaluate("""() => {
    const info = {};
    // Find all file inputs
    const fileInputs = document.querySelectorAll('input[type="file"]');
    info.fileInputs = Array.from(fileInputs).map(el => ({
        id: el.id,
        name: el.name,
        accept: el.accept,
        visible: el.offsetWidth > 0 || el.offsetHeight > 0,
        parentTag: el.parentElement?.tagName,
        parentId: el.parentElement?.id
    }));
    
    // Find buttons with "create" or "upload" or "select"
    const buttons = document.querySelectorAll('button, ytcp-button, [role="button"]');
    info.relevantButtons = Array.from(buttons)
        .filter(b => {
            const text = (b.textContent || '').toLowerCase();
            return text.includes('create') || text.includes('upload') || text.includes('select') || text.includes('file');
        })
        .map(b => ({
            tag: b.tagName,
            id: b.id,
            text: (b.textContent || '').trim().substring(0, 80),
            visible: b.offsetWidth > 0 || b.offsetHeight > 0
        }));
    
    // Find the CREATE button specifically
    const createIcon = document.querySelector('#create-icon');
    info.createIcon = createIcon ? {
        tag: createIcon.tagName,
        visible: createIcon.offsetWidth > 0 || createIcon.offsetHeight > 0,
        parentTag: createIcon.parentElement?.tagName,
        parentId: createIcon.parentElement?.id
    } : null;
    
    // Find any SELECT FILES button
    const selectFiles = document.querySelector('#select-files-button');
    info.selectFilesBtn = selectFiles ? {
        tag: selectFiles.tagName,
        visible: selectFiles.offsetWidth > 0 || selectFiles.offsetHeight > 0,
        text: (selectFiles.textContent || '').trim()
    } : null;
    
    // Check for upload dialog
    const dialogs = document.querySelectorAll('ytcp-uploads-dialog, [role="dialog"]');
    info.dialogs = Array.from(dialogs).map(d => ({
        tag: d.tagName,
        id: d.id,
        visible: d.offsetWidth > 0 || d.offsetHeight > 0
    }));
    
    return info;
}""")

import json
print("\\nDOM Analysis:")
print(json.dumps(result, indent=2))

# Try clicking CREATE button
print("\\nTrying to click CREATE button...")
create_btn = page.locator("#create-icon")
if create_btn.is_visible(timeout=3000):
    create_btn.click()
    time.sleep(3)
    page.screenshot(path=os.path.expanduser("~/video-uploads/diag-3-after-create.png"))
    print("Screenshot 3: after clicking CREATE")
    
    # Look for upload option in menu
    menu_items = page.evaluate("""() => {
        const items = document.querySelectorAll('tp-yt-paper-item, [role="menuitem"], ytcp-text-menu a');
        return Array.from(items).map(i => ({
            tag: i.tagName,
            text: (i.textContent || '').trim().substring(0, 80),
            visible: i.offsetWidth > 0 || i.offsetHeight > 0
        }));
    }""")
    print("Menu items:", json.dumps(menu_items, indent=2))
    
    # Click "Upload videos" if found
    upload_item = page.locator("text=Upload videos").first
    if upload_item.is_visible(timeout=3000):
        upload_item.click()
        time.sleep(4)
        page.screenshot(path=os.path.expanduser("~/video-uploads/diag-4-upload-dialog.png"))
        print("Screenshot 4: upload dialog")
        
        # Now check for file input again
        result2 = page.evaluate("""() => {
            const fileInputs = document.querySelectorAll('input[type="file"]');
            return Array.from(fileInputs).map(el => ({
                id: el.id,
                name: el.name,
                accept: el.accept,
                visible: el.offsetWidth > 0 || el.offsetHeight > 0,
                parentId: el.parentElement?.id
            }));
        }""")
        print("File inputs after dialog:", json.dumps(result2, indent=2))
        
        # Check for select files button
        sfb = page.locator("#select-files-button")
        if sfb.is_visible(timeout=3000):
            print("SELECT FILES button found and visible!")
        else:
            print("SELECT FILES still not visible")

context.close()
pw.stop()
print("\\nDone. Check ~/video-uploads/diag-*.png for screenshots.")
