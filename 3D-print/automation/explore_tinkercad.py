#!/usr/bin/env python3
"""
TinkerCAD Interaction Explorer
Tests dimension editing, hole toggle, and alignment in the actual editor.
"""
import sys
import time
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from tinkercad_helper import (
    get_persistent_context, wait_for_editor, create_new_design,
    EDITOR, drag_shape_to_workplane, select_all, force_inspector_visible,
)

BOX = "87"
CYLINDER = "88"


def explore_dimensions(page):
    """After placing a shape, explore how to set dimensions."""
    print("\n── Exploring dimension editing ──")

    # Place a box at center
    print("  Placing box...")
    drag_shape_to_workplane(page, BOX, EDITOR["workplane_center"])
    time.sleep(2)

    # Click the shape to select it
    page.mouse.click(*EDITOR["workplane_center"])
    time.sleep(1)

    # 1) Check for dimension input fields in DOM
    dim_info = page.evaluate("""() => {
        const inputs = Array.from(document.querySelectorAll('input'));
        return inputs.map(i => ({
            type: i.type,
            name: i.name,
            id: i.id,
            class: i.className,
            value: i.value,
            placeholder: i.placeholder,
            visible: i.offsetParent !== null,
            rect: i.getBoundingClientRect(),
            parent: i.parentElement?.className || '',
        })).filter(i => i.visible);
    }""")
    print(f"\n  Visible input fields: {len(dim_info)}")
    for inp in dim_info:
        print(f"    name={inp['name']!r} value={inp['value']!r} class={inp['class']!r} id={inp['id']!r}")
        print(f"      rect: ({inp['rect']['x']:.0f}, {inp['rect']['y']:.0f}) {inp['rect']['width']:.0f}x{inp['rect']['height']:.0f}")

    # 2) Check inspector panel for dimension fields
    inspector_info = page.evaluate("""() => {
        const insp = document.querySelector('.inspector-content, .js-editor__holder__inspector, [class*=inspector]');
        if (!insp) return {found: false};
        return {
            found: true,
            html: insp.innerHTML.substring(0, 3000),
            visible: insp.offsetParent !== null,
            rect: insp.getBoundingClientRect(),
        };
    }""")
    print(f"\n  Inspector panel found: {inspector_info.get('found')}")
    if inspector_info.get('html'):
        print(f"  Inspector HTML (first 500 chars):\n    {inspector_info['html'][:500]}")

    # 3) Try clicking on the shape's dimension labels
    # In TinkerCAD, white numbers appear near shape edges
    # Let's check for overlay elements that could be dimension labels
    overlays = page.evaluate("""() => {
        const els = document.querySelectorAll('[class*=dimension], [class*=Dimension], [class*=label], [class*=measure]');
        return Array.from(els).map(e => ({
            tag: e.tagName,
            class: e.className,
            text: e.textContent?.trim(),
            visible: e.offsetParent !== null,
            rect: e.getBoundingClientRect(),
        })).filter(e => e.visible);
    }""")
    print(f"\n  Dimension/label overlays: {len(overlays)}")
    for o in overlays:
        print(f"    {o['tag']} class={o['class']!r} text={o['text']!r}")

    # 4) Check for React state / shape data
    shape_data = page.evaluate("""() => {
        // TinkerCAD stores shape data in React fiber
        const inspTitle = document.querySelector('.js-inspector__title');
        const inspContent = document.querySelector('.inspector-content');

        // Look for dimension-related DOM more broadly
        const allText = document.body.innerText;
        const dimPattern = /\\b20\\.00\\b/g;  // Default box size
        const matches = allText.match(dimPattern);

        // Check for data- attributes on shapes
        const commEls = Array.from(document.querySelectorAll('[communication]'));

        return {
            inspTitle: inspTitle?.textContent || '',
            inspContentText: inspContent?.textContent?.substring(0, 500) || '',
            dimMatches: matches?.length || 0,
            commElements: commEls.length,
        };
    }""")
    print(f"\n  Inspector title: {shape_data['inspTitle']!r}")
    print(f"  Inspector content: {shape_data['inspContentText']!r}")
    print(f"  '20.00' matches in page text: {shape_data['dimMatches']}")

    # 5) Try Tab key to cycle dimension inputs
    print("\n  Testing Tab key for dimension cycling...")
    page.mouse.click(*EDITOR["workplane_center"])
    time.sleep(0.5)

    # Press Tab and check what gets focused
    for i in range(5):
        page.keyboard.press("Tab")
        time.sleep(0.3)
        focused = page.evaluate("""() => {
            const el = document.activeElement;
            return {
                tag: el?.tagName || '',
                type: el?.type || '',
                value: el?.value || '',
                class: el?.className || '',
                id: el?.id || '',
                role: el?.getAttribute('role') || '',
                rect: el?.getBoundingClientRect() || {},
            };
        }""")
        print(f"    Tab {i+1}: {focused['tag']} type={focused['type']!r} value={focused['value']!r} class={focused['class'][:50]!r}")

    # 6) Look for dimension handle click targets on the shape itself
    # Take a screenshot for visual reference
    page.screenshot(path="/tmp/tinkercad_shape_selected.png")
    print("\n  Screenshot saved: /tmp/tinkercad_shape_selected.png")

    return dim_info


