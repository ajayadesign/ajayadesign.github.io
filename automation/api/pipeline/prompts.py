"""
AjayaDesign Automation — All AI agent prompt templates.
Ported 1:1 from orchestrator/lib/prompts.js.
"""

# ─────────────────────────────────────────────────────────────
#  DESIGN INTELLIGENCE — Named styles, font pairings, landing patterns
#  Curated reference databases for AI agent decision-making
# ─────────────────────────────────────────────────────────────

DESIGN_STYLES = {
    "glassmorphism": "Frosted glass panels with backdrop-blur, transparency, subtle light borders. Best on dark/gradient backgrounds for tech, SaaS, fintech.",
    "neumorphism": "Soft extruded UI with dual inset/outset shadows on matching-color surfaces. Best for light themes, cards, buttons, dashboards.",
    "claymorphism": "3D clay-like elements with colored shadows, rounded corners, playful depth. Best for friendly/playful brands — pets, kids, education.",
    "aurora-ui": "Animated gradient mesh backgrounds with soft color blobs. Premium feel for SaaS, tech, AI products, startups.",
    "brutalism": "Raw bold typography, stark color blocks, visible grids, anti-design aesthetic. For creative agencies, portfolios, art.",
    "minimalism": "Maximum whitespace, restrained palette (1-2 colors), invisible UI chrome. For luxury, photography, architecture, high-end.",
    "swiss-design": "Grid-based, strong typography hierarchy, clean geometry, systematic spacing. For corporate, editorial, professional services.",
    "dark-luxe": "Near-black backgrounds (#0a0a0f), gold/cream accents, elegant serif type. For luxury, nightlife, premium dining, automotive.",
    "liquid-glass": "Morphing glass shapes with refraction effects, fluid blob backgrounds. For cutting-edge tech, AI products, innovation.",
    "retro-vintage": "Warm grain textures, rounded sans-serif, muted earth tones, nostalgic feel. For cafes, crafts, artisan brands, vintage shops.",
    "organic-natural": "Soft curves, earthy greens/browns, leaf/wave shapes, natural textures. For wellness, eco, farm-to-table, spas, bakeries.",
    "editorial": "Magazine-style layouts, dramatic typography scale, asymmetric grids, pull quotes. For media, fashion, content-rich brands.",
    "motion-driven": "Animation-first design with scroll-triggered reveals, parallax layers, morphing SVGs. For creative agencies, portfolios, entertainment.",
    "gradient-mesh": "Rich multi-stop gradients as primary visual language, vibrant color transitions. For SaaS, startups, events, music.",
    "neo-corporate": "Clean, accessible, professional with geometric accents, blue/navy palette, trust-building. For B2B, finance, healthcare, consulting.",
}

FONT_PAIRINGS = {
    "elegant-serif": [
        ("Playfair Display", "Lato", "Sophisticated, editorial, luxury"),
        ("Cormorant Garamond", "Montserrat", "Refined, high-end, fashion"),
        ("Libre Baskerville", "Source Sans Pro", "Authoritative, legal, publishing"),
        ("DM Serif Display", "DM Sans", "Modern elegance, balanced readability"),
    ],
    "modern-sans": [
        ("Inter", "Inter", "Clean, versatile, SaaS-ready"),
        ("Space Grotesk", "Inter", "Geometric, tech-forward, contemporary"),
        ("Outfit", "Inter", "Friendly, approachable, modern"),
        ("Sora", "Nunito Sans", "Futuristic, geometric, startup"),
        ("Plus Jakarta Sans", "Plus Jakarta Sans", "Premium sans, versatile weight range"),
    ],
    "bold-impact": [
        ("Oswald", "Roboto", "Strong, condensed, sports/fitness"),
        ("Bebas Neue", "Open Sans", "Ultra-bold, industrial, attention-grabbing"),
        ("Anton", "Roboto", "Maximum impact, fitness, events"),
    ],
    "creative-expressive": [
        ("Fredoka", "Nunito", "Playful, rounded, kids/pets/fun brands"),
        ("Righteous", "Poppins", "Retro-modern, entertainment, food"),
        ("Pacifico", "Quicksand", "Handwritten feel, casual, friendly"),
    ],
    "tech-mono": [
        ("JetBrains Mono", "Inter", "Developer-focused, code-inspired"),
        ("Fira Code", "Source Sans Pro", "Technical, precise, engineering"),
        ("IBM Plex Mono", "IBM Plex Sans", "Systematic, corporate tech"),
    ],
    "warm-humanist": [
        ("Merriweather", "Open Sans", "Warm, readable, editorial"),
        ("Lora", "Nunito Sans", "Gentle, inviting, storytelling"),
        ("Vollkorn", "Lato", "Classic warmth, academic, traditional"),
    ],
}

LANDING_PATTERNS = {
    "hero-features-social-proof": "Hero → Feature grid → Testimonials → CTA. The standard conversion machine. Works for most businesses.",
    "video-first": "Full-screen video hero → Brief copy → Services → Contact. High-impact for creative, fitness, events, music.",
    "split-hero-scroll": "50/50 hero (text + image) → Alternating zigzag sections → Stats bar → CTA. Great for services, agencies.",
    "pricing-focused": "Hero with value prop → Feature comparison → Pricing tiers → FAQ → CTA. Best for SaaS, memberships, subscriptions.",
    "portfolio-gallery": "Minimal text hero → Masonry gallery → Selected case studies → About → Contact. For creatives, photographers, agencies.",
    "storytelling-scroll": "Narrative hero → Timeline/journey → Values → Team → CTA. For mission-driven, nonprofits, legacy brands.",
    "product-showcase": "Product hero with angles → Feature deep-dive → Reviews → Trust badges → Buy CTA. For e-commerce, physical products.",
    "local-business": "Hero with location → Services grid → Google reviews → Map/hours → Contact. For restaurants, salons, shops, clinics.",
    "saas-dashboard": "Hero with app screenshot → Feature tabs → Integration logos → Pricing → CTA. For software products, platforms.",
    "appointment-booking": "Hero with booking CTA → Services menu with pricing → Team profiles → Reviews → Booking form. For salons, clinics, spas.",
    "real-estate-search": "Hero with property search overlay → Featured listings → Area guide → Agent profile → Contact. For realtors, property.",
    "event-countdown": "Hero with date countdown → Speakers/lineup → Schedule → Venue → Tickets CTA. For events, conferences, festivals.",
    "long-form-authority": "Hero → Problem statement → Solution → Case studies → FAQ → Consultation CTA. For consultants, law firms, B2B.",
    "minimal-elegant": "Full-viewport hero image → Short about → Selected work → Contact. For luxury, high-end services, weddings.",
}


# ─────────────────────────────────────────────────────────────
#  STRATEGIST — Site planning + information architecture
# ─────────────────────────────────────────────────────────────

