#!/usr/bin/env python3
"""Record slide-based lesson video from screenplay JSON using Playwright."""
import json
import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

OUTPUT_DIR = Path.home() / "video-uploads"
EDGE_TTS = str(Path(__file__).parent.parent.parent / ".venv" / "bin" / "edge-tts")

# Narration per slide (matched to screenplay sections)
NARRATIONS = {
    "Title card": "Welcome to Module six, Lesson three. Shopify Store Setup. In this lesson, we'll walk through building a professional online store for your three D printed magnet frame business.",
    "Why Shopify benefits": "Why Shopify? First, your store operates twenty four seven generating sales while you sleep. Shopify Payments eliminates per-transaction fees. It handles shipping labels, inventory tracking, and tax calculations. The free Dawn theme gives you a professional appearance that builds customer trust.",
    "Account and theme setup steps": "Step one: account and theme setup. Sign up at shopify dot com with the free trial. Choose a brand name like Frame Craft Studio or Magnet Memories Co. Select the free Dawn theme, it's fast, clean, and professional. Customize your colors, upload your logo, and use fonts like Montserrat. The Dawn theme lets your product photography shine, so keep backgrounds neutral.",
    "Product listing best practices": "Step two: create your product listings. Each frame style gets its own listing with a keyword-rich title. For example, Retro TV Magnet Photo Frame, Vintage Avocado Green, Fits three by four photos. Write engaging descriptions highlighting it's handmade, the material, and that magnets are included. Use Shopify's variant system for color options, keeping your catalog clean and organized.",
    "Product photography tips": "Step three: product photography. Upload four to five photos per listing. A hero shot on white, an angle view showing depth, a lifestyle shot on a fridge with a photo inside, a detail closeup, and a size reference in someone's hand. High quality photography is the number one factor in online sales conversion. Natural window light and a smartphone in portrait mode give you professional results.",
    "Shipping configuration": "Step four: shipping configuration. Use USPS First Class for magnet frames, typically four to six dollars. Offer flat rate shipping at four ninety-nine or free shipping over twenty five dollars. The free shipping threshold encourages customers to add a second frame. Use Pirate Ship for discounted shipping labels.",
    "Payment and checkout setup": "Step five: payments and checkout. Enable Shopify Payments for all major credit cards with no per-transaction fee. Add PayPal and Shop Pay for more conversion options. The most important feature: turn on abandoned checkout recovery. It automatically emails customers who add to cart but don't complete their purchase, recovering five to fifteen percent of lost sales.",
    "Summary checklist": "Here's your complete Shopify setup checklist. Free Dawn theme customized with your brand. Four to five professional photos per listing. Keyword-rich titles and compelling descriptions. Collections for browsing. Flat rate shipping plus free over twenty five. Multiple payment methods enabled. And abandoned checkout recovery turned on. Your online store now works around the clock to grow your business.",
    "End card": "Congratulations! Your Shopify store is ready to sell magnet frames online. In the next lesson, we'll cover marketing strategies to drive traffic to your new store.",
}


def generate_narrations():
    """Generate TTS for each slide narration."""
    audio_dir = OUTPUT_DIR / "tts-6-3"
    audio_dir.mkdir(exist_ok=True)
    segments = []
    durations = []
    
    for i, (desc, text) in enumerate(NARRATIONS.items()):
        seg_file = audio_dir / f"seg_{i:02d}.mp3"
        if not seg_file.exists():
            print(f"  Generating TTS for: {desc}")
            cmd = [EDGE_TTS, "--voice", "en-US-AndrewNeural", "--rate=-5%",
                   "--text", text, "--write-media", str(seg_file)]
            subprocess.run(cmd, check=True, capture_output=True)
        segments.append(str(seg_file))
        
        # Get duration
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                           "-of", "json", str(seg_file)], capture_output=True, text=True)
        dur = float(json.loads(r.stdout)["format"]["duration"])
        durations.append(dur)
    
    # Concatenate
    concat_file = audio_dir / "concat.txt"
    with open(concat_file, "w") as f:
        for seg in segments:
            f.write(f"file '{seg}'\n")
    
    full_audio = OUTPUT_DIR / "lesson-6-3-shopify-store-narration.mp3"
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0",
                    "-i", str(concat_file), "-c", "copy", str(full_audio)],
                   check=True, capture_output=True)
    
    print(f"  Total narration: {sum(durations):.1f}s ({len(segments)} segments)")
    return str(full_audio), durations


def record_slides():
    """Record the slide-based video using Playwright."""
    screenplay_path = Path(__file__).parent / "screenplays" / "lesson_6_3.json"
    with open(screenplay_path) as f:
        screenplay = json.load(f)
    
    video_dir = str(OUTPUT_DIR / "recording-6-3")
    Path(video_dir).mkdir(exist_ok=True)
    
    print("\n=== Recording slide video for Lesson 6-3 ===")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            record_video_dir=video_dir,
            record_video_size={"width": 1920, "height": 1080},
        )
        page = ctx.new_page()
        page.goto("about:blank")
        time.sleep(1)
        
        for action in screenplay["actions"]:
            desc = action.get("description", action.get("type"))
            print(f"  Slide: {desc}")
            
            if action["type"] == "eval":
                page.evaluate(action["script"])
            elif action["type"] == "navigate":
                page.goto(action["url"], wait_until="networkidle", timeout=30000)
            elif action["type"] == "wait":
                time.sleep(action.get("seconds", 2))
            
            pause = action.get("pause", 3)
            time.sleep(pause)
        
        ctx.close()
        browser.close()
    
    videos = sorted(Path(video_dir).glob("*.webm"))
    if videos:
        raw = videos[-1]
        print(f"  Raw recording: {raw} ({raw.stat().st_size / 1024 / 1024:.1f}MB)")
        return str(raw)
    return None


def merge(video_path, audio_path):
    """Merge video + audio with speed adjustment."""
    output = OUTPUT_DIR / "Shopify-Store-Setup.mp4"
    
    # Get durations
    def get_dur(path):
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                           "-of", "json", path], capture_output=True, text=True)
        d = json.loads(r.stdout).get("format", {}).get("duration")
        return float(d) if d and d != "N/A" else 0
    
    vid_dur = get_dur(video_path)
    aud_dur = get_dur(audio_path)
    speed = vid_dur / aud_dur if aud_dur > 0 else 1.0
    
    print(f"\n=== Merging ===")
    print(f"  Video: {vid_dur:.1f}s, Audio: {aud_dur:.1f}s, Speed: {speed:.2f}x")
    
    cmd = ["ffmpeg", "-y", "-i", video_path, "-i", audio_path,
           "-filter:v", f"setpts={1/speed}*PTS",
           "-map", "0:v", "-map", "1:a",
           "-c:v", "libx264", "-preset", "medium", "-crf", "23",
           "-c:a", "aac", "-b:a", "128k", "-shortest", str(output)]
    subprocess.run(cmd, check=True, capture_output=True)
    print(f"  Output: {output} ({output.stat().st_size / 1024 / 1024:.1f}MB)")
    return str(output)


if __name__ == "__main__":
    print("=== Lesson 6-3: Shopify Store Setup ===")
    audio_path, durations = generate_narrations()
    video_path = record_slides()
    if video_path:
        merge(video_path, audio_path)
    else:
        print("ERROR: No video recorded")
        sys.exit(1)
