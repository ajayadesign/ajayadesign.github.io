#!/usr/bin/env python3
"""Diagnostic: Dump YouTube Studio page structure for upload automation."""
import time, sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
from tinkercad_helper import get_persistent_context

CHANNEL_ID = "UCUDAzAh-qpKR4z1b9KaHNsg"

pw, context = get_persistent_context(headless=False)
page = context.pages[0] if context.pages else context.new_page()

try:
    # Navigate to YouTube Studio
    print("Navigating to studio.youtube.com ...")
    page.goto("https://studio.youtube.com", wait_until="networkidle")
    time.sleep(6)
    print(f"Current URL: {page.url}")
    page.screenshot(path=os.path.expanduser("~/video-uploads/diag-a-studio-home.png"))

    # Dump key elements
    info = page.evaluate("""() => {
        const result = {};
        
        // All buttons
        const allButtons = document.querySelectorAll('button, [role="button"], ytcp-button, tp-yt-paper-icon-button');
        result.allButtons = Array.from(allButtons).slice(0, 30).map(b => ({
            tag: b.tagName,
            id: b.id || '',
            cls: (b.className || '').toString().substring(0, 80),
            text: (b.textContent || '').trim().substring(0, 60),
            visible: b.offsetWidth > 0 || b.offsetHeight > 0,
            ariaLabel: b.getAttribute('aria-label') || ''
        }));
        
        // All icons 
        const icons = document.querySelectorAll('iron-icon, yt-icon, [icon]');
        result.icons = Array.from(icons).slice(0, 20).map(i => ({
            tag: i.tagName,
            id: i.id || '',
            icon: i.getAttribute('icon') || '',
            visible: i.offsetWidth > 0 || i.offsetHeight > 0
        }));
        
        // Any elements with id containing 'create' or 'upload'
        const all = document.querySelectorAll('*');
        result.createUploadElements = [];
        for (const el of all) {
            const id = (el.id || '').toLowerCase();
            const cls = (el.className || '').toString().toLowerCase();
            if (id.includes('create') || id.includes('upload') || cls.includes('create') || cls.includes('upload')) {
                result.createUploadElements.push({
                    tag: el.tagName,
                    id: el.id || '',
                    cls: (el.className || '').toString().substring(0, 80),
                    text: (el.textContent || '').trim().substring(0, 60),
                    visible: el.offsetWidth > 0 || el.offsetHeight > 0
                });
            }
        }
        
        // File inputs
        const fileInputs = document.querySelectorAll('input[type="file"]');
        result.fileInputs = Array.from(fileInputs).map(el => ({
            id: el.id || '',
            name: el.name || '',
            accept: el.accept || '',
            visible: el.offsetWidth > 0 || el.offsetHeight > 0
        }));
        
        // Page title
        result.title = document.title;
        
        return result;
    }""")
    
    print(f"\nPage title: {info.get('title', 'N/A')}")
    print(f"\n--- Buttons ({len(info['allButtons'])}) ---")
    for b in info['allButtons']:
        if b['visible']:
            print(f"  [{b['tag']}] id={b['id']!r} text={b['text']!r} aria={b['ariaLabel']!r}")
    
    print(f"\n--- Create/Upload elements ({len(info['createUploadElements'])}) ---")
    for e in info['createUploadElements']:
        print(f"  [{e['tag']}] id={e['id']!r} cls={e['cls']!r} visible={e['visible']} text={e['text']!r}")
    
    print(f"\n--- File inputs ({len(info['fileInputs'])}) ---")
    for f in info['fileInputs']:
        print(f"  id={f['id']!r} name={f['name']!r} accept={f['accept']!r} visible={f['visible']}")
    
    # Try clicking the CREATE button with various selectors
    print("\n--- Trying CREATE button selectors ---")
    selectors = [
        "#create-icon",
        "ytcp-button#create-button", 
        "[aria-label='Create']",
        "[aria-label='Upload videos']",
        "button:has-text('Create')",
        "#upload-icon",
        "ytcp-icon-button#create-icon",
    ]
    
    for sel in selectors:
        try:
            el = page.locator(sel)
            count = el.count()
            visible = el.first.is_visible(timeout=1000) if count > 0 else False
            print(f"  {sel}: count={count}, visible={visible}")
            if visible:
                print(f"    → CLICKING!")
                el.first.click()
                time.sleep(3)
                page.screenshot(path=os.path.expanduser("~/video-uploads/diag-b-after-create-click.png"))
                
                # Now check for upload dialog
                info2 = page.evaluate("""() => {
                    const fileInputs = document.querySelectorAll('input[type="file"]');
                    const selectBtn = document.querySelector('#select-files-button');
                    const dialogs = document.querySelectorAll('[role="dialog"]');
                    return {
                        fileInputs: Array.from(fileInputs).length,
                        selectBtn: selectBtn ? {visible: selectBtn.offsetWidth > 0} : null,
                        dialogCount: dialogs.length,
                        dialogVisible: Array.from(dialogs).filter(d => d.offsetWidth > 0).length
                    };
                }""")
                print(f"    After click: {json.dumps(info2)}")
                
                # Look for upload menu items
                items = page.evaluate("""() => {
                    const items = document.querySelectorAll('tp-yt-paper-item, [role="menuitem"], ytcp-text-menu-item');
                    return Array.from(items).map(i => ({
                        text: (i.textContent || '').trim().substring(0, 60),
                        visible: i.offsetWidth > 0
                    })).filter(i => i.visible);
                }""")
                print(f"    Visible menu items: {json.dumps(items)}")
                break
        except Exception as e:
            print(f"  {sel}: error - {e}")

finally:
    context.close()
    pw.stop()
    print("\nDone.")