STRATEGIST_SYSTEM = """You are a senior web strategist at AjayaDesign, a premium web design studio.

CRITICAL: Every business deserves its OWN visual identity. Do NOT default to the same aesthetic for every client. Think about what makes THIS niche special:
- A bakery → organic-natural style, warm cream tones, artisanal imagery, Playfair Display + Lato
- A tech startup → aurora-ui style, dark mode, electric accents, gradient mesh hero, Space Grotesk + Inter
- A law firm → neo-corporate style, navy/gold, authoritative serif typography, Libre Baskerville + Open Sans
- A yoga studio → organic-natural style, soft pastels, breathing whitespace, flowing curves
- A restaurant → dark-luxe style, moody dark lighting, full-bleed food photography, elegant serif headings
- A photography studio → minimalism style, near-black, image-centric, gallery-focused, minimal chrome
- A fitness gym → motion-driven style, black with electric red/orange, bold condensed Oswald + Roboto
- A SaaS product → glassmorphism style, dark gradient, app screenshots, frosted glass cards, Inter
- A pet grooming service → claymorphism style, playful warm colors, rounded elements, Fredoka + Nunito
- A wedding planner → minimalism style, blush/gold/ivory, romantic serif, Cormorant Garamond + Montserrat
- A healthcare clinic → neo-corporate style, white/teal, trustworthy, Plus Jakarta Sans + Inter
- A creative agency → brutalism style, bold typography, stark contrasts, asymmetric layouts
- A nonprofit → organic-natural style, earthy greens, compassionate, storytelling-scroll pattern
- A real estate agent → neo-corporate style, white/navy, property-focused, Montserrat + Open Sans
- A gaming platform → aurora-ui style, dark with neon purple/cyan, immersive, Space Grotesk + Inter
- An auto dealer → dark-luxe style, near-black with metallic accents, powerful, Bebas Neue + Roboto

Given a client's business details, you create a comprehensive site blueprint as JSON.

Your blueprint MUST include these exact keys:
{
  "siteName": "Business Name",
  "tagline": "Compelling one-liner (max 8 words, punchy, not generic)",
  "pages": [
    {
      "slug": "index",
      "title": "Home",
      "navLabel": "Home",
      "purpose": "What this page accomplishes",
      "sections": ["hero", "features", "testimonials", "cta"],
      "contentNotes": "Specific guidance for the page builder AI"
    }
  ],
  "brandVoice": "adjective, adjective, adjective",
  "colorDirection": {
    "primary": "#hex — rationale",
    "accent": "#hex — rationale",
    "surface": "#hex — main background",
    "surfaceAlt": "#hex — alternate section background",
    "textMain": "#hex — primary text on surface",
    "textMuted": "#hex — secondary text"
  },
  "typography": {
    "headings": "Font Name — rationale",
    "body": "Font Name — rationale"
  },
  "keyDifferentiators": ["What makes this business unique"],
  "siteGoals": "Primary conversion goal",
  "designStyle": "Pick ONE from: glassmorphism | neumorphism | claymorphism | aurora-ui | brutalism | minimalism | swiss-design | dark-luxe | liquid-glass | retro-vintage | organic-natural | editorial | motion-driven | gradient-mesh | neo-corporate",
  "landingPattern": "Pick ONE from: hero-features-social-proof | video-first | split-hero-scroll | pricing-focused | portfolio-gallery | storytelling-scroll | product-showcase | local-business | saas-dashboard | appointment-booking | real-estate-search | event-countdown | long-form-authority | minimal-elegant",
  "fontPairingStyle": "Pick ONE from: elegant-serif | modern-sans | bold-impact | creative-expressive | tech-mono | warm-humanist",
  "creativeMood": "3 adjectives describing the visual feeling (e.g. cinematic, warm, bold)",
  "themeMode": "dark | light | mixed",
  "themeRationale": "Why this theme fits this business",
  "animationStrategy": {
    "heroEffect": "parallax-image | text-reveal | fade-up-stagger | split-screen",
    "sectionReveals": "fade-up-stagger | slide-alternate | zoom-in",
    "hoverEffects": "lift-glow | scale-up | underline-expand"
  },
  "layoutStrategy": {
    "heroStyle": "full-viewport | split-50-50 | asymmetric-overlap | editorial",
    "sectionVariety": ["List 3+ DIFFERENT layout patterns for different sections"]
  }
}

Rules:
- FIRST choose the designStyle, landingPattern, and fontPairingStyle — these drive ALL other decisions
- designStyle must MATCH the niche. A pet groomer gets claymorphism, not brutalism. A law firm gets neo-corporate, not aurora-ui.
- Not every business needs 7 pages. Think about what THIS business actually needs.
- Minimum: Home + Contact. Typical: 3-5 pages.
- Think about the USER JOURNEY: visitor → interested → converted
- Hero section is the most important — give specific CTA guidance, not \"Learn More\"
- ALL colors must pass WCAG AA contrast (4.5:1 for normal text, 3:1 for large)
- Pick dark OR light theme based on the NICHE, not by default
- slug \"index\" is always the homepage. Other pages use descriptive slugs.
- Every page needs at least 3 sections
- contentNotes must be SPECIFIC enough for another AI to generate real copy
- The tagline should be PUNCHY and MEMORABLE, not a generic description

Output ONLY valid JSON. No explanations, no markdown fences."""


def strategist_propose(
    business_name: str, niche: str, goals: str, email: str,
    *, extra_context: dict | None = None,
) -> str:
    extra_lines: list[str] = []
    if extra_context:
        if extra_context.get("location"):
            extra_lines.append(f"Business Location: {extra_context['location']} (use for local SEO keywords)")
        if extra_context.get("existing_website"):
            extra_lines.append(f"Existing Website: {extra_context['existing_website']} (analyze for design patterns, content, branding)")
        if extra_context.get("brand_colors"):
            extra_lines.append(f"Brand Colors: {extra_context['brand_colors']} (PRESERVE these in the color scheme)")
        if extra_context.get("tagline"):
            extra_lines.append(f"Existing Tagline: {extra_context['tagline']}")
        if extra_context.get("target_audience"):
            extra_lines.append(f"Target Audience: {extra_context['target_audience']}")
        if extra_context.get("competitor_urls"):
            extra_lines.append(f"Competitor URLs (study for differentiation): {extra_context['competitor_urls']}")
        if extra_context.get("additional_notes"):
            extra_lines.append(f"Additional Context: {extra_context['additional_notes']}")

    extra_block = ("\n" + "\n".join(extra_lines)) if extra_lines else ""

    return f"""Create a site blueprint for this client:

Business Name: {business_name}
Industry/Niche: {niche}
Goals: {goals}
Contact Email: {email or 'not provided'}{extra_block}

Think carefully about what pages this specific business needs and the ideal user journey."""


def strategist_revise(blueprint: dict, critique: dict) -> str:
    issues = "\n".join(
        f"[{c['severity']}] {c['area']}: {c['issue']} → {c['suggestion']}"
        for c in critique.get("critiques", [])
    )
    import json

    return f"""Revise your site blueprint based on this UX critique:

FEEDBACK:
{issues}

OVERALL: {critique.get('summary', '')}

YOUR PREVIOUS BLUEPRINT:
{json.dumps(blueprint, indent=2)}

Address ALL high and medium severity issues. Output the COMPLETE revised blueprint as JSON."""


# ─────────────────────────────────────────────────────────────
#  CRITIC — UX review + quality gate for blueprints
# ─────────────────────────────────────────────────────────────

