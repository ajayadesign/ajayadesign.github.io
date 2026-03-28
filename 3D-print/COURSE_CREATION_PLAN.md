# 3D Print Academy — Course Creation Master Plan

## EXISTING INFRASTRUCTURE
| System | Status | Details |
|--------|--------|---------|
| Auth | ✅ Live | Firebase + Google OAuth (email whitelist in admin) |
| Admin | ✅ Live | 11-module command center at /admin/ |
| Backend | ✅ Live | FastAPI on port 3001 |
| Hosting | ✅ Live | GitHub Pages (ajayadesign.github.io) |
| Payments | ❌ None | Contact form only — need Stripe or Gumroad |
| Student Portal | ❌ None | Need gated access to course content |
| Course Content | ❌ None | 6 modules defined, 0 content created |

---

## PHASE 1: CONTENT CREATION (Weeks 1–4)

### Module-by-Module Production Strategy

#### Module 1: 3D Printing Fundamentals (2 hrs)
| Segment | Type | Tool | Notes |
|---------|------|------|-------|
| Printer anatomy (extruder, bed, frame) | 📹 Film yourself | Phone/webcam + tripod | Point at real printer parts, close-ups |
| Bed leveling demo | 📹 Film yourself | Phone + top-down angle | Show paper test, live leveling |
| Filament types (PLA, PLA+, PETG) | 🤖 AI slides + narration | Gamma.app → ElevenLabs | Side-by-side comparison chart, no filming needed |
| Slicer setup (Cura) | 🖥️ Screen record | OBS Studio (free) | Walk through download → first slice |
| Slicer setup (PrusaSlicer) | 🖥️ Screen record | OBS Studio | Same flow, different slicer |
| First test print walkthrough | 📹 Film yourself | Phone time-lapse | Film entire print start→finish (speed up 50x) |
| Module recap / key takeaways | 🎙️ AI audio | Google NotebookLM | Upload your script → auto-generates podcast-style recap |

#### Module 2: Magnet Frame Design — CAD Basics (3 hrs)
| Segment | Type | Tool | Notes |
|---------|------|------|-------|
| TinkerCAD intro + interface | 🖥️ Screen record | OBS Studio | YOU must narrate, this is your expertise |
| Design first magnet frame in TinkerCAD | 🖥️ Screen record | OBS Studio | Step-by-step, show magnet slot placement |
| Fusion 360 intro + interface | 🖥️ Screen record | OBS Studio | For advanced users |
| Magnet slot tolerances (6×2mm) | 🤖 AI slides + narration | Gamma → ElevenLabs | Diagrams with measurements, AI voice OK |
| Photo insert sizing | 🤖 AI slides | Gamma.app | Table of standard photo sizes with tolerances |
| Snap-fit clip design | 🖥️ Screen record | OBS Studio | Show parametric design in Fusion 360 |
| Export STL + test slice | 🖥️ Screen record | OBS Studio | Export → open in Cura → preview |

#### Module 3: Advanced Frame Designs (3 hrs)
| Segment | Type | Tool | Notes |
|---------|------|------|-------|
| Multi-piece magnetic assemblies | 🖥️ Screen record + 📹 Film | OBS + phone | CAD design on screen, then print + assemble on camera |
| Retro TV frame design | 🖥️ Screen record | OBS Studio | Full CAD walkthrough |
| Polaroid-style frame | 🖥️ Screen record | OBS Studio | Full CAD walkthrough |
| Instax Mini frame | 🖥️ Screen record | OBS Studio | Quick design (simpler dimensions) |
| Multi-photo collage frame | 🖥️ Screen record | OBS Studio | Most complex — grid layout |
| Custom text inserts | 🖥️ Screen record | OBS Studio | Show text tool in CAD, font embedding |
| All 5 STL files walkthrough | 📹 Film yourself | Phone | Show each printed frame, discuss quality |

#### Module 4: Print Optimization & Troubleshooting (2 hrs)
| Segment | Type | Tool | Notes |
|---------|------|------|-------|
| Layer height comparison (0.1 vs 0.2 vs 0.3) | 📹 Film yourself | Phone macro lens | Show physical print quality differences |
| Infill patterns + strength | 🤖 AI slides + narration | Gamma → ElevenLabs | Diagrams of grid/gyroid/honeycomb |
| Speed vs quality tuning | 🖥️ Screen record | OBS Studio | Cura speed settings demo |
| Temperature tower test | 📹 Film yourself | Phone time-lapse | Print a temp tower, show results |
| Fix stringing | 📹 Film yourself | Phone + slicer screen | Show retraction settings + result |
| Fix warping | 📹 Film yourself | Phone | Bed adhesion tricks (glue stick, hairspray) |
| Fix elephant's foot | 📹 Film yourself | Phone | Show before/after with Z-offset |
| Batch printing for production | 🖥️ Screen record + 📹 Film | OBS + phone | Plate multiple frames, show batch output |
| Slicer profiles included | 📦 Download | Google Drive | Pre-configured .curaprofile and .ini files |

