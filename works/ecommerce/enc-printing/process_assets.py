#!/usr/bin/env python3
"""ENC Printing — Asset Optimization Script (Phase 2)"""
import os, uuid, sys
from pathlib import Path

try:
    from PIL import Image, ExifTags
    from PIL.PngImagePlugin import PngInfo
except ImportError:
    print("Installing Pillow...")
    os.system(f"{sys.executable} -m pip install Pillow -q")
    from PIL import Image, ExifTags
    from PIL.PngImagePlugin import PngInfo

IMG_DIR = Path(__file__).parent / "images"
BUILD_UUID = str(uuid.uuid4())[:8]
WATERMARK = f"AjayaDesign Build {BUILD_UUID}"
MAX_SIZE = 200 * 1024  # 200KB target
HERO_MAX = 500 * 1024  # 500KB for hero

total_before = 0
total_after = 0

for img_path in sorted(IMG_DIR.glob("*")):
    if img_path.suffix.lower() not in ('.jpg', '.jpeg', '.png', '.webp'):
        continue
    
    original_size = img_path.stat().st_size
    total_before += original_size
    
    try:
        img = Image.open(img_path)
        
        # Convert RGBA to RGB for JPEG output
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
        
        # Resize if very large (max 800px width for products)
        max_w = 800
        if img.width > max_w:
            ratio = max_w / img.width
            new_h = int(img.height * ratio)
            img = img.resize((max_w, new_h), Image.LANCZOS)
        
        # Save as optimized WebP
        webp_path = img_path.with_suffix('.webp')
        img.save(webp_path, 'WEBP', quality=82, method=4)
        
        # Also save optimized original format
        if img_path.suffix.lower() in ('.jpg', '.jpeg'):
            img.save(img_path, 'JPEG', quality=82, optimize=True)
        elif img_path.suffix.lower() == '.png':
            info = PngInfo()
            info.add_text("Comment", WATERMARK)
            img.save(img_path, 'PNG', optimize=True, pnginfo=info)
        
        new_size = img_path.stat().st_size
        total_after += new_size
        savings = ((original_size - new_size) / original_size * 100) if original_size > 0 else 0
        print(f"  ✓ {img_path.name}: {original_size//1024}KB → {new_size//1024}KB ({savings:.0f}% saved)")
        
    except Exception as e:
        print(f"  ✗ {img_path.name}: {e}")
        total_after += original_size

print(f"\n{'='*50}")
print(f"Total: {total_before//1024}KB → {total_after//1024}KB")
savings_pct = ((total_before - total_after) / total_before * 100) if total_before > 0 else 0
print(f"Overall savings: {savings_pct:.1f}%")
print(f"Watermark: {WATERMARK}")