CRITIC_SYSTEM = """You are a senior UX critic and accessibility expert at AjayaDesign.
You review site blueprints and provide specific, actionable feedback.

Review criteria:
1. PAGE STRUCTURE: Right number of pages? User journey makes sense?
2. CONTENT STRATEGY: Are contentNotes specific enough for AI to generate real copy?
3. COLOR ACCESSIBILITY: Do proposed colors meet WCAG AA contrast ratios?
4. CONVERSION: Clear CTA path? Every page drives toward conversion?
5. MOBILE: Will this work on mobile? Too many sections = scroll fatigue.
6. SEO: Obvious keyword opportunities being missed?
7. DIFFERENTIATION: Does this feel unique to THIS business, or generic?
8. VISUAL IMPACT: Does the hero strategy grab attention in <3 seconds?
9. ANIMATION STRATEGY: Is the animation approach appropriate for this niche?
10. LAYOUT VARIETY: Are all sections just \"centered text + grid\"? That's boring.
11. EMOTIONAL RESONANCE: Will a visitor FEEL something, or just READ something?
12. THEME FIT: Does the chosen theme (dark/light) suit the niche?
13. DESIGN STYLE COHERENCE: Does the designStyle match the niche? (e.g. glassmorphism for SaaS=good, glassmorphism for bakery=wrong)
14. FONT PAIRING FIT: Does the fontPairingStyle match the brand voice? (e.g. elegant-serif for law=good, creative-expressive for finance=wrong)
15. LANDING PATTERN MATCH: Does the landingPattern serve the conversion goal? (e.g. appointment-booking for salon=good, saas-dashboard for bakery=wrong)

Output format — valid JSON only:
{
  "approved": true/false,
  "score": 1-10,
  "critiques": [
    { "severity": "high|medium|low", "area": "area name", "issue": "specific problem", "suggestion": "specific fix" }
  ],
  "strengths": ["what's good about the blueprint"],
  "summary": "One paragraph overall assessment"
}

Be tough but constructive. Only set approved=false if there are HIGH severity structural problems.
Output ONLY valid JSON."""


def critic_review(blueprint: dict) -> str:
    import json

    return f"""Review this site blueprint:

{json.dumps(blueprint, indent=2)}

Be specific. Don't say "improve the hero" — say exactly what's wrong and how to fix it."""


# ─────────────────────────────────────────────────────────────
#  DESIGNER — Design system generation
# ─────────────────────────────────────────────────────────────

DESIGNER_SYSTEM = """You are the lead visual designer at AjayaDesign. Given a site blueprint, you create a complete design system as a JSON object.

Your output MUST have these exact keys:
{
  "tailwindConfig": "tailwind.config = { theme: { extend: { colors: { primary: '#hex', accent: '#hex', cta: '#hex', ctaHover: '#hex', surface: '#hex', surfaceAlt: '#hex', textMain: '#hex', textMuted: '#hex' }, fontFamily: { heading: ['FontName'], body: ['FontName'] } } } }",
  "googleFontsUrl": "https://fonts.googleapis.com/css2?family=...",
  "bodyClass": "bg-surface text-textMain font-body antialiased overflow-x-hidden",
  "navHtml": "<nav>...</nav>",
  "footerHtml": "<footer>...</footer>",
  "mobileMenuJs": "<script>...</script>",
  "activeNavClass": "text-primary font-bold",
  "inactiveNavClass": "text-textMuted hover:text-primary transition"
}

Rules for navHtml:
- Fixed/sticky header with backdrop-blur-xl and semi-transparent background
- Each nav link MUST use class=\"{{ACTIVE:slug}}\" placeholder
- Mobile: hamburger button that toggles a full-width dropdown menu
- CTA button on far right with hover glow effect
- Smooth transition on scroll (shrink padding on scroll-down)
- ALL links MUST be relative (e.g. href=\"menu.html\", href=\"index.html\"). NEVER use root-relative links starting with / (e.g. NEVER href=\"/menu.html\" or href=\"/\")

Rules for footerHtml:
- Multi-column footer (2-3 columns) with social icon links
- MUST include: Built by <a href=\"https://ajayadesign.github.io\">AjayaDesign</a>
- Copyright year and business name
- ALL internal links MUST be relative (e.g. href=\"menu.html\"). NEVER use root-relative links starting with /

Rules for tailwindConfig:
- Must define all colors: primary, accent, surface, surfaceAlt, textMain, textMuted, cta, ctaHover
- Font families: heading and body
- ctaHover should be a brighter/lighter variant of cta

CRITICAL:
- All colors must pass WCAG AA contrast ratios
- If blueprint specifies designStyle, apply its visual language:
  * glassmorphism: backdrop-blur-xl cards, rgba backgrounds, subtle light borders
  * neumorphism: dual shadows (light + dark) on matching surface color
  * claymorphism: colored drop shadows, large border-radius (20-24px), playful depth
  * dark-luxe: near-black surface, gold/cream accents, subtle gradient overlays
  * aurora-ui: animated gradient mesh background via CSS, floating glass panels
  * brutalism: raw borders, stark mono fonts, visible grid structure
  * minimalism: maximum whitespace, 1-2 colors, invisible chrome
  * organic-natural: soft border-radius, earthy palette, wave/leaf SVG dividers
  * gradient-mesh: rich multi-stop gradients, vibrant transition backgrounds
  * neo-corporate: clean geometry, trust-blue palette, systematic spacing
- The nav must reflect the design style (glassmorphism nav = glass effect, brutalism nav = stark borders, etc.)
- Output ONLY valid JSON. No markdown fences, no explanation."""


def designer_create(blueprint: dict) -> str:
    import json
    from datetime import datetime

    pages_str = ", ".join(
        f"{p.get('navLabel', p['title'])} ({'' if p['slug'] == 'index' else p['slug'] + '.html'})"
        for p in blueprint["pages"]
    )

    design_style = blueprint.get('designStyle', '')
    style_desc = DESIGN_STYLES.get(design_style, '') if design_style else ''
    style_block = f"\nDesign Style: {design_style} — {style_desc}" if design_style else ""

    font_style = blueprint.get('fontPairingStyle', '')
    font_block = ""
    if font_style and font_style in FONT_PAIRINGS:
        pairings = FONT_PAIRINGS[font_style]
        font_block = f"\nFont Pairing Style: {font_style} — options: {', '.join(f'{h}+{b}' for h, b, _ in pairings)}"

    return f"""Create a design system for this site:

Site: {blueprint.get('siteName', 'Unknown')}
Pages: {pages_str}
Brand Voice: {blueprint.get('brandVoice', 'professional')}
Colors: {json.dumps(blueprint.get('colorDirection', {}))}
Typography: {json.dumps(blueprint.get('typography', {}))}
Tagline: {blueprint.get('tagline', '')}
Year: {datetime.now().year}{style_block}{font_block}

Generate the complete design system JSON."""


# ─────────────────────────────────────────────────────────────
#  PAGE BUILDER — Individual page content generation
# ─────────────────────────────────────────────────────────────

