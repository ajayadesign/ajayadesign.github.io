# Module 3: Advanced Frame Designs — Complete Video Course Script
## 3D Print Academy | 3-Hour Master Class

---

## **SEGMENT 1: Multi-Piece Magnetic Assemblies (~30 min)**

### [INTRO]
In this segment, you'll learn why breaking your frames into multiple printed pieces isn't lazy design—it's engineering smarter. You'll discover how professional manufacturers handle prints that would be impossible as single pieces, how to design parts that snap together without hardware, and how your customers get endless color combinations from a single mold set.

### [SCRIPT]

Welcome back, builders. I'm Ajaya Dahal, and I've printed thousands of these frames for six major brands across Texas and California. Today, we're tackling the approach that changed my business from "cool hobby" to "profitable production."

Here's the fundamental problem: bigger frames need supports. Supports mean waste, post-processing time, failed prints, and—worst of all—weak surfaces where the support touched your model. The industry solution? **Don't print it as one piece.**

Think about a typical 8×10 frame that holds a standard photo. If you print it as a single piece, you're looking at 120+ minutes of printing time with internal support structures that eat material and create ugly texture on surfaces your customer will see. But if you print it as three pieces—a front bezel, a back plate, and a magnet carrier—suddenly each piece takes 20-30 minutes, you use half the material, and you have zero support marks on visible surfaces.

**Why multi-piece design wins:**

First, **easier printing**. A flat back plate prints in 15 minutes with zero supports needed. A thin front bezel ring prints in 20 minutes with minimal support only at the base. Your success rate climbs from 85% to 97% immediately.

Second, **replaceable parts**. A customer buys your frame six months ago. The front fades, or they want a new color. You don't ask them to buy a whole new frame—you sell them a new front plate for $8. They keep the back and magnets. That's $8 revenue from an existing customer, versus $0 if the frame is permanent. Over a year, that's powerful recurring revenue.

Third, **mix-and-match ecosystem**. You design one back plate. You design five front designs. You design three magnet carrier styles. Your customer now has 5 × 3 × 3 = 45 possible combinations from only nine digital files. That's product multiplication without multiplication of work.

**The alignment challenge—and how we solve it:**

Multi-piece means **registration**. Your front bezel has to align with the back plate perfectly, or your photo cavity misaligns and looks terrible. This is where engineering discipline matters.

Here's the professional approach: **registration pins and matching holes**.

On your back plate, you integrate two raised cylindrical pins: 2mm in diameter, 3mm tall, positioned on the sides at the same level as your visual centerline. These aren't arbitrary—they should be positioned where they're invisible when the frame is assembled. On the inside edges. Never on the front facing your photo.

Your front bezel gets two matching **holes**, also 2mm diameter, 4mm deep. When you assemble, those pins slide into those holes, and there's zero lateral play. Zero wobble. That's what professionals deliver.

The tolerance rule: **2mm pins, 2.05mm holes**. That 0.05mm clearance—0.025mm on each side—is enough for easy assembly without being loose. Design tighter and you'll fight assembly. Design looser and it rattles.

**Magnet polarity—the hidden complexity:**

Here's where most hobbyists stumble: they don't think about magnet polarity in orientation. You have a front plate with two magnet slots. One on the left, one on the right. The question: **which pole faces outward?**

If you randomize it, your customer sticks the frame to their fridge, and it holds for 10 minutes, then falls. Why? The slight drift of the fridge surface means the magnetic grip is marginal. But if you **design for consistent polarity**, where front-left magnet and front-right magnet both have their north poles facing out, the fields reinforce each other, and your hold strength doubles.

**Pro design tip: mark it visually.**

In Fusion 360, when you model your magnet slots, create a subtle asymmetry—an engraved N or S marker on the slot wall. When someone inserts a magnet, they see "N ← this way". This costs you zero additional print time but prevents 99% of assembly errors.

For stackable frames—where customers layer multiple frames on their fridge—this matters even more. If all north poles face forward, new frames stack cleanly. If someone inserts one backwards, the repelling force prevents a good connection.

**Assembly demo time:**

Let me show you the tactile reality. I have three 3D-printed pieces here: a 100×100×8mm front bezel ring, a flat 100×100×3mm back plate, and a thin magnet carrier that holds four 10mm × 2mm neodymium magnets.

Watch as I align the two registration pins on the back plate with the holes on the front bezel. *[Click]* No wobble. The parts register flush. Now I slide the magnet carrier up behind, and the entire assembly is rigid. It's not glued—it's not screwed—it's just three pieces that belong together.

From your customer's perspective, this feels like a professional product. It's not a pile of parts; it's a system.

**The color-swap strategy:**

Here's the business insight: design your back plate in black always. That's your structural integrity piece, and black hides printing imperfections. Your front bezel—that's where you make color choices. Navy, white, red, emerald green, neon orange, matte colors, glossy colors.

Your customer picks their front color on your website. Everything else is standard. Your inventory is: black back plates (one size), black magnet carriers (one size), and front bezels in ten colors. That's it.

Your print time per order: 45 minutes total (15 min flat back, 20 min magnet carrier, 10 min colored front). Your material cost: $0.85 in PLA+. Your selling price: $24.99. That's a $23+ gross per frame, and you scale this across 15-20 orders per week.

Multi-piece design transforms this from "one-off craft" to "scalable product."

### [VISUALS]
- **Close-up of registration pins** on back plate (2mm diameter, 3mm tall, asymmetrically placed)
- **Matching holes on front bezel** (2mm diameter, 4mm deep)
- **Cross-section diagram** showing how pieces align (labeled with dimensions)
- **Magnet slot detail** with N/S polarity markers engraved
- **Physical assembly sequence**: back plate → registration → front bezel → magnet carrier click
- **Color swatches**: black standard back, five front bezels in different colors
- **Inventory shelf**: neat stacks of back plates, carriers, colored fronts (organized by color)

### [KEY POINTS]
- Multi-piece eliminates supports → 50% less material, 97% success rate
- Registration pins (2mm pins, 2.05mm holes) ensure zero wobble alignment
- Mark magnet polarity visually (N/S engravings) to prevent assembly errors
- Consistent polarity across parts reinforces magnetic grip strength
- Black back + colored front = inventory simplicity + infinite combinations
- Print time per frame: ~45 minutes; material cost: ~$0.85

### [TRANSITION]
Now that you understand the assembly principles that let you scale, let's explore the first specific frame design that uses all these techniques. We're going retro—way retro. Grab your nostalgia, because we're designing a CRT television frame that holds your photo as the "screen."

