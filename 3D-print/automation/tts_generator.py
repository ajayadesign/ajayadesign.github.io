#!/usr/bin/env python3
"""
TTS Narration Generator — edge-tts powered
Generates high-quality narration audio from lesson text files.

Usage:
    python tts_generator.py lesson-2-2-first-frame-tinkercad.txt output.mp3
    python tts_generator.py lesson-2-2-first-frame-tinkercad.txt output.mp3 --voice en-US-GuyNeural
    python tts_generator.py --segments narration_segments.json output_dir/
"""

import argparse
import asyncio
import json
import re
import sys
from pathlib import Path

import edge_tts

# Best voices for educational content
VOICES = {
    "andrew": "en-US-AndrewNeural",       # Professional, clear — DEFAULT
    "brian": "en-US-BrianNeural",          # Warm, conversational
    "christopher": "en-US-ChristopherNeural",  # Authoritative
    "guy": "en-US-GuyNeural",             # Friendly, educational
    "roger": "en-US-RogerNeural",          # Deep, confident
}
DEFAULT_VOICE = VOICES["andrew"]

# Speaking rate: "+0%", "+10%", "-10%", etc.
DEFAULT_RATE = "+0%"
# Volume: "+0%", "+20%", etc.
DEFAULT_VOLUME = "+0%"


def parse_lesson_text(text: str) -> list[dict]:
    """Parse a lesson .txt file into narration segments.

    Splits by section headers (ALL CAPS LINES) and returns a list of
    {heading, text, estimated_seconds} dicts.
    """
    lines = text.strip().split("\n")
    segments = []
    current_heading = "Introduction"
    current_lines = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        # Detect section headers: lines that are ALL CAPS and > 5 chars
        if stripped == stripped.upper() and len(stripped) > 5 and not stripped.startswith("---"):
            if current_lines:
                body = " ".join(current_lines)
                # ~150 words per minute for narration
                wc = len(body.split())
                segments.append({
                    "heading": current_heading,
                    "text": body,
                    "estimated_seconds": max(5, int(wc / 150 * 60)),
                })
            current_heading = stripped.title()
            current_lines = []
        else:
            current_lines.append(stripped)

    # Last segment
    if current_lines:
        body = " ".join(current_lines)
        wc = len(body.split())
        segments.append({
            "heading": current_heading,
            "text": body,
            "estimated_seconds": max(5, int(wc / 150 * 60)),
        })

    return segments


def clean_for_speech(text: str) -> str:
    """Clean text for natural TTS: expand abbreviations, fix punctuation."""
    # Expand common abbreviations
    text = text.replace("mm", " millimeters")
    text = text.replace("STL", "S T L")
    text = text.replace("CAD", "C A D")
    text = text.replace("PLA", "P L A")
    text = text.replace("PETG", "P E T G")
    text = text.replace("CRT", "C R T")
    text = text.replace("Ctrl+D", "Control D")
    text = text.replace("Ctrl+G", "Control G")
    text = text.replace("3D", "3 D")
    # Remove markdown-style formatting
    text = re.sub(r"[*_]{1,2}", "", text)
    # Ensure sentences end with periods
    text = re.sub(r"([a-z])\s*\n", r"\1. ", text)
    return text


async def generate_audio(text: str, output_path: str, voice: str = DEFAULT_VOICE,
                         rate: str = DEFAULT_RATE, volume: str = DEFAULT_VOLUME) -> str:
    """Generate a single audio file from text."""
    communicate = edge_tts.Communicate(text, voice, rate=rate, volume=volume)
    await communicate.save(output_path)
    return output_path


async def generate_segments(segments: list[dict], output_dir: str,
                            voice: str = DEFAULT_VOICE, rate: str = DEFAULT_RATE) -> list[str]:
    """Generate audio for each segment, return list of file paths."""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    paths = []
    for i, seg in enumerate(segments):
        clean_text = clean_for_speech(seg["text"])
        out_path = out_dir / f"segment_{i:03d}_{seg['heading'][:30].replace(' ', '_')}.mp3"
        print(f"  [{i+1}/{len(segments)}] {seg['heading']} ({seg['estimated_seconds']}s) → {out_path.name}")
        await generate_audio(clean_text, str(out_path), voice=voice, rate=rate)
        paths.append(str(out_path))

    return paths


async def generate_full_narration(text: str, output_path: str,
                                  voice: str = DEFAULT_VOICE, rate: str = DEFAULT_RATE) -> str:
    """Generate a single audio file for the entire lesson text."""
    clean_text = clean_for_speech(text)
    print(f"  Generating full narration → {output_path}")
    await generate_audio(clean_text, output_path, voice=voice, rate=rate)
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Generate TTS narration from lesson text")
    parser.add_argument("input", help="Lesson text file path")
    parser.add_argument("output", help="Output audio file (.mp3) or directory for segments")
    parser.add_argument("--voice", default=DEFAULT_VOICE,
                        help=f"TTS voice (default: {DEFAULT_VOICE})")
    parser.add_argument("--rate", default=DEFAULT_RATE,
                        help=f"Speaking rate (default: {DEFAULT_RATE})")
    parser.add_argument("--segments", action="store_true",
                        help="Generate separate audio per section")
    parser.add_argument("--list-voices", action="store_true",
                        help="List available voices and exit")
    args = parser.parse_args()

    if args.list_voices:
        for name, voice_id in VOICES.items():
            print(f"  {name:15} → {voice_id}")
        return

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: {input_path} not found")
        sys.exit(1)

    text = input_path.read_text()

    if args.segments:
        segments = parse_lesson_text(text)
        print(f"Found {len(segments)} segments")
        paths = asyncio.run(generate_segments(segments, args.output, voice=args.voice, rate=args.rate))
        print(f"\nGenerated {len(paths)} audio segments in {args.output}/")
    else:
        asyncio.run(generate_full_narration(text, args.output, voice=args.voice, rate=args.rate))
        print(f"\nDone: {args.output}")


if __name__ == "__main__":
    main()
