# 3D Print Academy — Full Course Content Production Plan

> **43 lessons • 6 modules • 14+ hours**
> AI-generatable content marked with 🤖 | Requires filming marked with 📹 | Screen recording marked with 🖥️

---

## Production Strategy

### What AI Can Generate (THIS SESSION)
| Type | Tool | Lessons |
|------|------|---------|
| **Lecture slide decks** | Google NotebookLM → Audio Overview | 1.3, 1.7, 2.4, 2.7, 4.2, 5.7, 6.1, 6.2, 6.4, 6.7 |
| **Narrated AI presentations** | Gamma.app + ElevenLabs | Same as above |
| **Module recap podcasts** | Google NotebookLM Audio | 1.7, 2.7, 6.7 |
| **Written scripts for all lessons** | This document | All 43 |

### What Requires Human Recording
| Type | Tool | Lessons |
|------|------|---------|
| **Physical printer demos** | Phone + tripod | 1.1, 1.2, 1.6, 3.7, 4.1, 4.4–4.7, 5.1–5.6, 6.5, 6.6 |
| **CAD screen recordings** | OBS Studio | 2.1–2.3, 2.5, 2.6, 3.1–3.6, 4.3, 4.8 |
| **Shopify walkthrough** | OBS Studio | 6.3 |

---

## Module 1: 3D Printing Fundamentals (2 hrs • Beginner)

### Lesson 1.1 — Printer Anatomy: Know Your Machine 📹
**Duration**: ~20 min | **Type**: Filmed physical demo
**Script**:
- **Intro** (2 min): "Welcome to 3D Print Academy. Before you print a single frame, let's understand the machine."
- **Frame/chassis** (3 min): Show the frame, explain rigidity matters for print quality
- **Print bed** (3 min): Glass vs PEI vs magnetic flex plates. Why magnetic flex = best for magnet frames (easy removal)
- **Extruder & hotend** (4 min): Direct drive vs Bowden. Temperature ranges. Nozzle sizes (0.4mm standard)
- **Stepper motors** (2 min): X/Y/Z axes. Belt tension — show loose vs tight belt
- **Control board & screen** (2 min): LCD interface, SD card slot, USB
- **Power supply & wiring** (2 min): Safety check, proper ventilation
- **Recommended printers** (2 min):
  - Budget: Ender 3 V3 SE ($199) - great for beginners
  - Mid: Bambu Lab A1 Mini ($299) - near-zero setup
  - Pro: Bambu Lab P1S ($599) - enclosed, multi-color

### Lesson 1.2 — Bed Leveling: The Foundation of Good Prints 📹
**Duration**: ~15 min | **Type**: Filmed physical demo
**Script**:
- **Why it matters** (2 min): Show a failed first layer vs a perfect one
- **Paper test method** (5 min): Step-by-step with A4 paper at all 4 corners + center
- **Auto bed leveling** (3 min): BLTouch/CR-Touch probe — how it works, why it's worth $30
- **Live leveling** (3 min): Print a first-layer calibration square, adjust in real-time
- **Pro tip** (2 min): Re-level every 5-10 prints, or after moving the printer

### Lesson 1.3 — Filament Types: PLA, PLA+, and PETG 🤖
**Duration**: ~20 min | **Type**: AI Slides + Narration
**NotebookLM Source Material**:
```
TOPIC: 3D Printing Filament Comparison for Magnet Photo Frames

PLA (Polylactic Acid):
- Temperature: 190-220°C nozzle, 50-60°C bed
- Pros: Easiest to print, low warping, biodegradable, cheap ($15-20/kg)
- Cons: Brittle, heat-sensitive (softens at 60°C), UV degrades over time
- Best for: Indoor magnet frames, prototyping, test prints
- Color range: Widest available — 50+ colors from most brands
- Recommended brands: eSun PLA+, Hatchbox PLA, Polymaker PolyLite

PLA+ (Enhanced PLA):
- Temperature: 200-230°C nozzle, 60°C bed
- Pros: Stronger than PLA, less brittle, better layer adhesion
- Cons: Slightly harder to print, costs $2-5 more per kg
- Best for: Production magnet frames — our recommended daily driver
- Why for magnet frames: Better impact resistance (won't snap when dropped),
  smoother finish, easier to sand and paint

PETG (Polyethylene Terephthalate Glycol):
- Temperature: 230-250°C nozzle, 70-80°C bed
- Pros: Strong, flexible, weather-resistant, food-safe
- Cons: Stringing issues, sticks to PEI beds too well, glossy finish harder to paint
- Best for: Outdoor magnet frames, bathroom/kitchen use
- Special consideration: Needs slower print speeds (40-50mm/s vs 60-80mm/s for PLA)

Cost comparison per magnet frame (4x6 size):
- PLA: ~$0.25-0.40 in filament
- PLA+: ~$0.30-0.50 in filament
- PETG: ~$0.35-0.55 in filament

Storage: All filaments must be kept dry. Use vacuum bags with desiccant.
Wet filament = popping sounds during printing = rough surface = bad for retail product.

Recommendation for this course: Start with PLA for learning in Modules 1-3.
Switch to PLA+ for production in Modules 4-6. Use PETG only for specialty outdoor orders.
```

