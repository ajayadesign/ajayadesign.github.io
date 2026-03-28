# Module 2: Magnet Frame Design — CAD Basics Video Course Script

**Total Runtime: ~3 hours | 7 Segments | Beginner-Friendly CAD Mastery**

---

## MODULE INTRODUCTION (2 min)

[VOICEOVER over B-roll of custom magnet frames, hands holding products]

"Welcome to Module 2: Magnet Frame Design — CAD Basics. I'm Ajaya Dahal, and I've designed and printed custom magnet frames for six+ major brands here in Austin. In this module, over the next three hours, we're going to take you from *zero* CAD experience to designing and printing your first production-ready magnet frame.

By the end, you'll understand the tools—TinkerCAD for quick prototypes and Fusion 360 for parametric precision. You'll know exactly how to size photo cavities for Instax, Polaroid, and standard prints. You'll master magnet tolerances—the small measurements that mean the difference between a frame that clicks *just right* and one where magnets fall out or won't seat flush.

And here's the thing: every CAD skill we cover here transfers directly to whatever you want to print next. Magnets, frames, enclosures, custom brackets—they all follow the same logic.

Let's get started."

---

---

## SEGMENT 1: TinkerCAD Intro + Interface (~25 min)

### [INTRO]

In this segment, you'll learn what TinkerCAD is, why it's perfect for magnet frame production, and how to navigate the interface like a pro. We'll create a new project, explore every tool you need, and talk about when TinkerCAD is enough and when you need to upgrade to Fusion 360.

### [SCRIPT]

TinkerCAD is a **free, browser-based CAD program** made by Autodesk. You access it from any computer with a web browser—Windows, Mac, Linux—and it handles 3D design for beginners and professionals alike. The beauty of TinkerCAD is simplicity: you drag shapes onto a workplane, resize them, combine them with holes or unions, and export STL files to your slicer. No downloads, no complicated licensing, no 10-hour learning curve.

I use TinkerCAD for exactly this reason. When I'm designing a one-off frame for a client, I can sketch it in TinkerCAD in 20 minutes, and it's production-ready. The file is small, it's easy to iterate on, and I can share it with team members or clients who might want to make edits.

Let me walk you through setting up your account. Go to **tinkercad.com**, click "Sign Up," and use your Google, Microsoft, or email account. It takes 90 seconds. Once you're in, click "Create New Design" and you'll land in the main workspace.

Here's what you're looking at: On the left, you have the **Shapes panel**—this is your toolkit. Rectangles, cylinders, spheres, pyramids, text, even imported STLs. In the center is the **workplane**, a white grid where you build. This is where your design lives. On the right is the **Inspector panel**—this is where precise dimensions go. Instead of dragging a shape with your mouse (which is imprecise), you can select an object and type exact measurements: X position, Y position, Z position, width, depth, height.

At the top, you have the **main toolbar**: undo/redo, align tools, group/ungroup, flip, mirror, and a hole toggle. That hole toggle is crucial—more on that in a second.

Beneath the workplane, you have a few key buttons. "Shape Generator" lets you create custom parametric designs using code—we'll skip that for now. "Workplane" buttons let you reposition your view. And the **viewcube** in the top-right corner of the workspace is your orientation guide—click a face on that cube to snap to front, top, side views instantly.

Now, **navigation**. You're going to spend half your time moving around your design.

- **Orbit**: Middle mouse button (or right-click and drag on a trackpad). Roll your mouse wheel or two-finger scroll in a trackpad to spin the view around your object.
- **Pan**: Hold Shift + middle mouse and drag to slide your view left/right/up/down without rotating.
- **Zoom**: Scroll wheel. Or hold Ctrl + middle mouse button and drag up/down. Your scroll wheel is your best friend.

These feel awkward for the first 10 minutes. After 30 minutes? Automatic.

Here's the workflow for **basic operations**:

1. **Drag a shape** from the Shapes panel onto the workplane. It lands at the origin (center). You can drag it with your mouse or use the Inspector to set exact coordinates.

2. **Resize**: With the shape selected, you see three colored arrows on the shape—red (X), green (Y), blue (Z). Drag these arrows to resize, or type dimensions in the Inspector. Type `100` in the Width field to make it exactly 100mm wide.

3. **Move**: Select the shape, grab the arrows, and move it. Or use the Inspector. Pro tip: move things to align edges, not centers. It's clearer.

4. **Rotate**: Right-click the shape and choose "Rotate," or use the curved rotation arrows. Or type exact rotation angles in the Inspector.

5. **Group**: Select multiple shapes (Shift+click each one), press Ctrl+G (or click Group top), and now they move as one unit. Perfect when you've positioned multiple parts and don't want them to drift.

6. **The Hole**: This is the game-changer. Select a shape, toggle the "Hole" button in the toolbar (looks like two overlapping circles), and suddenly that shape becomes a **subtractive hole**. It carves out from anything below it. So you can have a base rectangle, then place a cylinder on top and toggle it as a hole—now you have a circular cavity in your base. This is how you create magnet slots.

Why TinkerCAD for magnet frames? Because it's **simple enough for production but parametric enough for sizing**. You can design a frame in 30 minutes, export it, print it, measure the magnets, realize you need the slot 0.2mm larger, go back into TinkerCAD, change one number, and export a new STL. Fusion 360 is more powerful, but for iterative production frames, TinkerCAD's speed is often more valuable.

What TinkerCAD *won't* do easily: **smooth curves, fillets, and complex parametric families**. If you want a rounded edge or a beautiful tapered corner, Fusion 360 handles that better. If you're designing 50 frame sizes (small, medium, large, etc.) and want to change one master dimension and regenerate all sizes, Fusion 360 is the right tool. But for a single-size frame with rectangular cavities and holes? TinkerCAD wins.

That's the boundary you need to understand. Master TinkerCAD first. It gives you 80% of what you need. Then move to Fusion 360 when production demands it.

### [VISUALS]

- **Screen recording**: Navigate to tinkercad.com, sign up, create new design.
- **Close-up**: Point out Shapes panel on left, Inspector panel on right.
- **Highlight**: Toolbar at top (Group, Align, Hole toggle).
- **Demonstrate**: Drag cylinder onto workplane. Drag it around. Type dimensions in Inspector (Width: 50mm, Depth: 50mm, Height: 20mm).
- **Show viewcube**: Click it, snap to Front view, Top view, rotate to isometric.
- **Demonstrate**: Orbit (middle-click drag), Pan (Shift+middle-click), Zoom (scroll).
- **Demonstrate**: Group two shapes, move them as one.
- **Key moment**: Add a cylinder above a rectangle, toggle it as Hole, show the subtraction happen in real-time.

### [KEY POINTS]

- TinkerCAD is **free, browser-based, no installation needed**.
- Left panel = Shapes, Center = Workplane, Right = Inspector (dimensions).
- **Orbit** = middle-click drag to rotate view. **Zoom** = scroll wheel. **Pan** = Shift+middle-click drag.
- **Exact dimensions go in the Inspector**, not by dragging (more precise).
- **Group** shapes to lock them together after positioning.
- **Hole toggle** makes a shape subtractive (carves out a cavity).
- TinkerCAD is ideal for **simple frames with rectangular/circular holes**, limited curves.
- **Fusion 360 next** when you need fillets, complex parametrics, or production families.

### [TRANSITION]

Now that you know the interface, let's put these tools to work. In the next segment, we're going to design your *first* magnet frame from scratch. We'll build a simple Instax Mini holder, work through sizing the photo cavity, add magnet slots, and get hands-on with TinkerCAD's most important workflow: designing for three dimensions and testing with precise measurements.

---

---

