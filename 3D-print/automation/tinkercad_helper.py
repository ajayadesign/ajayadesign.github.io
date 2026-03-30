#!/usr/bin/env python3
"""
TinkerCAD Automation Helper
Handles login, persistent sessions, and 3D editor interactions.

Uses launch_persistent_context so Google/Autodesk sessions persist
between runs (no need to re-login each time).

TinkerCAD's 3D editor uses WebGL canvas, so:
- MUST run non-headless (visible browser window)
- Needs GPU or SwiftShader for WebGL
- Shape panel/toolbar = DOM elements (clickable via selectors)
- 3D workspace = canvas (interactions via mouse coordinates)
- Inspector/dimension inputs = DOM elements

Usage:
    # First time: login and save session (opens visible browser)
    python tinkercad_helper.py --login

    # Test: open editor and check WebGL
    python tinkercad_helper.py --test

    # Run a design script
    python tinkercad_helper.py --script magnet_frame_4x3.py
"""

import argparse
import json
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright, Page, BrowserContext

# ── Paths ────────────────────────────────────────────────────────────────
PROFILE_DIR = Path.home() / ".tinkercad-playwright-profile"
USER_DATA_DIR = PROFILE_DIR / "chromium-profile"

# ── Browser launch args for WebGL ────────────────────────────────────────
CHROME_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--use-gl=egl",           # Use EGL for GPU rendering
    "--enable-gpu",
    "--no-sandbox",
    "--disable-dev-shm-usage",
]

# Fallback if no GPU: use software renderer
CHROME_ARGS_SOFTWARE = [
    "--disable-blink-features=AutomationControlled",
    "--use-gl=swiftshader",   # Software WebGL renderer
    "--use-angle=swiftshader",
    "--no-sandbox",
    "--disable-dev-shm-usage",
]

# ── TinkerCAD Editor Coordinates (1920x1080 viewport) ───────────────────
# Calibrated from actual editor layout mapping.
# Main 3D canvas: 1644x984 at (0, 96)
# Shapes panel: right side, 3 columns at x=1695, 1782, 1869
# Toolbar: y=48..96, Inspector header: (1332, 108)
EDITOR = {
    # Workplane center (center of 1644x984 canvas offset at y=96)
    "workplane_center": (822, 588),

    # Shapes panel (right side) — Basic Shapes category
    # 3 columns × 8 visible rows, 70x70 thumbnails
    # Row 1: Box, Cylinder, Sphere (typical order)
    "shape_box": (1695, 276),
    "shape_cylinder": (1782, 276),
    "shape_sphere": (1869, 276),
    # Row 2: Cone, Torus, Wedge
    "shape_cone": (1695, 375),
    "shape_torus": (1782, 375),
    "shape_wedge": (1869, 375),
    # Row 3: (varies)
    "shape_row3_1": (1695, 479),
    "shape_row3_2": (1782, 479),
    "shape_scribble": (1869, 479),  # "scribble-07a6d0.png"
    # Row 4
    "shape_row4_1": (1695, 583),
    "shape_row4_2": (1782, 583),
    "shape_row4_3": (1869, 583),
    # More Shapes button
    "more_shapes_btn": (1782, 1074),

    # Shape category sidebar (far right icons at x=1676)
    "cat_your_creations": (1676, 1255),
    "cat_favorites": (1676, 1305),
    "cat_basic_shapes": (1676, 1359),
    "cat_text": (1676, 1409),

    # Top toolbar subnav (y=48..96)
    "toolbar_y": 72,  # vertical center of toolbar

    # Inspector header area
    "inspector_header": (1497, 128),

    # Workplane quadrants (for placing multiple shapes)
    "wp_front_left": (550, 650),
    "wp_front_right": (1050, 650),
    "wp_back_left": (550, 450),
    "wp_back_right": (1050, 450),
    "wp_near_center_left": (700, 550),
    "wp_near_center_right": (950, 550),
}