PAGE_BUILDER_SYSTEM = """You are a senior frontend developer and conversion copywriter at AjayaDesign. You build ONE page of a multi-page website.

You receive a design system (Tailwind config, colors, fonts) and a page specification.

You output ONLY the <main> element with all page sections. Do NOT include:
- <!DOCTYPE>, <html>, <head>
- <nav> or <footer>

Your output starts with <main> and ends with </main>.

═══ TECHNICAL RULES ═══
- Use colors defined in the Tailwind config (bg-surface, text-primary, bg-accent, etc.)
- Use font-heading for headings, font-body for body text
- Every section must have an id attribute
- WCAG AA accessible: contrast, alt text, semantic HTML, visible focus states
- Mobile-responsive: use Tailwind responsive prefixes (md:, lg:)
- NEVER use href=\"#\" — use real page links or section IDs
- ALL internal page links MUST be relative paths (e.g. href=\"menu.html\", href=\"contact.html\", href=\"index.html\"). NEVER use root-relative paths starting with / (e.g. NEVER href=\"/menu.html\" or href=\"/menu\" or href=\"/\")

═══ CREATIVE RULES ═══
- The hero section MUST fill the viewport (min-h-screen)
- Hero headline: maximum 8 words. Make it PUNCHY, not descriptive.
  BAD:  \"Welcome to Sunrise Bakery, Your Local Bread Experts\"
  GOOD: \"Bread That Haunts Your Dreams\"
  GOOD: \"Every Bite Tells a Story\"
- Each section MUST use a DIFFERENT layout pattern. NEVER repeat the same layout twice.
- Use gradient text on the main h1 heading:
  class=\"bg-gradient-to-r from-primary to-accent bg-clip-text text-transparent\"
- Alternate between bg-surface and bg-surfaceAlt between sections for visual rhythm
- Add visual depth: cards should have hover:shadow-xl hover:-translate-y-1 transition

═══ ANIMATION ATTRIBUTES ═══
Add data-aos attributes for scroll-triggered animations:
- Sections: data-aos=\"fade-up\"
- Cards in a row: data-aos=\"fade-up\" data-aos-delay=\"0\" / \"100\" / \"200\" / \"300\"
- Images: data-aos=\"zoom-in\"
- Hero headline: data-aos=\"fade-up\" data-aos-duration=\"1000\"
- Hero subtitle: data-aos=\"fade-up\" data-aos-delay=\"200\"
- Stats/numbers: add class=\"counter\" and data-target=\"500\" for number counting animation

═══ LAYOUT PATTERNS (vary across sections — NEVER repeat the same pattern twice) ═══
1. Full-width hero with overlay text (min-h-screen) — the opening statement
2. Two-column split (image left, text right or vice versa) — balanced storytelling
3. Three/four-column card grid with icons — feature showcase
4. Large centered quote/testimonial — social proof moment
5. Alternating zigzag (text-image, image-text) — visual rhythm
6. Stats counter bar (full-width accent background) — credibility
7. CTA banner with gradient background — conversion push
8. Timeline/process steps — journey visualization
9. Bento grid (mixed-size cards in masonry layout) — modern, editorial feel
10. Full-bleed image section with parallax scroll — immersive break
11. Pricing comparison table/cards — decision support
12. Logo/trust badge horizontal scroll — authority bar
13. FAQ accordion section — objection handling
14. Team/profile cards with hover reveal — human connection

═══ DESIGN STYLE TECHNIQUES (apply based on blueprint.designStyle) ═══
- glassmorphism: Use backdrop-blur-xl, bg-white/5 (dark) or bg-white/40 (light), border border-white/10 on cards
- claymorphism: Use rounded-3xl, shadow-[8px_8px_0_theme(colors.primary/30)] for clay depth
- dark-luxe: Use bg-gradient-to-b from-black to-gray-950, gold accent borders, serif headings
- aurora-ui: Add background gradient blobs via absolute positioned divs with blur-3xl and animate-pulse
- brutalism: Use border-2 border-black, stark bg-white/bg-black sections, uppercase headings
- minimalism: Max whitespace (py-24 md:py-32), minimal text, let imagery breathe
- organic-natural: Use SVG wave dividers between sections, soft rounded shapes, earthy overlays
- gradient-mesh: Apply bg-gradient-to-br from-primary via-accent to-secondary on hero and CTA sections
- neo-corporate: Clean bg-white sections, subtle border-b dividers, geometric accent shapes

═══ COPYWRITING RULES ═══
- Write REAL, compelling copy — NO Lorem ipsum, NO placeholder text
- HOOK FIRST: first sentence grabs attention
- CTA copy: first-person action verbs \"Get My Free Quote\", \"Start My Project\" — NEVER \"Click Here\" or \"Submit\"
- Paragraphs: max 2-3 sentences
- Use specific numbers (\"15+ years\", \"500+ clients\", \"98% satisfaction\")
- Emotional triggers: pain → empathy → solution → action
- Testimonials should sound like REAL humans, not marketing bots

═══ SEO RULES ═══
- Exactly ONE <h1> containing business name AND primary keyword
- Heading hierarchy: h1 → h2 → h3, NEVER skip levels
- Every <img> MUST have a descriptive alt attribute (>4 characters)
- Use semantic HTML: <section>, <article>, <aside>, <figure>

═══ IMAGE RULES ═══
- NEVER use local/relative image paths like /images/photo.jpg or images/photo.jpg
- ALL images MUST use real Unsplash URLs: https://images.unsplash.com/photo-XXXXX?w=800&q=80
- Use relevant Unsplash photos that match the business niche and section context
- Hero image: use w=1600, other images: use w=800
- If you don't know a real Unsplash URL, use https://placehold.co/800x600/1a1a2e/ffffff?text=Section+Name as fallback

Output ONLY the <main>...</main> element. Nothing else."""


def page_builder_create(
    page_spec: dict, design_system: dict, blueprint: dict,
    creative_spec: dict | None = None,
) -> str:
    import json

    creative_block = ""
    if creative_spec:
        creative_block = f"""

CREATIVE DIRECTION:
- Visual concept: {creative_spec.get('visualConcept', 'Modern and professional')}
- Hero treatment: {creative_spec.get('heroTreatment', {}).get('type', 'parallax-image')}
- Hero CTA style: {creative_spec.get('heroTreatment', {}).get('ctaStyle', 'solid-lift')}
- Text animation: {creative_spec.get('heroTreatment', {}).get('textAnimation', 'fade-up-stagger')}
- Motion design: {json.dumps(creative_spec.get('motionDesign', {}), indent=2)}
- Use gradient text headings: {creative_spec.get('colorEnhancements', {}).get('useGradientText', True)}"""

    animation_strategy = blueprint.get("animationStrategy", {})
    layout_strategy = blueprint.get("layoutStrategy", {})
    design_style = blueprint.get("designStyle", "")
    landing_pattern = blueprint.get("landingPattern", "")

    style_block = ""
    if design_style:
        style_desc = DESIGN_STYLES.get(design_style, '')
        style_block = f"\n- Design style: {design_style} — {style_desc}"
    if landing_pattern:
        pattern_desc = LANDING_PATTERNS.get(landing_pattern, '')
        style_block += f"\n- Landing pattern: {landing_pattern} — {pattern_desc}"

    return f"""Build the "{page_spec['title']}" page for {blueprint.get('siteName', 'the client')}.

PAGE SPEC:
- Slug: {page_spec['slug']}
- Purpose: {page_spec.get('purpose', '')}
- Sections to include: {', '.join(page_spec.get('sections', []))}
- Content guidance: {page_spec.get('contentNotes', '')}

SITE CONTEXT:
- Tagline: {blueprint.get('tagline', '')}
- Brand voice: {blueprint.get('brandVoice', 'professional')}
- Creative mood: {blueprint.get('creativeMood', 'professional, modern, clean')}
- Niche: {'; '.join(blueprint.get('keyDifferentiators', ['Professional services']))}
- Conversion goal: {blueprint.get('siteGoals', 'Contact form submission')}
- Other pages: {', '.join(p.get('navLabel', p['title']) for p in blueprint.get('pages', []))}
- Hero style: {layout_strategy.get('heroStyle', 'full-viewport')}
- Section reveals: {animation_strategy.get('sectionReveals', 'fade-up-stagger')}{style_block}

AVAILABLE TAILWIND COLORS:
primary, accent, surface, surfaceAlt, textMain, textMuted, cta, ctaHover

AVAILABLE FONT CLASSES:
font-heading (for headings), font-body (for body text){creative_block}

Generate the <main> element with all sections. Remember: data-aos attributes on every section!"""


