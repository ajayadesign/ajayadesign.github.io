#!/usr/bin/env python3
"""
Playwright Screen Recorder for CAD Lesson Videos
Records browser-based TinkerCAD/Fusion360 sessions with scripted actions.

Uses Playwright's built-in video recording (record_video_dir) to capture
the browser viewport while executing a screenplay of actions.

Usage:
    python screen_recorder.py --screenplay screenplays/lesson_2_2.json --output recording.webm
    python screen_recorder.py --url https://www.tinkercad.com --duration 60 --output demo.webm
"""

import argparse
import json
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright, Page, BrowserContext


# Video settings
VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1080


def execute_action(page: Page, action: dict, verbose: bool = True):
    """Execute a single screenplay action on the page."""
    action_type = action.get("type", "")

    if verbose:
        desc = action.get("description", action_type)
        print(f"    → {desc}")

    if action_type == "navigate":
        page.goto(action["url"], wait_until="networkidle", timeout=30000)

    elif action_type == "wait":
        seconds = action.get("seconds", 2)
        time.sleep(seconds)

    elif action_type == "click":
        selector = action.get("selector")
        x, y = action.get("x"), action.get("y")
        if selector:
            page.wait_for_selector(selector, timeout=10000)
            page.click(selector)
        elif x is not None and y is not None:
            page.mouse.click(x, y)

    elif action_type == "double_click":
        selector = action.get("selector")
        if selector:
            page.wait_for_selector(selector, timeout=10000)
            page.dblclick(selector)
        else:
            page.mouse.dblclick(action.get("x", 0), action.get("y", 0))

    elif action_type == "type":
        selector = action.get("selector")
        text = action["text"]
        if selector:
            page.wait_for_selector(selector, timeout=10000)
            page.fill(selector, text)
        else:
            page.keyboard.type(text, delay=50)

    elif action_type == "key":
        page.keyboard.press(action["key"])

    elif action_type == "scroll":
        page.mouse.wheel(action.get("dx", 0), action.get("dy", -300))

    elif action_type == "move":
        # Smooth mouse movement for visual guidance
        x, y = action["x"], action["y"]
        steps = action.get("steps", 20)
        page.mouse.move(x, y, steps=steps)

    elif action_type == "drag":
        page.mouse.move(action["from_x"], action["from_y"])
        page.mouse.down()
        time.sleep(0.1)
        page.mouse.move(action["to_x"], action["to_y"], steps=action.get("steps", 30))
        page.mouse.up()

    elif action_type == "screenshot":
        # Take a screenshot marker — useful for debugging
        path = action.get("path", f"screenshot_{int(time.time())}.png")
        page.screenshot(path=path)

    elif action_type == "highlight":
        # Draw a visual highlight circle/box on screen using JS overlay
        x, y = action.get("x", 500), action.get("y", 500)
        size = action.get("size", 60)
        color = action.get("color", "rgba(255, 87, 34, 0.6)")
        duration = action.get("duration", 2000)
        page.evaluate(f"""() => {{
            const el = document.createElement('div');
            el.style.cssText = `
                position: fixed; left: {x - size//2}px; top: {y - size//2}px;
                width: {size}px; height: {size}px;
                border: 3px solid {color};
                border-radius: 50%;
                pointer-events: none;
                z-index: 999999;
                animation: pulse 0.5s ease-in-out 3;
                box-shadow: 0 0 20px {color};
            `;
            document.body.appendChild(el);
            setTimeout(() => el.remove(), {duration});
        }}""")
        time.sleep(duration / 1000)

    elif action_type == "text_overlay":
        # Show text overlay on screen
        text = action["text"]
        x = action.get("x", 100)
        y = action.get("y", 50)
        font_size = action.get("font_size", 28)
        duration = action.get("duration", 4000)
        bg = action.get("bg", "rgba(10, 10, 15, 0.85)")
        page.evaluate(f"""() => {{
            const el = document.createElement('div');
            el.textContent = `{text}`;
            el.style.cssText = `
                position: fixed; left: {x}px; top: {y}px;
                padding: 16px 28px;
                background: {bg};
                color: #fff;
                font-family: 'Inter', 'Segoe UI', sans-serif;
                font-size: {font_size}px;
                font-weight: 600;
                border-radius: 12px;
                pointer-events: none;
                z-index: 999999;
                border: 1px solid rgba(255,255,255,0.15);
                box-shadow: 0 8px 32px rgba(0,0,0,0.4);
            `;
            document.body.appendChild(el);
            setTimeout(() => el.remove(), {duration});
        }}""")
        time.sleep(duration / 1000)

    elif action_type == "eval":
        page.evaluate(action["script"])

    else:
        print(f"    ⚠ Unknown action type: {action_type}")

    # Post-action pause
    pause = action.get("pause", 0.5)
    time.sleep(pause)


