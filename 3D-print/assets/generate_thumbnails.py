#!/usr/bin/env python3
"""Generate 43 engineering-themed lesson thumbnails for 3D Print Academy.

Creates dark, technical thumbnails with:
- Blueprint grid backgrounds
- Module-specific accent colors and iconography
- Lesson number + title typography overlay
- Consistent "Engineering Precision" aesthetic

Usage: python3 generate_thumbnails.py
Output: thumbnails/ directory + index.json
"""

import json
import math
import os
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageFilter

# ── Config ──────────────────────────────────────────────────────────────────
W, H = 1280, 720
OUT_DIR = Path(__file__).parent / "thumbnails"
OUT_DIR.mkdir(parents=True, exist_ok=True)

FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

BG_COLOR = (10, 10, 15)       # #0A0A0F
GRID_COLOR = (20, 30, 40)     # subtle grid

# Module accent colors
MODULE_ACCENTS = {
    1: ((0, 212, 255), "Setup & Fundamentals"),        # cyan
    2: ((57, 255, 20), "CAD Design Basics"),            # green
    3: ((255, 100, 50), "Advanced Frame Designs"),      # orange
    4: ((180, 80, 255), "Print Optimization"),          # purple
    5: ((255, 200, 50), "Post-Processing"),             # gold
    6: ((255, 60, 100), "Launch Your Business"),        # pink-red
}

# All 43 lessons
LESSONS = [
    # Module 1
    ("1.1", "Printer Anatomy — Know Your Machine"),
    ("1.2", "Bed Leveling — Foundation of Good Prints"),
    ("1.3", "Filament Types — PLA, PLA+, and PETG"),
    ("1.4", "Slicer Setup — Cura"),
    ("1.5", "Slicer Setup — PrusaSlicer"),
    ("1.6", "Your First Test Print"),
    ("1.7", "Module 1 Recap"),
    # Module 2
    ("2.1", "TinkerCAD Introduction & Interface"),
    ("2.2", "Design Your First Magnet Frame"),
    ("2.3", "Fusion 360 Introduction & Interface"),
    ("2.4", "Magnet Slot Tolerances & Photo Sizing"),
    ("2.5", "Snap-Fit Clip Design"),
    ("2.6", "Export STL & Test Slice"),
    ("2.7", "Module 2 Recap"),
    # Module 3
    ("3.1", "Multi-Piece Magnetic Assemblies"),
    ("3.2", "Retro TV Frame Design"),
    ("3.3", "Polaroid-Style Frame"),
    ("3.4", "Instax Mini Frame"),
    ("3.5", "Multi-Photo Collage Frame"),
    ("3.6", "Custom Text Inserts"),
    ("3.7", "Quality Showcase & Review"),
    # Module 4
    ("4.1", "Layer Height Comparison"),
    ("4.2", "Infill Patterns & Strength"),
    ("4.3", "Speed vs Quality Tuning"),
    ("4.4", "Temperature Tower Test"),
    ("4.5", "Fix Stringing"),
    ("4.6", "Fix Warping"),
    ("4.7", "Fix Elephant's Foot"),
    ("4.8", "Batch Printing for Production"),
    # Module 5
    ("5.1", "Sanding Technique — Grit Progression"),
    ("5.2", "Priming with Filler Primer"),
    ("5.3", "Spray Painting Technique"),
    ("5.4", "Clear Coating for Durability"),
    ("5.5", "Magnet Install — Mid-Print Pause"),
    ("5.6", "Magnet Install — Post-Glue"),
    ("5.7", "Quality Control Checklist"),
    # Module 6
    ("6.1", "Cost Per Unit Breakdown"),
    ("6.2", "Pricing Strategy ($5–$15 Retail)"),
    ("6.3", "Shopify Store Setup"),
    ("6.4", "Craft Fair Strategy"),
    ("6.5", "Product Photography"),
    ("6.6", "Packaging & Shipping"),
    ("6.7", "Scaling: Hobby → Income"),
]


def get_module(lesson_id: str) -> int:
    return int(lesson_id.split(".")[0])


