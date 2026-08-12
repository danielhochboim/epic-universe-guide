"""QA for map decluttering: category filter + measured label overlap."""
import json
import sys
from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:4173/index.html"
PARKS = ["epic", "studios", "islands"]

# Counts every pair of visible label boxes that physically intersect on screen.
OVERLAP_JS = """() => {
  const labels = [...document.querySelectorAll('.ride-marker-wrap.is-visible .map-ride-label')]
    .filter(el => el.style.visibility !== 'hidden' && el.offsetParent !== null)
    .map(el => el.getBoundingClientRect());
  let overlaps = 0;
  for (let i = 0; i < labels.length; i++)
    for (let j = i + 1; j < labels.length; j++) {
      const a = labels[i], b = labels[j];
      if (a.left < b.right && a.right > b.left && a.top < b.bottom && a.bottom > b.top) overlaps++;
    }
  return {visibleLabels: labels.length, overlappingPairs: overlaps};
}"""

STATE_JS = """() => ({
  markersInLayer: Object.values(rideMarkers).filter(m => rideLayer.hasLayer(m)).length,
  showsInLayer: RIDES.filter(r => r.tier === 'show' && rideMarkers[r.id] && rideLayer.hasLayer(rideMarkers[r.id])).length,
  ridesInLayer: RIDES.filter(r => r.tier !== 'show' && rideMarkers[r.id] && rideLayer.hasLayer(rideMarkers[r.id])).length,
  totalShows: RIDES.filter(r => r.tier === 'show').length,
  totalRides: RIDES.filter(r => r.tier !== 'show').length,
  category: mapCategory,
})"""

report = {}
errors = []

with sync_playwright() as p:
    browser = p.chromium.launch(args=["--no-sandbox"])
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
    page.on("console", lambda m: errors.append(f"console.{m.type}: {m.text[:140]}")
            if m.type == "error" else None)

    page.goto(BASE, wait_until="domcontentloaded")
    page.wait_for_timeout(2000)
    page.evaluate("() => document.getElementById('site-tour')?.remove()")
    page.evaluate("() => switchTab('map')")
    page.wait_for_timeout(1200)

    for park in PARKS:
        page.evaluate("() => document.getElementById('site-title-btn').click()")
        page.click(f"#park-menu [data-park='{park}']")
        page.wait_for_timeout(2500)
        entry = {}
        for cat in ["all", "rides", "shows"]:
            page.click(f".map-filter button[data-mapcat='{cat}']")
            page.wait_for_timeout(1200)
            st = page.evaluate(STATE_JS)
            st.update(page.evaluate(OVERLAP_JS))
            entry[cat] = st
        report[park] = entry

    # Category must survive a reload.
    page.click(".map-filter button[data-mapcat='shows']")
    page.wait_for_timeout(600)
    page.reload(wait_until="domcontentloaded")
    page.wait_for_timeout(2500)
    page.evaluate("() => document.getElementById('site-tour')?.remove()")
    report["persisted_category"] = page.evaluate("() => mapCategory")
    report["persisted_btn_active"] = page.evaluate(
        "() => document.querySelector('.map-filter button.is-active')?.dataset.mapcat")

    report["errors"] = errors or "none"
    browser.close()

print(json.dumps(report, indent=2, ensure_ascii=False))