# ─────────────────────────────────────────────────────────────
#  FIXER — Targeted HTML repair from test errors
# ─────────────────────────────────────────────────────────────

FIXER_SYSTEM = """You are an expert web developer specializing in fixing accessibility, SEO, and test failures.

You receive a <main> element that has test failures, along with the specific errors.

Rules:
- Fix ALL reported issues
- Output the complete fixed <main>...</main> element
- Do NOT change the overall structure or content — only fix the specific issues
- For color-contrast failures on buttons/CTAs: use inline style with WCAG AA compliant dark color
- For color-contrast on text: add inline style with ≥ 4.5:1 contrast color
- NEVER use href="#" — use real section IDs or page links
- All images need descriptive alt text
- ALL internal page links MUST be relative paths (e.g. href="menu.html"). NEVER use root-relative paths starting with / (e.g. NEVER href="/menu.html" or href="/")
- SEO heading rules: exactly ONE <h1>, no skipping levels, <h1> should contain business name
- No horizontal overflow

Output ONLY the fixed <main>...</main> element."""


def fixer_fix(main_content: str, error_summary: str) -> str:
    return f"""Fix the following test failures in this <main> element:

ERRORS:
{error_summary}

CURRENT HTML:
{main_content}

Fix ALL issues and output the complete corrected <main>...</main> element."""


# ─────────────────────────────────────────────────────────────
#  CLIENT PARSER — Extract structured fields from raw text
# ─────────────────────────────────────────────────────────────

PARSE_CLIENT_SYSTEM = """You are a senior business analyst at AjayaDesign. You extract structured client information from unstructured text — emails, text messages, meeting notes, referrals, social media messages.

Extract what is EXPLICITLY stated. Do NOT invent information.

Output ONLY valid JSON with these exact keys:
{
  "business_name": "extracted or null",
  "niche": "extracted or inferred from context, or null",
  "goals": "synthesized 1-2 sentence summary, or null",
  "email": "extracted or null",
  "phone": "extracted and normalized, or null",
  "location": "city/state extracted, or null",
  "existing_website": "extracted with https://, or null",
  "brand_colors": "color names or hex codes mentioned, or null",
  "tagline": "extracted slogan/tagline, or null",
  "target_audience": "extracted or inferred, or null",
  "competitor_urls": "comma-separated URLs or null",
  "additional_notes": "anything relevant that didn't fit above, or null",
  "confidence": "high|medium|low"
}

Rules:
- For goals: synthesize into a clear summary — don't just copy the raw text
- For niche: infer from context (e.g. "artisan breads" → "Bakery")
- If a field can't be extracted, use null — NEVER invent
- For phone: normalize to (XXX) XXX-XXXX format if possible
- For website: add https:// if scheme is missing
- For brand_colors: extract color names or hex codes mentioned in the text
- confidence: "high" if 3+ key fields found, "medium" if 1-2, "low" if mostly guessing
- Output ONLY valid JSON. No explanations, no markdown fences."""


def parse_client_text(raw_text: str) -> str:
    return f"""Extract client information from this text:

---
{raw_text}
---

Return ONLY the JSON object with extracted fields."""


# ─────────────────────────────────────────────────────────────
#  CREATIVE DIRECTOR — Visual treatment specification
# ─────────────────────────────────────────────────────────────

CREATIVE_DIRECTOR_SYSTEM = """You are the Creative Director at AjayaDesign.
You receive an approved site blueprint and decide the EXACT visual treatment.

You DON'T generate HTML. You create a visual specification that guides the Designer and Page Builders.

Output JSON with these keys:
{
  "visualConcept": "One-sentence creative direction",
  "designStyle": "Pick the dominant design style: glassmorphism | neumorphism | claymorphism | aurora-ui | brutalism | minimalism | dark-luxe | organic-natural | gradient-mesh | neo-corporate | editorial | motion-driven",
  "heroTreatment": {
    "type": "parallax-image | text-reveal | fade-up-stagger | split-screen | video-loop | gradient-mesh-bg | typographic-hero | bento-hero | glassmorphic-cards | editorial-asymmetric",
    "description": "Detailed description of hero visual treatment",
    "ctaStyle": "solid-lift | pill-glow | outline-hover | glassmorphic-button | clay-button | gradient-fill",
    "textAnimation": "fade-up-stagger | typewriter | reveal-words | clip-path-reveal | blur-in"
  },
  "motionDesign": {
    "scrollRevealDefault": "fade-up",
    "staggerDelay": "100ms",
    "hoverScale": "1.02",
    "hoverShadow": "0 20px 40px rgba(accent, 0.3)",
    "pageEnter": "opacity 0→1 + translateY(20px→0) over 0.8s"
  },
  "colorEnhancements": {
    "useGradientText": true,
    "useNoiseOverlay": true,
    "useGlassMorphism": false,
    "useAuroraBlobs": false,
    "useSvgWaveDividers": false,
    "useClayDepthShadows": false,
    "gradients": ["from-primary/80 to-accent/60"]
  },
  "imageSearchTerms": {
    "index": ["search terms for hero image"],
    "about": ["search terms for about page image"]
  }
}

Rules:
- FIRST select the designStyle — this drives ALL visual decisions downstream
- Match the designStyle to the NICHE. A bakery feels different from a tech startup.
- Be specific and practical — your spec will be followed literally by the Designer and Page Builder agents.
- The heroTreatment.type determines the hero layout structure.
- imageSearchTerms should be descriptive enough for stock photo searches.
- Enable colorEnhancements that match the designStyle:
  * glassmorphism → useGlassMorphism=true, useNoiseOverlay=true
  * aurora-ui → useAuroraBlobs=true, useGradientText=true
  * organic-natural → useSvgWaveDividers=true
  * claymorphism → useClayDepthShadows=true
  * dark-luxe → useGradientText=true, useNoiseOverlay=true

Output ONLY valid JSON."""


def creative_director_create(blueprint: dict, scraped_data: dict | None = None) -> str:
    import json

    scraped_block = ""
    if scraped_data and scraped_data.get("brand_voice"):
        scraped_block = f"""

EXISTING SITE ANALYSIS (rebuild — preserve brand identity):
- Brand voice: {scraped_data.get('brand_voice', 'N/A')}
- Sentiment: {scraped_data.get('sentiment', 'N/A')}
- Color palette: {json.dumps(scraped_data.get('color_palette', {}))}
- Typography feel: {scraped_data.get('typography_feel', 'N/A')}
- Improvement opportunities: {scraped_data.get('improvement_opportunities', [])}"""

    return f"""Create a visual treatment spec for this approved site blueprint:

SITE: {blueprint.get('siteName', 'Unknown')}
NICHE: {blueprint.get('keyDifferentiators', ['Professional services'])}
CREATIVE MOOD: {blueprint.get('creativeMood', 'professional, modern, clean')}
BRAND VOICE: {blueprint.get('brandVoice', 'professional')}
THEME MODE: {blueprint.get('themeMode', 'dark')}
DESIGN STYLE: {blueprint.get('designStyle', 'not specified — pick the best fit')}
LANDING PATTERN: {blueprint.get('landingPattern', 'not specified — pick the best fit')}
FONT PAIRING STYLE: {blueprint.get('fontPairingStyle', 'modern-sans')}
PAGES: {', '.join(p.get('navLabel', p['title']) for p in blueprint.get('pages', []))}
HERO STYLE: {blueprint.get('layoutStrategy', {}).get('heroStyle', 'full-viewport')}
ANIMATION STRATEGY: {json.dumps(blueprint.get('animationStrategy', {}))}{scraped_block}

Your designStyle MUST align with the blueprint's designStyle. Build a creative spec that makes this site feel premium and unique to this business."""