def get_persistent_context(
    headless: bool = False,
    use_software_gl: bool = False,
    video_dir: str = None,
):
    """
    Launch browser with a persistent user data directory.
    Google/Autodesk sessions survive between runs.
    Returns (playwright_instance, context).
    """
    USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
    p = sync_playwright().start()
    args = CHROME_ARGS_SOFTWARE if use_software_gl else CHROME_ARGS

    ctx_options = {
        "headless": headless,
        "args": args,
        "slow_mo": 50,
        "viewport": {"width": 1920, "height": 1080},
        "color_scheme": "light",
    }
    if video_dir:
        ctx_options["record_video_dir"] = video_dir
        ctx_options["record_video_size"] = {"width": 1920, "height": 1080}

    context = p.chromium.launch_persistent_context(
        user_data_dir=str(USER_DATA_DIR),
        **ctx_options,
    )
    return p, context


def login_tinkercad(page: Page):
    """Navigate to TinkerCAD login page. User completes auth in visible browser."""
    page.goto("https://www.tinkercad.com/login", wait_until="networkidle")
    time.sleep(2)

    print("\n  ⚡ PLEASE LOG IN TO TINKERCAD IN THE BROWSER WINDOW ⚡")
    print("  (Use Google sign-in or email)")
    print("  Waiting for dashboard redirect...")

    # Wait for redirect back to TinkerCAD dashboard
    page.wait_for_url("**/dashboard**", timeout=180000)
    print("  ✅ Login successful!")
    time.sleep(2)


def check_webgl(page: Page) -> bool:
    """Check if WebGL is working."""
    result = page.evaluate("""() => {
        const canvas = document.createElement('canvas');
        const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
        return {
            webgl: !!gl,
            renderer: gl ? gl.getParameter(gl.RENDERER) : null,
            vendor: gl ? gl.getParameter(gl.VENDOR) : null,
        };
    }""")
    print(f"  WebGL: {result['webgl']}")
    if result['webgl']:
        print(f"  Renderer: {result['renderer']}")
        print(f"  Vendor: {result['vendor']}")
    return result['webgl']


def create_new_design(page: Page) -> str:
    """Navigate to dashboard and create a new 3D design. Returns design URL."""
    page.goto("https://www.tinkercad.com/dashboard", wait_until="networkidle")
    time.sleep(2)

    # Click "Create" button
    page.click("button:has-text('Create')")
    time.sleep(1)

    # Click "3D Design" from dropdown
    page.click("text=3D Design")
    time.sleep(5)  # Wait for editor to fully load

    url = page.url
    print(f"  New design created: {url}")
    return url


def wait_for_editor(page: Page, timeout: int = 15):
    """Wait for TinkerCAD editor to fully load."""
    print("  Waiting for editor to load...")
    for _ in range(timeout):
        # Check for canvas element (the 3D viewport)
        has_canvas = page.evaluate("() => !!document.querySelector('canvas')")
        if has_canvas:
            print("  ✅ Editor canvas loaded")
            time.sleep(2)  # Extra wait for shapes panel
            return True
        time.sleep(1)
    print("  ⚠ Editor may not have fully loaded")
    return False


# ── Shape Operations ─────────────────────────────────────────────────────
# TinkerCAD's 3D viewport is a WebGL canvas. Shape panel items have
# [communication] attributes and must be DRAGGED (not clicked) to place.
# Toolbar buttons also use [communication] attrs.
# Shape comm IDs: 87=Box, 88=Cylinder, 89=Sphere, 90=Cone, 91=Torus, 92=Wedge
# Toolbar comm IDs: 18=Copy, 20=Paste, 22=Duplicate, 24=Delete,
#   26=Undo, 28=Redo, 40=Align, 42=Mirror, 52=Export

def drag_shape_to_workplane(page: Page, shape_comm_or_pos, target_pos: tuple = None):
    """Drag a shape from the panel onto the workplane.
    shape_comm_or_pos: either a communication ID string ("87") or (x,y) tuple.
    """
    if target_pos is None:
        target_pos = EDITOR["workplane_center"]

    if isinstance(shape_comm_or_pos, str):
        el = page.locator(f"[communication='{shape_comm_or_pos}']")
        bb = el.bounding_box()
        sx = bb['x'] + bb['width'] / 2
        sy = bb['y'] + bb['height'] / 2
    else:
        sx, sy = shape_comm_or_pos

    tx, ty = target_pos

    page.mouse.move(sx, sy)
    time.sleep(0.5)
    page.mouse.down()
    time.sleep(0.3)
    for step in range(30):
        frac = (step + 1) / 30
        page.mouse.move(int(sx + (tx - sx) * frac), int(sy + (ty - sy) * frac))
        time.sleep(0.05)
    time.sleep(0.3)
    page.mouse.up()
    time.sleep(2)