### Lesson 1.4 — Slicer Setup: Cura 🖥️
**Duration**: ~25 min | **Type**: Screen recording
**Script outline**:
- Download & install Cura (free, open source)
- Add your printer profile (Ender 3 / Bambu Lab / custom)
- Import our magnet frame slicer profile (download provided)
- Key settings walkthrough: layer height (0.2mm), infill (15%), wall count (3), support (off for frames)
- Slice a basic magnet frame STL, preview layer-by-layer
- Export G-code to SD card/USB

### Lesson 1.5 — Slicer Setup: PrusaSlicer 🖥️
**Duration**: ~15 min | **Type**: Screen recording
**Script outline**:
- Download & install PrusaSlicer (free, open source)
- Why some prefer it: better support generation, paint-on supports, variable layer height
- Import our .ini profile
- Slice the same magnet frame, compare output with Cura
- Brief comparison: Cura vs PrusaSlicer for magnet frames

### Lesson 1.6 — Your First Test Print 📹
**Duration**: ~20 min | **Type**: Filmed time-lapse + narration
**Script**:
- Load filament into the printer (step by step)
- Start the calibration cube print (20x20x20mm) — time-lapse
- While printing: explain what to watch for (first layer adhesion, consistent extrusion)
- Measure the cube with calipers — is it 20.0mm? Discuss tolerances
- Now print the basic magnet frame STL — time-lapse
- Remove from bed, insert magnet, test on fridge
- "You just made your first magnet frame. Module 1 complete."

### Lesson 1.7 — Module 1 Recap 🤖
**Duration**: ~5 min | **Type**: NotebookLM Audio Overview
**NotebookLM Source**: Upload Lessons 1.1–1.6 scripts as a Google Doc. Generate "Audio Overview" in NotebookLM. This creates a ~5 min podcast-style recap of all key concepts.

---

## Module 2: Magnet Frame Design — CAD Basics (3 hrs • Beginner–Intermediate)

### Lesson 2.1 — TinkerCAD Introduction & Interface 🖥️
**Duration**: ~25 min | **Type**: Screen recording
**Script outline**:
- Navigate to tinkercad.com (free, browser-based, no install)
- Create account, start new design
- Interface tour: workplane, shapes panel, inspector, ruler
- Basic operations: drag shape, resize, duplicate, group, hole
- Practice: create a 100x150mm rectangle (4x6 photo frame scale)
- Explain: TinkerCAD is perfect for beginners, but we'll graduate to Fusion 360

### Lesson 2.2 — Design Your First Magnet Frame in TinkerCAD 🖥️
**Duration**: ~35 min | **Type**: Screen recording (step-by-step build)
**Script outline**:
- Start with outer frame: 120x170mm rectangle, 8mm thick
- Create photo window: 100x150mm hole centered
- Create magnet slots: 4 cylinders (6.2mm diameter, 2.5mm deep) — at each corner backside
- Why 6.2mm for 6mm magnets: 0.2mm tolerance for press-fit
- Group all elements → export as STL
- Slice in Cura → preview → print
- **Key teaching moment**: Understanding tolerances is the #1 skill for magnet frames

### Lesson 2.3 — Fusion 360 Introduction & Interface 🖥️
**Duration**: ~30 min | **Type**: Screen recording
**Script outline**:
- Download Fusion 360 (free for personal use)
- Interface tour: timeline, sketch mode, extrude, components
- Parametric modeling explained: change one dimension → everything updates
- Create the same frame from 2.2, but parametrically
- Show how changing photo_width from 100→127mm automatically updates everything
- This is why Fusion 360 is worth learning for production work

