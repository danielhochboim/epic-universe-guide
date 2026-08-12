"""Screenshot the map per park per category (visual confirmation)."""
import os
import sys
from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:4173/index.html"
OUT = sys.argv[2] if len(sys.argv) > 2 else "/tmp/declutter"
os.makedirs(OUT, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(args=["--no-sandbox"])
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    page.goto(BASE, wait_until="domcontentloaded")
    page.wait_for_timeout(2000)
    page.evaluate("() => document.getElementById('site-tour')?.remove()")
    page.evaluate("() => switchTab('map')")
    page.wait_for_timeout(1200)

    for park in ["epic", "studios", "islands"]:
        page.evaluate("() => document.getElementById('site-title-btn').click()")
        page.click(f"#park-menu [data-park='{park}']")
        page.wait_for_timeout(2500)
        for cat in ["all", "rides", "shows"]:
            page.click(f".map-filter button[data-mapcat='{cat}']")
            page.wait_for_timeout(1500)
            path = f"{OUT}/{park}_{cat}.png"
            page.locator("#map-shell").screenshot(path=path)
            n = page.evaluate(
                "() => [...document.querySelectorAll('.ride-marker-wrap.is-visible .map-ride-label')]"
                ".filter(e => e.style.visibility !== 'hidden').length")
            print(f"{park}/{cat}: {n} labels -> {path}")
    browser.close()