def click_shape_on_workplane(page: Page, pos: tuple):
    """Click on a shape at the given position."""
    page.mouse.click(pos[0], pos[1])
    time.sleep(0.5)


def select_all(page: Page):
    """Select all shapes: Ctrl+A."""
    page.keyboard.press("Control+a")
    time.sleep(0.5)


def group_shapes(page: Page):
    """Group selected shapes: Ctrl+G."""
    page.keyboard.press("Control+g")
    time.sleep(1)


def ungroup_shapes(page: Page):
    """Ungroup selected shapes: Ctrl+Shift+G."""
    page.keyboard.press("Control+Shift+g")
    time.sleep(1)


def duplicate_shape(page: Page):
    """Duplicate selected shape: Ctrl+D."""
    page.keyboard.press("Control+d")
    time.sleep(0.5)


def delete_shape(page: Page):
    """Delete selected shape."""
    page.keyboard.press("Delete")
    time.sleep(0.3)


def undo(page: Page):
    """Undo: Ctrl+Z."""
    page.keyboard.press("Control+z")
    time.sleep(0.3)


def force_inspector_visible(page: Page):
    """Force the inspector panel to be visible (it starts hidden)."""
    page.evaluate("""() => {
        const holder = document.querySelector('.js-editor__holder__inspector');
        if (holder) {
            holder.style.opacity = '1';
            holder.style.pointerEvents = 'auto';
            holder.setAttribute('aria-expanded', 'true');
        }
        const controls = document.querySelector('.js-inspector__commonheadercontrols');
        if (controls) controls.style.display = '';
    }""")
    time.sleep(0.5)


def get_inspector_title(page: Page) -> str:
    """Get the current inspector panel title."""
    return page.evaluate(
        "() => document.querySelector('.js-inspector__title')?.textContent || ''"
    )


def orbit_view(page: Page, dx: int = 200, dy: int = 100):
    """Orbit the 3D view by right-click dragging."""
    cx, cy = EDITOR["workplane_center"]
    page.mouse.move(cx, cy)
    page.mouse.down(button="right")
    for step in range(20):
        frac = (step + 1) / 20
        page.mouse.move(int(cx + dx * frac), int(cy + dy * frac))
        time.sleep(0.05)
    page.mouse.up(button="right")
    time.sleep(0.5)


def zoom_view(page: Page, delta: int = -3):
    """Zoom in/out. Negative = zoom in, positive = zoom out."""
    cx, cy = EDITOR["workplane_center"]
    page.mouse.move(cx, cy)
    for _ in range(abs(delta)):
        page.mouse.wheel(0, -120 if delta < 0 else 120)
        time.sleep(0.1)
    time.sleep(0.5)


def export_stl(page: Page):
    """Open Export panel (comm=52)."""
    page.locator("[communication='52']").click()
    time.sleep(2)


# ── Visual Overlays (for video recording) ────────────────────────────────

def show_step_overlay(page: Page, step_num: int, title: str, detail: str = "",
                      duration: int = 4000):
    """Show a step overlay on the recording."""
    page.evaluate(f"""() => {{
        // Remove any existing overlay
        const existing = document.getElementById('step-overlay');
        if (existing) existing.remove();

        const el = document.createElement('div');
        el.id = 'step-overlay';
        el.innerHTML = `
            <div style="font-size:14px; color:#6366f1; letter-spacing:2px; margin-bottom:8px">STEP {step_num}</div>
            <div style="font-size:24px; font-weight:700; color:#fff; margin-bottom:6px">{title}</div>
            <div style="font-size:16px; color:#94a3b8">{detail}</div>
        `;
        el.style.cssText = `
            position: fixed; top: 20px; left: 20px;
            padding: 16px 24px;
            background: rgba(10, 10, 15, 0.9);
            border-radius: 12px;
            border: 1px solid rgba(99, 102, 241, 0.3);
            pointer-events: none;
            z-index: 999999;
            font-family: Inter, Segoe UI, sans-serif;
            box-shadow: 0 8px 32px rgba(0,0,0,0.4);
            max-width: 400px;
        `;
        document.body.appendChild(el);
        setTimeout(() => el.remove(), {duration});
    }}""")