def record_screenplay(screenplay_path: str, output_dir: str,
                      headless: bool = False, slow_mo: int = 100) -> str:
    """Record a browser session following a screenplay file. Returns video path."""
    screenplay = json.loads(Path(screenplay_path).read_text())

    lesson_id = screenplay.get("lesson_id", "unknown")
    base_url = screenplay.get("start_url", "about:blank")
    viewport_w = screenplay.get("viewport_width", VIDEO_WIDTH)
    viewport_h = screenplay.get("viewport_height", VIDEO_HEIGHT)
    actions = screenplay.get("actions", [])

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n🎬 Recording lesson {lesson_id}")
    print(f"   Screenplay: {screenplay_path}")
    print(f"   Actions: {len(actions)}")
    print(f"   Output: {output_dir}/")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=headless,
            slow_mo=slow_mo,
            args=["--disable-blink-features=AutomationControlled"],
        )

        context = browser.new_context(
            viewport={"width": viewport_w, "height": viewport_h},
            record_video_dir=str(out_dir),
            record_video_size={"width": viewport_w, "height": viewport_h},
            color_scheme="dark",
        )

        page = context.new_page()

        # Navigate to start URL
        if base_url != "about:blank":
            print(f"   Navigating to {base_url}")
            page.goto(base_url, wait_until="networkidle", timeout=30000)
            time.sleep(2)

        # Execute all actions
        for i, action in enumerate(actions):
            section = action.get("section", "")
            if section:
                print(f"\n  [{i+1}/{len(actions)}] Section: {section}")
            execute_action(page, action)

        # Final pause for clean ending
        time.sleep(2)

        # Close to finalize video
        video_path = page.video.path()
        context.close()
        browser.close()

    print(f"\n✅ Recording saved: {video_path}")
    return str(video_path)


def record_freeform(url: str, duration: int, output_dir: str,
                    headless: bool = False) -> str:
    """Record a URL for a set duration without scripted actions."""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n🎬 Recording {url} for {duration}s")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(
            viewport={"width": VIDEO_WIDTH, "height": VIDEO_HEIGHT},
            record_video_dir=str(out_dir),
            record_video_size={"width": VIDEO_WIDTH, "height": VIDEO_HEIGHT},
        )
        page = context.new_page()
        page.goto(url, wait_until="networkidle", timeout=30000)
        time.sleep(duration)

        video_path = page.video.path()
        context.close()
        browser.close()

    print(f"✅ Recording saved: {video_path}")
    return str(video_path)


def main():
    parser = argparse.ArgumentParser(description="Record browser sessions with Playwright")
    parser.add_argument("--screenplay", help="Screenplay JSON file")
    parser.add_argument("--url", help="URL to record (freeform mode)")
    parser.add_argument("--duration", type=int, default=60, help="Duration in seconds (freeform)")
    parser.add_argument("--output", default="./recordings", help="Output directory for video")
    parser.add_argument("--headless", action="store_true", help="Run headless (no GUI)")
    parser.add_argument("--slow-mo", type=int, default=100, help="Slow down actions (ms)")
    args = parser.parse_args()

    if args.screenplay:
        record_screenplay(args.screenplay, args.output, headless=args.headless, slow_mo=args.slow_mo)
    elif args.url:
        record_freeform(args.url, args.duration, args.output, headless=args.headless)
    else:
        print("Error: Provide --screenplay or --url")
        sys.exit(1)


if __name__ == "__main__":
    main()
