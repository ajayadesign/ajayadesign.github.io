#!/usr/bin/env python3
"""
Production TinkerCAD Lesson Video Recorder
Records actual TinkerCAD design work with step overlays and narration.

Usage:
    python3 record_tinkercad_lesson.py --lesson 2-2
    python3 record_tinkercad_lesson.py --lesson 3-3 --tts-only
    python3 record_tinkercad_lesson.py --lesson 2-2 --merge-only
"""
import argparse
import json
import os
import subprocess
import time
from pathlib import Path

from tinkercad_helper import (
    get_persistent_context, navigate_to_editor, get_viewport_center,
    get_material_state, set_material, set_dimension, read_dimensions,
    drag_shape_to_workplane, select_all, group_shapes, export_stl_download,
    show_step_overlay, show_mouse_highlight, orbit_view, zoom_view,
    get_inspector_title, EDITOR, _read_dim_value,
)

# ── Paths ────────────────────────────────────────────────────────────────
BASE = Path(__file__).parent
CONTENT_DIR = BASE.parent / "content" / "lessons"
OUTPUT_DIR = Path.home() / "video-uploads"
OUTPUT_DIR.mkdir(exist_ok=True)
VENV_PYTHON = str(BASE.parent.parent / ".venv" / "bin" / "python")
EDGE_TTS = str(BASE.parent.parent / ".venv" / "bin" / "edge-tts")