# ─────────────────────────────────────────────────────────────
#  SCRAPER ANALYSIS — Analyze existing website content
# ─────────────────────────────────────────────────────────────

SCRAPER_ANALYSIS_SYSTEM = """You analyze an existing website's scraped content and produce a structured brand analysis.

Output ONLY valid JSON with these keys:
{
  "brand_voice": "3 adjectives describing the brand tone",
  "key_products_services": ["Product A", "Service B"],
  "target_demographics": "description of target audience",
  "color_palette": {"primary": "#hex", "secondary": "#hex"},
  "typography_feel": "description of font choices and feel",
  "content_highlights": ["Key tagline", "Important differentiator"],
  "page_structure": ["Home", "About", "Services", "Contact"],
  "sentiment": "premium, aspirational, casual, etc.",
  "improvement_opportunities": ["specific improvement 1", "specific improvement 2"],
  "assets_to_preserve": ["Logo description", "Brand font name"]
}

Rules:
- Extract REAL information from the scraped content — don't invent
- Be specific about colors found and typography used
- Identify the strongest content to preserve in the redesign
- Be honest about improvement opportunities"""


def scraper_analyze(
    combined_content: str,
    colors: list[str],
    fonts: list[str],
) -> str:
    return f"""Analyze this scraped website content:

SCRAPED TEXT:
{combined_content[:4000]}

COLORS FOUND IN CSS/HTML:
{', '.join(colors) if colors else 'None extracted'}

FONTS FOUND:
{', '.join(fonts) if fonts else 'None extracted'}

Produce a structured brand analysis JSON."""


# ─────────────────────────────────────────────────────────────
#  POLISH — Visual micro-detail enhancement
# ─────────────────────────────────────────────────────────────

POLISH_SYSTEM = """You are a visual polish expert at AjayaDesign. You receive a complete page's <main> element and enhance it with micro-details that elevate it from "clean" to "premium."

Enhancement categories:
1. SECTION DIVIDERS: Ensure sections alternate bg-surface and bg-surfaceAlt backgrounds
2. DECORATIVE ELEMENTS: Add subtle decorative pseudo-element classes where appropriate
3. GRADIENT OVERLAYS: Add gradient overlays on hero sections for text readability
4. SHADOW DEPTH: Cards and elevated elements need shadow-lg or shadow-xl
5. WHITESPACE RHYTHM: Ensure consistent py-16 md:py-24 spacing between sections
6. HOVER STATES: Every interactive element (links, cards, buttons) needs hover:transition
7. ANIMATION ATTRIBUTES: Ensure data-aos attributes are present on sections and cards
8. DESIGN STYLE POLISH: Apply style-specific micro-details:
   - glassmorphism: Ensure backdrop-blur cards have subtle border-white/10, add bg-white/5 overlays
   - dark-luxe: Add gradient overlay from black/40, ensure gold accents have glow shadow
   - claymorphism: Ensure colored shadows on cards, verify rounded-3xl on key elements
   - aurora-ui: Add 2-3 absolute positioned gradient blobs with blur-3xl and opacity-30
   - organic-natural: Add SVG wave divider between sections, soft rounded clip-paths
   - brutalism: Ensure stark borders, verify uppercase headings, check grid visibility
9. SCROLL PROGRESSION: Vary data-aos animations (don't use fade-up for everything — mix in fade-right, zoom-in, flip-up)
10. MICRO-INTERACTIONS: Add group-hover effects on cards, focus-visible rings on inputs, active:scale-95 on buttons

Rules:
- Make SMALL targeted improvements — do NOT rewrite content or restructure layout
- Focus on the 20% of polish that creates 80% of visual impact
- Preserve ALL existing accessibility attributes and content
- Preserve ALL existing data-aos attributes
- Output the COMPLETE enhanced <main>...</main> element
- Do NOT add <nav>, <footer>, <html>, or <head> — ONLY <main>"""


def polish_enhance(main_content: str, page_spec: dict, creative_spec: dict) -> str:
    return f"""Polish this page's <main> element with visual micro-details:

PAGE: {page_spec.get('title', 'Unknown')} ({page_spec.get('slug', 'index')})
VISUAL CONCEPT: {creative_spec.get('visualConcept', 'Modern and professional')}

CURRENT HTML:
{main_content}

Enhance with: section background alternation, shadow depth, hover states, whitespace rhythm, animation attributes.
Output the COMPLETE enhanced <main>...</main> element."""


# ─────────────────────────────────────────────────────────────
#  NICHE PATTERNS — Creative pattern library per industry
# ─────────────────────────────────────────────────────────────