def show_mouse_highlight(page: Page, x: int, y: int, duration: int = 2000):
    """Show a pulsing highlight circle at mouse position."""
    page.evaluate(f"""() => {{
        const el = document.createElement('div');
        el.style.cssText = `
            position: fixed; left: {x - 25}px; top: {y - 25}px;
            width: 50px; height: 50px;
            border: 3px solid rgba(99, 102, 241, 0.8);
            border-radius: 50%;
            pointer-events: none;
            z-index: 999999;
            box-shadow: 0 0 20px rgba(99, 102, 241, 0.4);
        `;
        document.body.appendChild(el);
        setTimeout(() => el.remove(), {duration});
    }}""")


# ── Editor Navigation ────────────────────────────────────────────────────

def navigate_to_editor(page: Page) -> dict:
    """Navigate to TinkerCAD editor. Returns viewport info dict with cx, cy."""
    page.goto("https://www.tinkercad.com/dashboard", wait_until="networkidle", timeout=30000)
    time.sleep(3)
    page.click("text=Designs")
    time.sleep(3)
    href = page.evaluate("""() => {
        for (const a of document.querySelectorAll('a'))
            if (a.textContent.trim() === 'Tinker this') return a.href;
    }""")
    if not href:
        raise RuntimeError("No 'Tinker this' link found on dashboard")
    page.goto(href, wait_until="domcontentloaded", timeout=60000)
    time.sleep(15)
    page.wait_for_selector(".editor3d", timeout=60000)
    time.sleep(3)
    return get_viewport_center(page)


def get_viewport_center(page: Page) -> dict:
    """Find the largest canvas (main 3D viewport) and return its center coords."""
    return page.evaluate("""() => {
        let max = 0, best = null;
        document.querySelectorAll('canvas').forEach(c => {
            const r = c.getBoundingClientRect();
            if (r.width * r.height > max) { max = r.width * r.height; best = r; }
        });
        return {cx: best.x + best.width/2, cy: best.y + best.height/2,
                w: best.width, h: best.height};
    }""")


# ── Material (Solid/Hole) Operations ────────────────────────────────────

def get_material_state(page: Page) -> dict:
    """Read current Solid/Hole state from material buttons."""
    return page.evaluate("""() => {
        const btns = document.querySelectorAll('.editor__materialbtn');
        const state = {};
        for (const btn of btns) {
            const text = btn.textContent.trim();
            const icon = btn.querySelector('.js-btn__icon__selection');
            state[text] = icon ? icon.classList.contains('selected') : null;
        }
        return state;
    }""")


def set_material(page: Page, material: str):
    """Set material to 'Solid' or 'Hole' using all known methods."""
    btn_id = f"material-button-{material.lower()}"
    pos = page.evaluate(f"""() => {{
        const btn = document.getElementById('{btn_id}');
        if (!btn) return null;
        const r = btn.getBoundingClientRect();
        return {{x: r.x + r.width/2, y: r.y + r.height/2}};
    }}""")
    if pos:
        page.mouse.click(pos['x'], pos['y'])
        time.sleep(0.3)
    page.locator(".editor__materialbtn__label", has_text=material).first.click(force=True)
    time.sleep(0.2)
    page.evaluate(f"""() => {{
        const btn = document.getElementById('{btn_id}');
        if (btn) btn.dispatchEvent(new CustomEvent('Tinkercad:MaterialBtn:click', {{bubbles: true}}));
    }}""")
    time.sleep(0.3)


# ── Dimension Operations ────────────────────────────────────────────────

def _find_dim_slider(page: Page, label: str):
    """Locate the slider-text element for a dimension label. Returns {x, y} or None."""
    return page.evaluate("""(label) => {
        const items = document.querySelectorAll('.editor__inspector__item');
        for (const item of items) {
            const lbl = item.querySelector('.editor__inspector__item__label');
            if (lbl && lbl.textContent.trim() === label) {
                const slider = item.querySelector('.editor__inspector__item__ui-slider-text');
                if (slider) {
                    const r = slider.getBoundingClientRect();
                    return {x: r.x + r.width/2, y: r.y + r.height/2};
                }
            }
        }
        return null;
    }""", label)