# ── Lesson Definitions ──────────────────────────────────────────────────
# Each lesson defines the TinkerCAD operations to perform during recording.
LESSONS = {
    "2-2": {
        "title": "Design Your First Magnet Frame",
        "filename": "lesson-2-2-first-frame-tinkercad",
        "description": "Build a 4×3 photo frame from scratch in TinkerCAD",
        "steps": [
            {
                "overlay": "Design Planning",
                "detail": "4×3 frame: 112×87×8mm body, 102×77mm opening",
                "narration": "Let's design our first magnet frame. We'll build a standard four by three inch photo frame with a twelve millimeter border. The frame body will be one hundred twelve by eighty seven by eight millimeters.",
                "action": "pause",
                "pause": 6,
            },
            {
                "overlay": "Place Frame Body",
                "detail": "Drag a Box onto the workplane",
                "narration": "First, drag a Box shape from the shapes panel onto the workplane. This will become our frame body.",
                "action": "place_body",
            },
            {
                "overlay": "Set Body Dimensions",
                "detail": "112mm × 87mm × 8mm",
                "narration": "Now set the dimensions. Width to one hundred twelve millimeters, length to eighty seven, and height to eight. This gives us enough depth for the photo pocket while keeping material usage reasonable.",
                "action": "set_body_dims",
                "dims": {"Width": 112, "Length": 87, "Height": 8},
            },
            {
                "overlay": "Set Body to Solid",
                "detail": "Ensure frame body is a solid shape",
                "narration": "Make sure the frame body is set to Solid. This is the main structure that will remain after we subtract the openings.",
                "action": "set_solid",
            },
            {
                "overlay": "Place Photo Opening",
                "detail": "Drag another Box for the cutout",
                "narration": "Now drag a second Box onto the workplane. This will become the photo opening that gets subtracted from the body.",
                "action": "place_hole",
            },
            {
                "overlay": "Set as Hole",
                "detail": "Change the opening to Hole type",
                "narration": "Change this box to a Hole. In TinkerCAD, Hole shapes get subtracted when you group them with solid shapes. Watch how the shape becomes transparent, showing it will cut through the body.",
                "action": "set_hole",
            },
            {
                "overlay": "Set Opening Dimensions",
                "detail": "102mm × 77mm × 10mm",
                "narration": "Set the opening dimensions. Width one hundred two, length seventy seven. The height is ten millimeters, slightly taller than the body, to ensure a clean cut all the way through.",
                "action": "set_hole_dims",
                "dims": {"Width": 102, "Length": 77, "Height": 10},
            },
            {
                "overlay": "Center the Opening",
                "detail": "Align hole over the body center",
                "narration": "Center the opening over the frame body. The five millimeter border on each side gives our frame a clean, professional look while maintaining structural strength.",
                "action": "align_hole",
            },
            {
                "overlay": "Select All & Group",
                "detail": "Ctrl+A → Ctrl+G for Boolean subtraction",
                "narration": "Select all shapes with Control A, then group with Control G. TinkerCAD performs the Boolean subtraction. The hole shape cuts through the solid body, creating our photo frame opening.",
                "action": "group",
            },
            {
                "overlay": "Inspect the Result",
                "detail": "Orbit to verify the frame geometry",
                "narration": "Let's orbit around to inspect our frame. You can see the clean rectangular opening in the center. The walls are even on all sides. This is a production-ready frame design.",
                "action": "orbit_inspect",
            },
            {
                "overlay": "Export as STL",
                "detail": "Save for 3D printing",
                "narration": "Finally, export as an STL file. Click Export, then choose dot STL. This file is ready to open in your slicer for printing. Name it descriptively, like Magnet Frame four by three version one.",
                "action": "export",
            },
        ],
    },
    "3-3": {
        "title": "Polaroid-Style Frame",
        "filename": "lesson-3-3-polaroid-frame",
        "description": "Design a Polaroid-style frame with wider bottom border",
        "steps": [
            {
                "overlay": "Design Planning",
                "detail": "Polaroid frame: 88×107mm body, wider bottom border",
                "narration": "The Polaroid style frame has a distinctive wider bottom border. Our body will be eighty eight by one hundred seven by six millimeters, with the photo opening offset toward the top.",
                "action": "pause",
                "pause": 6,
            },
            {
                "overlay": "Place Frame Body",
                "detail": "Drag a Box onto the workplane",
                "narration": "Place a Box shape on the workplane for the frame body.",
                "action": "place_body",
            },
            {
                "overlay": "Set Body Dimensions",
                "detail": "88mm × 107mm × 6mm",
                "narration": "Set width to eighty eight, length to one hundred seven, and height to six millimeters. The taller length gives us room for that signature wide bottom border.",
                "action": "set_body_dims",
                "dims": {"Width": 88, "Length": 107, "Height": 6},
            },
            {
                "overlay": "Set Body to Solid",
                "detail": "Ensure frame body is solid",
                "narration": "Confirm the body is set to Solid.",
                "action": "set_solid",
            },
            {
                "overlay": "Place Photo Opening",
                "detail": "Opening for Polaroid-size photo",
                "narration": "Place another Box for the photo opening. This will be sized for a standard Polaroid print.",
                "action": "place_hole",
            },
            {
                "overlay": "Set as Hole",
                "detail": "Change to Hole for subtraction",
                "narration": "Set it to Hole so it will cut through the body when grouped.",
                "action": "set_hole",
            },
            {
                "overlay": "Set Opening Dimensions",
                "detail": "72mm × 72mm × 8mm (square opening)",
                "narration": "Set width and length both to seventy two millimeters for a square opening. Height to eight millimeters to cut completely through. A square opening is the hallmark of the Polaroid style.",
                "action": "set_hole_dims",
                "dims": {"Width": 72, "Length": 72, "Height": 8},
            },
            {
                "overlay": "Center the Opening",
                "detail": "Align with wider bottom border",
                "narration": "Center the opening. With the Polaroid style, the bottom border is wider than the top, which we achieve by slightly offsetting the opening upward.",
                "action": "align_hole",
            },
            {
                "overlay": "Select All & Group",
                "detail": "Boolean subtraction",
                "narration": "Select all and group. The Boolean subtraction creates our Polaroid-style frame with that characteristic wide bottom border.",
                "action": "group",
            },
            {
                "overlay": "Inspect & Export",
                "detail": "Verify and save STL",
                "narration": "Orbit around to inspect, then export as STL. This iconic frame style is one of the best sellers at craft fairs.",
                "action": "orbit_and_export",
            },
        ],
    },
    "3-4": {
        "title": "Instax Mini Frame",
        "filename": "lesson-3-4-instax-mini-frame",
        "description": "Design a frame for Fujifilm Instax Mini prints",
        "steps": [
            {
                "overlay": "Design Planning",
                "detail": "Instax Mini: 62×46mm print, 72×56mm frame",
                "narration": "The Instax Mini frame is designed for Fujifilm Instax Mini prints measuring sixty two by forty six millimeters. Our frame will be seventy two by fifty six by five millimeters.",
                "action": "pause",
                "pause": 6,
            },
            {
                "overlay": "Place Frame Body",
                "detail": "Drag Box onto workplane",
                "narration": "Place a Box shape for the frame body.",
                "action": "place_body",
            },
            {
                "overlay": "Set Body Dimensions",
                "detail": "72mm × 56mm × 5mm",
                "narration": "Set width to seventy two, length to fifty six, and height to five millimeters. The compact size keeps material costs very low.",
                "action": "set_body_dims",
                "dims": {"Width": 72, "Length": 56, "Height": 5},
            },
            {
                "overlay": "Set Body to Solid",
                "detail": "Solid frame body",
                "narration": "Confirm it's set to Solid.",
                "action": "set_solid",
            },
            {
                "overlay": "Place Photo Opening",
                "detail": "Sized for Instax Mini prints",
                "narration": "Place the photo opening box.",
                "action": "place_hole",
            },
            {
                "overlay": "Set as Hole & Dimensions",
                "detail": "62mm × 46mm × 7mm",
                "narration": "Set to Hole, then dimensions: sixty two by forty six by seven millimeters. The larger height ensures a clean cut through the body.",
                "action": "set_hole",
            },
            {
                "overlay": "Set Opening Dimensions",
                "detail": "62×46×7mm",
                "narration": "Width sixty two, length forty six, height seven.",
                "action": "set_hole_dims",
                "dims": {"Width": 62, "Length": 46, "Height": 7},
            },
            {
                "overlay": "Center & Group",
                "detail": "Align, select all, group",
                "narration": "Center the opening, select all shapes, and group. The Instax Mini frame is now complete with a five millimeter border on all sides.",
                "action": "align_and_group",
            },
            {
                "overlay": "Export STL",
                "detail": "Save for printing",
                "narration": "Export as STL. This compact frame uses minimal filament and prints in about twenty minutes, making it one of the most profitable designs per print hour.",
                "action": "orbit_and_export",
            },
        ],
    },
    "3-5": {
        "title": "Multi-Photo Collage Frame",
        "filename": "lesson-3-5-multi-photo-collage",
        "description": "Build a 3-photo collage frame for premium sales",
        "steps": [
            {
                "overlay": "Design Planning",
                "detail": "3-photo collage: 200×80mm body, three 52×52mm openings",
                "narration": "Let's design a multi-photo collage frame. This is your premium product. Three photos in a row, two hundred by eighty millimeters. Each opening is fifty two by fifty two. Five millimeter borders between photos and eight millimeter outer borders. This frame sells for twelve to fifteen dollars.",
                "action": "pause",
                "pause": 7,
            },
            {
                "overlay": "Place Frame Body",
                "detail": "Drag a Box onto the workplane",
                "narration": "Place a Box shape for the large frame body. This will be our biggest frame yet.",
                "action": "place_body",
            },
            {
                "overlay": "Set Body Dimensions",
                "detail": "200mm × 80mm × 6mm",
                "narration": "Set width to two hundred millimeters, length to eighty, and height to six. The wider format accommodates three photos side by side.",
                "action": "set_body_dims",
                "dims": {"Width": 200, "Length": 80, "Height": 6},
            },
            {
                "overlay": "Set Body to Solid",
                "detail": "Ensure frame body is solid",
                "narration": "Confirm the body is set to Solid.",
                "action": "set_solid",
            },
            {
                "overlay": "Place First Opening (Left)",
                "detail": "First of three photo cutouts",
                "narration": "Now we place three photo openings. First, prepare the Hole mode with our set and undo trick. Then place the first opening on the left side of the frame.",
                "action": "place_hole_at",
                "offset_mm": (-57, 0),
            },
            {
                "overlay": "Set Hole Dimensions",
                "detail": "52mm × 52mm × 8mm",
                "narration": "Set all three openings to fifty two by fifty two by eight millimeters. Square openings create a clean, modern look.",
                "action": "set_hole_dims",
                "dims": {"Width": 52, "Length": 52, "Height": 8},
            },
            {
                "overlay": "Place Second Opening (Center)",
                "detail": "Center photo cutout",
                "narration": "Place the second opening at the center of the frame. Use the same set and undo trick before each placement.",
                "action": "place_hole_at",
                "offset_mm": (0, 0),
            },
            {
                "overlay": "Set Center Dimensions",
                "detail": "52mm × 52mm × 8mm",
                "narration": "Same dimensions. Fifty two by fifty two by eight.",
                "action": "set_hole_dims",
                "dims": {"Width": 52, "Length": 52, "Height": 8},
            },
            {
                "overlay": "Place Third Opening (Right)",
                "detail": "Duplicate center opening and move right",
                "narration": "Place the third opening on the right side. Three evenly spaced openings with five millimeter gaps between them.",
                "action": "duplicate_and_move",
                "offset_mm": (57, 0),
            },
            {
                "overlay": "Select All & Group",
                "detail": "Boolean subtraction creates 3 openings",
                "narration": "Select all four shapes and group. TinkerCAD subtracts all three holes from the body in one operation. You now have a professional collage frame with three perfectly spaced photo openings.",
                "action": "group",
            },
            {
                "overlay": "Inspect & Export",
                "detail": "Verify and save STL",
                "narration": "Orbit around to inspect the result. Three clean openings with consistent borders. This is your premium product. Export as STL. This collage frame prints in about two hours and sells for three to four times the material cost.",
                "action": "orbit_and_export",
            },
        ],
    },
    "3-6": {
        "title": "Custom Text Frame",
        "filename": "lesson-3-6-custom-text-frame",
        "description": "Build a frame with embossed personalized text",
        "steps": [
            {
                "overlay": "Design Planning",
                "detail": "Personalized frame: 112×87mm with raised text on bottom",
                "narration": "Let's create a personalized frame with custom embossed text. We start with our standard four by three frame, one hundred twelve by eighty seven millimeters, then add raised text on the bottom border. Personalization lets you charge two to five dollars more per frame.",
                "action": "pause",
                "pause": 7,
            },
            {
                "overlay": "Place Frame Body",
                "detail": "Standard 4×3 frame base",
                "narration": "Place the frame body. We're using our proven four by three design as the foundation.",
                "action": "place_body",
            },
            {
                "overlay": "Set Body Dimensions",
                "detail": "112mm × 87mm × 8mm",
                "narration": "Set width to one hundred twelve, length to eighty seven, and height to eight millimeters. Same proven dimensions as our standard frame.",
                "action": "set_body_dims",
                "dims": {"Width": 112, "Length": 87, "Height": 8},
            },
            {
                "overlay": "Set Body to Solid",
                "detail": "Ensure frame body is solid",
                "narration": "Confirm the body is set to Solid.",
                "action": "set_solid",
            },
            {
                "overlay": "Place Photo Opening",
                "detail": "Offset upward for wider bottom border",
                "narration": "Place the photo opening. We'll offset it upward to leave a wider bottom border for the text. This is the same approach as our Polaroid frame.",
                "action": "place_hole",
            },
            {
                "overlay": "Set as Hole",
                "detail": "Change to Hole for subtraction",
                "narration": "Set it to Hole.",
                "action": "set_hole",
            },
            {
                "overlay": "Set Opening Dimensions",
                "detail": "96mm × 64mm × 10mm (wider bottom border for text)",
                "narration": "Set width to ninety six, length to sixty four, and height to ten millimeters. The shorter length leaves a wider bottom border of about fifteen millimeters for our text placement.",
                "action": "set_hole_dims",
                "dims": {"Width": 96, "Length": 64, "Height": 10},
            },
            {
                "overlay": "Center the Opening",
                "detail": "Align with offset for text area",
                "narration": "Center the opening. The bottom border is intentionally wider to accommodate the embossed text we'll add next.",
                "action": "align_hole",
            },
            {
                "overlay": "Select All & Group",
                "detail": "Boolean subtraction",
                "narration": "Select all and group to create the basic frame. Now we have a frame with a wide bottom border ready for text.",
                "action": "group",
            },
            {
                "overlay": "Add Text Shape",
                "detail": "Switch to Text category, place text on frame",
                "narration": "Now for the personalization. Switch to the Text and Numbers category in the shape panel. Place a text shape on the frame. In a real workflow, you'd type the customer's name or date. For our demo, we'll use the default text. Position it on the wide bottom border.",
                "action": "place_text",
            },
            {
                "overlay": "Adjust Text Dimensions",
                "detail": "Set text height for embossing",
                "narration": "Set the text shape height to about one millimeter above the frame surface. This creates a subtle raised embossed effect. Set width to fit within the bottom border area.",
                "action": "set_text_dims",
                "dims": {"Width": 80, "Length": 10, "Height": 9},
            },
            {
                "overlay": "Final Group & Export",
                "detail": "Group text with frame, export STL",
                "narration": "Select all and group one more time. The text merges with the frame body, creating a single printable piece with beautiful embossed lettering. Export as STL. This personalized frame commands premium pricing and makes an unforgettable gift.",
                "action": "group_and_export",
            },
        ],
    },
}