### Lesson 2.4 — Magnet Slot Tolerances & Photo Insert Sizing 🤖
**Duration**: ~20 min | **Type**: AI Slides + Narration
**NotebookLM Source Material**:
```
TOPIC: Magnet Slot Tolerances & Photo Insert Sizing for 3D Printed Frames

MAGNET SPECIFICATIONS:
- Standard magnet: 6mm diameter × 2mm thick neodymium (N52 grade)
- Bulk price: ~$0.05-0.10 each (buy 100+ on Amazon)
- Pull force: ~1.5 lbs per magnet — enough to hold a frame + photo on any fridge

TOLERANCE RULES:
- Magnet slot diameter: Magnet diameter + 0.1 to 0.3mm
  - 6mm magnet → 6.1mm slot (tight press-fit, no glue needed)
  - 6mm magnet → 6.2mm slot (standard fit, tiny drop of super glue)
  - 6mm magnet → 6.3mm slot (loose fit, always needs glue)
- Slot depth: Magnet thickness + 0.2mm
  - 2mm magnet → 2.2mm deep slot
  - This ensures magnet sits flush or slightly recessed (won't scratch fridge)

WHY TOLERANCES VARY:
- Every printer has slight dimensional inaccuracy
- Print a calibration cube (20mm) and measure:
  - If it measures 20.1mm → your printer prints 0.5% oversized → use tighter tolerances
  - If it measures 19.9mm → your printer prints 0.5% undersized → use looser tolerances
- PLA shrinks ~0.3-0.4% as it cools
- PETG shrinks ~0.5-0.7%

PHOTO INSERT SIZING:
Standard photo sizes and frame openings needed:
| Photo Size | Actual Dimensions | Frame Opening (with 1mm tolerance) |
|-----------|-------------------|-------------------------------------|
| 4×6 inch  | 102 × 152 mm      | 103 × 153 mm                       |
| 5×7 inch  | 127 × 178 mm      | 128 × 179 mm                       |
| Wallet     | 64 × 89 mm        | 65 × 90 mm                         |
| Instax Mini| 54 × 86 mm        | 55 × 87 mm                         |
| Polaroid   | 79 × 79 mm        | 80 × 80 mm (square)                |

FRAME BORDER WIDTH:
- Minimum: 8mm (structural integrity)
- Recommended: 12-15mm (looks better, stronger)
- With text: 20mm+ (room for "MONTHS" text etc)

MAGNET PLACEMENT:
- Minimum 2 magnets per frame (top corners)
- Recommended 4 magnets (all corners) for frames larger than wallet size
- For heavy frames (collage/multi-photo): 6 magnets (corners + middle sides)
- Orientation: All magnets same polarity facing out — test with a marked reference magnet

BACK COVER OPTIONS:
- Open back (cheapest, simplest) — photo slides in from top
- Snap-fit back plate — sounds professional (click!), patents expired on basic snap-fits
- Friction-fit back — 0.3mm interference fit, holds by friction alone
```

### Lesson 2.5 — Snap-Fit Clip Design 🖥️
**Duration**: ~25 min | **Type**: Screen recording
**Script outline**:
- What is a snap-fit clip: flexible tab that deflects and locks
- Design in Fusion 360: cantilever beam with angled tip
- Key dimensions: 1.5mm thick, 8mm long, 45° engagement angle
- Print orientation matters: clips along layer lines = weak, across = strong
- Test print the clip separately before adding to full frame
- Integrate into the magnet frame back cover

### Lesson 2.6 — Export STL & Test Slice 🖥️
**Duration**: ~15 min | **Type**: Screen recording
**Script outline**:
- TinkerCAD export: Download → STL
- Fusion 360 export: File → Export → STL (binary format, fine resolution)
- Common export mistakes: forgetting to group in TinkerCAD, non-manifold geometry in Fusion
- Verify in slicer: look for red/error zones in Cura preview
- Netfabb online repair tool (free) for fixing broken meshes

### Lesson 2.7 — Module 2 Recap 🤖
**Duration**: ~5 min | **Type**: NotebookLM Audio Overview
**NotebookLM Source**: Upload Lessons 2.1–2.6 scripts.

---

## Module 3: Advanced Frame Designs (3 hrs • Intermediate)

### Lesson 3.1 — Multi-Piece Magnetic Assemblies 🖥️📹
**Duration**: ~30 min | **Type**: Screen recording + physical demo
**Script outline**:
- Concept: frames that snap together magnetically to form collages
- Design interlocking edge profiles in Fusion 360
- Each piece has magnets on edges + back for fridge attachment
- Print demo: 4 small frames that combine into one large display
- Physical assembly demo: click them together on a fridge

### Lesson 3.2 — Retro TV Frame Design 🖥️
**Duration**: ~35 min | **Type**: Screen recording (full build)
**Script outline**:
- Design a miniature CRT TV shape in Fusion 360
- Rounded corners with fillet tool
- "Screen" opening for the photo
- Add antenna details, channel knob, speaker grille texture
- Magnet slots on the back
- Export STL → slice → show finished printed result

### Lesson 3.3 — Polaroid-Style Frame 🖥️
**Duration**: ~25 min | **Type**: Screen recording
**Script outline**:
- Classic Polaroid proportions: square photo + iconic bottom strip
- Design in Fusion 360 with exact Polaroid dimensions
- Optional: emboss "Polaroid" style text on bottom strip (or custom text)
- Two-piece design: frame + removable back
- Quick print: only 25 min at 0.2mm layer height

### Lesson 3.4 — Instax Mini Frame 🖥️
**Duration**: ~15 min | **Type**: Screen recording
**Script outline**:
- Instax Mini photo dimensions (54×86mm)
- Slim frame design — minimal border for modern look
- Side-loading photo slot (no back cover needed)
- Magnet recesses on back — 2 magnets sufficient (lightweight frame)
- This is the fastest-selling frame design at craft fairs

### Lesson 3.5 — Multi-Photo Collage Frame 🖥️
**Duration**: ~30 min | **Type**: Screen recording
**Script outline**:
- 2×2 grid layout for 4 wallet-size photos
- Design the grid dividers (3mm thick for strength)
- 6 magnet slots (4 corners + 2 middle for weight)
- Print considerations: large print bed needed (250mm+), or print in 2 halves
- Assembly: magnetic joining if printed in halves

