#!/usr/bin/env python3
"""Audit YouTube Studio: list ALL uploaded videos with titles, IDs, status."""
import time, json
from tinkercad_helper import get_persistent_context

p, ctx = get_persistent_context(headless=False)
page = ctx.pages[0] if ctx.pages else ctx.new_page()

# Navigate to YouTube Studio content page
print("=== Navigating to YouTube Studio ===")
page.goto("https://studio.youtube.com/channel/UCUDAzAh-qpKR4z1b9KaHNsg/videos/upload", 
          wait_until="networkidle", timeout=30000)
time.sleep(5)
page.screenshot(path="/tmp/yt_studio_audit.png")

# Check if we need to select account
url = page.url
print(f"  URL: {url}")

# Wait for content to load
try:
    page.wait_for_selector("ytcp-video-row, #video-list, [id*='video']", timeout=15000)
except:
    print("  Waiting more...")
    time.sleep(5)

# Try to extract video list
videos = page.evaluate("""() => {
    const results = [];
    
    // Method 1: ytcp-video-row elements
    const rows = document.querySelectorAll('ytcp-video-row');
    for (const row of rows) {
        const title = row.querySelector('#video-title')?.textContent?.trim() || 
                      row.querySelector('.video-title')?.textContent?.trim() || '';
        const visibility = row.querySelector('#visibility-icon')?.getAttribute('tooltip') || 
                          row.querySelector('.visibility-cell')?.textContent?.trim() || '';
        const date = row.querySelector('#date-text .date-text')?.textContent?.trim() ||
                    row.querySelector('.date-text')?.textContent?.trim() || '';
        // Try to find video ID from the link
        const link = row.querySelector('a[href*="/video/"]');
        let videoId = '';
        if (link) {
            const match = link.href.match(/\/video\/([^/]+)/);
            if (match) videoId = match[1];
        }
        if (title) results.push({title, visibility, date, videoId});
    }
    
    // Method 2: Try table rows  
    if (results.length === 0) {
        const trs = document.querySelectorAll('table tr, [class*="video-row"]');
        for (const tr of trs) {
            const text = tr.textContent.trim().substring(0, 200);
            if (text.length > 10) results.push({raw: text});
        }
    }
    
    // Method 3: Check page content
    if (results.length === 0) {
        results.push({debug: document.body.innerText.substring(0, 2000)});
    }
    
    return results;
}""")

print(f"\n=== Videos found: {len(videos)} ===")
for i, v in enumerate(videos):
    if 'title' in v:
        print(f"  {i+1}. [{v.get('videoId', '???')}] {v['title']} | {v['visibility']} | {v['date']}")
    elif 'raw' in v:
        print(f"  {i+1}. RAW: {v['raw'][:100]}")
    else:
        print(f"  {i+1}. DEBUG: {str(v)[:200]}")

# Scroll down to load more if needed
print("\n  Scrolling for more videos...")
for scroll in range(5):
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    time.sleep(2)

videos2 = page.evaluate("""() => {
    const results = [];
    const rows = document.querySelectorAll('ytcp-video-row');
    for (const row of rows) {
        const title = row.querySelector('#video-title')?.textContent?.trim() || '';
        const link = row.querySelector('a[href*="/video/"]');
        let videoId = '';
        if (link) {
            const match = link.href.match(/\/video\/([^/]+)/);
            if (match) videoId = match[1];
        }
        if (title) results.push({title, videoId});
    }
    return results;
}""")

if len(videos2) > len(videos):
    print(f"\n  After scroll: {len(videos2)} videos")
    for i, v in enumerate(videos2):
        print(f"  {i+1}. [{v.get('videoId', '???')}] {v['title']}")

page.screenshot(path="/tmp/yt_studio_audit_full.png")

ctx.close()
p.stop()