## SEGMENT 2: Design First Magnet Frame in TinkerCAD (~30 min)

### [INTRO]

This is where everything comes together. You're going to design a production-ready magnet frame from concept to export. We'll build an Instax Mini holder: a clean rectangular frame with a photo cavity and four corner magnet slots. By the end, you'll have an STL ready to slice and print—and a template you can adapt for any photo size.

### [SCRIPT]

Let's build a magnet frame for Instax Mini photos. These are the small, square instant photos from Fujifilm cameras. They're about 54mm × 86mm as a full card, but the actual *photo area* is 62mm × 46mm. We need to understand this distinction because it changes how we design the cavity.

Here's the design spec we're building today:

- **Base dimensions**: 100mm wide × 70mm deep × 8mm thick
- **Photo cavity**: Instax photo area (62mm × 46mm) with a 5mm border on all sides
- **Photo insert**:  We'll add 0.5mm tolerance on all sides for easy insertion, so 62.5mm × 46.5mm cavity opening
- **Photo depth**: Instax cards are about 0.8mm thick; we'll make the cavity 1.5mm deep so the photo sits in slightly (gives it a recessed look)
- **Magnet slots**: 6.2mm diameter cylinders, 2.2mm deep, one in each corner, positioned 8mm from the edge
- **Magnet specification**: Standard neodymium 6mm × 2mm (you can get these cheap on Amazon for like $5 per 20-pack)
- **Frame walls**: We'll keep at least 4mm wall thickness between the photo cavity and the magnet slots to prevent warping

Let me walk through the build step-by-step.

**Step 1: Create the base rectangle.**

Open TinkerCAD. Drag a **Rectangle shape** from the Shapes panel onto the workplane. Now, in the **Inspector panel** on the right, type:

- Width: `100`
- Depth: `70`
- Height: `8`

Position it at the center (or let's say coordinates X: 0, Y: 0, Z: `4` so the top surface is at Z: 8). Hit Enter and the shape snaps to those dimensions.

You now have your base slab. It's centered on the workplane. Good.

**Step 2: Create the photo cavity.**

This is a hole. Drag another **Rectangle** onto the workplane. In the Inspector, set its dimensions:

- Width: `62.5`
- Depth: `46.5`
- Height: `1.5`

Position it so it's centered on top of the base rectangle. Type X: `0`, Y: `0`, Z: `9.25` (this puts the top of the cavity at Z: 10.75, which is 2.75mm above the base—that's our 5mm recessed border plus tolerance). Actually, let me recalculate: if the base top is at Z: 8, and we want a 5mm border+1mm wall below, we need the cavity to be at Z: 6.5 to Z: 8. So type Z: `7.25` so the top is just at the base surface.

Wait, I'm overcomplicating this. Let me simplify:

**Easier approach**: Center everything at Z: 0. Create the base rectangle with Z: 0 for the bottom, Height: `8`. Now create the photo cavity rectangle at Z: `6.5` (so it sits on top, 1.5mm deep into the base). Set X: `0`, Y: `0` to center it. Now toggle this cavity shape as a **Hole**.

Click the shape. Click the **Hole** button in the toolbar. It turns red and gains a circle icon. Now when you group these together, the cavity will cut into the base.

**Step 3: Add the magnet slots.**

You need four **Cylinder** shapes, one in each corner. Drag a Cylinder onto the workplane. In the Inspector:

- Radius: `3.1` (diameter is 6.2mm, so radius is 3.1mm)
- Height: `2.2`

Position the first cylinder at coordinates:

- X: `46` (this is 100/2 - 4 = 46mm from center; we want 8mm from the edge which is 50mm from center, but let me recalc: base is 100×70, so edges are at ±50 and ±35. Corners are at (±46, ±31) to be 8mm from edges in both directions)
- Y: `29`
- Z: `5.8` (so it sits 1.5mm into the base from the top, with 0.7mm remaining clearance to not break through the bottom)

Toggle this cylinder as a **Hole**.

Now, use **Mirror** to create the other three corners. Select the first magnet cylinder, right-click, and choose "Duplicate." You now have two. Move the duplicate to X: `-46`, Y: `29`. Duplicate again, move to X: `46`, Y: `-29`. Duplicate once more, X: `-46`, Y: `-29`.

You now have four magnet slots, one per corner.

**Step 4: Add the border/lip.**

Optional, but professional-looking: add a thin rectangular lip around the photo cavity to hold the photo in place so it doesn't slide. Create a Rectangle shape:

- Width: `64.5` (photo cavity width + 2mm for the lip on each side = 62.5 + 2)
- Depth: `48.5` (photo cavity depth + 2mm = 46.5 + 2)
- Height: `0.3` (thin lip)

Position it at Z: `8.3` (top of the base, 0.3mm deep into the photo), X: `0`, Y: `0`. Do NOT toggle as a Hole—this is an *additive* feature. This creates a small step that holds the photo in place.

**Step 5: Group and export.**

Select all shapes (Ctrl+A or Shift+click each one). Click **Group** in the toolbar (or Ctrl+G). They're now one object.

Open the **Inspector** if it's closed. You can now see the overall dimensions of your grouped design. Verify:

- The base is 100×70mm
- The photo cavity is 62.5×46.5mm, centered
- Four magnet slots are at the corners
- Total height is 8.2mm (base) + 0.3mm (lip) = 8.5mm

Now, **Export**: Click the "Download" button (or the three-dot menu at the top), select "Download as STL," and save the file. Name it something like `magnet_frame_instax_mini_v1.stl`.

You now have an STL file. Import it into your slicer (Cura, PrusaSlicer, etc.), check the preview, and if it looks right, send it to the printer.

**Pro tip on tolerances**: That 0.5mm we added to the cavity width and depth? That's from experience. A 62mm cavity is *too tight* for a 62mm card; you'll struggle to insert it. 62.5mm gives play. Similarly, the magnet slots are 6.2mm diameter for 6mm magnets—the extra 0.2mm is split evenly (0.1mm per side) as press-fit tolerance. The magnets will sit snug but not stuck.

If you print this and the magnets are too loose or too tight, you adjust in TinkerCAD, change one number (the radius), and reprint. That's the iteration cycle. I go through 2-3 test prints before a design goes to production.

### [VISUALS]

- **Screen recording**: Open TinkerCAD, create new design.
- **Step 1**: Drag Rectangle, set 100×70×8mm, show Inspector with precise values.
- **Step 2**: Drag second Rectangle, set 62.5×46.5×1.5mm, center it, toggle as Hole (show red color change).
- **Step 3**: Drag Cylinder, set radius 3.1mm, height 2.2mm, position at first corner.
- **Mirror**: Duplicate cylinder, move to each corner, toggle each as Hole.
- **Visualization**: Rotate view (use viewcube) to show the cavity and slots from different angles.
- **Step 4** (optional): Add thin lip rectangle on top.
- **Group**: Select all, Group, verify dimensions in Inspector.
- **Export**: Click Download, select STL, save file.
- **Result**: Show the saved STL file in your file browser.

### [KEY POINTS]

- **Base slab = 100×70×8mm**, centered at origin.
- **Photo cavity = 62.5×46.5×1.5mm** (Instax photo area + 0.5mm tolerance, recessed 1.5mm deep).
- **Cavity is a Hole** (toggle in toolbar, turns red).
- **Magnet slots = 6.2mm diameter cylinders, 2.2mm deep, one per corner, 8mm from edges**.
- **Magnet diameter + 0.2mm tolerance** for press-fit (0.1mm each side).
- **Toggle magnet slots as Holes**.
- **Mirror** to quickly duplicate and place symmetrical features.
- **Group** everything before export.
- **Export as STL** for printing.
- **Iterate**: Print → measure → adjust dimensions → reprint.