### Lesson 3.6 — Custom Text Inserts 🖥️
**Duration**: ~20 min | **Type**: Screen recording
**Script outline**:
- Adding raised or recessed text to frames
- Fusion 360 text tool: font selection, size, emboss depth
- Examples: "Baby's First Year", "1 MONTH", "Love", names, dates
- Multi-color text: pause print, swap filament, resume
- Separate text piece that snaps into frame slot

### Lesson 3.7 — Printed Frames Showcase & Quality Review 📹
**Duration**: ~15 min | **Type**: Filmed physical demo
**Script outline**:
- Showcase all 5+ frame designs printed and finished
- Side-by-side comparison on a fridge
- Point out quality differences: layer lines, magnet fit, photo fit
- Rate each design for: print ease, sell-ability, uniqueness
- Student challenge: design your own themed frame, share in community

---

## Module 4: Print Optimization & Troubleshooting (2 hrs • Intermediate)

### Lesson 4.1 — Layer Height Comparison 📹
**Duration**: ~15 min | **Type**: Physical demo (macro close-ups)
**Script outline**:
- Print same frame at 0.12mm, 0.16mm, 0.20mm, 0.28mm
- Macro photography comparison of surface quality
- Time comparison: 0.12mm = 2.5hrs, 0.20mm = 1.5hrs, 0.28mm = 55min
- Recommendation: 0.20mm for production (best quality:speed ratio)
- 0.12mm only for display/portfolio pieces

### Lesson 4.2 — Infill Patterns & Strength 🤖
**Duration**: ~15 min | **Type**: AI Slides + Narration
**NotebookLM Source Material**:
```
TOPIC: Infill Patterns & Strength for 3D Printed Magnet Frames

WHAT IS INFILL:
- The internal structure of a 3D print (not solid)
- Reduces material use and print time dramatically
- For magnet frames, we DON'T need high strength — they hang on a fridge

INFILL PERCENTAGE:
- 0% (hollow): Too fragile, will crush
- 10%: Minimum for magnet frames. Very lightweight. Good for small wallet frames.
- 15%: Our recommended default. Good strength:weight:speed ratio.
- 20%: For larger frames or if you want extra rigidity.
- 100% (solid): Wasteful for frames. Only use for the magnet slot area.

INFILL PATTERNS (ranked for magnet frames):
1. GRID: Best overall. Fast to print, good bidirectional strength. Our default.
2. GYROID: Strongest per gram. Slightly slower. Use for premium/heavy frames.
3. LINES: Fastest to print. Weak in one direction. OK for small frames.
4. HONEYCOMB: Overkill for frames. Slower print, good strength but unnecessary.
5. TRI-HEXAGONAL: Beautiful cross-section but no practical advantage.

WALL COUNT:
- 2 walls: Minimum. Frame edges might be slightly translucent.
- 3 walls: Our default. Solid feel, great surface for painting.
- 4 walls: Premium feel. Adds ~10% print time. Worth it for retail.

TOP/BOTTOM LAYERS:
- 3 layers minimum (at 0.2mm = 0.6mm solid top/bottom)
- 4 layers recommended (0.8mm — fully opaque, smooth)

VARIABLE INFILL (PrusaSlicer only):
- Use "modifier mesh" to set 100% infill around magnet slots
- Rest of frame stays at 15%
- This ensures magnets are held securely without wasting filament everywhere

MATERIAL SAVINGS EXAMPLE (4×6 frame):
| Infill | Material | Time | Cost |
|--------|----------|------|------|
| 100% | 45g | 2h 15m | $0.90 |
| 15% | 18g | 1h 10m | $0.36 |
| Savings | 60% less | 48% faster | 60% cheaper |
```

### Lesson 4.3 — Speed vs Quality Tuning 🖥️
**Duration**: ~15 min | **Type**: Screen recording
**Script outline**:
- Default speed: 50mm/s (safe for all printers)
- Push to 80mm/s: what changes, what to watch for
- Input shaping (Bambu Lab): print at 150mm/s+ with quality
- Jerk and acceleration: what they do, safe ranges
- Speed profiles for production: "Quick Draft" vs "Retail Quality"

### Lesson 4.4 — Temperature Tower Test 📹
**Duration**: ~15 min | **Type**: Video (time-lapse)
**Script outline**:
- What is a temp tower: stacked sections printed at different temperatures
- Download and print a temp tower STL (provided)
- Evaluate each section: stringing, bridging, detail, strength
- Find your filament's sweet spot (usually 200-215°C for PLA+)
- Document your settings — every roll can be slightly different

### Lesson 4.5 — Fix Stringing 📹
**Duration**: ~10 min | **Type**: Physical demo + slicer settings
**Script outline**:
- What stringing looks like (thin wisps between parts)
- Cause: oozing during travel moves
- Fix 1: Retraction distance (5-6mm for Bowden, 1-2mm for direct drive)
- Fix 2: Retraction speed (40-60mm/s)
- Fix 3: Lower temperature 5°C
- Fix 4: Enable "combing" in Cura (travel moves stay inside)

