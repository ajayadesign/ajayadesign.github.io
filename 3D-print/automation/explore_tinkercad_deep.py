#!/usr/bin/env python3
"""
TinkerCAD Deep DOM Explorer — Focus on dimension inputs and Hole toggle.
"""
import sys, time, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from tinkercad_helper import (
    get_persistent_context, wait_for_editor, create_new_design,
    EDITOR, drag_shape_to_workplane, force_inspector_visible,
)

BOX = "87"

def main():
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

        # Place a box
        print("  Placing box...")
        drag_shape_to_workplane(page, BOX, EDITOR["workplane_center"])
        time.sleep(2)

        # Click to select it
        page.mouse.click(*EDITOR["workplane_center"])
        time.sleep(1)

        force_inspector_visible(page)
        time.sleep(1)

        # 1) Get all inspector item structure
        print("\n── Inspector Items (detail) ──")
        items = page.evaluate("""() => {
            const items = document.querySelectorAll('.editor__inspector__item, [class*=inspector__item]');
            return Array.from(items).map(item => {
                const label = item.querySelector('.editor__inspector__item__label, [class*=item__label]');
                const input = item.querySelector('input');
                const value = item.querySelector('[class*=value], [class*=display]');
                const children = Array.from(item.children).map(c => ({
                    tag: c.tagName, class: c.className?.substring(0, 80),
                    text: c.textContent?.trim()?.substring(0, 50),
                }));
                return {
                    class: item.className?.substring(0, 80),
                    labelText: label?.textContent?.trim() || '',
                    hasInput: !!input,
                    inputValue: input?.value || '',
                    valueText: value?.textContent?.trim() || '',
                    childCount: children.length,
                    children: children,
                    rect: item.getBoundingClientRect(),
                    visible: item.offsetParent !== null,
                };
            }).filter(i => i.visible);
        }""")
        for item in items:
            print(f"  Label: {item['labelText']!r:15} hasInput:{item['hasInput']} value:{item['inputValue']!r} valText:{item['valueText']!r}")
            for c in item['children']:
                print(f"    child: {c['tag']} class={c['class']!r} text={c['text']!r}")

        # 2) Get Solid/Hole button structure
        print("\n── Solid/Hole Buttons ──")
        btn_info = page.evaluate("""() => {
            const solidLabel = Array.from(document.querySelectorAll('.editor__materialbtn__label')).find(
                e => e.textContent.trim() === 'Solid'
            );
            const holeLabel = Array.from(document.querySelectorAll('.editor__materialbtn__label')).find(
                e => e.textContent.trim() === 'Hole'
            );
            const getInfo = (label) => {
                if (!label) return null;
                const btn = label.closest('[class*=materialbtn], button, a, [role=button], [communication]')
                    || label.parentElement;
                return {
                    labelRect: label.getBoundingClientRect(),
                    btnTag: btn?.tagName,
                    btnClass: btn?.className?.substring(0, 100),
                    btnComm: btn?.getAttribute('communication'),
                    btnRect: btn?.getBoundingClientRect(),
                    btnClickable: btn?.style?.pointerEvents !== 'none',
                    parentTag: btn?.parentElement?.tagName,
                    parentClass: btn?.parentElement?.className?.substring(0, 100),
                    parentComm: btn?.parentElement?.getAttribute('communication'),
                };
            };
            return { solid: getInfo(solidLabel), hole: getInfo(holeLabel) };
        }""")
        print(f"  Solid: {json.dumps(btn_info['solid'], indent=4)}")
        print(f"  Hole:  {json.dumps(btn_info['hole'], indent=4)}")

        # 3) Try clicking the Hole button by coordinates
        if btn_info['hole'] and btn_info['hole']['btnRect']:
            rect = btn_info['hole']['btnRect']
            hx = rect['x'] + rect['width'] / 2
            hy = rect['y'] + rect['height'] / 2
            print(f"\n  Clicking Hole button at ({hx:.0f}, {hy:.0f})...")
            page.mouse.click(int(hx), int(hy))
            time.sleep(1)

            # Check if it changed
            after = page.evaluate("""() => {
                const solidBtn = document.querySelector('.editor__materialbtn--selected .editor__materialbtn__label');
                const inspContent = document.querySelector('.js-inspector__title');
                return {
                    selectedLabel: solidBtn?.textContent?.trim() || 'NONE',
                    title: inspContent?.textContent?.trim() || '',
                };
            }""")
            print(f"  After click: selected={after['selectedLabel']!r} title={after['title']!r}")

            # Also check the shape visually
            page.screenshot(path="/tmp/tinkercad_after_hole_click.png")
            print("  Screenshot: /tmp/tinkercad_after_hole_click.png")

        # 4) Now explore dimension editing on the canvas
        print("\n── Exploring On-Canvas Dimension Editing ──")
        # Click on shape to select it
        page.mouse.click(*EDITOR["workplane_center"])
        time.sleep(1)

        # Look for any floating text/input elements that appear near the shape
        # TinkerCAD shows dimension handles as white text on the shape edges
        canvas_overlays = page.evaluate("""() => {
            // Check for elements positioned over the canvas that might be dimension inputs
            const allEls = document.querySelectorAll('div, span, input, text');
            const canvasRect = document.querySelector('canvas')?.getBoundingClientRect() || {x:0, y:0, width:1920, height:1080};
            const overlays = [];
            for (const el of allEls) {
                const rect = el.getBoundingClientRect();
                // Element must be over the canvas area  
                if (rect.x >= canvasRect.x && rect.x <= canvasRect.x + canvasRect.width &&
                    rect.y >= canvasRect.y && rect.y <= canvasRect.y + canvasRect.height &&
                    rect.width > 0 && rect.width < 200 &&
                    el.offsetParent !== null) {
                    const text = el.textContent?.trim();
                    if (text && text.length > 0 && text.length < 30 && /\d/.test(text)) {
                        overlays.push({
                            tag: el.tagName,
                            text: text,
                            class: el.className?.substring(0, 80) || '',
                            rect: {x: rect.x, y: rect.y, w: rect.width, h: rect.height},
                            editable: el.contentEditable === 'true',
                            isInput: el.tagName === 'INPUT',
                        });
                    }
                }
            }
            return overlays;
        }""")
        print(f"  Canvas overlays with numbers: {len(canvas_overlays)}")
        for o in canvas_overlays:
            print(f"    {o['tag']} text={o['text']!r} pos=({o['rect']['x']:.0f},{o['rect']['y']:.0f}) editable={o['editable']} input={o['isInput']}")

        # 5) Check for SVG-based dimension indicators
        svg_dims = page.evaluate("""() => {
            const texts = document.querySelectorAll('svg text, text');
            return Array.from(texts).filter(t => /\\d/.test(t.textContent) && t.offsetParent !== null).map(t => ({
                text: t.textContent?.trim(),
                tag: t.tagName,
                rect: t.getBoundingClientRect(),
            }));
        }""")
        print(f"\n  SVG text with numbers: {len(svg_dims)}")
        for s in svg_dims:
            print(f"    text={s['text']!r} pos=({s['rect']['x']:.0f},{s['rect']['y']:.0f})")

        # 6) Try double-clicking on the shape to see if dimension edit mode activates
        print("\n  Double-clicking shape...")
        page.mouse.dblclick(*EDITOR["workplane_center"])
        time.sleep(2)

        after_dblclick = page.evaluate("""() => {
            const inputs = Array.from(document.querySelectorAll('input')).filter(i => i.offsetParent !== null);
            return inputs.map(i => ({
                type: i.type, value: i.value, name: i.name,
                class: i.className?.substring(0, 50),
                rect: i.getBoundingClientRect(),
            }));
        }""")
        print(f"  Visible inputs after double-click: {len(after_dblclick)}")
        for inp in after_dblclick:
            print(f"    type={inp['type']!r} value={inp['value']!r} pos=({inp['rect']['x']:.0f},{inp['rect']['y']:.0f}) w={inp['rect']['width']:.0f}")

        page.screenshot(path="/tmp/tinkercad_after_dblclick.png")

        # 7) Check for dimension editor by looking at wider inspector area
        print("\n── Inspector value inputs ──")
        val_inputs = page.evaluate("""() => {
            // Look for the actual value containers next to labels
            const labels = document.querySelectorAll('.editor__inspector__item__label');
            const results = [];
            for (const label of labels) {
                const parent = label.parentElement;
                if (!parent) continue;
                const siblings = Array.from(parent.children);
                for (const sib of siblings) {
                    if (sib === label) continue;
                    results.push({
                        labelText: label.textContent?.trim(),
                        sibTag: sib.tagName,
                        sibClass: sib.className?.substring(0, 80),
                        sibText: sib.textContent?.trim()?.substring(0, 30),
                        sibComm: sib.getAttribute?.('communication') || '',
                        sibHtml: sib.innerHTML?.substring(0, 200),
                        sibRect: sib.getBoundingClientRect(),
                        sibVisible: sib.offsetParent !== null,
                    });
                }
            }
            return results.filter(r => r.sibVisible);
        }""")
        for v in val_inputs:
            print(f"  {v['labelText']!r:15} sibling: {v['sibTag']} class={v['sibClass']!r} text={v['sibText']!r} comm={v['sibComm']!r}")
            if v['sibHtml']:
                print(f"    html: {v['sibHtml'][:150]}")

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
    finally:
        context.close()
        p.stop()

if __name__ == "__main__":
    main()