# ── TTS Generation ──────────────────────────────────────────────────────

def _get_lesson_wall(lesson):
    """Calculate wall thickness from lesson step dimensions."""
    body_w = hole_w = body_l = hole_l = None
    for step in lesson["steps"]:
        dims = step.get("dims", {})
        if step["action"] == "set_body_dims":
            body_w = dims.get("Width")
            body_l = dims.get("Length")
        elif step["action"] == "set_hole_dims":
            hole_w = dims.get("Width")
            hole_l = dims.get("Length")
    if body_w and hole_w:
        return int(min((body_w - hole_w) / 2, (body_l - hole_l) / 2))
    return 8  # default

def generate_tts(lesson_id: str):
    """Generate TTS audio for each step's narration."""
    lesson = LESSONS[lesson_id]
    audio_dir = OUTPUT_DIR / f"tts-{lesson_id}"
    audio_dir.mkdir(exist_ok=True)

    segments = []
    for i, step in enumerate(lesson["steps"]):
        if not step.get("narration"):
            continue
        seg_file = audio_dir / f"seg_{i:02d}.mp3"
        if seg_file.exists():
            print(f"  Segment {i} exists: {seg_file}")
        else:
            print(f"  Generating TTS for step {i}: {step['overlay']}...")
            # Use edge-tts directly
            cmd = [
                EDGE_TTS,
                "--voice", "en-US-AndrewNeural",
                "--rate=-5%",
                "--text", step["narration"],
                "--write-media", str(seg_file),
            ]
            subprocess.run(cmd, check=True, capture_output=True)
        segments.append(str(seg_file))

    # Get durations of each segment
    durations = []
    for seg in segments:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "json", seg],
            capture_output=True, text=True,
        )
        dur = json.loads(result.stdout)["format"]["duration"]
        durations.append(float(dur))
        
    print(f"  Total narration: {sum(durations):.1f}s ({len(segments)} segments)")
    
    # Concatenate all segments into one audio file
    concat_file = audio_dir / "concat.txt"
    with open(concat_file, "w") as f:
        for seg in segments:
            f.write(f"file '{seg}'\n")
    
    full_audio = OUTPUT_DIR / f"{lesson['filename']}-narration.mp3"
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(concat_file), "-c", "copy", str(full_audio),
    ], check=True, capture_output=True)
    
    print(f"  Full narration: {full_audio}")
    return full_audio, segments, durations