### [TRANSITION]

Congratulations—you've designed your first magnet frame. It's a solid design that works for Instax Mini, and you can adapt it for any photo size by changing cavity dimensions.

But here's what TinkerCAD *can't* easily do: add smooth fillets to those sharp corners, create a parametric family of sizes (small/medium/large), or generate complex organic shapes. For those, you need **Fusion 360**, the industry standard. In the next segment, we'll introduce Fusion 360, show you the interface, and walk through that first simple design to understand the parametric workflow.

---

---

## SEGMENT 3: Fusion 360 Intro (~25 min)

### [INTRO]

TinkerCAD is fast. Fusion 360 is powerful. In this segment, you'll meet Fusion 360, Autodesk's professional parametric CAD software. It's free for personal use, and it opens up capabilities that take your magnet designs from good to great: rounded corners, complex assemblies, parametric families, and design history that lets you tweak any step—and everything downstream updates automatically. Here's the intro.

### [SCRIPT]

**Fusion 360** is a cloud-based CAD, CAM, and simulation software made by Autodesk. It costs $680/year for professionals, but Autodesk gives it away *free* for personal use, students, and startups with less than $100K revenue. Since you're learning, it's free for you.

The reason Fusion 360 is the industry standard: **parametric design**. In TinkerCAD, you design objects. In Fusion 360, you design *relationships*. You say, "I want a rectangular cavity that's always 0.5mm larger than the photo size." Then you change the photo size, and the cavity automatically scales. Everything downstream updates instantly. This is crucial for production frames where you want to create multiple sizes (Instax Mini, Instax Wide, Polaroid, etc.) without redesigning each one from scratch.

Let me walk you through setup and the interface.

**Getting started:**

1. Go to **autodesk.com/products/fusion-360** and click "Get Free." (If you're a student, use your .edu email for education licensing; if you're under $100K revenue, use the startup program.)
2. Create an Autodesk account. You'll get prompted for a company name (just put your name).
3. Download Fusion 360 for your OS (Windows, Mac, or Linux via browser).
4. Install it (Windows/Mac) or access it via web browser.
5. Open Fusion 360. You'll see a welcome screen. Click "New Design" to create a new project.

Now you're in the **Fusion 360 workspace**. Here's what you're looking at:

**Left side: Browser panel**

This is your design hierarchy. You see:

- **Document** (the overall file)
- **Components** (assembly parts; a frame might have Front, Back, and Magnets as separate components for assembly)
- **Bodies** (individual solid shapes; if you have one frame part, it's one body)
- **Sketches** (2D profiles that become 3D shapes)
- **Features** (history of operations: Extrude, Pocket, Fillet, etc.)

The browser shows your *design history*. Unlike TinkerCAD, where you just have shapes, Fusion has a timeline. You sketch a rectangle, extrude it, add a fillet, subtract a hole—each step is a feature in the timeline. Want to go back and edit the rectangle? Click on the sketch in the browser, and the 3D view reinterprets everything downstream.

**Center: 3D viewport**

This is where your design lives. It's similar to TinkerCAD but more sophisticated. You have a workplane (a flat surface), and you build up from there.

**Top: Toolbar**

This is organized by workflow. The main workflows are **Sketch**, **Model**, **Assemble**, and **Simulation**. Right now, we're in **Model** mode (you see "Model" highlighted at the top). Here, you'll see buttons for:

- **Create** → Extrude, Revolve, Sweep, Loft (turn a sketch into 3D)
- **Modify** → Fillet, Chamfer, Shell, Split (modify existing 3D geometry)
- **Pattern** → Rectangular Array, Circular Array (repeat features)
- And more.

**Right side: Properties panel**

When you select an object or feature, you see its properties here. You can edit dimensions, materials, visibility, etc.

**The workflow:**

Unlike TinkerCAD (drag shapes directly), Fusion 360 uses a **Sketch-to-3D workflow**:

1. **Create a sketch**: You draw a 2D profile on a workplane (a rectangle, a circle, whatever).
2. **Extrude**: You take that sketch and pull it up into 3D, adding thickness.
3. **Add more sketches and features**: Add another extrude, a hole (called a Pocket), a fillet (rounded edge), etc.
4. **Iterate**: Click back on any earlier feature in the browser, edit it, and everything updates.

Let me show you a simple example.

**Simple example: basic box with a hole**

Click **Model** (you should already be there). Look for the **Sketch** button (top toolbar). Click it. You'll be asked to select a plane. You'll see the Top of the object plane appears clickable. Click it.

Now you're in **Sketch mode**. The viewport has shifted to a top-down 2D view. You see a grid and a vertical blue line (the Y axis) and a horizontal red line (the X axis).

Look for the **Rectangle** tool in the toolbar (or press `R` as shortcut). Click it. Now draw a rectangle on the sketch plane: click one corner, drag to the opposite corner. You've drawn a 2D rectangle.

Now, to make this precise, you *constrain* it. In Fusion, you draw roughly, then add constraints (dimensions and geometric rules). In the toolbar, look for **Dimension** (usually a little ruler icon). Click it, then click two parallel edges of your rectangle. A dimension appears asking for a value. Type `50` (for 50mm width). Now click the perpendicular edges, type `40` (height). Your rectangle is now dimensioned.

Click **OK** or press **Escape** to exit Sketch mode. You're back in 3D.

Now, with the sketch selected, click **Extrude** (big button in the toolbar). A dialog opens asking how far to extrude. Type `20` (mm). A preview shows a 50×40×20mm box appearing. Click **OK**. You now have a 3D solid.

Now add a hole. Click **Sketch** again, and this time, click the *top face* of your box. You're now sketching on top of the solid. Draw a circle. Constrain it to 15mm diameter. Exit the sketch.

Click **Pocket** (it's the opposite of Extrude—it carves out). The dialog asks depth. Type `10` (half the height). Click OK. The circle is now a hole, 15mm diameter, 10mm deep.

You just created a box with a hole in two minutes. Every step is in the browser on the left. If you click on the first Rectangle sketch in the browser, you can *edit* it, change it from 50×40 to 60×50, and the entire model—the extrusion, the hole, everything—updates automatically.

**That's parametric design.** One change updates everything downstream. TinkerCAD doesn't do this cleanly. Fusion does.

When to use **Fusion 360 vs TinkerCAD**:

- **TinkerCAD**: Single-size frames, quick prototypes, simple geometry (rectangles, cylinders). Print time: 5 minutes.
- **Fusion 360**: Parametric families (Instax, Polaroid, 4×6 all in one design), complex shapes (rounded edges, tapered walls, press-fit clips), production at scale.

For a freelancer making 50+ frames a month in different sizes, Fusion 360 saves *hours* per design iteration.

Let's move forward. In later segments, we'll design the actual magnet frame in Fusion—complete with snap-fit clips, fillets, and parametric sizing. But first, you need to understand **tolerances**, because magnets and photos are unforgiving. A 0.1mm mistake, and nothing fits.

### [VISUALS]

- **Installation screen**: Download page, account creation, installation (time-lapse).
- **Fusion 360 welcome**: New Design screen.
- **Interface tour**: Browser panel (left), viewport (center), toolbar (top), properties (right).
- **Workflow demo**: Click Sketch → select Top plane → draw a rectangle (rough, 2D).
- **Constrain sketch**: Use Dimension tool → add 50mm width constraint → add 40mm height constraint.
- **Extrude**: Select sketch → click Extrude → type 20 → preview shows 3D box → OK.
- **Add hole**: Click Sketch → draw circle on top face → Dimension (15mm diameter) → Pocket (10mm deep) → OK.
- **Show result**: A 50×40×20mm box with a 15mm hole in top, 10mm deep.
- **Browser highlight**: Show the timeline of sketches and features on the left panel.
- **Edit demo**: Click the first Rectangle sketch in browser, change dimensions to 60×50, show the entire model update.

### [KEY POINTS]

- **Fusion 360 = free for personal use**, industry-standard parametric CAD.
- **Browser panel** (left) shows design hierarchy: Bodies, Sketches, Features.
- **Sketch → Extrude workflow**: Draw 2D profile, pull it into 3D.
- **Parametric**: Edit any sketch or feature, and everything downstream updates automatically.
- **Constraints**: Add dimensional rules to sketches (Width = 50mm) so design is precise and editable.
- **Pocket** = subtractive hole (like Hole in TinkerCAD, but cleaner).
- **When to upgrade to Fusion**: Parametric families, rounded fillets, complex production runs.
- **TinkerCAD for quick one-offs, Fusion for iterative production.**

### [TRANSITION]

Now that you understand Fusion 360's power, let's talk about the *precision* that separates a good frame from a failed print. In the next segment, we dive deep into **magnet tolerances**—exact measurements for different magnet sizes, why ±0.2mm matters, and how to design a tolerance test piece that saves you from printing failure. This is the secret to production-ready frames.

---

---

## SEGMENT 4: Magnet Slot Tolerances (~20 min)

### [INTRO]

Here's the hard truth: a magnet that's too loose falls out. A magnet that's too tight cracks the frame. The difference between success and failure is **0.2 millimeters**. In this segment, you'll learn the exact tolerances for three standard magnet sizes, understand why temperature and material matter, and see how to design a tolerance test piece that catches problems before your main print.

### [SCRIPT]

Let's talk about neodymium magnets. They're small, they're strong, and they're *unforgiving* about fit.

**Standard magnet sizes you'll encounter:**

First, **6×2mm** (diameter × height). This is the most common. Cost: about $0.25 per magnet. Strength: medium (about 2kg pull force). I use these for 80% of frames because they're cheap, reliable, and fit in thin prints.

Second, **8×2mm** (larger diameter, same height). Stronger pull force (about 3.5kg), but they're louder when they click together, and they require a thicker frame wall to seat safely.

Third, **10×3mm** (biggest). Very strong (about 5kg pull), but rare to use because they're expensive and require thick walls.

**The tolerance math:**

Here's the fundamental rule: **Slot diameter = Magnet diameter + 0.2mm**.

So for a 6mm magnet, your slot diameter is **6.2mm**. For an 8mm magnet, it's **8.2mm**. For a 10mm magnet, it's **10.2mm**.

Why 0.2mm? It's split: 0.1mm on each side. This gives you **press-fit tolerance**. The magnet slides in with light pressure—not loose, not stuck. If you cut the tolerance tighter (say, 6.0mm for a 6mm magnet), the magnets won't fit, or they'll crack the plastic as you try to force them in. If you go looser (6.3mm or larger), the magnet rattles and eventually falls out.

The same applies to **depth**. **Slot depth = Magnet height + 0.2mm**.

For 2mm magnets, your slot is **2.2mm deep**. For 3mm magnets, it's **3.2mm deep**. The extra 0.2mm lets the magnet seat flush without hammering it in.

Now, **wall thickness**. This is often ignored and it's a mistake. You need at least **1.5mm of material around the magnet slot** in all directions (except the top, where the magnet sits). Why? Because plastic is thin and brittle. If you have a 6.2mm hole surrounded by only 0.5mm of plastic, that wall will crack under the magnet's press-fit pressure, or it'll flex during printing (sagging), and now your hole is bigger than 6.2mm, and magnets are loose.

So in your frame design, ensure:

- **Magnet slot diameter = magnet diameter + 0.2mm**
- **Magnet slot depth = magnet height + 0.2mm**
- **Minimum wall thickness around slot = 1.5mm** (all sides except top)

**Material matters for tolerance.**

Different plastics shrink differently during cooling. This affects your final dimensions.

- **PLA**: Shrinks 0.3% to 0.5% in X/Y, up to 1% in Z (vertical direction).
- **PETG**: Shrinks 0.5% to 0.8% in X/Y, 1% to 1.5% in Z.
- **ASA**: Similar to PETG, around 0.7% shrinkage.

What does this mean? If you design a 6.2mm hole in Fusion or TinkerCAD, and you print in PLA, the hole might end up **6.15mm** (shrinkage of 0.05mm, or 0.8% of 6.2mm). That's still within tolerance. But if you print the same STL in PETG, it might shrink to **6.1mm** or less, and suddenly your 6mm magnet doesn't fit as cleanly.

**Solution**: Test print. Print one layer of your frame in the material you'll use for production. Measure the hole with calipers. Have a 6mm magnet handy and test-fit it. Does it slide in smoothly? Or is it stuck? Adjust accordingly.

**Temperature effects:**

Magnets themselves can change size slightly with temperature. Most neodymium magnets are rated for -20°C to +80°C. Above 80°C (which is possible in a sunny car or warehouse), they can lose magnetism *permanently*. But for our purposes, thermal expansion of the magnet is negligible (less than 0.01mm over that range).

The *frame* is more sensitive. If you design a frame in a cold room and the customer uses it in a hot environment, the plastic might expand slightly. This is usually negligible for small frames, but if you're designing large structures, keep it in mind.

**Designing a tolerance test piece:**

Here's a pro move: **don't design tolerances by guesswork. Design a test piece first.**

Create a small rectangular slab (50mm × 50mm × 5mm). On this slab, drill five holes:

- 6.0mm hole (slightly too tight for 6mm magnet)
- 6.1mm hole
- 6.2mm hole (correct tolerance)
- 6.3mm hole (slightly loose)
- 6.4mm hole (definitely loose)

Print this test piece in your target material. Test-fit a 6mm magnet in each hole. You'll find that 6.2mm is perfect—the magnet slides in smoothly with light pressure, and it won't fall out.

If 6.2mm feels too tight or loose, you've identified a print-specific tolerance that you can use for *all* future designs. Maybe your printer shrinks more than average, and 6.3mm is actually perfect for *your* machine. Now you know.

**Cross-section diagram (AI slides will show):**

[Imagine a 2D cross-section of a square frame cavity with a magnet inside]

```
Top view:
┌─────────────────┐
│    5mm border   │
│  ┌───────────┐  │
│  │   Photo   │  │
│  │62.5 × 46.5│  │
│  └───────────┘  │
└─────────────────┘
Profile (side view of magnet slot):
┌──────────────────┐
│    Frame wall    │ (≥1.5mm each side)
│   ┌──────────┐   │
│   │ Magnet   │   │ (6mm dia)
│   │6.2mm slot│   │ (actual cavity)
│   └──────────┘   │
└──────────────────┘
   Depth: 2.2mm
```

This diagram shows: magnet at center, slot is 6.2mm (0.1mm on each side of the 6mm magnet), walls are at least 1.5mm thick around it.

### [VISUALS]

- **AI slides**: Show a table with magnet sizes and corresponding slot tolerances:
  - 6×2mm magnet → 6.2mm diameter slot, 2.2mm deep
  - 8×2mm magnet → 8.2mm diameter slot, 2.2mm deep
  - 10×3mm magnet → 10.2mm diameter slot, 3.2mm deep
- **Cross-section diagram**: 2D view of a magnet slot showing the 0.2mm tolerance on each side.
- **Wall thickness diagram**: Show minimum 1.5mm walls around the slot.
- **Shrinkage table**: PLA 0.3-0.5%, PETG 0.5-0.8%, show what 6.2mm becomes after shrinkage.
- **Test piece design**: Show a 50×50×5mm slab with 5 holes (6.0, 6.1, 6.2, 6.3, 6.4mm). Screen record creating this in TinkerCAD or Fusion.
- **Magnet test-fit**: Photo or video of a hand inserting a 6mm magnet into a 6.2mm hole—smooth fit, no forcing.

### [KEY POINTS]

- **Standard magnets**: 6×2mm (most common), 8×2mm (strong), 10×3mm (heavy duty).
- **Slot diameter = magnet diameter + 0.2mm** (0.1mm tolerance per side).
- **Slot depth = magnet height + 0.2mm**.
- **Walls around slots: minimum 1.5mm** to prevent cracking.
- **Material shrinkage**: PLA 0.3-0.5%, PETG 0.5-0.8% (affects final hole size).
- **Test print first**: Create a tolerance test piece with 5 holes (±0.2mm range), test-fit magnets, calibrate for your printer.
- **Thermal expansion**: Minimal effect for small frames, but note for large structures.
- Magnet **tolerances don't forgive**. 6.0mm is too tight. 6.4mm is too loose. 6.2mm is the sweet spot.

### [TRANSITION]

Magnets are one half of the frame equation. The other half is the *photo insert*. Instax, Polaroid, wallet prints, 4×6 standard prints—each has different dimensions. In the next segment, we'll catalog every standard photo size with exact measurements and the cavity tolerances you need to make them fit perfectly, based on the tolerance lesson you just learned.

---

---

## SEGMENT 5: Photo Insert Sizing (~15 min)

### [INTRO]

Photos come in many sizes, and each size demands precise cavity dimensions. In this segment, we'll walk through every photo size you're likely to encounter—from Instax Mini to standard 4×6 prints—and the cavity tolerances that make them *fit just right*. By the end, you'll know the exact dimensions to build for any photo format your customers request.

### [SCRIPT]

Let's start with a reality: **you need to know the difference between the photo image area and the full card size.**

**Instax Mini**: This is the small camera from Fujifilm. The full card is 86mm wide × 54mm tall. But the actual *photo image area* is 62mm × 46mm. The remaining space is a white border (the "instant film" aesthetic). When you're designing a frame for Instax Mini, you're NOT framing the whole card—you're framing the *photo area*. If you build a 86×54mm cavity, the white borders show, and it looks weird. You want 62×46mm, so only the photo is visible.

**Cavity dimension = 62.5mm × 46.5mm** (image area + 0.5mm tolerance on each side for insertion). Depth: **1.5mm** (Instax cards are about 0.8mm thick, so 1.5mm cavity gives a recessed look and accommodates paper thickness variance).

**Instax Wide**: Fujifilm's larger camera. Full card is 216mm × 110mm. Photo area is 62×99mm (wait, that seems narrow... let me correct: actually, Instax Wide image is 62mm × 127mm approximately, but let me consult standard specs... actually, the printed photo on Instax Wide is about 99mm × 62mm—that's the actual image, and the card is larger with white borders).

Actually, let me clarify: Instax Wide film is **210mm × 86mm** total, and the printed image is **99mm × 62mm**. So cavity should be **99.5mm × 62.5mm**. Depth: **1.5mm**.

**Instax Square**: This is Fujifilm's square format. Full card is 86mm × 86mm, and the image area is 62mm × 62mm (it's a square photo on a square card). Cavity: **62.5mm × 62.5mm**, Depth: **1.5mm**.