### Lesson 4.6 — Fix Warping 📹
**Duration**: ~10 min | **Type**: Physical demo
**Script outline**:
- What warping looks like (corners lift off bed)
- Cause: thermal contraction as plastic cools
- Fix 1: Clean bed with IPA (isopropyl alcohol)
- Fix 2: Increase bed temperature (+5°C)
- Fix 3: Use glue stick or hairspray
- Fix 4: Add a brim in slicer (3-5mm)
- Fix 5: Enclose the printer (reduce drafts)

### Lesson 4.7 — Fix Elephant's Foot 📹
**Duration**: ~10 min | **Type**: Physical demo
**Script outline**:
- What elephant's foot looks like (first layer squished outward)
- Cause: nozzle too close to bed, or bed too hot
- Fix 1: Raise Z-offset by 0.02mm increments
- Fix 2: Lower bed temp for first layer only
- Fix 3: "Elephant foot compensation" setting in slicer (0.1-0.2mm)
- Why it matters for frames: bottom edge won't sit flush

### Lesson 4.8 — Batch Printing for Production 🖥️📹
**Duration**: ~15 min | **Type**: Screen recording + time-lapse
**Script outline**:
- Arrange multiple frames on one build plate (9 wallet frames on a 220mm bed)
- Slicer settings for batch: sequential printing vs all-at-once
- Sequential: prints one complete frame before starting next (safer)
- All-at-once: faster total time but risk losing entire batch if one fails
- Time-lapse: batch of 9 frames printing overnight
- Per-unit time drops from 45min to 28min in batch mode

---

## Module 5: Post-Processing & Finishing (2 hrs • All Levels)

### Lesson 5.1 — Sanding Technique: Grit Progression 📹
**Duration**: ~15 min | **Type**: Physical demo (close-ups)
**Script outline**:
- Start with 120 grit to remove layer lines
- Progress: 120 → 220 → 400 → 600 grit
- Wet sanding at 400+ for smoother finish
- Focus areas: frame edges, front face, text details
- Skip interior/back surfaces (saves time, nobody sees them)
- Time budget: 3-5 min per frame for "retail ready"

### Lesson 5.2 — Priming with Filler Primer 📹
**Duration**: ~15 min | **Type**: Physical demo
**Script outline**:
- Why prime: fills tiny layer line gaps, creates uniform surface
- Product: Rust-Oleum Filler Primer (~$6/can, does 30+ frames)
- Technique: light coats, 6-8 inches distance, 3 passes
- Dry time: 15 min between coats, 1 hour before sanding
- Light sand with 400 grit after primer for glass-smooth finish

### Lesson 5.3 — Spray Painting Technique 📹
**Duration**: ~15 min | **Type**: Physical demo
**Script outline**:
- Color selection: what sells (white, matte black, rose gold, pastel pink)
- Technique: sweeping motions, multiple thin coats, NOT one thick coat
- Common mistakes: runs (too close), orange peel (too far), dust nibs (dirty area)
- Metallic finishes: requires specific paint + technique (show gold, chrome, copper)
- Dry time: 30 min between coats, 24 hours before handling

### Lesson 5.4 — Clear Coating for Durability 📹
**Duration**: ~10 min | **Type**: Physical demo
**Script outline**:
- Matte clear coat: modern, fingerprint-resistant look
- Gloss clear coat: shiny, premium feel
- Satin: compromise between the two
- Application: 2-3 light coats, same spray technique as paint
- Why it matters for retail: prevents scratches, adds perceived quality, justifies higher price

### Lesson 5.5 — Magnet Installation: Mid-Print Pause Method 📹
**Duration**: ~20 min | **Type**: Physical demo (the tricky one!)
**Script outline**:
- Set pause point in slicer at the magnet slot ceiling layer
- Printer pauses → drop magnets into slots → resume print
- The next layer prints OVER the magnets, encapsulating them
- Pros: strongest hold, invisible from outside, no glue needed
- Cons: requires accurate pause timing, can't fix mistakes
- Cura pause-at-height plugin setup
- PrusaSlicer custom G-code at layer setup

### Lesson 5.6 — Magnet Installation: Post-Glue Method 📹
**Duration**: ~15 min | **Type**: Physical demo
**Script outline**:
- Print frame with open magnet recesses on back
- Apply super glue (cyanoacrylate) to recess
- Press magnet in with correct polarity (CHECK FIRST!)
- Hold 30 seconds
- Optional: cover with adhesive felt pad for clean look
- Pros: easiest method, fix mistakes, no slicer setup
- Cons: visible from back, glue can be messy