def _read_dim_value(page: Page, label: str):
    """Read a single dimension's current value. Returns float or None."""
    val = page.evaluate("""(label) => {
        const items = document.querySelectorAll('.editor__inspector__item');
        for (const item of items) {
            const lbl = item.querySelector('.editor__inspector__item__label');
            if (lbl && lbl.textContent.trim() === label) {
                const slider = item.querySelector('.editor__inspector__item__ui-slider-text');
                if (slider) return slider.textContent.trim();
            }
        }
        return null;
    }""", label)
    if val is not None:
        try:
            return float(val)
        except ValueError:
            return None
    return None


def set_dimension(page: Page, label: str, value, retries: int = 3):
    """Set a dimension (Width/Length/Height) via click+type on slider text.
    Verifies the value was accepted and retries if needed."""
    target = float(value)
    for attempt in range(retries):
        info = _find_dim_slider(page, label)
        if not info:
            time.sleep(0.5)
            continue
        # Click the slider text to focus it
        page.mouse.click(info['x'], info['y'])
        time.sleep(0.3)
        # Triple-click to select all text in the field
        page.mouse.click(info['x'], info['y'], click_count=3)
        time.sleep(0.2)
        page.keyboard.press("Control+a")
        time.sleep(0.1)
        page.keyboard.press("Backspace")
        time.sleep(0.1)
        page.keyboard.type(str(value), delay=50)
        time.sleep(0.2)
        page.keyboard.press("Enter")
        time.sleep(0.8)
        # Verify the value was accepted
        actual = _read_dim_value(page, label)
        if actual is not None and abs(actual - target) < 1.0:
            return True
        print(f"  ⚠ Dimension {label}={value} attempt {attempt+1}: got {actual}, retrying...")
        time.sleep(0.5)
    print(f"  ❌ Failed to set {label}={value} after {retries} attempts")
    return False


def read_dimensions(page: Page) -> dict:
    """Read all dimension values from the inspector."""
    return page.evaluate("""() => {
        const items = document.querySelectorAll('.editor__inspector__item');
        const dims = {};
        for (const item of items) {
            const lbl = item.querySelector('.editor__inspector__item__label');
            const val = item.querySelector('.editor__inspector__item__ui-slider-text');
            if (lbl && val) dims[lbl.textContent.trim()] = val.textContent.trim();
        }
        return dims;
    }""")


# ── Frame Building ───────────────────────────────────────────────────────

def build_frame(page: Page, outer_w: float, outer_l: float, thickness: float,
                wall: float, cx: float = None, cy: float = None,
                y_nudge: int = None) -> str:
    """Build a picture frame in TinkerCAD. Returns inspector title of result.

    Args:
        outer_w: Outer width (mm)
        outer_l: Outer length (mm)
        thickness: Frame thickness/height (mm)
        wall: Wall thickness (mm) — inner cutout will be (outer - 2*wall)
        cx, cy: Viewport center coords (auto-detected if None)
        y_nudge: ArrowUp presses for Y alignment (auto-calculated if None)
    """
    if cx is None or cy is None:
        vp = get_viewport_center(page)
        cx, cy = vp['cx'], vp['cy']

    inner_w = outer_w - 2 * wall
    inner_l = outer_l - 2 * wall
    hole_h = thickness + 2  # Slightly taller to cut through

    # Clear workplane
    page.keyboard.press("Control+a")
    time.sleep(0.3)
    page.keyboard.press("Delete")
    time.sleep(1)

    # Place body
    drag_shape_to_workplane(page, "87", (cx, cy))
    page.mouse.click(cx, cy)
    time.sleep(0.5)

    # Set body to Solid
    state = get_material_state(page)
    if not state.get('Solid'):
        set_material(page, "Solid")
        page.mouse.click(cx, cy)
        time.sleep(0.5)

    # Set body dimensions
    set_dimension(page, "Width", outer_w)
    set_dimension(page, "Length", outer_l)
    set_dimension(page, "Height", thickness)

    # Set Hole mode via set+undo trick
    set_material(page, "Hole")
    time.sleep(0.3)
    page.keyboard.press("Control+z")
    time.sleep(0.5)

    # Deselect body
    page.mouse.click(200, 800)
    time.sleep(0.5)

    # Place hole shape (auto-inherits Hole mode)
    drag_shape_to_workplane(page, "87", (cx, cy))
    page.mouse.click(cx, cy)
    time.sleep(0.5)

    # Set hole dimensions
    set_dimension(page, "Width", inner_w)
    set_dimension(page, "Length", inner_l)
    set_dimension(page, "Height", hole_h)

    # Fix Y alignment: nudge hole to center over body
    # Placement offset varies ~5-10mm depending on frame size.
    # Use wall size as upper bound to avoid overcorrection.
    if y_nudge is None:
        y_nudge = min(8, wall)
    page.mouse.click(cx, cy)
    time.sleep(0.3)
    for _ in range(y_nudge):
        page.keyboard.press("ArrowUp")
        time.sleep(0.1)
    time.sleep(0.5)

    # Group (boolean subtraction)
    page.keyboard.press("Control+a")
    time.sleep(1)
    page.keyboard.press("Control+g")
    time.sleep(3)

    # Click to select grouped result
    page.mouse.click(cx, cy)
    time.sleep(0.5)
    return get_inspector_title(page)