#### Module 5: Post-Processing & Finishing (2 hrs)
| Segment | Type | Tool | Notes |
|---------|------|------|-------|
| Sanding technique (grits progression) | 📹 Film yourself | Phone close-up | 120 → 220 → 400 grit, show texture change |
| Priming (filler primer spray) | 📹 Film yourself | Phone | Ventilated area, spraying technique |
| Spray painting technique | 📹 Film yourself | Phone | Even coats, drying time |
| Clear coating for durability | 📹 Film yourself | Phone | Matte vs gloss finish |
| Magnet installation: mid-print pause | 📹 Film yourself | Phone + printer | Pause print, drop magnet, resume — tricky! |
| Magnet installation: post-glue | 📹 Film yourself | Phone close-up | Super glue application, alignment |
| Quality control checklist | 🤖 AI slides | Gamma.app | Printable PDF checklist |
| Materials list with links | 📦 Download | Google Drive | PDF with Amazon/hardware store links |

#### Module 6: Launch Your Magnet Business (2 hrs)
| Segment | Type | Tool | Notes |
|---------|------|------|-------|
| Cost per unit breakdown | 🤖 AI slides + narration | Gamma → ElevenLabs | Spreadsheet: filament + magnets + time + packaging |
| Pricing strategy ($5–$15 retail) | 🤖 AI slides + narration | Gamma → ElevenLabs | Margin analysis, competitor pricing |
| Shopify store setup | 🖥️ Screen record | OBS Studio | Full walkthrough: create store, listing SEO, photos. Upsell AjayaDesign website builds. |
| Craft fair strategy | 🤖 AI slides + 📹 Film | Gamma + phone | Tips + B-roll of your actual booth setup |
| Product photography | 📹 Film yourself | Phone | Show lighting setup, angles, backdrop |
| Packaging ideas | 📹 Film yourself | Phone | Show your actual packaging process |
| Scaling: hobby → income | 🤖 AI slides + 🎙️ AI audio | Gamma → NotebookLM | Growth trajectory, when to invest in 2nd printer |
| Pricing calculator template | 📦 Download | Google Sheets | Editable Google Sheet template |

---

### Content Production Summary

| Production Type | Modules | Est. Time to Create | Tool Stack |
|-----------------|---------|---------------------|------------|
| 📹 Film yourself (physical demos) | 1,3,4,5,6 | ~12 hours filming + 6 hrs editing | Phone + tripod + OBS for editing |
| 🖥️ Screen record (CAD/slicer/Shopify) | 1,2,3,4,6 | ~8 hours recording + 4 hrs editing | OBS Studio (free) |
| 🤖 AI slides + narration | 1,2,4,5,6 | ~4 hours scripting → 1 hr generation | Gamma.app ($10/mo) + ElevenLabs ($5/mo) |
| 🎙️ NotebookLM audio recaps | All 6 | ~2 hours (upload scripts, generate) | Google NotebookLM (free) |
| 📦 Downloadable resources | 1,4,5,6 | ~3 hours creating | Google Sheets, PDF (Canva free) |

**Total estimated production: ~40 hours over 3–4 weeks**

---

### Tool Stack & Costs

| Tool | Purpose | Cost | Notes |
|------|---------|------|-------|
| **OBS Studio** | Screen record + film editing | Free | Primary recording tool |
| **Gamma.app** | AI slide decks | $10/mo (Plus) | Generate branded slides from scripts |
| **ElevenLabs** | AI voice narration | $5/mo (Starter) | Clone your voice → narrate AI slides |
| **Google NotebookLM** | Podcast-style module recaps | Free | Upload module script → auto-generates audio overview |
| **Canva** | PDFs, checklists, thumbnails | Free tier | Export as PDF for downloadables |
| **Descript** | Video editing (text-based) | $16/mo (Hobbyist) | Edit video by editing transcript — killer for course content |
| **Phone + tripod** | Physical demos | ~$25 tripod | You already have a phone |

**Monthly cost during production: ~$31/mo** (cancel after content is done)

---

## PHASE 2: VIDEO HOSTING & DELIVERY