### Lesson 5.7 — Quality Control Checklist Walkthrough 🤖
**Duration**: ~10 min | **Type**: AI Slides
**NotebookLM Source Material**:
```
TOPIC: Quality Control Checklist for 3D Printed Magnet Frames (Retail)

PRE-SHIP QC CHECKLIST — Every frame must pass ALL checks before packaging:

STRUCTURAL CHECKS:
□ Frame is flat (no warping) — test on flat surface, no rocking
□ No visible cracks or layer separation
□ Photo window dimensions correct (test with actual photo)
□ Photo slides in/out smoothly with slight friction
□ Frame edges are smooth (no sharp burrs or blobs)

MAGNET CHECKS:
□ All magnets installed with correct polarity (test on fridge)
□ Magnets are secure (shake test — no rattling)
□ Magnets sit flush or slightly recessed (won't scratch fridge)
□ Frame holds on fridge without sliding (minimum 4 magnets for 4x6+)
□ Frame holds with photo inserted (weight test)

FINISH CHECKS (if painted):
□ No bare spots or missed areas
□ No paint runs or drips
□ Even color coverage
□ Clear coat applied and fully cured (24hr minimum)
□ No fingerprints embedded in finish

FINAL CHECKS:
□ Back cover fits properly (if applicable)
□ Snap-fit clips engage and disengage smoothly
□ Overall appearance is "gift worthy" — would you pay $10-15 for this?
□ Weight feels substantial but not heavy

REJECTION CRITERIA (reprint instead of fix):
✗ Visible layer shifts (printer issue)
✗ Elephant's foot affecting base flatness
✗ Stringing that can't be removed cleanly
✗ Wrong magnet polarity (can't remove embedded magnets)
✗ Cracked during post-processing
```

---

## Module 6: Launch Your Magnet Business (2 hrs • Business)

### Lesson 6.1 — Cost Per Unit Breakdown 🤖
**Duration**: ~20 min | **Type**: AI Slides + Narration
**NotebookLM Source Material**:
```
TOPIC: Cost Per Unit Breakdown for 3D Printed Magnet Frames Business

MATERIALS COST (per 4×6 magnet frame):
| Item | Qty | Unit Cost | Total |
|------|-----|-----------|-------|
| PLA+ filament | 18g | $0.02/g | $0.36 |
| Neodymium magnets (6x2mm) | 4 | $0.08 | $0.32 |
| Super glue | 4 drops | $0.01 | $0.04 |
| Filler primer | 1/30 can | $0.20 | $0.20 |
| Spray paint | 1/25 can | $0.28 | $0.28 |
| Clear coat | 1/40 can | $0.15 | $0.15 |
| **TOTAL MATERIALS** | | | **$1.35** |

TIME COST (per frame):
| Step | Time |
|------|------|
| Print time | 65 min (batch: 28 min effective) |
| Sanding | 3 min |
| Priming | 2 min (+ 15 min dry) |
| Painting | 2 min (+ 30 min dry) |
| Clear coating | 2 min (+ 24 hr dry) |
| Magnet install | 2 min |
| QC check | 1 min |
| **TOTAL ACTIVE TIME** | **12 min/frame** |

OVERHEAD (monthly, amortized per frame at 300 frames/month):
| Item | Monthly | Per Frame |
|------|---------|-----------|
| Electricity | $15 | $0.05 |
| Printer wear (replacement parts) | $10 | $0.03 |
| Packaging materials | $30 | $0.10 |
| Shopify ($29/mo) | $29 | $0.10 |
| **TOTAL OVERHEAD** | | **$0.28** |

TOTAL COST PER FRAME: $1.35 + $0.28 = $1.63
RETAIL PRICE RANGE: $8-15
PROFIT PER FRAME: $6.37-13.37 (75-89% margin!)

BREAK-EVEN ANALYSIS:
- Startup cost (printer + supplies): ~$350
- At $8/frame profit × 10 frames/day = $80/day
- Break even in: 4.4 days of selling
- Monthly potential (20 selling days): $1,600 profit

SCALING PATH:
- 1 printer: 10-20 frames/day (hobby income: $1,600-3,200/mo)
- 2 printers: 20-40 frames/day (part-time income: $3,200-6,400/mo)
- 4 printers: 40-80 frames/day (full-time income: $6,400-12,800/mo)
```

### Lesson 6.2 — Pricing Strategy ($5–$15 Retail) 🤖
**Duration**: ~15 min | **Type**: AI Slides + Narration
**NotebookLM Source Material**:
```
TOPIC: Pricing Strategy for 3D Printed Magnet Frames

PRICING TIERS:
| Frame Type | Suggested Price | Why |
|-----------|----------------|-----|
| Basic single-color (wallet) | $5-7 | Entry point, impulse buy |
| Basic single-color (4x6) | $8-10 | Bread and butter product |
| Themed frame (retro TV, Polaroid) | $12-15 | Perceived higher value |
| Custom text/name frame | $15-20 | Personalization premium |
| Multi-photo collage | $18-25 | Larger size, more magnets |
| Baby milestone set (12 frames) | $45-65 | Bundle deal, gift market |

PRICING PSYCHOLOGY:
- $9.99 vs $10 — the $0.01 difference matters (charm pricing)
- Odd pricing ($7, $9, $13) outperforms even ($8, $10, $12) at craft fairs
- Anchor pricing: always show your premium option first ($25 collage frame)
  then the $10 frame looks like a deal
- Bundle discounts: "3 for $25" instead of "$10 each" — increases average order

PLATFORM-SPECIFIC PRICING:
- Shopify: higher prices OK ($10-15 + $5 shipping)
- Etsy: competitive market, stay $8-12 or differentiate with custom options
- Craft fairs: mark up 20-30% vs online (impulse buy + no shipping cost)
- Facebook Marketplace: lower prices, local delivery, volume play

WHEN TO RAISE PRICES:
- Selling out at craft fairs → price too low
- >5% conversion rate on Shopify → can probably raise 10-20%
- Adding personalization → automatic $5-8 premium
- Holiday season → add $2-3 "limited edition" surcharge

NEVER COMPETE ON PRICE:
- Someone will always be cheaper (especially mass-produced from China)
- Compete on: custom designs, local/handmade story, personalization, quality
- Your story: "Designed and printed locally by [Name]" = worth more than "Made in China"
```

