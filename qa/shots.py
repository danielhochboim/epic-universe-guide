"""Capture a screenshot of the map for each park (visual confirmation)."""
import sys
from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:4173/index.html"
OUT = sys.argv[2] if len(sys.argv) > 2 else "/tmp"

with sync_playwright() as p:
    browser = p.chromium.launch(args=["--no-sandbox"])
    page = browser.new_page(viewport={"width": 1100, "height": 780})
    page.goto(BASE, wait_until="domcontentloaded")
    page.wait_for_timeout(1500)
    page.evaluate("() => document.getElementById('site-tour')?.remove()")
    page.click("button[data-tab='map']")
    page.wait_for_timeout(800)
    for park in ["epic", "studios", "islands"]:
        page.evaluate("() => document.getElementById('site-title-btn').click()")
        page.click(f"#park-menu [data-park='{park}']")
        page.wait_for_timeout(1000)
        try:
            page.wait_for_function(
                "() => document.querySelectorAll('.leaflet-tile-loaded').length > 3",
                timeout=15000)
        except Exception:
            pass
        page.wait_for_timeout(1500)
        path = f"{OUT}/map_{park}.png"
        page.locator("#map").screenshot(path=path)
        n = page.locator(".ride-marker-icon").count()
        print(f"{park}: {n} markers -> {path}")
    browser.close()