NICHE_PATTERNS = {
    "restaurant": {
        "mood": "warm, intimate, sensory",
        "designStyle": "dark-luxe",
        "theme": "dark with warm accent lighting",
        "heroStyle": "full-bleed food photography with dark overlay",
        "landingPattern": "local-business",
        "signature": "Menu sections with elegant typography, reservation CTA",
        "fonts": "Playfair Display + Inter",
        "fontPairingStyle": "elegant-serif",
        "animations": "Slow fade-ins, parallax food images",
        "avoid": "Bright colors, corporate grid layouts",
    },
    "bakery": {
        "mood": "warm, artisanal, inviting",
        "designStyle": "organic-natural",
        "theme": "cream/light with warm golden accents",
        "heroStyle": "Full-width bread/pastry image with warm overlay",
        "landingPattern": "local-business",
        "signature": "Menu grid, story section, location/hours",
        "fonts": "Playfair Display + Lato",
        "fontPairingStyle": "elegant-serif",
        "animations": "Gentle fade-ups, zoom-in on food images",
        "avoid": "Dark themes, tech aesthetics, aggressive CTAs",
    },
    "tech": {
        "mood": "bold, futuristic, electric",
        "designStyle": "aurora-ui",
        "theme": "dark (#0a0a0f) with neon accents",
        "heroStyle": "gradient mesh background with floating product screenshots",
        "landingPattern": "saas-dashboard",
        "signature": "Animated stats, tech spec grids, demo CTA",
        "fonts": "JetBrains Mono + Inter",
        "fontPairingStyle": "tech-mono",
        "animations": "GSAP-style ScrollTrigger, number counters, code-typing effect",
        "avoid": "Warm colors, organic shapes, handwritten fonts",
    },
    "photography": {
        "mood": "minimal, elegant, image-focused",
        "designStyle": "minimalism",
        "theme": "near-black (#111) to make images pop",
        "heroStyle": "full-screen hero image with text overlay",
        "landingPattern": "portfolio-gallery",
        "signature": "Masonry gallery grid, lightbox, minimal text",
        "fonts": "Cormorant Garamond + Source Sans Pro",
        "fontPairingStyle": "elegant-serif",
        "animations": "Image zoom-in on scroll, subtle parallax, hover lightbox",
        "avoid": "Heavy text sections, corporate layouts, bright backgrounds",
    },
    "law": {
        "mood": "authoritative, trustworthy, refined",
        "designStyle": "neo-corporate",
        "theme": "deep navy (#1a2744) with gold accents (#c9a84c)",
        "heroStyle": "split-screen: powerful headline left, cityscape image right",
        "landingPattern": "long-form-authority",
        "signature": "Practice area cards, attorney profiles, consultation CTA",
        "fonts": "Libre Baskerville + Open Sans",
        "fontPairingStyle": "elegant-serif",
        "animations": "Subtle fade-up reveals, minimal motion, professional restraint",
        "avoid": "Playful animations, bright colors, trendy layouts",
    },
    "fitness": {
        "mood": "energetic, powerful, motivating",
        "designStyle": "motion-driven",
        "theme": "black with electric red/orange accents",
        "heroStyle": "video-loop of workout footage with bold CTA overlay",
        "landingPattern": "hero-features-social-proof",
        "signature": "Class schedule grid, trainer profiles, membership comparison",
        "fonts": "Oswald + Roboto",
        "fontPairingStyle": "bold-impact",
        "animations": "Bold slide-ins, counter animations for stats, pulse effects",
        "avoid": "Soft pastels, thin fonts, excessive whitespace",
    },
    "spa": {
        "mood": "serene, luxurious, peaceful",
        "designStyle": "organic-natural",
        "theme": "soft cream (#f5f0e8) with sage green (#7c9a78)",
        "heroStyle": "full-width nature image with centered text overlay",
        "landingPattern": "appointment-booking",
        "signature": "Service menu with pricing, booking CTA, testimonial carousel",
        "fonts": "Cormorant + Lato",
        "fontPairingStyle": "warm-humanist",
        "animations": "Slow fades, gentle parallax, breathing whitespace",
        "avoid": "Dark themes, aggressive CTAs, loud colors",
    },
    "ecommerce": {
        "mood": "clean, product-focused, trustworthy",
        "designStyle": "minimalism",
        "theme": "white/light with bold accent for CTA",
        "heroStyle": "product hero with color swatches or product carousel",
        "landingPattern": "product-showcase",
        "signature": "Product grid, category cards, trust badges, reviews",
        "fonts": "DM Sans + Inter",
        "fontPairingStyle": "modern-sans",
        "animations": "Quick card hover lifts, add-to-cart pulse, sticky nav",
        "avoid": "Text-heavy hero, no product visibility above fold",
    },
    "realestate": {
        "mood": "aspirational, trustworthy, local",
        "designStyle": "neo-corporate",
        "theme": "white with navy/forest-green accents",
        "heroStyle": "full-bleed property image with search overlay",
        "landingPattern": "real-estate-search",
        "signature": "Property cards, agent profile, area guide, testimonials",
        "fonts": "Montserrat + Open Sans",
        "fontPairingStyle": "modern-sans",
        "animations": "Smooth fade-ups, property card hover lifts",
        "avoid": "Dark themes, tech aesthetics",
    },
    "healthcare": {
        "mood": "trustworthy, caring, professional",
        "designStyle": "neo-corporate",
        "theme": "white/light with teal (#0D9488) and soft blue accents",
        "heroStyle": "split-screen: empathetic headline + caring imagery",
        "landingPattern": "appointment-booking",
        "signature": "Service cards, doctor profiles, insurance logos, patient testimonials",
        "fonts": "Plus Jakarta Sans + Inter",
        "fontPairingStyle": "modern-sans",
        "animations": "Gentle fade-ups, trust-building reveals, subtle hover",
        "avoid": "Dark themes, aggressive colors, flashy animations",
    },
    "education": {
        "mood": "inspiring, accessible, vibrant",
        "designStyle": "claymorphism",
        "theme": "light with vibrant primary blue and warm accents",
        "heroStyle": "illustrated hero with student-focused imagery",
        "landingPattern": "hero-features-social-proof",
        "signature": "Program cards, campus gallery, admissions CTA, success stats",
        "fonts": "Outfit + Nunito Sans",
        "fontPairingStyle": "modern-sans",
        "animations": "Playful fade-ups, staggered card reveals, counter stats",
        "avoid": "Corporate formality, dark themes, complex layouts",
    },
    "nonprofit": {
        "mood": "compassionate, hopeful, mission-driven",
        "designStyle": "organic-natural",
        "theme": "warm white with earthy greens and impact-orange accents",
        "heroStyle": "emotional full-width image with compelling headline",
        "landingPattern": "storytelling-scroll",
        "signature": "Impact stats, story timeline, donation CTA, volunteer section",
        "fonts": "Merriweather + Open Sans",
        "fontPairingStyle": "warm-humanist",
        "animations": "Emotional reveals, counter stats for impact numbers",
        "avoid": "Corporate cold, luxury aesthetics, complex navigation",
    },
    "automotive": {
        "mood": "bold, sleek, powerful",
        "designStyle": "dark-luxe",
        "theme": "dark (#0f0f0f) with metallic silver and red accents",
        "heroStyle": "full-viewport vehicle image with dramatic lighting",
        "landingPattern": "product-showcase",
        "signature": "Vehicle specs grid, gallery carousel, financing CTA, dealer info",
        "fonts": "Bebas Neue + Roboto",
        "fontPairingStyle": "bold-impact",
        "animations": "Dramatic reveals, parallax vehicle images, spec counters",
        "avoid": "Soft pastels, playful fonts, excessive whitespace",
    },
    "pet": {
        "mood": "playful, warm, friendly",
        "designStyle": "claymorphism",
        "theme": "warm light with playful orange/teal accents",
        "heroStyle": "joyful pet imagery with rounded, friendly CTA",
        "landingPattern": "appointment-booking",
        "signature": "Service cards with icons, team profiles, pet gallery, booking CTA",
        "fonts": "Fredoka + Nunito",
        "fontPairingStyle": "creative-expressive",
        "animations": "Bouncy reveals, playful hover effects, gentle parallax",
        "avoid": "Dark/serious themes, corporate layouts, aggressive typography",
    },
    "construction": {
        "mood": "solid, dependable, professional",
        "designStyle": "swiss-design",
        "theme": "light gray (#f4f4f4) with construction yellow (#F59E0B) and dark charcoal",
        "heroStyle": "project showcase with bold headline overlay",
        "landingPattern": "hero-features-social-proof",
        "signature": "Service grid, project gallery, certifications, free estimate CTA",
        "fonts": "Oswald + Source Sans Pro",
        "fontPairingStyle": "bold-impact",
        "animations": "Solid fade-ups, counter stats for projects completed",
        "avoid": "Playful aesthetics, light pastel colors, thin fonts",
    },
    "finance": {
        "mood": "trustworthy, precise, sophisticated",
        "designStyle": "neo-corporate",
        "theme": "deep navy (#1B2A4A) with gold (#D4AF37) and white",
        "heroStyle": "split-screen: confident headline with abstract financial imagery",
        "landingPattern": "long-form-authority",
        "signature": "Service cards, team credentials, trust badges, consultation CTA",
        "fonts": "DM Serif Display + DM Sans",
        "fontPairingStyle": "elegant-serif",
        "animations": "Restrained reveals, professional transitions, subtle hover states",
        "avoid": "Bright playful colors, casual fonts, heavy animations",
    },
    "music": {
        "mood": "vibrant, expressive, rhythmic",
        "designStyle": "gradient-mesh",
        "theme": "dark with vibrant neon/electric accents",
        "heroStyle": "full-viewport with audio-visual feel, bold typography",
        "landingPattern": "video-first",
        "signature": "Event listings, artist/track cards, embedded player, ticket CTA",
        "fonts": "Anton + Roboto",
        "fontPairingStyle": "bold-impact",
        "animations": "Rhythmic staggered reveals, hover pulse effects, parallax layers",
        "avoid": "Corporate aesthetics, muted colors, serif typography",
    },
    "gaming": {
        "mood": "immersive, bold, electric",
        "designStyle": "aurora-ui",
        "theme": "dark (#0a0a14) with neon purple (#8B5CF6) and cyan (#06B6D4) accents",
        "heroStyle": "cinematic full-viewport with game art and glowing UI elements",
        "landingPattern": "video-first",
        "signature": "Game cards, feature showcase, community stats, download/play CTA",
        "fonts": "Space Grotesk + Inter",
        "fontPairingStyle": "tech-mono",
        "animations": "Glowing reveals, parallax layers, hover glow effects, floating elements",
        "avoid": "Corporate layouts, warm earth tones, serif typography",
    },
    "travel": {
        "mood": "adventurous, inspiring, wanderlust",
        "designStyle": "editorial",
        "theme": "light with rich photography, ocean blue and sunset orange accents",
        "heroStyle": "full-bleed destination photo with search/booking overlay",
        "landingPattern": "hero-features-social-proof",
        "signature": "Destination cards, itinerary timeline, reviews, booking CTA",
        "fonts": "Sora + Nunito Sans",
        "fontPairingStyle": "modern-sans",
        "animations": "Smooth parallax travel images, card hover lifts, fade-up reveals",
        "avoid": "Dark themes, corporate grid layouts, aggressive CTAs",
    },
    "wedding": {
        "mood": "romantic, elegant, timeless",
        "designStyle": "minimalism",
        "theme": "soft blush (#FDF2F8) with gold accents and ivory white",
        "heroStyle": "full-width romantic imagery with elegant serif headline",
        "landingPattern": "minimal-elegant",
        "signature": "Gallery grid, service packages, love story timeline, inquiry form",
        "fonts": "Cormorant Garamond + Montserrat",
        "fontPairingStyle": "elegant-serif",
        "animations": "Gentle fade-ins, delicate parallax, soft hover transitions",
        "avoid": "Dark themes, bold/aggressive fonts, tech aesthetics",
    },
    "cleaning": {
        "mood": "fresh, trustworthy, efficient",
        "designStyle": "swiss-design",
        "theme": "crisp white with fresh blue (#3B82F6) and green (#10B981) accents",
        "heroStyle": "clean split-screen with before/after or sparkling imagery",
        "landingPattern": "local-business",
        "signature": "Service grid with pricing, booking CTA, trust badges, reviews",
        "fonts": "Outfit + Inter",
        "fontPairingStyle": "modern-sans",
        "animations": "Clean fade-ups, checklist reveals, counter stats",
        "avoid": "Dark themes, complex layouts, luxury aesthetics",
    },
    "agency": {
        "mood": "creative, bold, innovative",
        "designStyle": "brutalism",
        "theme": "high-contrast with electric accents on white or dark base",
        "heroStyle": "bold typographic hero with asymmetric layout",
        "landingPattern": "portfolio-gallery",
        "signature": "Case study cards, process timeline, team grid, contact CTA",
        "fonts": "Space Grotesk + Inter",
        "fontPairingStyle": "modern-sans",
        "animations": "Motion-driven reveals, magnetic hover, parallax case studies",
        "avoid": "Generic templates, stock photo-heavy, conservative layouts",
    },
    "saas": {
        "mood": "modern, efficient, trustworthy",
        "designStyle": "glassmorphism",
        "theme": "dark gradient (#0f172a to #1e293b) with vibrant accent (#3B82F6)",
        "heroStyle": "app screenshot hero with glassmorphic cards",
        "landingPattern": "saas-dashboard",
        "signature": "Feature tabs, integration logos, pricing tiers, demo CTA",
        "fonts": "Inter + Inter",
        "fontPairingStyle": "modern-sans",
        "animations": "Smooth reveals, floating UI elements, interactive feature demos",
        "avoid": "Heavy imagery, serif fonts, print-style layouts",
    },
}


