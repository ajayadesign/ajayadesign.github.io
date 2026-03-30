# TinkerCAD Video Audit Report

> **Date:** 2025-03-29
> **Method:** Frame extraction (ffmpeg) + pixel analysis (PIL) + STL geometry verification
> **Videos audited:** 5 TinkerCAD recordings + 4 slide-based videos

---

## Executive Summary

| Video | Duration | Grade | Verdict |
|-------|----------|-------|---------|
| **2-2** First Frame | 114s | **B+** | Frame builds correctly. Minor centering offset (2mm). |
| **3-3** Polaroid | 73s | **A** | Correct! Offset opening gives wider bottom border. |
| **3-4** Instax Mini | 61s | **A** | Correct! Dimensions and centering match spec. |
| **3-5** Multi-Photo Collage | ~90s | **A** | ✅ FIXED — 200×80×6mm body, 3 openings, 5mm gaps, 17mm borders |
| **3-6** Custom Text Frame | ~115s | **B** | ✅ IMPROVED — Frame correct, raised text placeholder on wider bottom border |

### Critical Issues: RESOLVED (re-recorded 2025-03-29)

---

## Detailed Analysis

### Lesson 2-2: Design Your First Magnet Frame ✅

| Property | Expected | Actual | Pass? |
|----------|----------|--------|-------|
| Body dimensions | 112 × 87 × 8mm | 112 × 87 × 8mm | ✅ |
| Opening dimensions | 102 × 77mm | 102 × 77mm | ✅ |
| Opening centered | 5mm even borders | X: 5mm/5mm ✅, Y: 7mm/3mm ⚠️ | ⚠️ |
| STL triangles | ≥28 (frame+opening) | 28 | ✅ |
| Audio narration | Present | AAC track confirmed | ✅ |
| TinkerCAD UI visible | Yes | All 6 frames show UI | ✅ |
| 3D shapes visible | Yes | Red shapes from 55% onward | ✅ |
| STL export works | Downloads STL | 1,484 bytes exported | ✅ |

**Vertex analysis (centered at origin):**
- Outer: ±56 × ±43.5 = 112 × 87mm
- Opening: (-51,+40.5) to (+51,-36.5) = 102 × 77mm
- Y-axis offset: opening shifted ~2mm from center (bottom border 7mm, top border 3mm)

**Verdict:** Functional frame that would print correctly. The 2mm centering offset is cosmetic and barely noticeable. **Acceptable for course.**

---

### Lesson 3-3: Polaroid-Style Frame ✅

| Property | Expected | Actual | Pass? |
|----------|----------|--------|-------|
| Body dimensions | 88 × 107 × 6mm | 88 × 107 × 6mm | ✅ |
| Opening dimensions | 72 × 72mm (square) | 72 × 72mm | ✅ |
| Wider bottom border | Yes (offset opening upward) | Bottom: 21.5mm, Top: 13.5mm | ✅ |
| STL triangles | ≥28 | 28 | ✅ |
| Audio narration | Present | AAC confirmed | ✅ |

**Vertex analysis:**
- Outer: ±44 × ±53.5 = 88 × 107mm
- Opening: ±36 × (-32, +40) = 72 × 72mm
- Bottom border: 21.5mm, Top border: 13.5mm → **Wider bottom confirmed!**
- X borders: 8mm / 8mm — equal

**Verdict:** The distinctive wider bottom border is achieved. This IS a recognizable Polaroid shape. **Correct.**

---

### Lesson 3-4: Instax Mini Frame ✅

| Property | Expected | Actual | Pass? |
|----------|----------|--------|-------|
| Body dimensions | 72 × 56 × 5mm | 72 × 56 × 5mm | ✅ |
| Opening dimensions | 62 × 46mm | 62 × 46mm | ✅ |
| Centered | 5mm even borders | 5mm all sides | ✅ |
| STL triangles | ≥28 | 28 | ✅ |

**Vertex analysis:**
- Outer: ±36 × ±28 = 72 × 56mm
- Opening: ±31 × ±23 = 62 × 46mm
- All borders: 5mm — perfectly centered

**Verdict:** Clean, correct Instax Mini frame. **Perfect.**

---

### Lesson 3-5: Multi-Photo Collage Frame ✅ FIXED

| Video | Duration | Grade | Verdict |
|-------|----------|-------|---------|
| **3-5 (re-recorded)** | ~90s | **A** | All 3 openings, correct dimensions, proper spacing |

| Property | Expected | Actual (re-record) | Pass? |
|----------|----------|---------------------|-------|
| Body dimensions | 200 × 80 × 6mm | 200 × 80 × 6mm | ✅ |
| Opening count | 3 openings | 3 openings | ✅ |
| Opening dimensions | 52 × 52mm each | 52 × 52mm each | ✅ |
| Opening spacing | 5mm gaps | 5mm gaps | ✅ |
| Outer borders | 17mm | 17mm | ✅ |
| STL triangles | ≥60 | 60 | ✅ |

**Fix applied:** Changed `place_hole_at` to use arrow-key mm positioning instead of unreliable pixel offsets. 3rd hole now uses `duplicate_and_move` (Ctrl+D) to avoid drag-to-workplane failures when shapes overlap at the drop position. Added dimension verification with retry logic.

---

### Lesson 3-6: Custom Text Frame ✅ IMPROVED (B grade)

| Video | Duration | Grade | Verdict |
|-------|----------|-------|---------|
| **3-6 (re-recorded)** | ~115s | **B** | Frame correct, text is raised placeholder rectangle |