# ── TinkerCAD Recording ────────────────────────────────────────────────

def record_lesson(lesson_id: str):
    """Record TinkerCAD lesson with Playwright video recording."""
    lesson = LESSONS[lesson_id]
    video_dir = str(OUTPUT_DIR / f"recording-{lesson_id}")
    os.makedirs(video_dir, exist_ok=True)

    print(f"\n=== Recording Lesson {lesson_id}: {lesson['title']} ===")

    # Start browser with video recording
    p, ctx = get_persistent_context(headless=False, video_dir=video_dir)
    page = ctx.pages[0] if ctx.pages else ctx.new_page()

    # Navigate to editor
    vp = navigate_to_editor(page)
    cx, cy = vp['cx'], vp['cy']
    print(f"  Editor loaded. Viewport: ({cx}, {cy})")

    # Clear workplane
    page.keyboard.press("Control+a")
    time.sleep(0.3)
    page.keyboard.press("Delete")
    time.sleep(1)

    # Show title card
    page.evaluate(f"""() => {{
        const el = document.createElement('div');
        el.id = 'title-card';
        el.innerHTML = `
            <div style="font-size:16px; color:#818cf8; letter-spacing:3px; margin-bottom:12px">3D PRINT ACADEMY • MODULE {lesson_id.split('-')[0]}</div>
            <div style="font-size:36px; font-weight:800; color:#fff; margin-bottom:8px">{lesson['title']}</div>
            <div style="font-size:18px; color:#94a3b8">{lesson['description']}</div>
        `;
        el.style.cssText = `
            position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%);
            padding: 40px 60px; background: rgba(10, 10, 15, 0.95);
            border-radius: 16px; border: 1px solid rgba(99, 102, 241, 0.4);
            z-index: 999999; font-family: Inter, Segoe UI, sans-serif;
            text-align: center; box-shadow: 0 16px 64px rgba(0,0,0,0.6);
        `;
        document.body.appendChild(el);
        setTimeout(() => el.remove(), 5000);
    }}""")
    time.sleep(5)

    # Execute each step
    step_num = 0
    last_placed_pos = (cx, cy)  # Track where the last shape was placed
    shape_selected = False  # Track if a shape is already selected
    for step in lesson["steps"]:
        step_num += 1
        action = step["action"]
        print(f"  Step {step_num}: {step['overlay']} → action={action}")

        # Show step overlay
        show_step_overlay(page, step_num, step["overlay"], step.get("detail", ""),
                         duration=8000)
        time.sleep(1)

        if action == "pause":
            time.sleep(step.get("pause", 4))

        elif action == "place_body":
            drag_shape_to_workplane(page, "87", (cx, cy))
            page.mouse.click(cx, cy)
            last_placed_pos = (cx, cy)
            shape_selected = True
            time.sleep(1)

        elif action == "set_body_dims":
            dims = step["dims"]
            for label, value in dims.items():
                ok = set_dimension(page, label, value)
                if not ok:
                    # Fallback: click shape to re-select, retry
                    page.mouse.click(cx, cy)
                    time.sleep(0.5)
                    set_dimension(page, label, value)
                time.sleep(0.5)
            # Verify all dimensions were accepted
            for label, value in dims.items():
                actual = _read_dim_value(page, label)
                if actual is None or abs(actual - float(value)) >= 1.0:
                    print(f"  ⚠ VERIFY FAIL: {label} expected={value}, actual={actual}")
            time.sleep(1)

        elif action == "set_solid":
            state = get_material_state(page)
            if not state.get('Solid'):
                set_material(page, "Solid")
                page.mouse.click(cx, cy)
                time.sleep(0.5)
            time.sleep(1)

        elif action == "place_hole":
            # Set Hole mode via set+undo trick BEFORE placing
            page.mouse.click(cx, cy)
            time.sleep(0.3)
            set_material(page, "Hole")
            time.sleep(0.3)
            page.keyboard.press("Control+z")
            time.sleep(0.5)
            # Deselect
            page.mouse.click(200, 800)
            time.sleep(0.5)
            # Place new shape (auto-inherits Hole)
            drag_shape_to_workplane(page, "87", (cx, cy))
            page.mouse.click(cx, cy)
            last_placed_pos = (cx, cy)
            shape_selected = True
            time.sleep(1)

        elif action == "set_hole":
            # Shape was placed as Hole already. Verify.
            state = get_material_state(page)
            if not state.get('Hole'):
                set_material(page, "Hole")
                page.mouse.click(cx, cy)
                time.sleep(0.5)
            time.sleep(1)

        elif action == "set_hole_dims":
            # Click on the last-placed shape if not already selected
            if not shape_selected:
                click_x, click_y = last_placed_pos
                page.mouse.click(click_x, click_y)
                time.sleep(0.3)
            shape_selected = False
            dims = step["dims"]
            for label, value in dims.items():
                ok = set_dimension(page, label, value)
                if not ok:
                    page.mouse.click(last_placed_pos[0], last_placed_pos[1])
                    time.sleep(0.5)
                    set_dimension(page, label, value)
                time.sleep(0.5)
            # Debug: verify dims were set
            dims_after = read_dimensions(page)
            mat_state = get_material_state(page)
            print(f"    → set_hole_dims: dims={dims_after}, material={mat_state}")
            time.sleep(1)

        elif action == "align_hole":
            # Fix Y alignment: nudge = min(8, wall)
            wall = step.get("wall", _get_lesson_wall(lesson))
            nudge = min(8, wall)
            page.mouse.click(cx, cy)
            time.sleep(0.3)
            for _ in range(nudge):
                page.keyboard.press("ArrowUp")
                time.sleep(0.15)
            time.sleep(1)

        elif action == "align_and_group":
            # Align + group in one step
            wall = step.get("wall", _get_lesson_wall(lesson))
            nudge = min(8, wall)
            page.mouse.click(cx, cy)
            time.sleep(0.3)
            for _ in range(nudge):
                page.keyboard.press("ArrowUp")
                time.sleep(0.15)
            time.sleep(0.5)
            page.keyboard.press("Control+a")
            time.sleep(1)
            page.keyboard.press("Control+g")
            time.sleep(3)
            page.mouse.click(cx, cy)
            time.sleep(1)

        elif action == "group":
            page.keyboard.press("Control+a")
            time.sleep(1)
            page.keyboard.press("Control+g")
            time.sleep(3)
            page.mouse.click(cx, cy)
            time.sleep(1)

        elif action == "orbit_inspect":
            orbit_view(page, dx=300, dy=150)
            time.sleep(2)
            orbit_view(page, dx=-200, dy=-100)
            time.sleep(2)

        elif action == "export":
            export_stl_download(page, f"/tmp/lesson_{lesson_id}_frame.stl")
            time.sleep(2)

        elif action == "orbit_and_export":
            orbit_view(page, dx=300, dy=150)
            time.sleep(2)
            orbit_view(page, dx=-200, dy=-100)
            time.sleep(1)
            export_stl_download(page, f"/tmp/lesson_{lesson_id}_frame.stl")
            time.sleep(2)

        elif action == "place_hole_at":
            # Place a hole then move it to exact mm position using arrow keys.
            # Drop each hole at the center of the workplane (cx, cy) since
            # arrow keys provide absolute mm movement from there.
            # The shape is auto-selected after drag (no click needed).
            offset_mm = step.get("offset_mm", (0, 0))
            dx_mm, dy_mm = offset_mm
            # Deselect everything first
            page.mouse.click(200, 800)
            time.sleep(0.5)
            # Drop at center — TinkerCAD creates new shapes even with overlaps
            drag_shape_to_workplane(page, "87", (cx, cy))
            time.sleep(1.5)
            # Set to Hole (shape is auto-selected after drag)
            set_material(page, "Hole")
            time.sleep(0.5)
            # Verify it's a Hole
            state = get_material_state(page)
            if not state.get('Hole'):
                print(f"  ⚠ Hole mode not set, retrying... state={state}")
                set_material(page, "Hole")
                time.sleep(0.5)
            # Move shape using arrow keys (1 press = 1mm in TinkerCAD)
            dx_mm, dy_mm = offset_mm
            if dx_mm != 0:
                key = "ArrowRight" if dx_mm > 0 else "ArrowLeft"
                for _ in range(abs(int(dx_mm))):
                    page.keyboard.press(key)
                    time.sleep(0.05)
                time.sleep(0.3)
            if dy_mm != 0:
                key = "ArrowUp" if dy_mm > 0 else "ArrowDown"
                for _ in range(abs(int(dy_mm))):
                    page.keyboard.press(key)
                    time.sleep(0.05)
                time.sleep(0.3)
            last_placed_pos = (cx, cy)
            shape_selected = True
            # Debug: verify shape placement
            dims_after = read_dimensions(page)
            mat_state = get_material_state(page)
            print(f"    → Placed hole at offset_mm={offset_mm}, dims={dims_after}, material={mat_state}")
            time.sleep(0.5)

        elif action == "duplicate_and_move":
            # Duplicate the currently selected shape and move the copy
            # This is more reliable than placing a new shape when shapes overlap
            offset_mm = step.get("offset_mm", (0, 0))
            dx_mm, dy_mm = offset_mm
            page.keyboard.press("Control+d")
            time.sleep(1.5)
            # The duplicate is auto-selected and placed at a ~10mm offset
            # Move it to the target position: need to go from current (near prev shape)
            # to the absolute target offset from workplane center
            # The duplicate starts near the previous shape. We need to move it
            # (target_offset - prev_offset) mm. Since prev was at 0 (center hole),
            # we move by target_offset mm from wherever the duplicate landed.
            # Use a large movement to ensure we overshoot, then fine-tune:
            if dx_mm != 0:
                key = "ArrowRight" if dx_mm > 0 else "ArrowLeft"
                for _ in range(abs(int(dx_mm))):
                    page.keyboard.press(key)
                    time.sleep(0.05)
                time.sleep(0.3)
            if dy_mm != 0:
                key = "ArrowUp" if dy_mm > 0 else "ArrowDown"
                for _ in range(abs(int(dy_mm))):
                    page.keyboard.press(key)
                    time.sleep(0.05)
                time.sleep(0.3)
            shape_selected = True
            dims_after = read_dimensions(page)
            mat_state = get_material_state(page)
            print(f"    → Duplicated+moved offset_mm={offset_mm}, dims={dims_after}, material={mat_state}")
            time.sleep(0.5)

        elif action == "place_text":
            # Switch to Text & Numbers category and place a Text shape
            from tinkercad_helper import EDITOR as ED
            cat_x, cat_y = ED["cat_text"]
            page.mouse.click(cat_x, cat_y)
            time.sleep(2)
            # Find the Text shape by communication attribute (shape type "Text")
            # TinkerCAD Text category: first item is typically the Text shape
            # Try comm attribute first, fall back to grid position
            text_shape = page.evaluate("""() => {
                // Look for shapes in the panel with text-related comm IDs
                const candidates = document.querySelectorAll('[communication]');
                for (const el of candidates) {
                    const title = el.getAttribute('title') || el.textContent || '';
                    if (title.toLowerCase().includes('text')) {
                        const r = el.getBoundingClientRect();
                        if (r.width > 20 && r.height > 20)
                            return {x: r.x + r.width/2, y: r.y + r.height/2};
                    }
                }
                // Also check shape panel thumbnails
                const thumbs = document.querySelectorAll('.shapePanelItem, .shape-panel-item, [data-shape-type]');
                for (const el of thumbs) {
                    const t = (el.getAttribute('title') || el.getAttribute('data-shape-type') || '').toLowerCase();
                    if (t.includes('text')) {
                        const r = el.getBoundingClientRect();
                        return {x: r.x + r.width/2, y: r.y + r.height/2};
                    }
                }
                return null;
            }""")
            if text_shape:
                drag_shape_to_workplane(page, (text_shape['x'], text_shape['y']),
                                       (cx, cy + 30))
            else:
                # Fallback: first shape position in text category panel
                # Row 1, Col 1 of shape panel (same grid, different category content)
                drag_shape_to_workplane(page, (1695, 276), (cx, cy + 30))
            time.sleep(2)
            # Click on the placed text shape to select it
            page.mouse.click(cx, cy + 30)
            time.sleep(1)
            # Type the text — TinkerCAD Text shape has an editable text field
            # Look for text input in the inspector
            text_input = page.evaluate("""() => {
                const inputs = document.querySelectorAll('input[type="text"], textarea, [contenteditable="true"]');
                for (const inp of inputs) {
                    const r = inp.getBoundingClientRect();
                    if (r.width > 50 && r.height > 10 && r.y > 100)
                        return {x: r.x + r.width/2, y: r.y + r.height/2};
                }
                // Check inspector for text content field
                const items = document.querySelectorAll('.editor__inspector__item');
                for (const item of items) {
                    const lbl = item.querySelector('.editor__inspector__item__label');
                    if (lbl && lbl.textContent.trim().toLowerCase() === 'text') {
                        const inp = item.querySelector('input, textarea, [contenteditable]');
                        if (inp) {
                            const r = inp.getBoundingClientRect();
                            return {x: r.x + r.width/2, y: r.y + r.height/2};
                        }
                    }
                }
                return null;
            }""")
            if text_input:
                page.mouse.click(text_input['x'], text_input['y'])
                time.sleep(0.3)
                page.keyboard.press("Control+a")
                time.sleep(0.1)
                page.keyboard.type("BABY", delay=100)
                page.keyboard.press("Enter")
                time.sleep(1)
            else:
                print("  ⚠ No text input field found — trying keyboard type directly")
                page.keyboard.type("BABY", delay=100)
                page.keyboard.press("Enter")
                time.sleep(1)
            # Switch back to basic shapes
            cat_bx, cat_by = ED["cat_basic_shapes"]
            page.mouse.click(cat_bx, cat_by)
            time.sleep(1)

        elif action == "set_text_dims":
            page.mouse.click(cx, cy + 30)
            time.sleep(0.3)
            dims = step["dims"]
            for label, value in dims.items():
                set_dimension(page, label, value)
                time.sleep(0.5)
            time.sleep(1)

        elif action == "group_and_export":
            page.keyboard.press("Control+a")
            time.sleep(1)
            page.keyboard.press("Control+g")
            time.sleep(3)
            page.mouse.click(cx, cy)
            time.sleep(1)
            orbit_view(page, dx=300, dy=150)
            time.sleep(2)
            orbit_view(page, dx=-200, dy=-100)
            time.sleep(1)
            export_stl_download(page, f"/tmp/lesson_{lesson_id}_frame.stl")
            time.sleep(2)

        else:
            print(f"  ⚠️ Unknown action: {action}")
            time.sleep(2)

    # End card
    page.evaluate(f"""() => {{
        const el = document.createElement('div');
        el.innerHTML = `
            <div style="font-size:32px; font-weight:800; color:#fff; margin-bottom:12px">Frame Complete! ✓</div>
            <div style="font-size:18px; color:#94a3b8">Your {lesson['title']} is ready for 3D printing</div>
        `;
        el.style.cssText = `
            position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%);
            padding: 40px 60px; background: rgba(10, 10, 15, 0.95);
            border-radius: 16px; border: 1px solid rgba(34, 197, 94, 0.4);
            z-index: 999999; font-family: Inter, Segoe UI, sans-serif;
            text-align: center; box-shadow: 0 16px 64px rgba(0,0,0,0.6);
        `;
        document.body.appendChild(el);
    }}""")
    time.sleep(4)

    # Close context to finalize video
    ctx.close()
    p.stop()

    # Find recorded video file (most recently modified)
    video_files = sorted(Path(video_dir).glob("*.webm"), key=lambda f: f.stat().st_mtime)
    if video_files:
        raw_video = video_files[-1]
        print(f"  Raw recording: {raw_video} ({raw_video.stat().st_size / 1024 / 1024:.1f}MB)")
        return str(raw_video)
    else:
        print("  ⚠️ No video file found!")
        return None


