#!/usr/bin/env python3
"""
Video Pipeline — Master script for generating lesson videos.

Orchestrates: TTS narration (edge-tts) → Screen recording (Playwright) → Merge (ffmpeg)

Usage:
    # Full pipeline for a lesson
    python video_pipeline.py --lesson 2-2

    # TTS only (generates narration audio)
    python video_pipeline.py --lesson 2-2 --tts-only

    # Record only (records screen from screenplay)
    python video_pipeline.py --lesson 2-2 --record-only

    # Merge existing audio + video
    python video_pipeline.py --merge --audio narration.mp3 --video recording.webm --output final.mp4

    # List lessons that need screen recording
    python video_pipeline.py --list-needed
"""

import argparse
import subprocess
import sys
import json
import shutil
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent.parent  # 3D-print/
CONTENT_DIR = BASE_DIR / "content" / "lessons"
AUTOMATION_DIR = BASE_DIR / "automation"
SCREENPLAY_DIR = AUTOMATION_DIR / "screenplays"
OUTPUT_DIR = Path.home() / "video-uploads"

PYTHON = str(Path(__file__).parent.parent.parent / ".venv" / "bin" / "python")

# ── Voice config ─────────────────────────────────────────────────────────
DEFAULT_VOICE = "en-US-AndrewNeural"
DEFAULT_RATE = "-5%"  # Slightly slower for tutorial content

# ── Lesson registry ─────────────────────────────────────────────────────
# Maps lesson IDs to their content files and metadata
LESSONS = {
    "2-1": {
        "title": "TinkerCAD Introduction & Interface",
        "content_file": "lesson-2-1-tinkercad-intro.txt",
        "needs_screen_record": True,
        "screenplay": "lesson_2_1.json",
    },
    "2-2": {
        "title": "Design Your First Magnet Frame in TinkerCAD",
        "content_file": "lesson-2-2-first-frame-tinkercad.txt",
        "needs_screen_record": True,
        "screenplay": "lesson_2_2.json",
    },
    "2-3": {
        "title": "Fusion 360 Introduction & Interface",
        "content_file": "lesson-2-3-fusion360-intro.txt",
        "needs_screen_record": True,
        "screenplay": "lesson_2_3.json",
    },
    "2-5": {
        "title": "Snap-Fit Clip Design",
        "content_file": "lesson-2-5-snap-fit-clips.txt",
        "needs_screen_record": True,
        "screenplay": "lesson_2_5.json",
    },
    "2-6": {
        "title": "Export STL & Test Slice",
        "content_file": "lesson-2-6-export-stl.txt",
        "needs_screen_record": True,
        "screenplay": "lesson_2_6.json",
    },
    "3-2": {
        "title": "Retro TV Frame Design",
        "content_file": "lesson-3-2-retro-tv-frame.txt",
        "needs_screen_record": True,
        "screenplay": "lesson_3_2.json",
    },
    "3-3": {
        "title": "Polaroid-Style Frame",
        "content_file": "lesson-3-3-polaroid-frame.txt",
        "needs_screen_record": True,
        "screenplay": "lesson_3_3.json",
    },
    "3-4": {
        "title": "Instax Mini Frame",
        "content_file": "lesson-3-4-instax-mini-frame.txt",
        "needs_screen_record": True,
        "screenplay": "lesson_3_4.json",
    },
    "3-5": {
        "title": "Multi-Photo Collage Frame",
        "content_file": "lesson-3-5-multi-photo-collage.txt",
        "needs_screen_record": True,
        "screenplay": "lesson_3_5.json",
    },
    "3-6": {
        "title": "Custom Text Inserts",
        "content_file": "lesson-3-6-custom-text-inserts.txt",
        "needs_screen_record": True,
        "screenplay": "lesson_3_6.json",
    },
    "6-3": {
        "title": "Shopify Store Setup",
        "content_file": "lesson-6-3-shopify-store.txt",
        "needs_screen_record": True,
        "screenplay": "lesson_6_3.json",
    },
}


