"""Interaction QA: rides tab, show-on-map button, nearby tab, filters, tab persistence."""
import json
import sys
from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:4173/index.html"
PARKS = ["epic", "studios", "islands"]


def main():
    errors = []
    report = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox"])
        page = browser.new_page(viewport={"width": 420, "height": 900})  # mobile-ish
        page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))

        page.goto(BASE, wait_until="domcontentloaded")
        page.wait_for_timeout(1500)
        page.evaluate("() => document.getElementById('site-tour')?.classList.add('hidden')")

        for park in PARKS:
            page.evaluate("() => document.getElementById('site-title-btn').click()")
            page.click(f"#park-menu [data-park='{park}']")
            page.wait_for_timeout(900)

            # rides tab
            page.click("button[data-tab='rides']")
            page.wait_for_timeout(600)
            cards = page.locator("#rides-container .ride").count()
            map_btns = page.locator("#rides-container .ride-map-btn").count()

            # click first show-on-map button
            switched = None
            popup = None
            if map_btns:
                page.locator("#rides-container .ride-map-btn").first.click()
                page.wait_for_timeout(1200)
                switched = page.evaluate(
                    "() => document.querySelector(\"button[data-tab='map']\").classList.contains('active')")
                popup = page.locator(".leaflet-popup").count()

            # filters
            page.click("button[data-tab='rides']")
            page.wait_for_timeout(400)
            land_vals = page.evaluate(
                "() => [...document.getElementById('land-filter').options].map(o=>o.value)")
            filtered = None
            if len(land_vals) > 1:
                page.select_option("#land-filter", land_vals[1])
                page.wait_for_timeout(500)
                filtered = page.locator("#rides-container .ride").count()
                page.select_option("#land-filter", "all")
                page.wait_for_timeout(400)

            # search
            page.fill("#search-input", "a")
            page.wait_for_timeout(500)
            searched = page.locator("#rides-container .ride").count()
            page.fill("#search-input", "")
            page.wait_for_timeout(400)

            # nearby tab
            page.click("button[data-tab='nearby']")
            page.wait_for_timeout(600)
            nearby_text = page.locator("#tab-nearby").inner_text()[:60]

            report[park] = {
                "rideCards": cards,
                "showOnMapButtons": map_btns,
                "clickSwitchedToMap": switched,
                "popupOpened": popup,
                "landFilterOptions": len(land_vals),
                "cardsAfterLandFilter": filtered,
                "cardsAfterSearch": searched,
                "nearbyPanel": nearby_text.replace("\n", " | "),
            }

        # tab persistence
        page.click("button[data-tab='overview']")
        page.wait_for_timeout(500)
        page.reload(wait_until="domcontentloaded")
        page.wait_for_timeout(1500)
        page.evaluate("() => document.getElementById('site-tour')?.remove()")
        report["tabAfterReload_expect_overview"] = page.evaluate(
            "() => [...document.querySelectorAll('.tab-btn')].find(b=>b.classList.contains('active'))?.dataset.tab")
        page.click("button[data-tab='nearby']")
        page.wait_for_timeout(400)
        page.reload(wait_until="domcontentloaded")
        page.wait_for_timeout(1500)
        page.evaluate("() => document.getElementById('site-tour')?.remove()")
        report["tabAfterReload_expect_nearby"] = page.evaluate(
            "() => [...document.querySelectorAll('.tab-btn')].find(b=>b.classList.contains('active'))?.dataset.tab")
        report["parkAfterReload"] = page.evaluate(
            "() => localStorage.getItem('universalActivePark')")

        browser.close()

    report["pageErrors"] = errors or "none"
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