### Lesson 6.3 — Shopify Store Setup: Full Walkthrough 🖥️
**Duration**: ~25 min | **Type**: Screen recording
**Script outline**:
- Sign up for Shopify ($1/month for first 3 months)
- Choose a free theme (Dawn or Craft)
- Create product listing: title, description, photos, pricing, variants (size/color)
- Shipping settings: flat rate ($5) for single, free shipping over $25
- Payment setup: Shopify Payments (no extra fees) or Stripe
- Domain: custom domain vs myshopify.com
- Install essential free apps: photo reviews, SEO, order tracking
- Test order walkthrough

### Lesson 6.4 — Craft Fair Strategy 🤖📹
**Duration**: ~15 min | **Type**: AI Slides + filmed booth setup
**NotebookLM Source Material**:
```
TOPIC: Craft Fair Strategy for Selling 3D Printed Magnet Frames

FINDING FAIRS:
- Search "craft fair near me" + your city on Facebook Events
- Eventbrite local craft/artisan markets
- Holiday bazaars (November-December = peak season)
- Farmers markets often have artisan vendor spots ($25-50/day)
- School/church craft fairs (cheap, family audience = magnets sell great)

BOOTH SETUP:
- Table cover: black tablecloth ($10, makes colors pop)
- Display: magnetic whiteboard or metal sheet standing up — frames displayed ON it
- Signage: "Handmade 3D Printed Magnet Frames" + price tiers clearly visible
- Business cards with QR code to your Shopify store
- Demo: have a fridge magnet surface so people can try removing/placing frames

INVENTORY TO BRING:
- 50-100 frames minimum (you WILL sell out at good fairs)
- Mix of sizes: 60% 4x6, 20% wallet, 20% themed/collage
- Color variety: white, black, pastels, metallics
- At least 5 "premium" display pieces (custom text, multi-photo) for upselling

PRICING DISPLAY:
| Size | Price |
|------|-------|
| Wallet | $7 |
| 4×6 | $10 |
| Themed (TV/Polaroid) | $13 |
| Custom Name | $15 |
| 3 for $25 deal | (posted prominently) |

CRAFT FAIR MATH:
- Booth fee: $25-75 (average)
- Inventory cost: $50-100 (100 frames at ~$1 each)
- Revenue at average fair: $200-500
- Profit: $125-375 per fair day
- Great fairs to target: holiday markets, farmers markets, school events

SALES TIPS:
- Let people TOUCH the frames — the quality sells itself
- Have photos IN the frames — people buy the vision, not empty frames
- "These work on any fridge?" — yes, neodymium magnets work on all fridges
- Square card reader for card payments (90%+ of sales are card now)
- Offer custom orders: "I can print any name or text — pick up next week!"
```

### Lesson 6.5 — Product Photography 📹
**Duration**: ~15 min | **Type**: Physical demo
**Script outline**:
- Phone photography setup (no DSLR needed)
- Lightbox from Amazon ($15) or DIY from a cardboard box
- Key shots: front, 45° angle, on-fridge lifestyle, with-photo-inside
- Editing: free apps (Snapseed, VSCO) for white balance and exposure
- Lifestyle shots: frame on fridge with family photos visible
- Background ideas: marble contact paper ($5), wooden cutting board, white foam board

### Lesson 6.6 — Packaging & Shipping 📹
**Duration**: ~10 min | **Type**: Physical demo
**Script outline**:
- Packaging: small kraft box ($0.30 each bulk), tissue paper, sticker seal
- Thank-you card: printed at home, includes care instructions + QR code for reorders
- Shipping: USPS First Class Package ($3-4 for most frames, under 4oz)
- Shopify automatic shipping labels (discounted rates)
- Poly mailer alternative: cheaper ($0.10), less premium feel
- Include extra magnets as a nice touch (costs $0.16, builds loyalty)