def get_content_path(lesson_id: str) -> Path:
    """Get path to lesson content text file."""
    info = LESSONS.get(lesson_id)
    if info:
        return CONTENT_DIR / info["content_file"]
    # Fallback: guess the filename pattern
    parts = lesson_id.split("-")
    candidates = list(CONTENT_DIR.glob(f"lesson-{lesson_id}-*.txt"))
    return candidates[0] if candidates else None


def get_screenplay_path(lesson_id: str) -> Path:
    """Get path to screenplay JSON."""
    info = LESSONS.get(lesson_id)
    if info and info.get("screenplay"):
        return SCREENPLAY_DIR / info["screenplay"]
    return SCREENPLAY_DIR / f"lesson_{lesson_id.replace('-', '_')}.json"


def generate_tts(lesson_id: str, voice: str = DEFAULT_VOICE, rate: str = DEFAULT_RATE) -> Path:
    """Generate TTS narration for a lesson. Returns audio file path."""
    content_path = get_content_path(lesson_id)
    if not content_path or not content_path.exists():
        print(f"Error: Content file not found for lesson {lesson_id}")
        sys.exit(1)

    output_path = OUTPUT_DIR / f"narration-{lesson_id}.mp3"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"\n🎤 Generating TTS narration for lesson {lesson_id}")
    print(f"   Content: {content_path}")
    print(f"   Voice: {voice}")
    print(f"   Rate: {rate}")
    print(f"   Output: {output_path}")

    cmd = [
        PYTHON, str(AUTOMATION_DIR / "tts_generator.py"),
        str(content_path), str(output_path),
        "--voice", voice, f"--rate={rate}",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error generating TTS: {result.stderr}")
        sys.exit(1)
    print(result.stdout)

    return output_path


def record_screen(lesson_id: str, headless: bool = True) -> Path:
    """Record screen using Playwright screenplay. Returns video file path."""
    screenplay_path = get_screenplay_path(lesson_id)
    if not screenplay_path.exists():
        print(f"Error: Screenplay not found: {screenplay_path}")
        print(f"  Create it at: {screenplay_path}")
        sys.exit(1)

    recording_dir = OUTPUT_DIR / f"recording-{lesson_id}"
    recording_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n🎬 Recording screen for lesson {lesson_id}")
    print(f"   Screenplay: {screenplay_path}")

    cmd = [
        PYTHON, str(AUTOMATION_DIR / "screen_recorder.py"),
        "--screenplay", str(screenplay_path),
        "--output", str(recording_dir),
    ]
    if headless:
        cmd.append("--headless")

    result = subprocess.run(cmd, capture_output=True, text=True)
    print(result.stdout)
    if result.returncode != 0:
        print(f"Error recording: {result.stderr}")
        sys.exit(1)

    # Find the output webm file
    videos = list(recording_dir.glob("*.webm"))
    if not videos:
        print("Error: No video file produced")
        sys.exit(1)

    return videos[0]


def get_audio_duration(audio_path: str) -> float:
    """Get duration of audio file in seconds using ffprobe."""
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", audio_path],
        capture_output=True, text=True,
    )
    return float(result.stdout.strip())


def get_video_duration(video_path: str) -> float:
    """Get duration of video file in seconds using ffprobe."""
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", video_path],
        capture_output=True, text=True,
    )
    return float(result.stdout.strip())


