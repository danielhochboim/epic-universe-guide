"""Headless QA harness for the Universal Orlando guide map.

Runs a real Chromium against the locally served site, switches between all
three parks and reports what the map actually renders: marker counts, marker
pixel positions relative to the map viewport, active tile layer and any
console / page errors.

Usage:  /tmp/qavenv/bin/python qa/map_qa.py [base_url]
"""
import json
import sys
from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:4173/index.html"
PARKS = ["epic", "studios", "islands"]

PROBE = """
() => {
  const mapEl = document.getElementById('map');
  const box = mapEl.getBoundingClientRect();
  const icons = [...document.querySelectorAll('.ride-marker-icon')];
  let inside = 0;
  const positions = [];
  for (const el of icons) {
    const r = el.getBoundingClientRect();
    const cx = r.left + r.width / 2;
    const cy = r.top + r.height / 2;
    const ok = cx >= box.left && cx <= box.right && cy >= box.top && cy <= box.bottom;
    if (ok) inside++;
    positions.push([Math.round(cx - box.left), Math.round(cy - box.top), ok]);
  }
  const tiles = [...document.querySelectorAll('.leaflet-tile-loaded')].map(t => t.src);
  const tileHosts = [...new Set(tiles.map(u => { try { return new URL(u).host; } catch (e) { return 'bad'; } }))];
  const brokenTiles = [...document.querySelectorAll('img.leaflet-tile')].filter(t => t.complete && t.naturalWidth === 0).length;
  return {
    title: document.getElementById('site-title-btn').textContent.trim(),
    mapSize: [Math.round(box.width), Math.round(box.height)],
    markerEls: icons.length,
    markersInsideViewport: inside,
    tilesLoaded: tiles.length,
    tileHosts,
    brokenTiles,
    landOptions: document.getElementById('land-filter').options.length,
    rideCards: document.querySelectorAll('#tab-rides .ride-card, #rides-container .ride-card').length,
    samplePositions: positions.slice(0, 6),
    storedPark: localStorage.getItem('universalActivePark'),
  };
}
"""

DATASET = """
() => {
  const out = {};
  for (const k of Object.keys(PARKS)) {
    const rides = PARKS[k].rides;
    const bad = rides.filter(r => !Number.isFinite(Number(r.lat)) || !Number.isFinite(Number(r.lng)));
    const lats = rides.map(r => Number(r.lat));
    const lngs = rides.map(r => Number(r.lng));
    out[k] = {
      count: rides.length,
      badCoords: bad.map(r => r.id),
      latRange: [Math.min(...lats).toFixed(5), Math.max(...lats).toFixed(5)],
      lngRange: [Math.min(...lngs).toFixed(5), Math.max(...lngs).toFixed(5)],
      spanMetersLat: Math.round((Math.max(...lats) - Math.min(...lats)) * 111000),
      spanMetersLng: Math.round((Math.max(...lngs) - Math.min(...lngs)) * 98000),
      missingLand: [...new Set(rides.filter(r => !LANDS[r.land]).map(r => r.land))],
    };
  }
  return out;
}
"""


def main():
    errors = []
    report = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox"])
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.on("console", lambda m: errors.append(f"console.{m.type}: {m.text}") if m.type in ("error", "warning") else None)
        page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))

        page.goto(BASE, wait_until="networkidle")
        page.evaluate("() => { document.getElementById('site-tour')?.classList.add('hidden'); }")

        try:
            report["dataset"] = page.evaluate(DATASET)
        except Exception as exc:  # dataset lives in script scope, not window
            report["dataset"] = f"unavailable in page scope: {exc}"

        page.click("button[data-tab='map']")
        page.wait_for_timeout(1200)

        for park in PARKS:
            page.evaluate("() => document.getElementById('site-title-btn').click()")
            page.click(f"#park-menu [data-park='{park}']")
            page.wait_for_timeout(1000)
            # Basemap tiles load asynchronously; give them a real chance before probing.
            try:
                page.wait_for_function(
                    "() => document.querySelectorAll('.leaflet-tile-loaded').length > 0",
                    timeout=15000,
                )
            except Exception:
                errors.append(f"{park}: no basemap tiles loaded within 15s")
            page.wait_for_timeout(800)
            report[park] = page.evaluate(PROBE)

        # reload persistence check
        page.reload(wait_until="networkidle")
        page.wait_for_timeout(1200)
        report["after_reload"] = page.evaluate(PROBE)

        browser.close()

    report["errors"] = errors
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