### Lesson 6.7 — Scaling: Hobby → Income 🤖
**Duration**: ~15 min | **Type**: AI Slides + NotebookLM recap
**NotebookLM Source Material**:
```
TOPIC: Scaling a 3D Printed Magnet Frame Business from Hobby to Income

PHASE 1 — HOBBY ($0-500/month):
- 1 printer running 4-8 hours/day
- 5-15 frames per day
- Sell at 1-2 craft fairs/month + Shopify/Etsy
- Total investment: $350 (printer + supplies)
- Time commitment: 1-2 hours/day active work
- Goal: cover printer cost, validate demand

PHASE 2 — SIDE INCOME ($500-2,000/month):
- 1-2 printers running 12-16 hours/day
- 15-40 frames per day
- Regular craft fair circuit + growing online presence
- Add custom text/personalization service
- Instagram/TikTok content showing the process (builds audience)
- Total investment: $700 (2nd printer + more supplies)
- Time commitment: 2-3 hours/day

PHASE 3 — PART-TIME INCOME ($2,000-5,000/month):
- 2-4 printers running near-continuously
- 40-80 frames per day
- Hire part-time help for post-processing ($12-15/hr)
- Wholesale to local gift shops (50% discount, volume orders)
- Etsy + Shopify + Amazon Handmade presence
- Consider a dedicated workspace (spare room or garage)
- Total investment: $1,500 (additional printers + workspace)

PHASE 4 — FULL-TIME INCOME ($5,000-15,000/month):
- 4-8 printers (or 1-2 Bambu Lab AMS multi-color systems)
- 100+ frames per day production capacity
- Full Shopify store with paid ads (Facebook/Instagram)
- Private label wholesale partnerships
- Seasonal products: holiday frames, baby milestone sets, wedding frames
- Custom B2B orders: real estate agents, photographers, event planners
- Consider LLC formation and business checking account

KEY SCALING MISTAKES TO AVOID:
1. Buying too many printers before validating sales → start with 1, add when sold out
2. Ignoring quality as you scale → one bad review on Etsy tanks your rating
3. Not tracking costs → use the pricing calculator spreadsheet religiously
4. Underpricing at craft fairs → if you sell out in 2 hours, your prices are too low
5. Trying to sell everything everywhere → master 1 channel before adding another

AUTOMATION TOOLS:
- Cura project files: save batch arrangements, one-click slice
- Octoprint (free): remote monitoring, auto-start next job
- Shopify order automation: auto-fulfill, tracking emails
- Social media scheduling: Buffer (free tier) or Later
```

---

## AI Content Generation Checklist

### Lessons That Can Be Fully AI-Generated (10 lessons):

| Lesson | Content Type | AI Tool | Status |
|--------|-------------|---------|--------|
| 1.3 | Filament comparison slides | NotebookLM → Audio | ⬜ |
| 1.7 | Module 1 recap | NotebookLM Audio Overview | ⬜ |
| 2.4 | Tolerances & sizing | NotebookLM → Audio | ⬜ |
| 2.7 | Module 2 recap | NotebookLM Audio Overview | ⬜ |
| 4.2 | Infill patterns | NotebookLM → Audio | ⬜ |
| 5.7 | QC checklist | NotebookLM → Audio | ⬜ |
| 6.1 | Cost breakdown | NotebookLM → Audio | ⬜ |
| 6.2 | Pricing strategy | NotebookLM → Audio | ⬜ |
| 6.4 | Craft fair strategy | NotebookLM → Audio | ⬜ |
| 6.7 | Scaling guide | NotebookLM → Audio | ⬜ |

### NotebookLM Workflow:
1. Create a Google Doc per lesson with the source material above
2. Upload to NotebookLM as a "Source"
3. Add all sources for a module → Generate "Audio Overview" for recap lessons
4. Add individual lesson source → Generate "Audio Overview" for lesson content
5. Download audio → pair with slides created in Gamma.app or Canva
6. Upload final video-with-slides to YouTube (unlisted) → add ID to video-config.js

---

## STL Files Needed (15+ total)

### Module 2 Downloads:
1. `basic-magnet-frame-4x6.stl` — Simple rectangular 4×6 frame, 4 magnet slots
2. `parametric-frame-fusion.f3d` — Fusion 360 parametric source file
3. `snap-clip-test.stl` — Standalone snap-fit clip test piece

### Module 3 Downloads:
4. `retro-tv-frame.stl` — CRT TV shaped frame
5. `polaroid-frame.stl` — Polaroid-style square frame
6. `instax-mini-frame.stl` — Fuji Instax Mini frame
7. `collage-2x2-frame.stl` — 4-photo wallet grid
8. `text-insert-template.stl` — Blank text plate for customization

### Baby Milestone Set (Premium — Module 3/6 bonus):
9–20. `month-01.stl` through `month-12.stl` — Baby month milestone frames (1-12 months) as shown in product reference image

### Module 4 Downloads:
21. `magnet-frame-cura.curaprofile` — Optimized Cura profile
22. `magnet-frame-prusa.ini` — Optimized PrusaSlicer profile
23. `temp-tower.stl` — Temperature test tower

### Module 5 Downloads:
24. `qc-checklist.pdf` — Printable quality control checklist
25. `materials-list.pdf` — Shopping list with links

### Module 6 Downloads:
26. `pricing-calculator.xlsx` — Cost/profit calculator spreadsheet