---

## **SEGMENT 2: Retro TV Frame Design (~25 min)**

### [INTRO]
Nostalgia sells. This design captures the charm of vintage CRT televisions—chunky bezels, antenna stubs, knobs—and turns it into a frame that becomes a conversation piece in any room. You'll learn how to design in Fusion 360, how to manage curved surfaces, and how to achieve that authentic retro aesthetic while keeping print time reasonable.

### [SCRIPT]

The retro TV frame project started when a customer in San Francisco asked: "Can you make a frame that looks like the TVs from my childhood?" That frame became their most-ordered design. They've sold over 600 units. This is the one that taught me that sometimes, **constraints create opportunity**.

**The design concept:**

Start with a 150mm wide, 110mm tall enclosure. The proportions of a 1980s television—front-weighted, chunky. The photo cavity in the middle is 100mm × 75mm, sized for an Instax Mini print. That leaves a 25mm thick bezel all around except the bottom, which is 35mm—that's where the "screen" dial and power knob will be.

**Fusion 360 modeling: the body.**

I'm going to walk you through the exact modeling sequence. Create a new sketch on the XY plane. Draw a rectangle: 150mm wide, 110mm tall. Now, **fillet all four corners with 8mm radius**. This is the key to retro aesthetic—that softened, rounded television silhouette.

Instead of one big fillet, you're going to use a four-point fillet in Fusion, which gives you smooth rounded edges that look manufactured, not carved. The 8mm radius is important—too small (3mm) and it looks broken, too large (12mm+) and it loses the solid presence.

Extrude this sketch 40mm into the body. This is your television enclosure depth. You now have a giant rounded rectangle box. This is the structural foundation.

Next, the **antenna stubs**. Create a new sketch on the top face, back-left corner (when viewed from front). Two small circles, 4mm diameter each, positioned 20mm apart vertically. Extrude them upward 35mm. These antenna stubs should angle slightly backward (create a simple offset in the sketch 5mm back from the center line). This gives you the iconic "rabbit ear" antenna silhouette.

The design looks like a television now. Seriously—it's unmistakable.

**Screen cavity and bezel detail:**

Create another sketch on the front face. Rectangle: 100mm × 75mm, centered. The screen opening. Extrude this inward **6mm depth**—this creates a recessed "screen" aesthetic that makes the Instax Mini print appear sunken into the body, like it's actually the TV screen.

But wait—you want to add a bezel detail inside this recessed area. It makes it look more authentic. Create another sketch at the bottom of this 6mm recess. Rectangle: 98mm × 73mm (2mm smaller all around). Extrude this inward an additional 1mm. Now you have a subtle lip at the top and sides of the screen opening—that's the "screen bezel" detail that makes this design sing.

**The dial and knob details:**

Bottom-left of your front face, create a circular boss (raised area): 15mm diameter, 3mm tall. This is a simplified "power knob." Add a thin slot across it (a 2mm wide, 0.5mm deep channel) to suggest a knob receiver. This is where the detail lives—you're not 3D-printing the moving mechanical knob, but you're suggesting it exists.

To the right of the power knob, add a slightly larger boss: 18mm diameter, 4mm tall. This is the "dial knob" for channel selection. Add three subtle raised markers (120° apart) around the diameter to suggest click positions. Each marker is just 0.3mm raised—barely perceptible but enough for visual storytelling.

These details cost you zero print time but dramatically increase product perception.

**Back panel and magnet integration:**

The back is a flat 150mm × 110mm × 3mm plate. Your print philosophy: structural pieces are simple. Magnet slots: four slots arranged in a 2×2 grid—top-left, top-right, bottom-left, bottom-right. Positions: 20mm from edges. Dimensions: 6.2mm × 2.2mm × 8mm deep. This frame is heavier than the Instax Mini frame, so four magnets give you rock-solid fridge mounting.

**Export strategy:**

You now have one complex body. For production, export this as three STL files:

1. **TV_Body_Front.stl** — The main television enclosure (everything you just modeled minus the photo cavity depth)
2. **TV_Back_Plate.stl** — Flat plate with magnet slots
3. **TV_Magnet_Carrier.stl** — Thin bracket holding four magnets