# ── Merge Video + Audio ─────────────────────────────────────────────────

def merge_video_audio(lesson_id: str, video_path: str, audio_path: str):
    """Merge recorded video with TTS narration using ffmpeg."""
    lesson = LESSONS[lesson_id]
    output = OUTPUT_DIR / f"{lesson['filename']}.mp4"

    print(f"\n=== Merging video + audio ===")
    print(f"  Video: {video_path}")
    print(f"  Audio: {audio_path}")

    # Get durations
    def get_duration(path):
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "json", path],
            capture_output=True, text=True,
        )
        dur = json.loads(r.stdout).get("format", {}).get("duration")
        if dur and dur != "N/A":
            return float(dur)
        # Fallback: count frames for webm with missing duration
        r2 = subprocess.run(
            ["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
             "-show_entries", "stream=nb_read_frames,r_frame_rate",
             "-of", "json", path],
            capture_output=True, text=True,
        )
        stream = json.loads(r2.stdout).get("streams", [{}])[0]
        frames = int(stream.get("nb_read_frames", 0))
        fps_str = stream.get("r_frame_rate", "25/1")
        num, den = map(int, fps_str.split("/"))
        fps = num / den if den else 25
        return frames / fps if frames else 0

    vid_dur = get_duration(video_path)
    aud_dur = get_duration(audio_path)
    print(f"  Video: {vid_dur:.1f}s, Audio: {aud_dur:.1f}s")

    # Speed adjust video to match audio duration
    speed = vid_dur / aud_dur if aud_dur > 0 else 1.0
    print(f"  Speed factor: {speed:.2f}x")

    # ffmpeg: merge with speed adjustment
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-i", audio_path,
        "-filter:v", f"setpts={1/speed}*PTS",
        "-map", "0:v", "-map", "1:a",
        "-c:v", "libx264", "-preset", "medium", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        "-shortest",
        str(output),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    print(f"  ✅ Output: {output} ({output.stat().st_size / 1024 / 1024:.1f}MB)")
    return str(output)


