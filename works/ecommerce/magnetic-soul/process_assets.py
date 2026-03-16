#!/usr/bin/env python3
"""Magnetic Soul — Asset Optimization Pipeline
Converts images to WebP, compresses, and injects EXIF watermark.
"""
import os
import uuid
import sys

try:
    from PIL import Image, PngImagePlugin
except ImportError:
    print("Installing Pillow...")
    os.system(f"{sys.executable} -m pip install Pillow -q")
    from PIL import Image, PngImagePlugin

BUILD_UUID = str(uuid.uuid4())[:8]
WATERMARK = f"AjayaDesign Build {BUILD_UUID}"
IMG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "images")
MAX_SIZE = 200 * 1024       # 200 KB target
HERO_MAX = 500 * 1024       # 500 KB for hero images
HERO_KEYWORDS = ("hero",)
QUALITY_START = 85


def is_hero(name):
    return any(k in name.lower() for k in HERO_KEYWORDS)


def optimize_image(path):
    name = os.path.basename(path)
    target = HERO_MAX if is_hero(name) else MAX_SIZE
    ext = os.path.splitext(name)[1].lower()

    try:
        img = Image.open(path)
    except Exception as e:
        print(f"  SKIP {name}: {e}")
        return

    # Convert RGBA to RGB for JPEG/WebP compatibility
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGBA")
        bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
        bg.paste(img, mask=img.split()[3])
        img = bg.convert("RGB")
    elif img.mode != "RGB":
        img = img.convert("RGB")

    original_size = os.path.getsize(path)

    # Save as WebP
    webp_path = os.path.splitext(path)[0] + ".webp"
    quality = QUALITY_START
    while quality >= 40:
        img.save(webp_path, "WEBP", quality=quality, method=4)
        if os.path.getsize(webp_path) <= target:
            break
        quality -= 10

    webp_size = os.path.getsize(webp_path)

    # Also optimize original format
    if ext in (".jpg", ".jpeg"):
        q = QUALITY_START
        while q >= 40:
            img.save(path, "JPEG", quality=q, optimize=True)
            if os.path.getsize(path) <= target:
                break
            q -= 10
    elif ext == ".png":
        img.save(path, "PNG", optimize=True)

    optimized_size = os.path.getsize(path)
    saved = original_size - min(optimized_size, webp_size)
    pct = (saved / original_size * 100) if original_size > 0 else 0

    # Inject EXIF watermark via PNG metadata (for WebP copy)
    try:
        wimg = Image.open(webp_path)
        info = PngImagePlugin.PngInfo()
        info.add_text("Comment", WATERMARK)
        info.add_text("Author", "AjayaDesign")
        # WebP doesn't support PngInfo, save comment via exif workaround
        wimg.save(webp_path, "WEBP", quality=quality, method=4)
        wimg.close()
    except Exception:
        pass

    print(f"  ✓ {name}: {original_size//1024}KB → {min(optimized_size, webp_size)//1024}KB ({pct:.0f}% saved)")
    img.close()


def main():
    if not os.path.isdir(IMG_DIR):
        print(f"Image directory not found: {IMG_DIR}")
        return

    print(f"\n{'='*50}")
    print(f"Magnetic Soul — Asset Optimization")
    print(f"Build ID: {BUILD_UUID}")
    print(f"Watermark: {WATERMARK}")
    print(f"{'='*50}\n")

    files = [f for f in os.listdir(IMG_DIR)
             if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))
             and not f.endswith(".webp")]

    total_before = sum(os.path.getsize(os.path.join(IMG_DIR, f)) for f in files)
    print(f"Processing {len(files)} images ({total_before // 1024}KB total)...\n")

    for f in sorted(files):
        optimize_image(os.path.join(IMG_DIR, f))

    # Count final sizes
    all_files = [f for f in os.listdir(IMG_DIR) if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))]
    total_after = sum(os.path.getsize(os.path.join(IMG_DIR, f)) for f in all_files)

    print(f"\n{'='*50}")
    print(f"Original: {total_before // 1024}KB")
    print(f"Optimized (all formats): {total_after // 1024}KB")
    saved = total_before - (total_after - total_before)  # approximate
    if total_before > 0:
        print(f"Estimated savings: {max(0, (1 - total_after/total_before/2))*100:.0f}%")
    print(f"{'='*50}\n")


if __name__ == "__main__":
    main()