def merge_audio_video(audio_path: Path, video_path: Path, output_path: Path,
                      match_duration: str = "audio") -> Path:
    """Merge audio narration with screen recording video using ffmpeg.

    match_duration: 'audio' = adjust video speed to match audio length
                    'video' = pad/trim audio to match video length
                    'longest' = use the longer of the two
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    audio_dur = get_audio_duration(str(audio_path))
    video_dur = get_video_duration(str(video_path))

    print(f"\n🔀 Merging audio + video")
    print(f"   Audio: {audio_path.name} ({audio_dur:.1f}s)")
    print(f"   Video: {video_path.name} ({video_dur:.1f}s)")
    print(f"   Strategy: match to {match_duration}")

    if match_duration == "audio" and abs(audio_dur - video_dur) > 2:
        # Speed up/slow down video to match audio duration
        speed_factor = video_dur / audio_dur
        print(f"   Video speed factor: {speed_factor:.2f}x")
        cmd = [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-i", str(audio_path),
            "-filter_complex",
            f"[0:v]setpts={1/speed_factor:.4f}*PTS[v]",
            "-map", "[v]",
            "-map", "1:a",
            "-c:v", "libx264", "-preset", "medium", "-crf", "23",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest",
            "-movflags", "+faststart",
            str(output_path),
        ]
    else:
        # Simple merge — use shortest
        cmd = [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-i", str(audio_path),
            "-c:v", "libx264", "-preset", "medium", "-crf", "23",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest",
            "-movflags", "+faststart",
            str(output_path),
        ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"ffmpeg error: {result.stderr[-500:]}")
        sys.exit(1)

    final_dur = get_video_duration(str(output_path))
    file_size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"\n✅ Output: {output_path}")
    print(f"   Duration: {final_dur:.1f}s | Size: {file_size_mb:.1f} MB")

    return output_path


def full_pipeline(lesson_id: str, voice: str = DEFAULT_VOICE, headless: bool = True):
    """Run the full pipeline: TTS → Record → Merge."""
    info = LESSONS.get(lesson_id, {"title": f"Lesson {lesson_id}"})
    title = info["title"]

    print(f"\n{'='*60}")
    print(f"  FULL PIPELINE: Lesson {lesson_id}")
    print(f"  {title}")
    print(f"{'='*60}")

    # Step 1: Generate TTS
    audio_path = generate_tts(lesson_id, voice=voice)

    # Step 2: Record screen
    video_path = record_screen(lesson_id, headless=headless)

    # Step 3: Merge
    safe_title = title.replace(" ", "-").replace("'", "").replace(",", "")
    output_path = OUTPUT_DIR / f"{safe_title}.mp4"
    merge_audio_video(audio_path, video_path, output_path)

    # Cleanup temp recording dir
    recording_dir = OUTPUT_DIR / f"recording-{lesson_id}"
    if recording_dir.exists():
        shutil.rmtree(recording_dir)

    print(f"\n{'='*60}")
    print(f"  DONE! Final video: {output_path}")
    print(f"{'='*60}\n")

    return output_path


def list_needed():
    """List all lessons that need screen-recorded videos."""
    print("\n📋 Lessons needing screen-recorded videos:\n")
    for lid, info in sorted(LESSONS.items()):
        screenplay = get_screenplay_path(lid)
        has_screenplay = "✅" if screenplay.exists() else "❌"
        content = get_content_path(lid)
        has_content = "✅" if content and content.exists() else "❌"
        print(f"  {lid}  {info['title'][:45]:<45}  content:{has_content}  screenplay:{has_screenplay}")


def main():
    parser = argparse.ArgumentParser(description="3D Print Academy Video Pipeline")
    parser.add_argument("--lesson", help="Lesson ID (e.g., 2-2)")
    parser.add_argument("--tts-only", action="store_true", help="Generate TTS audio only")
    parser.add_argument("--record-only", action="store_true", help="Record screen only")
    parser.add_argument("--merge", action="store_true", help="Merge existing audio + video")
    parser.add_argument("--audio", help="Audio file path (for --merge)")
    parser.add_argument("--video", help="Video file path (for --merge)")
    parser.add_argument("--output", help="Output file path (for --merge)")
    parser.add_argument("--voice", default=DEFAULT_VOICE, help="TTS voice")
    parser.add_argument("--headless", action="store_true", default=True, help="Run headless")
    parser.add_argument("--no-headless", dest="headless", action="store_false", help="Show browser")
    parser.add_argument("--list-needed", action="store_true", help="List lessons needing videos")
    args = parser.parse_args()

    if args.list_needed:
        list_needed()
        return

    if args.merge:
        if not args.audio or not args.video or not args.output:
            print("Error: --merge requires --audio, --video, and --output")
            sys.exit(1)
        merge_audio_video(Path(args.audio), Path(args.video), Path(args.output))
        return

    if not args.lesson:
        print("Error: --lesson required (e.g., --lesson 2-2)")
        parser.print_help()
        sys.exit(1)

    if args.tts_only:
        generate_tts(args.lesson, voice=args.voice)
    elif args.record_only:
        record_screen(args.lesson, headless=args.headless)
    else:
        full_pipeline(args.lesson, voice=args.voice, headless=args.headless)


if __name__ == "__main__":
    main()