### Recommended: YouTube Unlisted + Google Drive

| Content Type | Host | Why |
|-------------|------|-----|
| Video lessons | YouTube (unlisted) | Free, unlimited, fast CDN, works on all devices, embeddable |
| STL files | Google Drive (shared link) | Free 15GB, direct download links |
| Slicer profiles | Google Drive | Same folder structure |
| PDF checklists | Google Drive | Same |
| Pricing calculator | Google Sheets | Students get a copy, can edit |

**Why not Vimeo?** $12/mo ongoing cost for password protection, which Firebase Auth already provides for free.

**Why not self-host video?** GitHub Pages has 100MB file limit. A 2-hour module is ~2-4GB.

**Why YouTube unlisted over Drive?** YouTube has adaptive bitrate streaming (auto adjusts quality), better player, chapters support, and subtitle generation. Drive player is clunky.

### Video URL Protection Strategy
- YouTube unlisted URLs **can** be shared if someone leaks them
- **Mitigation**: Embed videos in Firebase-gated pages only. No direct YouTube links exposed.
- If a link leaks → you can re-upload with a new URL and update the embed
- For extra security later: move to Bunny.net Stream ($1/month + $0.01/GB) with signed URLs

---

## PHASE 3: PAYMENT & ACCESS CONTROL

### Option A: Stripe Checkout (Recommended) — DIY, $0/mo fixed cost
```
Flow: CTA button → Stripe Checkout → Webhook → Firebase RTDB → Grant access
```

1. **Stripe Checkout Session**: Create 4 products (STL $29, Course $97, 1-on-1 $149, Bundle $349)
2. **Webhook endpoint**: FastAPI (already on port 3001) receives `checkout.session.completed`
3. **Firebase RTDB update**: Write `{userId: {tier: "bundle", purchased: timestamp, email: "..."}}`
4. **Client-side gating**: JS on course pages checks Firebase Auth + RTDB purchase record
5. **Fee**: 2.9% + $0.30 per transaction. On $97 sale = $3.11 fee → you keep $93.89

**Implementation**: ~1 day to wire up. You already have Firebase Auth + FastAPI backend.

### Option B: Gumroad — Zero code, higher fee
- Upload course as digital product on Gumroad
- They handle payment, delivery, refunds
- **Fee**: 10% per sale. On $97 = $9.70 → you keep $87.30
- **Downside**: Students go to Gumroad, not your branded site
- **Upside**: Zero coding, built-in email sequences, analytics

### Option C: LemonSqueezy — Middle ground
- 5% + $0.50 per transaction. On $97 = $5.35 → you keep $91.65
- Embeddable checkout overlay (stays on your site)
- Handles VAT/tax automatically
- License key system for digital products

### Recommendation: **Start with Stripe (Option A)**
- You already have Firebase + FastAPI
- Lowest fees (2.9%)
- Full brand control (checkout stays on your site domain)
- Student portal on YOUR site, not a third-party
- Can upgrade to subscription model later if needed

---

## PHASE 4: STUDENT PORTAL (on GitHub Pages)

### Architecture
```
/3D-print/
  index.html          ← Public landing page (already built)
  promo.html          ← Public promo card (already built)
  portal/
    index.html        ← Login gate (Google "Sign in to access your course")
    dashboard.html    ← Module list, progress tracking
    module-1.html     ← Gated: embedded YouTube + downloads
    module-2.html     ← Gated
    module-3.html     ← Gated
    module-4.html     ← Gated
    module-5.html     ← Gated
    module-6.html     ← Gated
    downloads.html    ← All STL files, profiles, checklists
```

### Access Control (JS on each gated page)
```javascript
// On every portal page — check Firebase Auth + purchase status
firebase.auth().onAuthStateChanged(async (user) => {
  if (!user) return window.location.href = '/3D-print/portal/';
  const snap = await firebase.database().ref(`courses/${user.uid}`).once('value');
  const data = snap.val();
  if (!data || !data.tier) return window.location.href = '/3D-print/?access=denied';
  // User has access — show content
  document.getElementById('course-content').style.display = 'block';
});
```

### Progress Tracking
- Store module completion in Firebase RTDB: `courses/{uid}/progress/module-1: true`
- Dashboard shows checkmarks per module
- No need for a full LMS — simple checkbox tracking

---

## PHASE 5: 1-ON-1 SESSION BOOKING

### Tool: Calendly (Free tier) or Cal.com (Free, open-source)
- Embed booking widget on course page
- Auto-sends Google Meet/Zoom link
- Student picks available time slot
- You get email + calendar notification