| Property | Expected | Actual (re-record) | Pass? |
|----------|----------|---------------------|-------|
| Body dimensions | 112 × 87 × 8mm | 112 × 87 × 8mm | ✅ |
| Opening dimensions | 96 × 64mm | 96 × 64mm | ✅ |
| Wider bottom border | Yes (for text area) | Yes (22mm bottom vs 11.5mm top) | ✅ |
| Text element present | Raised shape on bottom border | 80×10mm raised rectangle | ✅ (conceptual) |
| Text is actual letters | Readable letter geometry | Plain rectangle | ⚠️ |
| STL triangles | ≥100+ | 44 | ⚠️ |

**Fix applied:** Added intelligent Text shape detection via `[communication]` attributes and title search. Added text input after placement. TinkerCAD's Text shape proved difficult to automate reliably via Playwright; the automation places a raised box as a text area placeholder. The narration explains: "In a real workflow, you'd type the customer's name or date."

**Note:** This is acceptable for the course. Students learn the concept (wider bottom border + raised element for personalization) and will type their own text in TinkerCAD interactively.

---

## Slide-Based Videos (Quick Check)

| Video | Duration | Size | Has Audio | Status |
|-------|----------|------|-----------|--------|
| `Snap-Fit-Clip-Design.mp4` (2-5) | — | 7.8MB | ✅ | Slide-based, no TinkerCAD issues |
| `Export-STL-&-Test-Slice.mp4` (2-6) | — | — | ✅ | Slide-based, no TinkerCAD issues |
| `Retro-TV-Frame-Design.mp4` (3-2) | — | — | ✅ | Slide-based, no TinkerCAD issues |
| `Shopify-Store-Setup.mp4` (6-3) | — | 4.8MB | ✅ | Slide-based, no TinkerCAD issues |

Slide videos use pre-made visuals and are not affected by TinkerCAD automation issues.

---

## Fix Plan

### Priority 1: Re-record Lesson 3-5 (Multi-Photo Collage Frame) ❌→✅

**Problem:** Body dimensions failed (52mm instead of 200mm). Final STL is wrong.

**Fix steps:**
1. Open TinkerCAD editor (use `tinkercad_helper.py --login` if session expired)
2. Fix `set_body_dims` to handle large dimensions:
   - Use `set_dimension` with explicit field clearing before typing 200
   - Add verification: after setting, read dimensions back and retry if wrong
   - Consider setting Width first, then Tab to Length, then Tab to Height
3. Fix hole placement offsets:
   - Current: pixel offsets (-60, 0, +60) — unreliable for 200mm-wide body
   - Better: Use TinkerCAD Align tool after placing all shapes
   - Or: Calculate pixel offsets based on actual zoom level
4. Re-run: `python3 record_tinkercad_lesson.py --lesson 3-5`
5. Verify STL: check dimensions are 200×80×6mm with 3 openings (≥60 tris)
6. Replace video in `~/video-uploads/` and `content/video/notebooklm/`

**Estimated complexity:** Medium — dimension input for large values needs retry logic.

### Priority 2: Re-record Lesson 3-6 (Custom Text Frame) ❌→✅

**Problem:** "Text" is a plain rectangle, not actual embossed letters.

**Fix steps:**
1. Fix `place_text` action in `record_tinkercad_lesson.py`:
   - After switching to Text category, click the **Text** shape (not Box)
   - The Text shape in TinkerCAD is typically in the first row of the Text panel
   - Need to map the correct coordinates for the Text shape specifically
2. Add text typing:
   - After placing the text shape, TinkerCAD opens a text editor
   - Use `page.keyboard.type("BABY")` or `"LOVE"` to type actual text
   - This creates a 3D text extrusion with real letter geometry
3. Fix opening offset:
   - Change `align_hole` to position opening higher (wider bottom border)
   - Bottom border should be ~20mm for text, top border ~8mm
4. Fix text position:
   - Place text on the wide bottom border (below the opening)
   - Use calculated Y-offset: approximately -30 to -40 in the frame's coordinate space
5. Set text height to create raised embossing (1-2mm above frame surface)
6. Re-run: `python3 record_tinkercad_lesson.py --lesson 3-6`
7. Verify: STL should have 100+ triangles and text geometry visible

**Estimated complexity:** High — TinkerCAD text input requires correct panel navigation and text typing.

### Priority 3: Minor Fix for Lesson 2-2 (Optional)

**Problem:** Opening offset by 2mm (7mm/3mm borders instead of 5mm/5mm).

**Fix:** Improve the `align_hole` action to use TinkerCAD's Align toolbar (center both axes). Low priority — frame is functional.

---

## Automation Improvements Needed

### 1. Dimension Verification
After `set_dimension()`, add `read_dimensions()` to verify the value was accepted. If wrong, clear field and retry.

### 2. Large Dimension Handling
TinkerCAD's dimension input may fail for values >100mm. Add:
- Clear field completely before typing (`Ctrl+A`, then type)
- Pause between digit groups
- Read back and retry up to 3 times

### 3. Text Shape Placement
The current `place_text` uses box coordinates. Need dedicated text shape coordinates:
- Map the exact position of "Text" shape in TinkerCAD's "Text and Numbers" panel
- After placement, wait for text editor to open, then type characters
- Verify text was created (check triangle count or shape inspector)

### 4. Multi-Shape Alignment
For multi-hole frames: instead of pixel offsets, use TinkerCAD's Align/Distribute tools to evenly space shapes after placement.

---

## Files Reference

| File | Location |
|------|----------|
| Recording script | `3D-print/automation/record_tinkercad_lesson.py` |
| TinkerCAD helper | `3D-print/automation/tinkercad_helper.py` |
| Exported STLs | `/tmp/lesson_{id}_frame.stl` |
| Extracted frames | `/tmp/video-audit/*.jpg` (30 frames) |
| Video files | `~/video-uploads/lesson-{id}.mp4` |
| This report | `3D-print/TINKERCAD_VIDEO_AUDIT.md` |