Now, **Polaroid**. There are different Polaroid formats:

- **Polaroid SX-70** (classic): Full card is 107mm × 88mm, image area is 79mm × 79mm (roughly square). Cavity: **79.5mm × 79.5mm**, Depth: **1.2mm** (Polaroid cards are thinner than Instax). Actually, the standard instant Polaroid now is called **i-Type**, and it's similar to SX-70 dimensions.

- **Polaroid Originals i-Type (modern)**: Same as SX-70, roughly 107mm × 88mm full card, 79mm × 79mm image area. Cavity: **79.5mm × 79.5mm**, Depth: **1.2mm**.

Now the **standard photo prints** (the stuff from CVS, Walgreens, etc.):

- **2×3 (wallet)**: 51mm × 76mm. Cavity: **51.5mm × 76.5mm**, Depth: **0.5mm** (these are thin paper).

- **3×5**: 76mm × 127mm. Cavity: **76.5mm × 127.5mm**, Depth: **0.5mm**.

- **4×6 (most common)**: 102mm × 152mm. Cavity: **102.5mm × 152.5mm**, Depth: **0.5mm**.

- **5×7**: 127mm × 178mm. Cavity: **127.5mm × 178.5mm**, Depth: **0.5mm**.

- **8×10**: 203mm × 254mm. Cavity: **203.5mm × 254.5mm**, Depth: **0.5mm**.

**Why the depth difference?** Instax and Polaroid cards are thick (0.8-1mm), so you need 1.5-1.2mm cavity depth to accommodate and recess them. Standard photo prints are thin (0.1-0.2mm), so 0.5mm depth is enough. Go too deep on a thin photo, and it falls around inside the cavity.

**Lip or friction fit?**

You have two design choices for *keeping the photo in place*:

1. **Lip design**: Add a thin rectangular frame (1mm tall, 0.3mm thick) around the cavity opening. This lip rests on the edge of the photo and holds it in place. Pros: repeatable, looks professional. Cons: requires precise depth control.

2. **Friction fit**: Just rely on a snug cavity (the ±0.5mm tolerance I mentioned). The photo wedges in slightly, and friction keeps it in place. Pros: simple to design. Cons: depends on print tolerance, might fall out if cavity is slightly oversized.

For production, I recommend **friction fit** for simplicity (fewer features = better print reliability). The ±0.5mm tolerance you add to dimensions *is* the friction margin. The photo is 62.0mm wide, cavity is 62.5mm wide—0.5mm play on each side is enough friction to hold at angles.

**Special case: Matte photos**

If your customer is printing with a matte finish (matte paper creates more friction), you might reduce tolerance to ±0.3mm to increase grip. Gloss photos are slippery, so ±0.5-0.7mm is better.

**Frame size around the cavity:**

This is where customer preference comes in. The magnet frame itself (the *outer perimeter*) should be larger than the cavity to look balanced. Common ratios:

- **Small border (3-5mm)**: 62.5mm cavity → 72.5mm×56.5mm outer frame (5mm border). Looks modern, minimal.
- **Medium border (8-10mm)**: 62.5mm cavity → 82.5×66.5mm outer frame (10mm border). Classic Instagram frame look.
- **Large border (15+mm)**: 62.5mm cavity → 92.5×76.5mm outer frame (15mm border). Feels more substantial.

For magnet strength and aesthetic, I usually go with **8-10mm border** for small formats (Instax Mini) and **10-15mm** for larger formats (4×6, 5×7).

**Complete example: Instax Mini frame**

- Outer dimensions: 82mm × 72mm (10mm border on all sides)
- Photo cavity: 62.5mm × 46.5mm (±0.5mm tolerance)
- Cavity depth: 1.5mm (recessed)
- Magnet slots: 4 corners, 6.2mm × 2.2mm
- Wall thickness: 4mm between photo cavity and magnet slots
- Total frame thickness: 8mm

This is your baseline for any Instax Mini frame. Change outer dimensions or border size, but keep the cavity and magnet dimensions—it's what makes the frame fit the photo and magnets.

### [VISUALS]

- **AI slides**: Comprehensive table showing all photo sizes:
  