def draw_grid(draw: ImageDraw.Draw, accent: tuple, seed: int):
    """Draw a subtle blueprint grid with occasional highlight lines."""
    rng = random.Random(seed)
    # Main grid
    spacing = 40
    for x in range(0, W, spacing):
        c = GRID_COLOR if rng.random() > 0.15 else tuple(min(v + 15, 255) for v in GRID_COLOR)
        draw.line([(x, 0), (x, H)], fill=c, width=1)
    for y in range(0, H, spacing):
        c = GRID_COLOR if rng.random() > 0.15 else tuple(min(v + 15, 255) for v in GRID_COLOR)
        draw.line([(0, y), (W, y)], fill=c, width=1)
    
    # Accent crosshairs (2-3 random)
    for _ in range(rng.randint(2, 3)):
        cx, cy = rng.randint(200, W - 200), rng.randint(100, H - 200)
        a = tuple(list(accent) + [30])
        draw.line([(cx - 30, cy), (cx + 30, cy)], fill=accent[:3], width=1)
        draw.line([(cx, cy - 30), (cx, cy + 30)], fill=accent[:3], width=1)
        draw.ellipse([(cx - 15, cy - 15), (cx + 15, cy + 15)], outline=accent[:3], width=1)


def draw_decorative_elements(draw: ImageDraw.Draw, img: Image.Image, accent: tuple, module: int, seed: int):
    """Draw module-specific decorative elements."""
    rng = random.Random(seed + 100)
    ar, ag, ab = accent[:3]
    dim = (ar // 4, ag // 4, ab // 4)  # dimmed accent
    
    # Corner brackets (all modules)
    blen = 60
    bw = 2
    # Top-right
    draw.line([(W - 20, 20), (W - 20, 20 + blen)], fill=accent[:3], width=bw)
    draw.line([(W - 20, 20), (W - 20 - blen, 20)], fill=accent[:3], width=bw)
    # Bottom-left
    draw.line([(20, H - 20), (20, H - 20 - blen)], fill=accent[:3], width=bw)
    draw.line([(20, H - 20), (20 + blen, H - 20)], fill=accent[:3], width=bw)
    
    # Module-specific shapes
    if module == 1:  # Setup: printer silhouette shapes
        # Simplified printer outline (right side)
        px, py = W - 250, 150
        draw.rectangle([(px, py), (px + 120, py + 140)], outline=dim, width=1)
        draw.rectangle([(px + 10, py - 20), (px + 110, py)], outline=dim, width=1)
        draw.line([(px + 60, py - 20), (px + 60, py - 50)], fill=dim, width=1)  # extruder rod
        # Bed lines
        for i in range(5):
            y = py + 100 + i * 8
            draw.line([(px + 15, y), (px + 105, y)], fill=dim, width=1)
    
    elif module == 2:  # CAD: geometric shapes, wireframe cube
        cx, cy = W - 220, 180
        s = 70
        # Wireframe cube
        pts_front = [(cx, cy), (cx + s, cy), (cx + s, cy + s), (cx, cy + s)]
        off = 25
        pts_back = [(p[0] + off, p[1] - off) for p in pts_front]
        for i in range(4):
            draw.line([pts_front[i], pts_front[(i + 1) % 4]], fill=dim, width=1)
            draw.line([pts_back[i], pts_back[(i + 1) % 4]], fill=dim, width=1)
            draw.line([pts_front[i], pts_back[i]], fill=dim, width=1)
    
    elif module == 3:  # Advanced: frame outlines
        fx, fy = W - 260, 130
        draw.rectangle([(fx, fy), (fx + 140, fy + 100)], outline=dim, width=2)
        draw.rectangle([(fx + 15, fy + 15), (fx + 125, fy + 85)], outline=dim, width=1)
        # Magnet dots
        for mx, my in [(fx + 10, fy + 50), (fx + 130, fy + 50), (fx + 70, fy + 10), (fx + 70, fy + 90)]:
            draw.ellipse([(mx - 4, my - 4), (mx + 4, my + 4)], fill=dim)
    
    elif module == 4:  # Optimization: chart/graph lines
        gx, gy = W - 280, 120
        draw.line([(gx, gy + 120), (gx + 160, gy + 120)], fill=dim, width=1)  # x-axis
        draw.line([(gx, gy), (gx, gy + 120)], fill=dim, width=1)  # y-axis
        # Curve
        pts = []
        for i in range(20):
            x = gx + i * 8
            y = gy + 120 - int(80 * (1 - math.exp(-i / 5)))
            pts.append((x, y))
        if len(pts) > 1:
            draw.line(pts, fill=accent[:3], width=2)
    
    elif module == 5:  # Post-processing: sandpaper/spray pattern
        for _ in range(40):
            x = rng.randint(W - 300, W - 100)
            y = rng.randint(100, 300)
            r = rng.randint(1, 3)
            draw.ellipse([(x - r, y - r), (x + r, y + r)], fill=dim)
    
    elif module == 6:  # Business: dollar signs, chart bars
        bx, by = W - 260, 140
        bar_widths = [30, 50, 45, 65, 80]
        for i, bw_val in enumerate(bar_widths):
            x = bx + i * 35
            draw.rectangle([(x, by + 100 - bw_val), (x + 25, by + 100)], outline=dim, width=1)

    # Horizontal accent line across middle-right
    line_y = rng.randint(H // 3, 2 * H // 3)
    draw.line([(W // 2 + 100, line_y), (W - 40, line_y)], fill=dim, width=1)
    # Small dots along line
    for dx in range(0, W // 2 - 140, 30):
        x = W // 2 + 100 + dx
        draw.ellipse([(x - 1, line_y - 1), (x + 1, line_y + 1)], fill=accent[:3])


def draw_gradient_overlay(img: Image.Image):
    """Add dark gradient at bottom for text readability."""
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    for y in range(H // 2, H):
        alpha = int(200 * (y - H // 2) / (H // 2))
        draw.line([(0, y), (W, y)], fill=(0, 0, 0, alpha))
    img.paste(Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB"))


def draw_typography(draw: ImageDraw.Draw, lesson_id: str, title: str, accent: tuple, module_name: str):
    """Add lesson number and title text."""
    # Lesson number - large, top-left
    font_num = ImageFont.truetype(FONT_BOLD, 80)
    font_title = ImageFont.truetype(FONT_BOLD, 34)
    font_module = ImageFont.truetype(FONT_REG, 18)
    
    # Cyan glow effect for lesson number (draw multiple offset copies)
    num_text = lesson_id
    nx, ny = 50, 40
    for ox, oy in [(-2, 0), (2, 0), (0, -2), (0, 2), (-1, -1), (1, 1)]:
        draw.text((nx + ox, ny + oy), num_text, fill=accent[:3], font=font_num)
    draw.text((nx, ny), num_text, fill=(255, 255, 255), font=font_num)
    
    # Accent underline below number
    bbox = font_num.getbbox(num_text)
    num_w = bbox[2] - bbox[0]
    draw.line([(nx, ny + 85), (nx + num_w + 20, ny + 85)], fill=accent[:3], width=3)
    
    # Module name - small, below number
    draw.text((nx + 5, ny + 95), f"MODULE {lesson_id[0]} — {module_name}", fill=(150, 150, 160), font=font_module)
    
    # Title - bottom center area
    # Word wrap if needed
    max_title_w = W - 120
    words = title.split()
    lines = []
    current = ""
    for word in words:
        test = f"{current} {word}".strip()
        if font_title.getbbox(test)[2] > max_title_w:
            lines.append(current)
            current = word
        else:
            current = test
    if current:
        lines.append(current)
    
    ty = H - 60 - len(lines) * 44
    for line in lines:
        bbox = font_title.getbbox(line)
        lw = bbox[2] - bbox[0]
        tx = (W - lw) // 2
        # Shadow
        draw.text((tx + 2, ty + 2), line, fill=(0, 0, 0), font=font_title)
        draw.text((tx, ty), line, fill=(255, 255, 255), font=font_title)
        ty += 44


def generate_thumbnail(lesson_id: str, title: str) -> str:
    """Generate a single thumbnail and return the output filename."""
    module = get_module(lesson_id)
    accent, module_name = MODULE_ACCENTS[module]
    seed = hash(lesson_id) & 0xFFFFFFFF
    
    # Create base image
    img = Image.new("RGB", (W, H), BG_COLOR)
    draw = ImageDraw.Draw(img)
    
    # Layer 1: Blueprint grid
    draw_grid(draw, accent, seed)
    
    # Layer 2: Decorative elements
    draw_decorative_elements(draw, img, accent, module, seed)
    
    # Layer 3: Gradient overlay
    draw_gradient_overlay(img)
    
    # Redraw on final composited image
    draw = ImageDraw.Draw(img)
    
    # Layer 4: Typography
    draw_typography(draw, lesson_id, title, accent, module_name)
    
    # Save
    fname = f"lesson-{lesson_id.replace('.', '-')}.jpg"
    out_path = OUT_DIR / fname
    img.save(out_path, "JPEG", quality=92)
    return fname


def main():
    index = {}
    for lesson_id, title in LESSONS:
        fname = generate_thumbnail(lesson_id, title)
        index[lesson_id] = fname
        print(f"  ✅ {fname}")
    
    # Write index.json
    index_path = OUT_DIR / "index.json"
    with open(index_path, "w") as f:
        json.dump(index, f, indent=2)
    print(f"\n📋 Index written to {index_path}")
    print(f"🎯 Generated {len(LESSONS)} thumbnails in {OUT_DIR}")


if __name__ == "__main__":
    main()