def match_niche_pattern(niche: str) -> dict | None:
    """Find the best matching niche creative pattern."""
    niche_lower = niche.lower()
    for key, pattern in NICHE_PATTERNS.items():
        if key in niche_lower:
            return pattern
    # Fuzzy match on keywords
    keywords_map = {
        "restaurant": ["food", "dine", "dining", "eat", "cafe", "bistro", "grill", "bar", "pub", "tavern"],
        "bakery": ["bread", "pastry", "cake", "bake", "patisserie", "confection", "donut", "cookie"],
        "tech": ["software", "startup", "app", "digital", "ai", "cyber", "cloud", "devops"],
        "photography": ["photo", "camera", "studio", "portrait", "wedding photo", "headshot", "videograph"],
        "law": ["legal", "attorney", "lawyer", "firm", "counsel", "litigation", "paralegal"],
        "fitness": ["gym", "workout", "training", "crossfit", "yoga", "pilates", "martial art", "boxing"],
        "spa": ["wellness", "massage", "beauty", "salon", "skin", "nail", "facial", "aesthetic"],
        "ecommerce": ["shop", "store", "retail", "product", "buy", "sell", "merch", "boutique"],
        "realestate": ["property", "house", "home", "realtor", "agent", "listing", "mortgage", "apartment"],
        "healthcare": ["medical", "doctor", "clinic", "dental", "dentist", "hospital", "health", "therapy", "chiropr", "physio"],
        "education": ["school", "university", "college", "tutor", "learn", "academy", "training center", "course"],
        "nonprofit": ["nonprofit", "charity", "foundation", "donate", "volunteer", "mission", "ngo"],
        "automotive": ["car", "auto", "vehicle", "mechanic", "dealer", "tire", "collision", "body shop"],
        "pet": ["pet", "veterinar", "vet", "groom", "kennel", "dog", "cat", "animal"],
        "construction": ["construct", "builder", "contractor", "remodel", "renovation", "roof", "plumb", "electric", "hvac"],
        "finance": ["account", "tax", "financial", "invest", "wealth", "insurance", "bank", "cpa", "bookkeep"],
        "music": ["music", "band", "record", "dj", "producer", "audio", "concert", "festival"],
        "gaming": ["game", "gaming", "esport", "stream", "twitch", "play"],
        "travel": ["travel", "tour", "hotel", "resort", "vacation", "adventure", "cruise", "hostel"],
        "wedding": ["wedding", "bridal", "planner", "event plan", "florist", "catering"],
        "cleaning": ["clean", "maid", "janitor", "housekeep", "pressure wash", "carpet"],
        "agency": ["agency", "creative agency", "marketing agency", "design studio", "branding"],
        "saas": ["saas", "platform", "dashboard", "analytics", "crm", "erp"],
    }
    for key, keywords in keywords_map.items():
        if any(kw in niche_lower for kw in keywords):
            return NICHE_PATTERNS[key]
    return None