| Format | Full Size (mm) | Image Area (mm) | Cavity Size (mm) | Depth (mm) |
|--------|---|---|---|---|
| Instax Mini | 86×54 | 62×46 | 62.5×46.5 | 1.5 |
| Instax Wide | 210×86 | 99×62 | 99.5×62.5 | 1.5 |
| Instax Square | 86×86 | 62×62 | 62.5×62.5 | 1.5 |
| Polaroid i-Type | 107×88 | 79×79 | 79.5×79.5 | 1.2 |
| 2×3 Wallet | 51×76 | 51×76 | 51.5×76.5 | 0.5 |
| 4×6 Standard | 102×152 | 102×152 | 102.5×152.5 | 0.5 |
| 5×7 | 127×178 | 127×178 | 127.5×178.5 | 0.5 |

- **Visual examples**: Photos of actual Instax, Polaroid, and standard prints placed next to their frame cavities.
- **Lip diagram**: Cross-section showing optional lip (1mm tall) holding photo in place vs. friction-fit cavity.
- **Border size comparison**: Show same cavity with 3mm, 8mm, and 15mm borders — demonstrate visual difference.
- **Tolerance tolerance chart**: Show what happens if cavity is too tight (photo doesn't fit) or too loose (falls around).

### [KEY POINTS]

- **Know the image area, not just the card size.** Instax Mini image: 62×46mm (not 86×54mm full card).
- **Cavity dimensions = image area ± 0.5mm tolerance** for easy insertion.
- **Depth matters**: Instax/Polaroid 1.5mm (thick), Standard prints 0.5mm (thin).
- Instax Mini cavity: **62.5×46.5×1.5mm**
- Instax Wide cavity: **99.5×62.5×1.5mm**
- Polaroid cavity: **79.5×79.5×1.2mm**
- 4×6 cavity: **102.5×152.5×0.5mm**
- **Friction fit** (just tolerance) is simpler than lip design for production.
- **Outer frame border**: 8-10mm for Instax Mini (looks professional and balanced).
- Matte photos have more friction; reduce tolerance to ±0.3mm if desired.

### [TRANSITION]

You now know exact dimensions for any photo size and exact magnet tolerances. You can design a cavity for Instax Mini, Polaroid, or 4×6 prints and know it'll fit. But a frame is more than a cavity—it's a *product*. The next segment is about design details that make a frame feel premium: **snap-fit clips** that hold the frame together without glue, creating a multi-piece assembly that's elegant and reusable. This is where Fusion 360's advanced features shine.

---

---

## SEGMENT 6: Snap-Fit Clip Design (~20 min)

### [INTRO]

A single-piece frame is simple but boring. A two-piece frame held together with snap-fit clips feels *professional*. The front piece holds the photo, the back piece holds the magnets, and they click together with a satisfying *snap*. In this segment, you'll learn to design snap-fit clips—the flexible beams that make this work—and understand how material, deflection angle, and print orientation all affect success or failure.

### [SCRIPT]

**What is a snap-fit?**

A snap-fit (or snap-hook) is a small plastic feature that flexes to allow assembly, then locks in place. Think of a phone case: the back snaps onto the front. Or a battery cover on a remote: it clips on and won't fall off unless you flex it back.

For magnet frames, a snap-fit clip design means:

- **Front piece**: 5mm thick, holds the photo cavity and the lip. Just the frame around the photo—no magnets, so it's lightweight.
- **Back piece**: 3mm thick, holds the four magnet slots. All the weight.
- **Assembly**: The front piece has two or four small cantilever clips that flex outward. You slide the back piece underneath, pushing against clips, and they *snap* into grooves on the back piece. Now it's locked together, no glue, completely reversible.

**Snap-fit geometry**

Here's the ideal snap-fit design (we'll use TinkerCAD or Fusion to build it):

A cantilever clip is a **small beam** that sticks out from the edge. In 2D cross-section, it looks like:

```
Front piece edge profile:
    │ Frame wall
    │
    └─→  This is the clip (beam)
        ╱─── Grip surface (0.5mm deep)
        │    ╲
        │      (1.5mm wide)
        │
    ╱─ Hook end (points down at 45°)
    │
    Start: 8mm from bottom of front piece
```

Here are the exact dimensions:

- **Beam width**: 1.5mm (thin enough to flex, thick enough to not break)
- **Beam length**: 8mm (long enough to get good flex without creating stress points)
- **Beam thickness**: 1.5mm (same as width, makes it a square cross-section, which flexes best)
- **Hook depth**: 0.5mm (the part that engages with a groove on the back piece)
- **Deflection angle**: 30°-45° (the angle the beam needs to flex to lock in place)

**Why these dimensions matter:**

- If the beam is **too thick** (>2mm), it won't flex, and assembly becomes force. You'll crack the plastic or hurt your fingers.
- If the beam is **too thin** (<1mm), it'll flex fine, but the hook breaks on the first assembly/disassembly cycle.
- If the beam is **too short** (<6mm), there's not enough material to absorb the deflection, and stress concentrates at the base, causing cracks.
- If the beam is **too long** (>10mm), deflection is easy, but you need a larger back piece to accommodate the clip travel, and the frame looks awkward.

**Material choice affects snap-fit design:**

- **PLA**: Brittle. Snap-fits are possible but risky. Clips might snap off on the second assembly. Use 1.2mm thickness, not 1.5mm, to reduce cracking risk.
- **PLA+**: Better than PLA, more flex. 1.5mm thickness is safer.
- **PETG**: Better than all PLA variants. It's flexible and durable. Use 1.5mm thickness. Snap-fits work great. Recommended for production frames.
- **TPU/Flexible filament**: Best for snap-fits, but slow to print and requires special nozzles. Overkill for frames, but it exists.

For magnet frames, I recommend **PETG** if the customer is willing to pay more (PETG is ~$5-10/kg more than PLA). If they want cheap, **PLA+ with 1.2mm clips** is acceptable, but advise them: "This design is reversible, but repeated assembly/disassembly may eventually crack the clips."

**Designing the clip in Fusion 360**

Here's how to build it:

1. **Sketch the back piece**: Rectangle 72mm × 62mm × 3mm (Instax Mini back).
2. **Sketch the front piece** on top: Rectangle 82mm × 72mm × 5mm (outer frame).
3. **Add a groove** on the back piece (where the clip hook engages): Sketch a thin rectangular groove (0.5mm deep, 2mm wide) running along the bottom and sides of the back piece, about 1mm inward from the edge.
4. **Design the clips** on the front piece: Create a cantilever beam sketch on the front piece's underside. Extrude it 1.5mm × 1.5mm × 8mm. Add a 0.5mm hook at the end.
5. **Orient the hook** at a 30°-45° angle pointing downward, so when the back piece slides in, the hook engages with the groove.

Actually, scratch that—it's complex in CAD. Here's a **simpler approach** for a first-time design:

- **Front and back pieces are separate**, just fitted tight together by friction (like puzzle pieces).
- No snap-fit clips (too much design complexity).
- The front and back are glued together with a tiny drop of super glue, or they just stay together from friction fit.

This is what I do for **custom production**. Snap-fits are cool, but gluing is faster and more reliable for small batches. Save snap-fits for mass production where you're injection-molding thousands of frames.

**If you want to pursue snap-fits** (for advanced design), I recommend:

1. **Print a prototype first** in PETG.
2. **Test the clip flex**: Assemble the frame. Does the clip bend smoothly? Or does it crack?
3. **Adjust beam thickness**: If it cracks, thicken to 1.7mm. If it's too stiff, reduce to 1.3mm.
4. **Re-print and test** until it feels right.
5. **Then lock in the dimensions** and design the rest of the frame around this clip geometry.