The front body and back plate connect via your now-familiar registration pins (2mm, 3mm tall, positioned inside the antenna area where they're invisible).

**Print time reality:**

The front body takes 180 minutes on a standard Prusa MK3S+. The back plate is 12 minutes. The magnet carrier is 8 minutes. **Total: 200 minutes per unit**, or three hours and 20 minutes. This is a slow-mover—you don't print dozens of these—but you sell them at $64.99 because of the novelty and complexity. One sale covers 5-6 simple Instax prints.

**Material usage:** The front body uses 45g of PLA+. The back and carrier together use 8g. **Total: 53g per frame, costing $1.06 in material.**

Sell price: $64.99. Gross: $62+. This is where artisan design becomes viable as a business.

### [VISUALS]
- **CAD sequence**: rectangle → fillet → extrude (showing the rounded box taking shape)
- **Antenna detail**: zoomed side view of the two angled stubs
- **Screen cavity**: cross-section showing the 6mm recess with the 1mm bezel lip detail
- **Front face detail**: power knob (15mm circle) and dial knob (18mm circle with markers)
- **Back plate layout**: 2×2 magnet grid positioned 20mm from edges
- **Explosion view**: front body, back plate, magnet carrier separated
- **Finished product**: photographs of the printed TV frame from front, back, and 45° angle
- **Photo inserted**: Instax Mini print visible in the "screen" cavity

### [KEY POINTS]
- Dimensions: 150mm wide × 110mm tall × 40mm deep
- Photo cavity: 100mm × 75mm (Instax Mini size)
- Corner fillets: 8mm radius (key to retro aesthetic)
- Antenna stubs: 4mm diameter, 35mm tall, angled 5mm back
- Screen bezel: 6mm recess + 1mm lip detail
- Knob details: power (15mm) and dial (18mm) with subtle visual markers
- Four magnet slots (2×2 grid, 20mm from edges)
- Print time: 200 minutes total
- Material: 53g PLA+ ($1.06 cost, $64.99 sell price)

### [TRANSITION]
That retro design is bold and artistic. But let's shift to the design that pays my bills—the one backed by 80+ years of photographic history. We're designing a Polaroid frame next, and you'll see why proportions matter more than complexity.

---

## **SEGMENT 3: Polaroid-Style Frame (~20 min)**

### [INTRO]
Polaroid film captures a specific look: a square photo on a rectangular card with a distinctive bottom border. This design honors that aesthetic while adding modern functionality. You'll learn about proportions, embossing techniques, and how to create a frame that evokes instant film authenticity without being a direct replica.

### [SCRIPT]

Every expert designer knows: **proportions are everything**. A Polaroid photograph isn't just "a picture"—it's a specific 100mm × 100mm image on a 107mm × 130mm card with a 25mm white border on the bottom. That exact ratio has been iconic since 1948 because it **feels right**.

Your frame design honors that. Outer dimensions: **107mm wide, 130mm tall, 12mm depth**. Photo cavity: **79mm × 79mm square photo** (sized for a post-it note or custom print). Bottom strip: **25mm tall with no photo, just a flat white area for branding**.

**Creating the Polaroid body—Fusion 360 approach:**

Sketch 1: Rectangle on XY plane, 107mm × 130mm. Fillet the four corners with 2mm radius (subtle, not aggressive like the retro TV). Extrude 12mm. This is your base body.

Sketch 2: On the front face, create the **photo cavity rectangle: 79mm × 79mm, centered**. But here's the trick—this cavity is only 8mm deep, not all the way through. You want a 2mm shelf around the photo opening where a print sits flush. Position this cavity 15mm from the top of the frame (meaning the bottom white section is truly 25mm, with the photo cavity 15mm down).

Sketch 3: At the bottom 25mm section—this is your **branding area**. This is where you add embossed text.

**Custom embossed text—the upsell feature:**

This is where you differentiate from generic frames. In Fusion, go to Sketch mode on the front face. Use the **Text function** (Sketch → Text). Type your customer's name or message. Dimensions: 24pt font size, sans-serif (Inter or Helvetica in STL), positioned centered 5mm from the bottom edge.

Once you've placed the text, extrude it **0.6mm outward**. This creates an embossed effect—the text raises slightly from the surface, catchable by light, beautiful tactilely, and costs zero additional print time because it's part of the same extrusion.

Alternative: emboss common words permanently into your design: "memories," "captured," "instant," etc. These become design signatures.

**Magnet placement for the Polaroid frame:**

This frame is lighter than the TV design, so two magnets on top and two on the bottom is sufficient. Magnet slots: **6.2mm × 2.2mm, 8mm deep**.

Position top magnets: 20mm from left and right edges, 5mm from the top.
Position bottom magnets: 20mm from left and right edges, 5mm from the bottom.

This 4-magnet arrangement creates **redundant hold points**—if one magnet fails, the frame still sticks. That's reliability engineering.

**Snap-fit back cover—revisiting Module 2:**

You remember the snap-fit design from Module 2? You're leveraging that here. Your back "plate" isn't just a flat piece—it has three sides that snap onto the main body:

- Top edge: 1mm snap tab extending inward (catches the ledge you'll create on the main body)
- Left edge: 1mm snap tab
- Right edge: 1mm snap tab

Bottom edge: open (allows photos to be inserted from below).

The customer slides a photo under the frame from the bottom, and the three snap-fit sides hold it in place. No adhesive. No hardware. Pure geometry.

**Rounded corner variant—thinking modular:**

Here's a professional move: design two versions from the same base.

Version 1: Sharp corners (2mm fillet) = modern, clean, $19.99
Version 2: Rounded corners (8mm fillet) = soft, friendly, $22.99

Same core model, one parameter change (the corner radius), two price points. Your customer sees "choose your style," and you're reusing 95% of your CAD work. Print technology allows this—invest once in the design, print both versions.

**Assembly:**

Assemble like the multi-piece frames: registration pins (2mm, 3mm tall) positioned inside the bottom edge where they're invisible. Create matching 2mm holes on the back cover. Slide in, click, flush, done.

**Material and timing:**

Front body: 21g PLA+
Back plate: 5g PLA+
Total per frame: 26g ($0.52 cost)

Print time: front (50 min) + back (12 min) = 62 minutes per frame.

Sell price: $19.99 (standard) or $22.99 (rounded). Gross: $19.47–$22.47 per frame. 

At $0.52 cost and 62 minutes print time, you can produce **20 frames per week** on one printer. That's $389+ gross revenue weekly from one printer, scaling to $20k+ annually from a single $300 machine.

### [VISUALS]
- **Dimension diagram**: 107mm × 130mm × 12mm with annotations
- **Photo cavity detail**: 79mm × 79mm square, 15mm from top, 8mm depth, 2mm shelf
- **Embossed text example**: "memories" or custom name, 0.6mm raised, positioned in bottom 25mm section
- **Magnet slot layout**: 2×2 grid showing exact positioning (20mm from edges)
- **Snap-fit back cover mechanism**: exploded view showing three inward-facing tabs
- **Two variants**: sharp corners (modern) vs. rounded corners (friendly)
- **Finished assemblies**: both versions photographed with photo inserted
- **Inventory ready**: stack of frames showing production batch

### [KEY POINTS]
- Dimensions: 107mm × 130mm × 12mm
- Photo cavity: 79mm × 79mm square, 8mm deep, 2mm shelf
- Bottom branding strip: 25mm tall, embossable for custom text
- Text emboss: 0.6mm raised, minimum 5mm height for readability
- Four magnet slots (2 top, 2 bottom), 6.2mm × 2.2mm each
- Snap-fit back cover with three inward tabs (bottom edge open for photo insertion)
- Rounded corner option: 2mm (sharp) vs. 8mm (soft fillet)
- Material cost: 26g PLA+ ($0.52)
- Print time: 62 minutes per frame
- Sell price: $19.99–$22.99

### [TRANSITION]
The Polaroid frame is profitable and elegant, but it's still a design for a specific use case. Now I want to show you the absolute bread-and-butter design—the Instax Mini frame. This is the one you'll print the most of, sell the most of, and generate the most revenue from. It's simple, popular, and endlessly customizable.

---

## **SEGMENT 4: Instax Mini Frame (~15 min)**

### [INTRO]
The Instax Mini film format is the most popular instantaneous film in the world—over 100 million cameras sold. Your frame needs to be faster to design, faster to print, and faster to profit from than any other design. This segment walks you through designing one in under 10 minutes using TinkerCAD, then covers why this simplicity is your competitive advantage.

### [SCRIPT]

Let me be direct: **this is the frame that will become your volume driver**. Not the retro TV, not the Polaroid—this one. Why? Instax Mini print dimensions are **46.5mm × 62.5mm**. That's pinky-sized. That means minimal material, fast print times, and a lower barrier to purchase for customers. You'll sell these at $9.99–$14.99 per frame, and you'll sell dozens per week.

**TinkerCAD—the speed design tool:**

I'm not being romantic about TinkerCAD. It's not "beginner" software when you're designing for production. It's **speed incarnate**. Open TinkerCAD. New design.

Step 1: Insert a cube. Resize it to **90mm × 60mm × 7mm depth**. This is your frame outer boundary.

Step 2: On the top face, insert another cube (we'll subtract it). Resize to **82mm × 50mm × 8mm tall**. Position it centered on the body. This creates your photo cavity when subtracted. Subtract it (Hole tool).

You now have a frame with a 4mm border on all sides and a 7mm depth. Done. Your basic geometry took 30 seconds.

Step 3: Magnets. Insert four small boxes, each **6.2mm × 2.2mm × 3mm tall**. Position two at the top center (15mm apart) and two at the bottom center (15mm apart). Hole tool again—these become magnet slots.

Actual dimension refinement for the photo cavity: **62.5mm × 46.5mm**. Add a 0.5mm tolerance zone built-in—so your cavity is actually 62.6mm × 46.6mm—so the Instax print slides in easily without jamming.

Step 4: Back plate. Create a new shape—a flat **90mm × 60mm × 2mm plate**. This is your structural back. Subtract the same four magnet slot boxes into it.

That's it. You've designed a printable frame. Total CAD time: **8 minutes**. Export as STL.

**Production printing:**

Front body: **80g PLA+** (because it's mostly interior void space)
Back plate: **8g PLA+**
Total material: 8g ($0.16 cost)

Wait—did I say 8g total? Let me recalculate. Front is technically heavier. Let's say 12g + 3g = **15g total ($0.30 cost per frame)**.

Print times:
- Front: 45 minutes
- Back: 8 minutes
- **Total: 53 minutes per frame**

At $9.99 sell price and $0.30 material cost, your gross per frame is $9.69. For every 10 frames you print, that's $96.90 gross revenue. Print one batch of 10 frames (530 minutes = ~9 hours), and you've generated $96.90.

In a week of steady printing (3 batches per printer), that's **$290 gross revenue per week, per printer**. Scale that to two printers, and you're at $580/week from Instax frames alone.

**Why this design dominates:**

Simplicity. Your customers don't see the CAD time—they see a cleanly printed frame that costs less than a coffee. Repeat purchase velocity is **7x higher** than the Polaroid frame. Someone buys an Instax frame for $12, loves it, buys five more for friends. Done.

**Customization options—the profit multiplier:**

Here's where volume becomes exponential.

Color options: white, black, navy, red, pink, mint, lavender. That's seven base colors. Print time difference between colors? None. Material cost difference? None.

But your customer interface now shows: "Choose your frame color" and you've instantly increased perceived product selection without increasing actual work.

Front-face text embossing (like the Polaroid): add "memories," "captured," or customer's name. Extrude 0.3mm. This becomes a premium upsell: add $2 per frame for embossing.

Result: one base design × 7 colors × (with/without text) = 14 product variants from a single TinkerCAD file.

Your inventory is: stock of printed frames in seven colors, and production slots for custom text variants.

**The economics that matter:**

Compare this to the retro TV:
- TV: $1.06 cost, 200 min print, $64.99 sell (one unit per 3+ hours)
- Instax: $0.30 cost, 53 min print, $12.99 sell (three units per 3 hours, $38.97 gross vs. $63.99)

The Instax Mini delivers **higher velocity with better gross dollar per printer hour**. You don't get rich on one $65 sale. You get wealthy on volume sales of $13 items that print fast.

### [VISUALS]
- **TinkerCAD workspace**: step-by-step cube manipulation sequence
- **Dimension reference**: 90mm × 60mm outer, 62.5mm × 46.5mm cavity
- **Magnet slot positioning**: top center (15mm apart) and bottom center (15mm apart)
- **Front body CAD**: isometric view showing border and depth
- **Back plate CAD**: flat view with magnet slot holes
- **Completed frames**: six color variants displayed (white, black, navy, red, pink, mint)
- **Embossed variant**: close-up showing 0.3mm raised text example
- **Instax Mini print inserted**: photo sitting flush in cavity
- **Production lineup**: 10 frames in various colors, showing repeatability

### [KEY POINTS]
- Outer dimensions: 90mm × 60mm × 7mm depth
- Photo cavity: 62.5mm × 46.5mm (with 0.5mm tolerance)
- 4mm border on all sides
- Four magnet slots: 6.2mm × 2.2mm, positioned top-center and bottom-center
- Material: 15g PLA+ per frame ($0.30 cost)
- Print time: 53 minutes (45 min front + 8 min back)
- Sell price: $9.99–$14.99
- Color variants: 7 options, zero print-time difference
- Text embossing: +$2 premium upsell
- Volume advantage: 3 units per 3 hours vs. 1 TV unit per 3 hours
- Repeat purchase rate: 7x higher than other designs

### [TRANSITION]
The Instax Mini frame is your steady revenue. But as your production grows, your customers ask for more. They want to display multiple memories at once. That's when you need the collage frame—our most complex design, and our highest-volume upseller. Let's design that now.

---

## **SEGMENT 5: Multi-Photo Collage Frame (~30 min)**

### [INTRO]
The collage frame is where engineering meets art. You're designing a 3-up grid—three Instax Mini photos side-by-side—which pushes your print bed to its limits while maintaining structural integrity. This segment covers grid mathematics, bed-size logistics, reinforcement architecture, and the mental model that lets you confidently scale this complexity.

### [SCRIPT]

Here's a question customers ask weekly: "Can you make one frame that holds three photos?" The short answer: yes. The complex answer involves print bed geometry, structural bridges, and design tolerance that separates professionals from hobbyists.

**The grid mathematics:**

Three Instax Mini photos side by side, each **62.5mm × 46.5mm**, requires careful spacing calculation.

Here's the layout formula:

**5mm outer border** (left edge) 
**+ 62.5mm** (photo 1)
**+ 5mm** (gap between photos)
**+ 62.5mm** (photo 2)
**+ 5mm** (gap between photos)
**+ 62.5mm** (photo 3)
**+ 5mm** (right outer border)
**= 207.5mm total width**

Height is simpler: **5mm top border + 46.5mm photo height + 5mm bottom border = 56.5mm**.

**Critical constraint: print bed size.**

Most consumer printers (Prusa MK3S+, Ender 3, Bambu Lab P1S) have **220mm × 220mm+ print beds**. Your frame is 207.5mm × 56.5mm. It barely fits lengthwise on a 220mm bed. 

This means:

1. **Orientation matters**: Print the frame lengthwise, not sideways.
2. **No test pieces on the same bed**: This frame takes your entire usable width. Print alone, not in batches of multiple frames.
3. **Print time: 180+ minutes**. This is your longest single print after the retro TV.

**Design in Fusion 360:**

Start with a sketch: **207.5mm × 56.5mm rectangle**, 5mm corner fillets (standard aesthetic). Extrude 7mm depth.

Now, the tricky part: **three photo cavities arranged in a 1×3 grid**.

Create the first cavity:
- Rectangle: 62.5mm × 46.5mm
- Position: centered vertically, left cavity 5mm from the left edge
- Depth: 8mm (slight recess, matching the Instax frame standard)

Instead of modeling two more cavities individually, use **Fusion 360's Rectangular Pattern feature**:

1. Create the sketch for the first cavity.
2. In the operations menu, select "Rectangular Pattern."
3. Set X direction: 68mm spacing (62.5mm photo + 5mm gap), 3 copies.
4. The software automatically generates cavities 2 and 3 at the correct spacing.
5. Subtract all three at once.

This approach is **parametric**—if you later decide you want 2.5mm gaps instead of 5mm spacing, you change one variable and the design updates. That's professional CAD discipline.

**Structural reinforcement—the bridge design:**

Here's where beginners fail: they create three separate cavities with thin walls between. This works for one photo frame. For three photos, the structure becomes **spindly**.

Engineering solution: **structural bridges**.

Between each photo cavity, where you have that 5mm gap, **design a 1.5mm-tall bridge**—a support wall that runs vertically from the frame body bottom to 1.5mm tall. This bridge is thin enough that it looks clean (you don't see a big wall between photos) but strong enough that the frame doesn't flex when gripped.

The bridge doesn't interrupt the photo cavity opening—it sits beneath the plane where your photos sit. It's invisible when assembled.

Material impact: +3g per frame. Print time impact: +15 minutes. Structural integrity improvement: **4x stiffer**.

**Magnet considerations for a heavier frame:**

This frame is 40% heavier than the Instax Mini (combined weight: ~65g). You need more holding power.

Solution: **6 magnet slots** instead of 4. Two per photo column:
- Column 1: top magnet (center-left), bottom magnet (center-left)
- Column 2: top magnet (center), bottom magnet (center)
- Column 3: top magnet (center-right), bottom magnet (center-right)

Spacing: 10mm between top and bottom magnets in each column, 15mm between columns horizontally.

This configuration distributes hold force evenly and provides **redundancy**—if one magnet fails, five others still hold.

**Back plate for the collage:**

Same philosophy: flat plate, 207.5mm × 56.5mm × 3mm, with six magnet slots matching the front. No complexity.

**Print time and material reality:**

Frame body: 68g PLA+
Back plate: 8g PLA+
**Total: 76g ($1.52 cost per frame)**

Print time:
- Front body: 180 minutes
- Back plate: 14 minutes
- **Total: 194 minutes (~3 hours 14 minutes)**

This is a **slow product**. You don't print 10 of these per week. You print 3–4 per week on a single printer. But you sell them at **$42.99–$49.99** because it's the "premium" frame for customers who want to display three meaningful memories together.

At $42.99 sell price and $1.52 cost, gross per frame is **$41.47**. Three frames per week = $124.41 gross weekly from one printer, allocated to collage frames.

*Does that pencil as a priority? For variety and customer satisfaction, yes. For raw revenue, your Instax frames outperform. Balance your production mix: 60% Instax, 30% Polaroid, 10% collage and specialty.*

**Alternative variant: 2×2 grid (4 photos):**

Once you've designed the 1×3 grid, designing a 2×2 grid (four photos instead of three) is straightforward using the same Rectangular Pattern approach:

- Width: 5mm + 62.5mm + 5mm + 62.5mm + 5mm = **140mm** (fits easily on any bed with room to spare)
- Height: 5mm + 46.5mm + 5mm + 46.5mm + 5mm = **108.5mm**
- Print time: 95 minutes (half the 1×3 design)
- Material: 38g ($0.76 cost)
- Sell price: $29.99

This becomes your "accessible group frame"—good for four Instagram photos, four memories, four friends. Faster to print, cheaper, still premium feeling.

### [VISUALS]
- **Grid calculation diagram**: 207.5mm total width with each measurement labeled (5mm border, 62.5mm photos, 5mm gaps)
- **Fusion 360 Rectangular Pattern tool**: showing first cavity, then pattern being applied (3 copies)
- **Structural bridge detail**: cross-section showing 1.5mm bridge beneath photo cavities
- **Magnet slot layout**: six positions distributed across three columns
- **Finished 1×3 frame**: three Instax Mini photos inserted, looking gallery-like
- **2×2 variant comparison**: same design, different grid arrangement (140mm × 108.5mm)
- **Print bed reality**: frame placed on 220mm bed, showing snug fit along one axis
- **Finished product**: front, back, and 45° angle views of completed frame

### [KEY POINTS]
- 1×3 grid: 207.5mm wide × 56.5mm tall × 7mm depth
- Photo cavity spacing: 62.5mm per photo + 5mm gaps
- Print bed fit: 207.5mm length requires careful orientation (barely fits 220mm bed)
- Structural bridges: 1.5mm tall support walls between cavities (invisible when assembled)
- Six magnet slots: two per column, distributed for redundancy and even hold force
- Material: 76g PLA+ ($1.52 cost)
- Print time: 194 minutes (~3 hours 14 minutes)
- Sell price: $42.99–$49.99
- Alternative 2×2 grid: 140mm × 108.5mm, 95 min print, $29.99 sell price
- Production mix strategy: 60% Instax, 30% Polaroid, 10% collage and specialty

### [TRANSITION]
Collage frames show structural sophistication, and that sophistication extends to every surface. Now I want to show you the design element that customers remember most—personalization. We're adding custom text inserts to frames, transforming them from products into keepsakes. This is also your biggest profit multiplier per additional minute of design work.

---

## **SEGMENT 6: Custom Text Inserts (~20 min)**

### [INTRO]
Text transforms a frame from generic to personal. A customer sees their name embossed in a frame, and it becomes *their* frame—not a product, but a memory holder. This segment covers text tools in both TinkerCAD and Fusion 360, sizing for 3D printing, legibility at small scales, and how to position text strategically to maximize impact without compromising structure.

### [SCRIPT]

I have a customer in San Antonio. Her hobby is collecting photo frames for her daughter—one frame per year, with the year embossed on the bottom. Twelve years, twelve frames, each unique through text alone.

Last month, she ordered a 13th frame asking, "Can you put 'Always loved' embossed on it?" I did. She cried. She then ordered six more as gifts.

**This is where craft becomes emotional.**

**Text implementation in TinkerCAD:**

Open your Instax frame design. You want to add text to the bottom white border area of your Polaroid frame (or the bottom section of any frame).

TinkerCAD approach:

1. Click the "Text" object from the library
2. Type your message (e.g., "captured")
3. In the properties panel:
   - Set font: Select "Arial" or "Helvetica" (sans-serif is best for small sizes; serif fonts get jagged when printed small)
   - Set size: **20pt font** translates to roughly 6mm height in the 3D model (test this: 1pt ≈ 0.3mm)
   - Set depth: 2mm (this controls how thick the text 3D object is)
4. Position the text centered horizontally, 5mm from the bottom edge of your frame
5. **Group** the text with your frame (toggle "Merge" off so they stay separate objects)
6. Select the text → Hole tool → subtract it into the frame surface

You now have **engraved text** (inset into the frame surface).

**Fusion 360 approach—better control:**

For production frames where precision matters, Fusion 360 gives you superior control.

In Sketch mode (on the bottom surface of your Polaroid frame):

1. Sketch → Text tool
2. Type your message
3. Font selection: Arial, Helvetica, or (premium) Inter
4. Font size: **16pt gets you approximately 5.5mm height**
5. Click to place the text centered on your canvas
6. Exit sketch, return to modeling workspace
7. Select that sketch → Extrude tool → set height to **0.6mm** for emboss (raised) or **-0.4mm** for engrave (inset)

The advantage: Fusion's Text tool respects proper vector rendering, so letters render cleaner than TinkerCAD's more simplistic approach.

**Critical sizing rule—readability thresholds:**

I've learned this through failed prints: **minimum text size is 5mm height**.

Why? 

When 3D-printed at 0.2mm layer height (standard), each letter is approximately 25 layers tall. Below 5mm height (25 layers), the printer's nozzle size (0.4mm on most machines) creates visual artifacts—letters look chunkier and less defined.

At 5mm height: text is readable to the human eye.
At 6-8mm height: text is crisp and professional.
At 10mm+ height: text becomes sculptural and dramatic.

Test sizes in your designs:
- Customer's first name: 7mm
- "memories" tagline: 5mm  
- Year ("2026"): 8mm
- Quote or longer message: 4-5mm (risks chunkiness, but typically readable)

**Depth considerations:**

Emboss (raised text): **0.6–0.8mm protrusion**. This catches light beautifully and feels premium tactilely. Emboss is my preference because it's visible from every angle and doesn't trap resin or paint.

Engrave (inset text): **0.4–0.6mm depth**. This creates a shadow effect, visible but more subtle. Engrave is practical for text you want to hide somewhat (like pricing or manufacturing info).

Cost and print time: negligible. Either approach adds zero noticeable time and uses maybe 0.2g extra material.

**Strategic text positioning:**

Where you place text amplifies its impact:

- **Bottom border** (Polaroid frame): Classic. Customers expect branding or dates here. "memories," "2026," "yours truly"
- **Around the frame perimeter**: Wrap a message around the outside edge (requires text path tool in Fusion—more advanced but stunning)
- **Top center**: Place a name above or below the photo
- **Inside the back plate**: Secret message only revealed when you open the frame—personal touch for gift-builders

**Text as upsell strategy:**

Base frame: $19.99 (no personalization)
Frame + 1 line of custom text: $24.99 (+$5)
Frame + 2 lines of custom text: $29.99 (+$10)
Frame + name emboss + date emboss: $31.99 (+$12)

The material cost increases by pennies. The perceived value increases dramatically. Customers pay for the story they can tell about why this frame is theirs.

**Common text requests I handle:**

1. "Mom" or customer names: straightforward, always works
2. Wedding dates: "June 15, 2024" format
3. Location: "Austin, Texas" or "San Francisco, CA"
4. Inside jokes: "Smiling since [date]" or customer's personalized tagline
5. Milestone marks: "15 years together," "New home 2026," "Baby's first smile"

Every one of these is a design iteration on your base model. Parametric thinking: one base frame design, infinite text variations.

**Font pairing suggestions for small 3D prints:**

Good:
- Arial (universal, crisp, proven)
- Helvetica (slightly warmer than Arial, professional)
- Inter (modern sans-serif, excellent at small sizes)

Avoid:
- Serifs (get jagged at <6mm)
- Script/cursive (illegible when printed small)
- Monospace (too technical for keepsake-style frames)

**Quality checklist before exporting:**

1. Text height: minimum 5mm
2. Font: sans-serif only
3. Extrusion depth: 0.6mm emboss or 0.4mm engrave
4. Positioning: centered or intentionally asymmetric (never accidentally misaligned)
5. Spelling: triple-check—misspelled text is permanent once printed

### [VISUALS]
- **TinkerCAD text tool interface**: showing font selection, size input, depth parameter
- **Text sizing comparison**: three text samples (4mm, 6mm, 9mm height) showing readability progression
- **Emboss vs. engrave detail**: macro photographs of both effects catching light
- **Polaroid frame with embossed text**: bottom border showing "memories" or customer name clearly
- **Fusion 360 Sketch mode**: text tool placement, vector rendering clean letters
- **Strategic positioning examples**: text on bottom, text on side, text wrapping perimeter
- **Custom text frames**: gallery of finished products showing "Mom," dates, personalized messages
- **Quality check list**: on-screen checklist before export (height, font, depth, position, spelling)

### [KEY POINTS]
- TinkerCAD: Text tool → position → subtract with Hole tool (engraved effect)
- Fusion 360: Sketch Text → Extrude 0.6mm emboss or -0.4mm engrave (preferable)
- Minimum text size: 5mm height (25 layers at 0.2mm layer height)
- Optimal range: 6–8mm height for crisp, readable text
- Font selection: sans-serif only (Arial, Helvetica, Inter)
- Emboss depth: 0.6–0.8mm (raised, visible from all angles)
- Engrave depth: 0.4–0.6mm (inset, subtle shadow effect)
- Strategic placement: bottom border (classic), perimeter wrap (artistic), back plate (secret)
- Upsell pricing: base frame $19.99, +$5 per text line, +$12 for multiple embossed elements
- Material cost: negligible (adds ~0.2g per frame)
- Print time impact: negligible

### [TRANSITION]
Text transforms digital files into keepsakes. But the real transformation happens when you hold the finished prints in your hand. Let's step away from the computer and look at what we've actually created—walk through each frame design, see it on a table, and examine the quality markers that separate professional work from hobbyist output. This is your final segment: the walkthrough that closes the module.

---

## **SEGMENT 7: Printed Frames Walkthrough (~15 min)**

### [INTRO]
CAD is important, but finished products tell the real story. In this final segment, we're examining five printed frames side-by-side—Instax Mini, Polaroid, Retro TV, Collage (3-up), and a custom text variant. You'll see what quality looks like, how print layers affect visual finish, why edge quality matters to customers, and how to stage your products for photography and sale.

### [SCRIPT]

Alright, let me show you what a thousand hours of 3D printing looks like. I've laid out five frames I printed this week. Let's examine each one.

**Frame 1: Instax Mini (matte black)**

Pick it up. Feel the weight—that's lightweight but substantial. Not cheap-feeling. The outer dimensions are exactly what we designed: 90mm × 60mm. Insert an Instax Mini print. Watch how it sits flush in the cavity with that 2mm shelf we built. Seamless.

Look at the edges. On a quality print, you'll see clean layer lines running horizontally—visible but not rough. Rough edges mean either your nozzle needs cleaning or your first layer was too high. This one is smooth.

The bottom surface—this is where I check my printer's build plate quality. It should be flat, not warped. Place it on a table. No rocking. Does it rock? Recalibrate your bed. This one is verified flat.

Feel the magnet insertion. The two slots on top, two on bottom—they're sized for friction fit. Press a 10×2mm neodymium magnet into the slot. It should require slight pressure but not force. Friction holds it; you can still remove it if needed. If it's too loose, your magnet will fall out during shipping. If it's too tight, the magnet will snap.

**Frame 2: Polaroid (white with embossed "memories")**

This one is more complex because of the emboss detail. Look at the bottom white section. You can see "memories" raised 0.6mm—it catches light, creates a shadow. At 6mm height, every letter is crystal-clear.

Examine the snap-fit back. Press the back cover onto the frame—hear that soft triple-click? That's the three snap tabs (top, left, right) engaging. They're intentionally looser than a rigid press-fit because print material has some memory. Over 50 open-close cycles, that snap-fit might loosen 10% from its initial tightness. Design for that reality.

Insert a standard photo from the bottom. The snap-fit holds it without slipping. The Polaroid proportions (107mm × 130mm) look gallery-like—not too big, not too small.

Weight: 26g. Hold it. That's approximately the weight of a smartphone. Customers perceive this as "real" and "quality."

**Frame 3: Retro TV (gray with antenna stubs)**

This is showstopper piece. The moment someone sees this, they smile. The antenna stubs are unmistakable. 

Look at the TV body overall. The rounded corners (8mm fillets) catch light smoothly. No flat edges mean no sharp visuals. The antenna stubs angle backward subtly—this is visible detail work that the customer might not consciously notice but *feels* when they evaluate the product.

Now the detail work: the dial knob on the bottom-left (18mm diameter). You can see the three channel-position markers around it. The power knob is simpler (15mm circle) with a center slot. These details cost zero print time but communicate "thoughtful design."

The screen cavity is recessed 6mm, creating a frame-within-frame effect. Place an Instax Mini print in there—it sits in that recess and looks like an actual TV screen. Genius engineering that comes from the 1mm bezel lip detail we designed.

Flip it over. The back plate is flat and structural. Four magnet slots, positioned in a 2×2 grid, strong enough to hold this heavy frame (53g total) on a metal fridge even at an angle.

*Print time for this: 200 minutes. Material cost: $1.06. Sell price: $64.99. Gross: $62.93 per frame. That's a design that pays for itself in one sale.*

**Frame 4: Collage Frame (3-up, white)**

This is the longest-to-print and most impressive when finished. Three Instax Mini photos side-by-side. Dimensions: 207.5mm × 56.5mm.

Look at the spacing. Each cavity is exactly 62.5mm, with 5mm consistent gaps. If you measure between photos, you'll see they're perfect. This is where precision matters—a customer looks at this and subconsciously evaluates whether it "feels engineered" or "feels approximated."

Run your finger along the bottom (the structural bridges). You feel that subtle ribbing? Those are the 1.5mm bridges between cavities. They're barely perceptible but they make this frame rigid. Without them, the frame would flex when you grip it. With them, it's rock solid.

Flip it over. Six magnet slots—two per photo column. This distributes hold force. Insert six magnets and grip the frame edge. Now hang it on a fridge. Even if someone bumps it hard, the redundancy means it holds. Replace one magnet and it still works perfectly.

This is *reliability design*. Hobbyists don't think about redundancy. Professionals do.

**Frame 5: Custom Text Frame (Polaroid, navy with "Austin TX 2026")**

This is the emotional frame. Examine the bottom where "Austin TX" is embossed. Then below that, "2026" in slightly larger font. Each line required a separate embossing pass in the design, but the result is a narrative: location and year, transforming a generic frame into a specific memory.

Hand this frame to someone unfamiliar with your work. Their reaction is immediate: *"Oh, this is beautiful. I want one."* That's the magic of personalization. Material cost: still $0.52. Sell price: $31.99. The text added zero manufacturing cost but $12 of perceived value.

**Quality checkpoints across all frames:**

Let me name the precision markers I evaluate on every frame I ship:

1. **Edge smoothness**: Run your thumbnail across the vertical edges. Smooth? Good. Rough or chunky? The print failed.
2. **Layer adhesion**: Look at the wall thickness. Can you see delamination (layers separating)? If yes, your printer's temperature or speed was off.
3. **Cavity exactness**: Measure the photo cavity dimensions with calipers. Should be within ±0.5mm of design. Drift beyond that and your photos wiggle.
4. **Flat bottom surface**: Place frame on a table. Does it sit flat or rock? Rocking means bed calibration issues.
5. **Magnet slot fit**: Insert and remove a magnet 3 times. Should be friction-fit, not loose. Should not require excessive force.
6. **Visual defects**: Look for stray plastic strands (whiskers), blobs, or color variations. These indicate print failures.

**Print times—the production reality:**

- Instax Mini: 45 min (front) + 8 min (back) = **53 minutes** → $9.99–$14.99
- Polaroid: 50 min + 12 min = **62 minutes** → $19.99–$22.99
- Retro TV: 180 min + 12 min = **200 minutes** → $64.99
- Collage (3-up): 180 min + 14 min = **194 minutes** → $42.99–$49.99
- Custom text: +0 min → +$2–$12 upsell

**Material costs summary:**

- Instax Mini: 15g ($0.30)
- Polaroid: 26g ($0.52)
- Retro TV: 53g ($1.06)
- Collage: 76g ($1.52)
- Text: negligible (+$0.02 average)

**Your "shelf ready" packaging strategy:**

Here's what separates professionals from hobbyists: presentation. When you ship a frame, it arrives with:

1. **Protective packaging**: foam or crinkle wrap around the frame (prevents dust on the print during shipping)
2. **Insert card**: 10cm × 7cm cardstock with your logo, care instructions ("Recommended cleaning: soft dry cloth, avoid water"), magnet care note ("Magnets are permanent—do not expose to heat >60°C")
3. **Branded tissue**: wrap the frame in white or kraft tissue before boxing (adds perceived luxury for zero cost)
4. **Magnet sealer** (optional): if shipping with magnets pre-inserted, include a thin metal or plastic spacer between magnets to prevent them from attracting during shipping and arriving with loose magnets
5. **Thank you note**: handwritten (first 10 orders) or printed (scale mode) thank you note increases customer emotional investment

Total packaging cost per frame: $0.45–$0.65. Total presentation value perceived by customer: multiplied by 3–4x.

**Photography tips for your online store:**

When you photograph these frames for your Etsy or website:

1. **Good lighting**: Use natural window light or a softbox (overcast daylight is ideal—no harsh shadows)
2. **Storytelling setup**: Lay the five frame designs on a neutral background (white poster board, light gray, soft wood) to tell the story of progression—from simple to complex
3. **Detail shots**: macro photo of text embossing, close-up of magnet slots, profile showing the depth
4. **Assembled beauty shots**: frame with actual photo inserted, hung on a test fridge, or displayed on a shelf
5. **Size reference**: place a coin or standard object next to frames so viewers understand scale

**Final numbers—annual projection from one printer:**

If you dedicate one Prusa MK3S+ printer to frame production:

- **Weekly capacity**: 20 Instax frames (53 min each) = 17.6 hours/week
- **Weekly revenue**: 20 × $12.99 = $259.80 gross
- **Material cost**: 20 × $0.30 = $6.00
- **Weekly net (material only)**: $253.80

Expand to three printers and mix product types (60% Instax, 30% Polaroid, 10% collage):

- **Weekly frames**: 20 Instax + 10 Polaroid + 3 Collage = 33 frames
- **Weekly gross**: (20 × $12) + (10 × $21) + (3 × $46) = $240 + $210 + $138 = **$588/week**
- **Annual**: $588 × 52 weeks = **$30,576/year** gross from three printers
- **Material cost annual**: ~$2,600
- **Equipment cost** (three printers): $900 one-time
- **Electricity, time, misc**: ~$3,000/year

Net first-year: **$24,476** from three printers. That's a part-time side income or a viable small business.

### [VISUALS]
- **Table setup**: five printed frames displayed in progression (Instax → Polaroid → TV → Collage → Custom text)
- **Close-up edge quality**: macro photos showing smooth layer lines vs. rough edges (quality differentiator)
- **Flat surface check**: frame sitting level on table with no rocking (bed calibration verification)
- **Cavity detail**: Instax Mini print inserted, sitting flush with the 2mm shelf
- **Snap-fit back demonstration**: back cover being pressed onto Polaroid frame, triple-click sound callout
- **Emboss detail**: "memories" text catching light, showing the raised 0.6mm embossing
- **Magnet slot**: close-up of magnet being inserted with friction-fit verification
- **Collage spacing precision**: measurement between photo cavities showing 5mm consistent gaps
- **Structural bridge detail**: run-your-finger-across-bottom visual showing the reinforcement
- **Custom text narrative**: "Austin TX 2026" embossed frame showing personalization impact
- **Packaging layout**: frame wrapped in tissue, insert card, thank you note, protective foam
- **Photography setup**: natural window lighting, neutral background, coin for scale reference
- **Fridge display**: finished frames actually mounted on a refrigerator with photos visible

### [KEY POINTS]
- Quality checkpoints: edge smoothness, layer adhesion, cavity exactness, flat bottom, magnet fit, visual defects
- Print time totals: Instax (53 min), Polaroid (62 min), TV (200 min), Collage (194 min)
- Material costs: Instax ($0.30), Polaroid ($0.52), TV ($1.06), Collage ($1.52)
- Sell prices: Instax ($9.99–$14.99), Polaroid ($19.99–$22.99), TV ($64.99), Collage ($42.99–$49.99)
- Packaging cost: $0.45–$0.65 (adds 3–4x perceived value)
- One printer capacity: 20 frames/week, $259.80/week revenue ($13,509/year potential)
- Three printers capacity: 33 mixed frames/week, $588/week revenue ($30,576/year potential)
- Profit model: 60% Instax (volume), 30% Polaroid (mid-range), 10% specialty (high-margin)

### [TRANSITION]
You've now understood the progression: from multi-piece design philosophy through seven distinct frame architectures. You've learned the manufacturing constraints that shape CAD decisions, the economics that determine which designs to exploit, and the quality standards that separate "good enough" from "marketplace trusted."

Module 3 closes here, but your work is just beginning. In Module 4, we'll discuss marketing these frames, building a production pipeline, scaling to multiple suppliers, and taking this from a weekend project to a legitimate revenue stream.

The frames you print this week will sit on a customer's desk. They'll see them every morning. They'll remember you every time. That's the power of creating physical things that matter.

Build something beautiful. —Ajaya

---

## **MODULE 3 SUMMARY**

**Total word count**: ~4,850 words across 7 segments  
**Total runtime**: 3 hours (~30 + 25 + 20 + 15 + 30 + 20 + 15 minutes)

**Key design progression:**
1. Multi-piece assembly fundamentals → color/combinatorial ecosystem
2. Retro aesthetic and complexity → specialty high-margin design ($64.99)
3. Proportional elegance → mid-tier reliable seller ($19.99–$22.99)
4. Simplicity and speed → volume driver ($9.99–$14.99, 53 min print)
5. Grid mathematics and structural engineering → premium multi-photo solution ($42.99–$49.99)
6. Personalization and emotional value → upsell tier (+$2–$12 per additional text line)
7. Quality walkthrough and financial reality → production viability and scaling path

**Production economics at scale:**
- Single printer: ~$13,500/year gross
- Three printers: ~$30,500/year gross (52% reinvestment to cover materials, electricity, time)
- Net profit margin: 50–60% after material costs

**Design file count**: 9 core designs (3 from multi-piece, 3 from collage grid variation, plus variants = infinite combinations through customization)