# ── Main ────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Record TinkerCAD lesson videos")
    parser.add_argument("--lesson", required=True, help="Lesson ID (e.g., 2-2)")
    parser.add_argument("--tts-only", action="store_true", help="Only generate TTS")
    parser.add_argument("--record-only", action="store_true", help="Only record video")
    parser.add_argument("--merge-only", action="store_true", help="Only merge existing files")
    parser.add_argument("--list", action="store_true", help="List available lessons")
    args = parser.parse_args()

    if args.list:
        for lid, lesson in LESSONS.items():
            print(f"  {lid}: {lesson['title']} ({len(lesson['steps'])} steps)")
        return

    if args.lesson not in LESSONS:
        print(f"Unknown lesson: {args.lesson}. Available: {list(LESSONS.keys())}")
        return

    lesson = LESSONS[args.lesson]

    if args.tts_only:
        generate_tts(args.lesson)
        return

    if args.merge_only:
        video_dir = OUTPUT_DIR / f"recording-{args.lesson}"
        videos = sorted(video_dir.glob("*.webm"), key=lambda f: f.stat().st_mtime)
        audio = OUTPUT_DIR / f"{lesson['filename']}-narration.mp3"
        if videos and audio.exists():
            merge_video_audio(args.lesson, str(videos[-1]), str(audio))
        else:
            print(f"Missing files. Video: {videos}, Audio: {audio.exists()}")
        return

    # Full pipeline: TTS → Record → Merge
    print(f"=== Full Pipeline: Lesson {args.lesson} ===")
    print(f"  Title: {lesson['title']}")
    print(f"  Steps: {len(lesson['steps'])}")

    # Step 1: TTS
    audio_path, segments, durations = generate_tts(args.lesson)

    if args.record_only:
        record_lesson(args.lesson)
        return

    # Step 2: Record
    video_path = record_lesson(args.lesson)

    # Step 3: Merge
    if video_path and audio_path:
        merge_video_audio(args.lesson, video_path, str(audio_path))
    
    print(f"\n=== Pipeline Complete ===")


if __name__ == "__main__":
    main()
