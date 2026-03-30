#!/usr/bin/env python3
"""
Lesson 2-2: Design Your First Magnet Frame in TinkerCAD
Actual CAD automation — places real shapes in TinkerCAD's 3D editor,
shows professional overlays, orbits to show the design, groups shapes,
and records the entire session as video.

Verified interactions (from testing):
  - Drag shape from panel (comm=87=Box, 88=Cylinder) to workplane
  - Select All (Ctrl+A) -> Group (Ctrl+G) -> "Union"
  - Right-click drag to orbit view
  - Mouse wheel to zoom
  - Force inspector visible via JS
  - Export panel opens (comm=52)
  - CSS overlays on canvas
  - Playwright video recording (1920x1080)

Usage:
    # First time: login (opens visible browser)
    python tinkercad_helper.py --login

    # Record the lesson
    python record_lesson_2_2.py

    # Merge with TTS narration
    python video_pipeline.py --merge --audio narration-2-2.mp3 --video recording.webm --output lesson-2-2.mp4
"""

import sys
import time
from pathlib import Path

from playwright.sync_api import Page

# Import our helpers
sys.path.insert(0, str(Path(__file__).parent))
from tinkercad_helper import (
    get_persistent_context, wait_for_editor, create_new_design, EDITOR,
    show_step_overlay, show_mouse_highlight,
    select_all, group_shapes, duplicate_shape,
    orbit_view, zoom_view, drag_shape_to_workplane,
    click_shape_on_workplane, force_inspector_visible,
    get_inspector_title, export_stl,
)

OUTPUT_DIR = Path.home() / "video-uploads" / "recording-2-2"

# Shape communication IDs (from panel mapping)
BOX = "87"
CYLINDER = "88"


def show_fullscreen_card(page: Page, html: str, duration: float = 5):
    """Show a fullscreen overlay card."""
    safe_html = html.replace('`', '\\`')
    page.evaluate(f"""() => {{
        const existing = document.getElementById('fullscreen-card');
        if (existing) existing.remove();
        const el = document.createElement('div');
        el.id = 'fullscreen-card';
        el.innerHTML = `{safe_html}`;
        el.style.cssText = `
            position: fixed; top: 0; left: 0; right: 0; bottom: 0;
            background: linear-gradient(135deg, #0A0A0F 0%, #1a1a2e 50%, #16213e 100%);
            display: flex; flex-direction: column;
            align-items: center; justify-content: center;
            z-index: 999999;
            font-family: Inter, Segoe UI, sans-serif;
            text-align: center;
        `;
        document.body.appendChild(el);
    }}""")
    time.sleep(duration)
    page.evaluate("""() => {
        const el = document.getElementById('fullscreen-card');
        if (el) { el.style.transition = 'opacity 1s ease'; el.style.opacity = '0';
                   setTimeout(() => el.remove(), 1000); }
    }""")
    time.sleep(1.2)