### Session Recording
- Record via Google Meet (built-in recording)
- Upload to student's private Google Drive folder
- Or use Descript to record + auto-transcribe + share

---

## MODULE CREATION PRIORITY ORDER

Prioritize by: (1) what drives sales, (2) what showcases your unique expertise

| Priority | Module | Why First |
|----------|--------|-----------|
| 🥇 1st | **Module 2: CAD Basics** | This is your unique value — nobody else teaches magnet-specific CAD. Makes the best preview/trailer. |
| 🥈 2nd | **Module 5: Post-Processing** | Visually impressive before/after. Great for social media clips. |
| 🥉 3rd | **Module 1: Fundamentals** | Foundation module, funnels beginners in. |
| 4th | **Module 3: Advanced Designs** | Builds on Module 2, keeps students engaged. |
| 5th | **Module 4: Optimization** | Troubleshooting — students need this once they start printing. |
| 6th | **Module 6: Business** | Business module — can be partly AI-generated (slides + narration). |

### Launch Strategy: "Module Drop" Model
- **Week 1**: Launch with Module 2 (CAD) as free preview trailer (2-min clip) + full Module 1
- **Week 2**: Release Module 2 + 5
- **Week 3**: Release Module 3 + 4
- **Week 4**: Release Module 6 → Full course live

This creates urgency ("new module every week!") and lets you iterate based on early student feedback.

---

## CONTENT YOU CAN CREATE THIS WEEK (No filming needed)

These can be generated right now, today, with AI:

1. **All 6 module scripts** — Write detailed scripts for every segment using Claude/ChatGPT
2. **Module recap audio** — Feed scripts to NotebookLM → instant podcast-style recaps
3. **Slide decks** — Gamma.app: paste scripts → auto-generates branded slides
4. **PDF checklists** — Module 4 QC checklist, Module 5 materials list → Canva
5. **Pricing calculator** — Module 6 Google Sheet template (filament cost + time + margin)
6. **Course trailer script** — 60-second script for social media / landing page video
7. **Email onboarding sequence** — 5 emails: Welcome → Module 1 → Module 2 → Check-in → Upsell 1-on-1

---

## FULL TIMELINE

| Week | Milestone | Deliverables |
|------|-----------|-------------|
| **Week 1** | Scripts + AI content | All 6 module scripts, slide decks, NotebookLM recaps, PDFs, calculator |
| **Week 2** | Screen recording | Modules 1, 2, 4 (slicer + CAD recordings via OBS) |
| **Week 3** | Physical filming | Modules 1, 3, 4, 5 (printer demos, post-processing, quality comparison) |
| **Week 4** | Editing + Assembly | Combine screen records + films + AI slides into final videos via Descript |
| **Week 5** | Payment + Portal | Wire up Stripe → Firebase, build /portal/ pages, embed videos |
| **Week 6** | Launch | Push Module 1 + 2 live, social media campaign, promo card distribution |

---

## COST SUMMARY

### One-Time Setup
| Item | Cost |
|------|------|
| Phone tripod | ~$25 |
| Macro lens clip (for close-ups) | ~$15 |
| Ring light (optional) | ~$20 |
| **Total** | **~$60** |

### Monthly During Production (cancel after)
| Service | Cost/mo |
|---------|---------|
| Gamma.app Plus | $10 |
| ElevenLabs Starter | $5 |
| Descript Hobbyist | $16 |
| **Total** | **$31/mo × ~2 months = $62** |

### Ongoing After Launch
| Service | Cost/mo |
|---------|---------|
| Stripe | 2.9% per sale (no monthly fee) |
| YouTube | Free (unlisted hosting) |
| Firebase | Free tier (10K auth/month, 1GB RTDB) |
| GitHub Pages | Free |
| **Total fixed** | **$0/mo** |

### Break-even: First 2 sales at $97 tier ($194) covers ALL setup + production costs (~$122)

---

## QUICK WINS YOU CAN DO RIGHT NOW

- [ ] Write Module 1 script (use Claude — "Write a detailed 2-hour video script for 3D printing fundamentals covering printer anatomy, bed leveling, filament types PLA/PLA+/PETG, slicer setup for Cura and PrusaSlicer, and first test print")
- [ ] Generate Module 1 slides in Gamma.app
- [ ] Upload Module 1 script to NotebookLM → get podcast recap
- [ ] Create Stripe account + 4 products
- [ ] Set up OBS Studio for screen recording
- [ ] Film first segment: printer anatomy (5 min, phone + tripod)