def explore_hole_toggle(page):
    """After selecting a shape, explore how to toggle Hole mode."""
    print("\n── Exploring Hole toggle ──")

    # Click to select the shape
    page.mouse.click(*EDITOR["workplane_center"])
    time.sleep(1)

    force_inspector_visible(page)
    time.sleep(1)

    # Find Solid/Hole toggle
    hole_info = page.evaluate("""() => {
        // Method 1: Look for Solid/Hole text/labels
        const solidHoleLabels = Array.from(document.querySelectorAll('*')).filter(
            el => el.textContent?.trim() === 'Solid' || el.textContent?.trim() === 'Hole'
        ).filter(el => el.children.length === 0); // Leaf text nodes

        // Method 2: Look for inspector images/icons for solid/hole
        const inspectorImgs = Array.from(document.querySelectorAll('.js-editor__holder__inspector img, .inspector-content img'));

        // Method 3: Look for radio buttons or toggles
        const radios = Array.from(document.querySelectorAll('input[type=radio], [role=radio], [role=tab]'));

        // Method 4: Look for clickable elements with Solid/Hole nearby
        const clickables = Array.from(document.querySelectorAll('button, [role=button], a, [onclick], [tabindex]'));
        const solidHoleClickables = clickables.filter(el => {
            const text = el.textContent?.trim() || '';
            const label = el.getAttribute('aria-label') || '';
            return /solid|hole/i.test(text + label);
        });

        return {
            solidHoleTexts: solidHoleLabels.map(e => ({
                tag: e.tagName, text: e.textContent?.trim(),
                class: e.className, visible: e.offsetParent !== null,
                rect: e.getBoundingClientRect(),
                parentClass: e.parentElement?.className || '',
            })),
            inspectorImgs: inspectorImgs.map(i => ({
                src: i.src?.split('/').pop(), alt: i.alt,
                visible: i.offsetParent !== null,
                rect: i.getBoundingClientRect(),
                class: i.className, parentClass: i.parentElement?.className || '',
            })),
            radios: radios.map(r => ({
                tag: r.tagName, type: r.type, name: r.name, value: r.value,
                checked: r.checked, visible: r.offsetParent !== null,
                class: r.className, rect: r.getBoundingClientRect(),
            })),
            solidHoleClickables: solidHoleClickables.map(c => ({
                tag: c.tagName, text: c.textContent?.trim()?.substring(0, 50),
                class: c.className, visible: c.offsetParent !== null,
                rect: c.getBoundingClientRect(),
            })),
        };
    }""")

    print(f"\n  Solid/Hole text nodes: {len(hole_info['solidHoleTexts'])}")
    for t in hole_info['solidHoleTexts']:
        print(f"    {t['tag']} text={t['text']!r} visible={t['visible']} rect=({t['rect']['x']:.0f},{t['rect']['y']:.0f})")

    print(f"\n  Inspector images: {len(hole_info['inspectorImgs'])}")
    for i in hole_info['inspectorImgs']:
        print(f"    src={i['src']!r} alt={i['alt']!r} visible={i['visible']} rect=({i['rect']['x']:.0f},{i['rect']['y']:.0f})")

    print(f"\n  Radio/tab elements: {len(hole_info['radios'])}")
    for r in hole_info['radios']:
        print(f"    {r['tag']} name={r['name']!r} value={r['value']!r} checked={r['checked']}")

    print(f"\n  Solid/Hole clickables: {len(hole_info['solidHoleClickables'])}")
    for c in hole_info['solidHoleClickables']:
        print(f"    {c['tag']} text={c['text']!r} visible={c['visible']} rect=({c['rect']['x']:.0f},{c['rect']['y']:.0f})")

    # Check inspector panel structure in detail
    panel_html = page.evaluate("""() => {
        const panel = document.querySelector('.js-editor__holder__inspector');
        return panel?.innerHTML?.substring(0, 5000) || 'NOT FOUND';
    }""")
    print(f"\n  Inspector panel HTML (truncated):\n{panel_html[:1000]}")

    page.screenshot(path="/tmp/tinkercad_hole_explore.png")
    print("\n  Screenshot: /tmp/tinkercad_hole_explore.png")


def explore_align_tool(page):
    """Test the Align tool (comm=40)."""
    print("\n── Exploring Align tool ──")

    # Place a second box offset from center
    drag_shape_to_workplane(page, BOX, (700, 500))
    time.sleep(2)

    # Select all
    select_all(page)
    time.sleep(1)

    # Click Align (comm=40)
    try:
        align_btn = page.locator("[communication='40']")
        if align_btn.is_visible():
            align_btn.click()
            time.sleep(2)

            # Look for align control points that appear
            align_ui = page.evaluate("""() => {
                const dots = document.querySelectorAll('[class*=align], [class*=Align]');
                return Array.from(dots).map(d => ({
                    tag: d.tagName, class: d.className,
                    visible: d.offsetParent !== null,
                    rect: d.getBoundingClientRect(),
                }));
            }""")
            print(f"  Align UI elements: {len(align_ui)}")
            for a in align_ui:
                print(f"    {a['tag']} class={a['class']!r} visible={a['visible']}")

            page.screenshot(path="/tmp/tinkercad_align.png")
            print("  Screenshot: /tmp/tinkercad_align.png")
        else:
            print("  Align button not visible")
    except Exception as e:
        print(f"  Align error: {e}")


def main():
    print("TinkerCAD Interaction Explorer")
    print("="*50)

    p, context = get_persistent_context(headless=False)
    page = context.pages[0] if context.pages else context.new_page()

    try:
        page.goto("https://www.tinkercad.com/dashboard",
                  wait_until="networkidle", timeout=30000)
        time.sleep(3)

        if "/login" in page.url:
            from tinkercad_helper import login_tinkercad
            login_tinkercad(page)

        create_new_design(page)
        wait_for_editor(page, timeout=20)

        explore_dimensions(page)
        explore_hole_toggle(page)
        explore_align_tool(page)

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
    finally:
        context.close()
        p.stop()
        print("\nDone.")


if __name__ == "__main__":
    main()