def run_lesson(page: Page):
    """Execute the full lesson 2-2 design sequence."""

    # ── Title Card (5s) ──
    print("\n  Title Card")
    show_fullscreen_card(page, """
        <div style="font-size:18px; color:#6366f1; letter-spacing:3px; margin-bottom:16px">
            3D PRINT ACADEMY &mdash; MODULE 2, LESSON 2
        </div>
        <div style="font-size:44px; font-weight:800; color:#fff; margin-bottom:16px; line-height:1.2">
            Design Your First<br>Magnet Frame
        </div>
        <div style="font-size:22px; color:#a5b4fc">
            Step-by-Step in TinkerCAD
        </div>
    """, duration=5)

    # ── Design Dimensions Card (7s) ──
    print("  Dimensions Card")
    show_fullscreen_card(page, """
        <div style="max-width:800px; padding:40px">
            <div style="font-size:30px; font-weight:700; color:#6366f1; margin-bottom:24px">
                Design Planning
            </div>
            <div style="display:grid; grid-template-columns:1fr 1fr; gap:16px">
                <div style="background:rgba(255,255,255,0.08); padding:20px; border-radius:12px; border:1px solid rgba(255,255,255,0.1)">
                    <div style="color:#a5b4fc; font-size:14px; margin-bottom:6px">Frame Body</div>
                    <div style="color:#fff; font-size:22px; font-weight:600">112 x 87 x 8 mm</div>
                </div>
                <div style="background:rgba(255,255,255,0.08); padding:20px; border-radius:12px; border:1px solid rgba(255,255,255,0.1)">
                    <div style="color:#a5b4fc; font-size:14px; margin-bottom:6px">Photo Opening</div>
                    <div style="color:#fff; font-size:22px; font-weight:600">102 x 77 mm (hole)</div>
                </div>
                <div style="background:rgba(255,255,255,0.08); padding:20px; border-radius:12px; border:1px solid rgba(255,255,255,0.1)">
                    <div style="color:#a5b4fc; font-size:14px; margin-bottom:6px">Magnet Slots</div>
                    <div style="color:#fff; font-size:22px; font-weight:600">6.2mm dia x 2.1mm</div>
                </div>
                <div style="background:rgba(255,255,255,0.08); padding:20px; border-radius:12px; border:1px solid rgba(255,255,255,0.1)">
                    <div style="color:#a5b4fc; font-size:14px; margin-bottom:6px">Target Photo Size</div>
                    <div style="color:#fff; font-size:22px; font-weight:600">4x3 inch (101.6 x 76.2mm)</div>
                </div>
            </div>
        </div>
    """, duration=7)

    # ── STEP 1: Create Frame Body ──
    print("\n  Step 1: Create frame body")
    show_step_overlay(page, 1, "Create the Frame Body",
                      "Drag a Box from the shapes panel onto the workplane", duration=5000)
    time.sleep(2)

    # Highlight shapes panel
    bx, by = EDITOR["shape_box"]
    show_mouse_highlight(page, bx, by, duration=2000)
    time.sleep(1)

    # Drag Box to workplane center
    drag_shape_to_workplane(page, BOX, EDITOR["workplane_center"])
    time.sleep(1)

    title = get_inspector_title(page)
    print(f"    Inspector: {title}")

    # Show dimension overlay
    show_step_overlay(page, 1, "Frame Body Dimensions",
                      "Width: 112mm | Depth: 87mm | Height: 8mm", duration=5000)
    time.sleep(3)

    # Orbit to show the 3D shape
    orbit_view(page, dx=150, dy=-80)
    time.sleep(2)

    # ── STEP 2: Create Photo Opening ──
    print("  Step 2: Photo opening")
    show_step_overlay(page, 2, "Photo Insert Opening",
                      "Second Box — will become a Hole to cut through the frame",
                      duration=5000)
    time.sleep(2)

    drag_shape_to_workplane(page, BOX, (750, 520))
    time.sleep(1)

    title = get_inspector_title(page)
    print(f"    Inspector: {title}")

    show_step_overlay(page, 2, "Converting to Hole",
                      "In TinkerCAD: select shape > Inspector > Hole | 102x77mm opening",
                      duration=5000)

    # Force inspector visible to show the Solid/Hole UI
    force_inspector_visible(page)
    time.sleep(4)

    orbit_view(page, dx=-100, dy=50)
    time.sleep(2)

    # ── STEP 3: Retention Lip ──
    print("  Step 3: Retention lip")
    show_step_overlay(page, 3, "Photo Retention Lip",
                      "Thin box at back: 100x75x1mm — prevents photo from falling through",
                      duration=5000)
    time.sleep(2)

    drag_shape_to_workplane(page, BOX, (900, 550))
    time.sleep(1)

    show_step_overlay(page, 3, "Lip Dimensions",
                      "100x75mm, only 1mm thick — sits behind the photo cutout",
                      duration=4000)
    time.sleep(4)

    # ── STEP 4: Magnet Slots ──
    print("  Step 4: Magnet slots")
    show_step_overlay(page, 4, "Magnet Slots",
                      "Cylinder holes — 6.2mm diameter x 2.1mm deep at each corner",
                      duration=5000)
    time.sleep(2)

    # Highlight cylinder in shapes panel
    cx, cy = EDITOR["shape_cylinder"]
    show_mouse_highlight(page, cx, cy, duration=1500)
    time.sleep(1)

    # Place 4 cylinders at corner positions
    drag_shape_to_workplane(page, CYLINDER, (650, 450))
    time.sleep(1)

    show_step_overlay(page, 4, "Corner Positions",
                      "Place magnet slots near each corner for strong adhesion",
                      duration=4000)
    time.sleep(1)

    drag_shape_to_workplane(page, CYLINDER, (950, 600))
    time.sleep(1)

    drag_shape_to_workplane(page, CYLINDER, (650, 600))
    time.sleep(1)

    drag_shape_to_workplane(page, CYLINDER, (950, 450))
    time.sleep(1)

    orbit_view(page, dx=200, dy=-60)
    time.sleep(2)

    # ── STEP 5: Group All ──
    print("  Step 5: Group all shapes")
    show_step_overlay(page, 5, "Group All Shapes",
                      "Ctrl+A (Select All) then Ctrl+G (Group) — Holes subtract from Solids!",
                      duration=5000)
    time.sleep(2)

    select_all(page)
    time.sleep(1)

    title = get_inspector_title(page)
    print(f"    After Select All: {title}")

    group_shapes(page)
    time.sleep(2)

    title = get_inspector_title(page)
    print(f"    After Group: {title}")

    # Show result with orbiting
    show_step_overlay(page, 5, "Frame Complete!",
                      "Photo pocket, magnet slots, and retention lip — all in one piece",
                      duration=5000)

    orbit_view(page, dx=250, dy=-80)
    time.sleep(2)
    orbit_view(page, dx=-200, dy=60)
    time.sleep(2)
    orbit_view(page, dx=100, dy=-120)
    time.sleep(2)

    # ── STEP 6: Export ──
    print("  Step 6: Export")
    show_step_overlay(page, 6, "Export as STL",
                      "File > Export > .STL — ready for your slicer!", duration=4000)
    time.sleep(2)

    export_stl(page)
    time.sleep(3)
    page.keyboard.press("Escape")
    time.sleep(1)

    # ── Outro ──
    print("  Outro")
    show_fullscreen_card(page, """
        <div style="font-size:44px; font-weight:800; color:#fff; margin-bottom:16px">
            Your First Frame Design!
        </div>
        <div style="font-size:22px; color:#a5b4fc; margin-bottom:32px">
            Body &rarr; Opening &rarr; Lip &rarr; Magnets &rarr; Group &rarr; Export
        </div>
        <div style="font-size:18px; color:#6366f1; margin-bottom:8px">
            Next: Snap-Fit Clip Design
        </div>
        <div style="font-size:16px; color:#64748b; margin-top:24px">
            3D Print Academy &mdash; AJ DESIGN
        </div>
    """, duration=6)


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("\n  Lesson 2-2: Design Your First Magnet Frame")
    print(f"  Output: {OUTPUT_DIR}")
    print(f"  Recording 1920x1080\n")

    p, context = get_persistent_context(headless=False, video_dir=str(OUTPUT_DIR))
    page = context.pages[0] if context.pages else context.new_page()

    try:
        page.goto("https://www.tinkercad.com/dashboard",
                  wait_until="networkidle", timeout=30000)
        time.sleep(3)

        if "/login" in page.url:
            print("  Not logged in. Run: python tinkercad_helper.py --login")
            from tinkercad_helper import login_tinkercad
            login_tinkercad(page)

        print("  Creating new 3D design...")
        create_new_design(page)
        wait_for_editor(page, timeout=20)

        run_lesson(page)

    except Exception as e:
        print(f"\n  Error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        video_path = page.video.path()
        context.close()
        p.stop()

        import os
        size = os.path.getsize(video_path) / (1024 * 1024)
        print(f"\n  Recording saved: {video_path} ({size:.1f} MB)")
        print(f"  To merge with TTS:")
        print(f"  .venv/bin/python 3D-print/automation/video_pipeline.py lesson-2-2")


if __name__ == "__main__":
    main()
