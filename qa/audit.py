"""Full-site audit: screenshot every tab at desktop + mobile, collect console/a11y signals."""
import json
import os
import sys
from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:4173/index.html"
OUT = sys.argv[2] if len(sys.argv) > 2 else "/tmp/audit"
os.makedirs(OUT, exist_ok=True)

TABS = ["overview", "rides", "map", "nearby", "navigation", "planner"]

# Structural/visual smells we can measure rather than guess at.
PROBE_JS = """() => {
  const out = {};
  const vw = window.innerWidth;

  // 1. Horizontal overflow (breaks mobile).
  out.docScrollW = document.documentElement.scrollWidth;
  out.viewportW = vw;
  out.hasHOverflow = document.documentElement.scrollWidth > vw + 1;

  // 2. Elements physically wider than the viewport.
  out.overflowing = [...document.querySelectorAll('body *')]
    .filter(el => {
      const r = el.getBoundingClientRect();
      return r.width > vw + 2 && r.height > 0 && getComputedStyle(el).position !== 'fixed';
    })
    .slice(0, 8)
    .map(el => `${el.tagName.toLowerCase()}.${(el.className || '').toString().split(' ')[0]} w=${Math.round(el.getBoundingClientRect().width)}`);

  // 3. Tap targets below 36px. Inline text links are excluded — they are part of
  //    a sentence and cannot be padded without breaking the line box.
  out.smallTapTargets = [...document.querySelectorAll('button, select, input')]
    .filter(el => {
      const r = el.getBoundingClientRect();
      return r.width > 0 && r.height > 0 && (r.height < 36 || r.width < 36);
    })
    .slice(0, 12)
    .map(el => `${el.tagName.toLowerCase()}#${el.id || ''}.${(el.className||'').toString().split(' ')[0]} ${Math.round(el.getBoundingClientRect().width)}x${Math.round(el.getBoundingClientRect().height)}`);

  // 4. Distinct font sizes / colors in use -> typographic + palette consistency.
  const sizes = {}, colors = {}, radii = {};
  [...document.querySelectorAll('body *')].forEach(el => {
    const r = el.getBoundingClientRect();
    if (!r.width || !r.height) return;
    const cs = getComputedStyle(el);
    if (el.textContent && el.children.length === 0) {
      sizes[cs.fontSize] = (sizes[cs.fontSize] || 0) + 1;
      colors[cs.color] = (colors[cs.color] || 0) + 1;
    }
    if (cs.borderRadius && cs.borderRadius !== '0px') radii[cs.borderRadius] = (radii[cs.borderRadius] || 0) + 1;
  });
  out.fontSizes = Object.entries(sizes).sort((a,b)=>b[1]-a[1]);
  out.textColors = Object.entries(colors).sort((a,b)=>b[1]-a[1]).length;
  out.borderRadii = Object.entries(radii).sort((a,b)=>b[1]-a[1]).map(e=>e[0]);

  // 5. Images without alt.
  out.imgNoAlt = [...document.querySelectorAll('img:not([alt])')].length;

  // 6. Buttons with no accessible name.
  out.btnNoName = [...document.querySelectorAll('button')]
    .filter(b => !(b.innerText||'').trim() && !b.getAttribute('aria-label')).length;

  return out;
}"""

report = {}
errors = []

with sync_playwright() as p:
    browser = p.chromium.launch(args=["--no-sandbox"])

    for label, vp in [("desktop", {"width": 1440, "height": 950}),
                      ("mobile", {"width": 390, "height": 844})]:
        page = browser.new_page(viewport=vp, device_scale_factor=1)
        page.on("pageerror", lambda e, l=label: errors.append(f"[{l}] pageerror: {e}"))
        page.on("console", lambda m, l=label: errors.append(f"[{l}] console.error: {m.text[:160]}")
                if m.type == "error" else None)

        page.goto(BASE, wait_until="domcontentloaded")
        page.wait_for_timeout(2500)
        page.evaluate("() => document.getElementById('site-tour')?.remove()")

        section = {}
        for tab in TABS:
            ok = page.evaluate(f"() => !!document.getElementById('tab-{tab}')")
            if not ok:
                section[tab] = "MISSING"
                continue
            page.evaluate(f"() => switchTab('{tab}')")
            page.wait_for_timeout(1400)
            path = f"{OUT}/{label}_{tab}.png"
            page.screenshot(path=path, full_page=(label == "desktop"))
            section[tab] = {"shot": path, **page.evaluate(PROBE_JS)}
        report[label] = section
        page.close()

    report["errors"] = errors or "none"
    browser.close()

print(json.dumps(report, indent=2, ensure_ascii=False))