**Alternative: Mechanical interlocks**

Instead of snap-fits, use **cutouts and tabs**:

- Sketch a rectangular tab on the front piece (5mm wide, 10mm long) that sticks out from the bottom edge.
- Sketch a corresponding rectangular cutout on the back piece (5.2mm × 10.2mm) that accepts the tab.
- When you assemble, the tab slides into the cutout, and they're locked in place by friction (or you add a small screw through the tab into the back).

This is **simpler to design, more reliable to manufacture**, and reusable (easy to disassemble if the customer wants to change the photo).

For your first design, I recommend **starting simple**: a friction-fit assembly (just two pieces fitted tightly together, glued). Once you master that, move to mechanical interlocks, then snap-fits.

**Print orientation for clips**

If you do design clip features, **orientation matters**.

- **Best**: Print the frame so the clip points *perpendicular to the build platform* (i.e., clips stick out horizontally). This means no overhangs, and the clip prints cleanly.
- **Worst**: Print the frame so the clip points *up* (parallel to build platform). The hook end is an overhang, which requires support material, which is ugly and needs cleanup.

Use your slicer's *view angles* to confirm before printing.

### [VISUALS]

- **AI slides**: Diagram of snap-fit clip geometry from side view:
  ```
  Side view of clip:
  ┌─────────────────────┐  Front piece (5mm)
  │                     │
  └─────┬───────────────┘
        │ Beam (1.5×1.5×8mm)
        └┗━ Hook (0.5mm deep, 45° angle)
  
        Groove on back piece →  ╱________╱  (engages hook)
  ```

- **Cross-section**: Show the hook engaging with the groove.
- **Material comparison table**: PLA (brittle, risky), PLA+ (okay), PETG (best), TPU (overkill).
- **Clip thickness chart**: Show what happens if too thin vs. too thick.
- **Mechanical interlocks diagram**: Show tab-and-slot design as alternative.
- **Print orientation**: Show correct (clip horizontal) vs. incorrect (clip vertical, needs support) orientation.
- **Screen recording** (optional): Design a simple clip in Fusion 360 (extrude beam, add hook).

### [KEY POINTS]

- **Snap-fit clip**: Flexible cantilever beam with a hook that engages a groove.
- **Ideal dimensions**: 1.5mm wide × 1.5mm thick × 8mm long, 0.5mm hook, 30°-45° deflection angle.
- Material matters: **PETG best**, PLA+ acceptable, PLA risky.
- **Too thin clips** (< 1mm) break. **Too thick clips** (> 2mm) won't flex.
- **Too short** (< 6mm) stresses the base. **Too long** (> 10mm) requires larger back piece.
- **Simpler approach for beginners**: Friction-fit assembly (glued) or mechanical interlocks (tabs and slots).
- **Snap-fits** are for advanced design and high-volume production. Test print and iterate before committing.
- **Print orientation**: Clips should point horizontally (no overhangs) for clean prints.

### [TRANSITION]

Congratulations on learning clip design. For your first frame, you'll probably stick with a simple two-piece friction-fit assembly (simpler, fewer things to break). But now you know the advanced option. 

In the final segment of this module, we'll close the loop: **exporting your design to STL, importing it into your slicer, checking the preview for problems, and sending it to the printer**. This is the bridge between CAD and reality.

---

---

## SEGMENT 7: Export STL + Test Slice (~15 min)

### [INTRO]

Your design is finished. Now it's time to get it into the real world: export an STL file, import it into your slicer, run through a virtual print preview to catch any problems, adjust slicer settings based on learning from Module 1, and send your design to the printer. This final segment ties everything together.

### [SCRIPT]

**Exporting from TinkerCAD**

If you've been designing in TinkerCAD:

1. Make sure your design is grouped (everything should be one object in the browser).
2. Click the **Download** button at the top (or the three-dot menu → Download).
3. Select **"Download as STL."**
4. Your browser will download a file named something like `design_1.stl` or whatever you named the design.
5. Save it to a folder on your computer—I recommend creating a folder like `/my-frames/stl-exports/` to stay organized.

**Note**: TinkerCAD exports are *binary STL*, which is compact (a few MB for a frame) and ready to slice.

**Exporting from Fusion 360**

If you've been designing in Fusion 360:

1. In the browser panel on the left, find your **Body** (the solid part you designed).
2. Right-click it and select **"Save as STL."** (Not "Export"—that's different.)
3. A dialog opens asking for filename and location. Name it clearly: `magnet_frame_instax_mini_v2.stl`.
4. Choose whether to save as **ASCII** or **Binary**. Binary is smaller; use Binary.
5. Click OK. The file is saved.

**Organizing your files**

Pro tip: keep a folder structure like this:

```
/my-magnet-frame-designs/
  /instax-mini/
    magnet_frame_instax_mini_v1.f3d    (Fusion 360 project file)
    magnet_frame_instax_mini_v1.stl    (exported STL)
    magnet_frame_instax_mini_v2.f3d    (newer version)
    magnet_frame_instax_mini_v2.stl
  /instax-wide/
    ...
  /polaroid/
    ...
```

This way, you keep the original design files (Fusion or TinkerCAD projects) *separate* from the STL exports. If you need to edit a design, you open the `.f3d` or TinkerCAD project, make changes, and re-export the STL. Never edit the STL directly (it's mesh data, hard to edit correctly).

**Importing into Cura (or your slicer)**

Now you have an STL. Time to slice.

1. Open **Cura** (or Prusaslicer, SuperSlicer, etc.). I'll assume Cura.
2. Click **File → Open** (or drag the STL file into Cura's viewport).
3. The model appears in the build platform view. It might be at a weird angle.

**Orienting the frame**

Orientation is crucial. You want to **print the frame flat** (the widest face parallel to the build platform).

- **Best**: Print with the 8mm face (the photo cavity face) pointing *down* on the bed, and the magnet slots pointing *up*. This means no overhangs on the magnet part, and the photo cavity is smooth (resting on the bed).
- **Acceptable**: Any flat orientation where the majority of features print without extensive support material.
- **Worst**: Print it at an angle, standing up on an edge. You'll need tons of support material.

In Cura, select your model, then click **Rotate** (icon in the left toolbar). You can manually rotate or right-click and choose **Rotate Around X/Y/Z**. Spin it until it's flat.

**Checking the preview for problems**

This is critical. Before you print, **slice the model** (Cura does this automatically, or press the "Slice" button). The slicer generates toolpaths. In Cura, once sliced, you can:

1. **Switch to "Preview" mode** (see the timeline slider at the bottom).
2. **Drag the timeline** layer by layer and watch how the print builds up.
3. **Look for problems**:
   - **Unsupported overhangs**: The magnet slots should be visible from below (if they're overhangs without support, they'll look messy or collapse).
   - **Support material**: If you see orange/blue support material (depending on your slicer settings) covering the magnet slots, that's bad. You'll have to clean it out. Rotate the model or adjust orientation.
   - **Bridge quality**: If the photo cavity has a thin bridge across it (e.g., if you printed the frame upside down, the cavity opening becomes an overhang), check if the slicer will bridge it successfully.
   - **Missing features**: Make sure all magnet slots, cavities, and clips are there and look correct.

If something looks wrong, go back to the 3D view and **rotate the model** until it looks good in preview.

**Slicer settings recap (from Module 1)**

Remember these settings from Module 1? Apply them now:

- **Layer height**: 0.2mm for speed, 0.1mm for detail. For frames, 0.2mm is fine.
- **Nozzle temperature**: PLA 200-210°C, PETG 230-240°C.
- **Bed temperature**: PLA 60°C, PETG 80°C.
- **Print speed**: 50-60mm/s for detail parts (like magnet slots), 80mm/s for walls.
- **Infill**: 15-20% for frames (strong enough, doesn't waste material). If those magnet slots are wide, you can go 10%.
- **Support**: Enabled if there are overhangs. Disabled if the model is oriented flat.
- **Raft**: Disabled for frames (you want the bottom flat). But if your bed adhesion is iffy, enable it.

For a flat-oriented frame, you probably won't need support material. That's ideal—faster print, no cleanup.

**Checking the slicer preview for magnet slots**

Important detail: **zoom in on the preview and look at the magnet slots**. In a well-oriented frame (flat on the bed with slots pointing up), the slots should show as small circular holes in the preview. If they don't appear, or if they're buried in support material, your orientation is wrong.

Also, **check wall thickness**: The walls around the magnet slots should be at least 1.5mm thick (we designed it that way, but double-check the preview). If they look thin (< 1mm visually), you might have a design error.

**Estimating print time and filament**

Once sliced, Cura shows:

- **Estimated print time** (hours:minutes)
- **Filament weight** (grams) and **cost estimate**

For a single Instax Mini frame:

- **Dimensions**: ~82 × 72 × 8mm
- **Material**: ~30-40 grams
- **Print time**: ~45-120 minutes (depends on settings)
- **Cost**: ~$0.50-1.00 in filament

This is your baseline. If a customer wants a frame, you can quote them: "This will take 90 minutes to print, and cost me $0.75 in material, so my price is $8-12 depending on your color/material choice."

**Saving the sliced project (optional but recommended)**

Before printing, **save the project file** (not just the STL):

- In Cura, click **File → Save Project**.
- This saves all your slicer settings (nozzle temp, infill, etc.) so if you need to reprint the same frame, you just open this project file instead of re-slicing.

**Sending to the printer**

Once sliced and previewed:

1. **Export G-code**: Click **File → Export G-code** (or the USB icon if your printer is connected).
2. Save the G-code file (usually named something like `model.gcode`).
3. Load it onto your printer's SD card (or send via USB/network, depending on your printer).
4. Start the print.
5. **Monitor the first layer**: Watch the first layer print to ensure bed adhesion. If it's going poorly, stop and re-level your bed.
6. Walk away. It'll take 45 minutes to 2 hours.

**After printing: cleanup and quality check**

Once the print finishes:

1. **Remove from bed**: Let it cool slightly (a few minutes), then carefully peel it off the bed. If it's stuck, gently flex the bed or use a plastic spatula.
2. **Remove support material** (if any): Use a flush cutter or pliers. This takes 5-10 minutes for a frame with light support.
3. **Inspect the magnet slots**: Take a 6mm magnet and test-fit it in each corner. Does it slide in smoothly? (Good.) Or is it too tight? (Time to adjust the STL.) Or too loose? (Also time to adjust.)
4. **Insert a test photo**: Place a photo or printout in the cavity. Does it sit well? Does it want to slide around? Take mental notes.
5. **Measure key dimensions** (optional but recommended): Cavity width/depth with calipers, magnet slot diameter, wall thicknesses. Compare to your CAD dimensions. Did it shrink as expected?

**If magnet fit is wrong:**

- **Too loose**: Go back to CAD, reduce slot diameter by 0.1mm (e.g., 6.2mm → 6.1mm), export STL, re-slice, and reprint.
- **Too tight**: Increase diameter by 0.1mm (e.g., 6.2mm → 6.3mm), export STL, re-slice, reprint.
- **Just right**: Keep the file, label it clearly ("magnet_frame_instax_mini_FINAL"), and reuse the dimensions for future frames.

**Saving the successful design**

Once the frame turns out well:

1. Keep the **original CAD project file** (.f3d or TinkerCAD link) saved with a clear name.
2. Keep the **STL file** in a versioned folder (magnet_frame_instax_mini_v1.stl, v2.stl, etc.).
3. Save your **slicer settings** (export project from Cura).
4. Document the **results**: "Tested 2026-03-27. Magnets fit perfectly (6.2mm slots). Photo sits snugly. Print time: 95 min, mass: 35g. Ready for production."

This becomes your **template**. Next time a customer wants an Instax Mini frame, you open this project, change the color, and print. Consistency.

### [VISUALS]

- **Screen recording**: Export STL from TinkerCAD (Download menu).
- **Screen recording**: Export STL from Fusion 360 (Right-click Body → Save as STL).
- **File structure diagram**: Show organized folder structure for designs, projects, exports.
- **Screen recording**: Import STL into Cura, show the model in the viewport.
- **Rotate demonstration**: Drag the model, rotate until it's flat on the build platform (correct orientation).
- **Slicer preview walkthrough**: Show layer-by-layer preview, zoom in on magnet slots, verify they're visible and not buried in support.
- **Timeline in preview**: Drag the timeline slider to show the frame building layer by layer.
- **Final result**: Photo of a finished printed frame, hands holding it, magnet test-fit.
- **Measurement**: Photo of calipers measuring the cavity width (should be ~62.5mm).

### [KEY POINTS]

- **TinkerCAD export**: Click Download → Download as STL → Save locally.
- **Fusion 360 export**: Right-click Body → Save as STL → Choose Binary format.
- **Keep originals**: Store CAD project files (.f3d, TinkerCAD links) separate from STL exports.
- **Flat orientation**: Print the frame lying flat on the bed (widest face down). No overhangs, no support needed.
- **Slicer preview**: Check layer-by-layer preview for unsupported overhangs, missing features, bridge quality.
- **Settings recap**: 0.2mm layer height, 15-20% infill, appropriate nozzle/bed temps for material.
- **Print time estimate**: ~45-120 minutes for single frame, ~30-40g filament, ~$0.75 cost.
- **After printing**: Test-fit magnets in each slot, insert test photo, measure critical dimensions.
- **Iterate if needed**: Tight magnets? Reduce slot diameter 0.1mm. Loose? Increase 0.1mm.
- **Save successful design**: Version the STL, document results, use as template for future frames.

### [TRANSITION & MODULE CLOSE]

Congratulations. You've now mastered the core of custom magnet frame design. You've learned:

- **TinkerCAD**: Fast, simple tool for quick prototypes.
- **Fusion 360**: Professional parametric CAD for complex designs.
- **Tolerances**: The math behind magnet fits (6.2mm slots for 6mm magnets).
- **Photo sizing**: Exact dimensions for Instax, Polaroid, standard prints.
- **Advanced features**: Snap-fit clips (for later).
- **From CAD to printer**: Export, slice, preview, print, test, iterate.

These skills scale from a single frame to a production line. Whether you're printing one frame for yourself or 50 frames for a client, the workflow is the same.

In **Module 3**, we'll cover **scaling to production**: batch printing, material options, cost optimization, and how to take custom orders and fulfill them. We'll also explore design variations (color combinations, custom photo frames for weddings, corporate gift frames, etc.).

For now, **take what you've learned here, design your first frame, print it, and test it**. The real learning happens in that feedback loop. Good luck.

---

**END OF MODULE 2 SCRIPT**

---

## Script Statistics
- **Total word count**: ~5,200 words (excluding intros/transitions)
- **7 segments**: TinkerCAD Intro, First Frame, Fusion 360 Intro, Tolerances, Photo Sizing, Snap-Fit Clips, Export & Slice
- **Detailed specifications**: 20+ exact dimensions, 3 magnet sizes, 7 photo formats, tolerance math, material properties
- **Practical workflow**: Concept → CAD → export → slice → print → test → iterate
- **Production-ready**: Includes organizational structure, quality checks, and template-building practices