def export_stl_download(page: Page, save_path: str) -> str:
    """Export STL and save to disk. Returns the file path."""
    page.locator("[communication='52']").first.click()
    time.sleep(2)
    stl_btn = page.locator("text=.STL").first
    if stl_btn.is_visible(timeout=3000):
        with page.expect_download(timeout=15000) as dl:
            stl_btn.click()
        download = dl.value
        download.save_as(save_path)
        return save_path
    raise RuntimeError("STL export button not visible")


# ── CLI ──────────────────────────────────────────────────────────────────

def cmd_login():
    """Interactive login and save session to persistent profile."""
    print("\n🔑 TinkerCAD Login (persistent browser profile)")
    print(f"  Profile: {USER_DATA_DIR}")
    p, context = get_persistent_context(headless=False)
    page = context.pages[0] if context.pages else context.new_page()

    # Check if already logged in
    page.goto("https://www.tinkercad.com/dashboard", wait_until="networkidle", timeout=30000)
    time.sleep(3)

    if "/login" in page.url:
        login_tinkercad(page)
    else:
        print("  ✅ Already logged in (session persisted from previous run)")
        print(f"  Dashboard: {page.url}")

    print("\n  Session saved in persistent profile. Future runs will auto-login.")
    input("  Press Enter to close browser...")
    context.close()
    p.stop()


def cmd_test():
    """Test WebGL and editor functionality."""
    print("\n🧪 TinkerCAD Test")
    p, context = get_persistent_context(headless=False)
    page = context.pages[0] if context.pages else context.new_page()

    # Check WebGL
    page.goto("about:blank")
    webgl_ok = check_webgl(page)
    if not webgl_ok:
        print("  ⚠ Trying software GL...")
        context.close()
        p.stop()
        p, context = get_persistent_context(headless=False, use_software_gl=True)
        page = context.pages[0] if context.pages else context.new_page()
        page.goto("about:blank")
        webgl_ok = check_webgl(page)

    if not webgl_ok:
        print("  ❌ WebGL not available. TinkerCAD editor won't work.")
        context.close()
        p.stop()
        return

    # Try opening TinkerCAD
    page.goto("https://www.tinkercad.com/dashboard", wait_until="networkidle", timeout=30000)
    time.sleep(3)

    # Check if logged in
    if "/login" in page.url:
        print("  Not logged in. Run --login first.")
    else:
        print("  ✅ Logged in to TinkerCAD")

        # Try creating a new design
        create_new_design(page)
        wait_for_editor(page)

        # Report what we see
        dom_info = page.evaluate("""() => {
            return {
                canvas: !!document.querySelector('canvas'),
                canvasCount: document.querySelectorAll('canvas').length,
                bodyChildren: document.body.children.length,
                title: document.title,
            };
        }""")
        print(f"  Canvas elements: {dom_info['canvasCount']}")
        print(f"  Page title: {dom_info['title']}")

        # Take a screenshot for coordinate calibration
        page.screenshot(path="/tmp/tinkercad_editor_test.png")
        print("  Screenshot: /tmp/tinkercad_editor_test.png")

    input("  Press Enter to close browser...")
    context.close()
    p.stop()


def main():
    parser = argparse.ArgumentParser(description="TinkerCAD Automation Helper")
    parser.add_argument("--login", action="store_true", help="Log in and save session")
    parser.add_argument("--test", action="store_true", help="Test WebGL and editor")
    parser.add_argument("--software-gl", action="store_true", help="Force software GL")
    args = parser.parse_args()

    if args.login:
        cmd_login()
    elif args.test:
        cmd_test()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
