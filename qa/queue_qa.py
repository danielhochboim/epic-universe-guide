"""QA for live queue-times: per-park fetch, proxy fallback, console cleanliness."""
import json
import sys
from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:4173/index.html"
PARKS = ["epic", "studios", "islands"]

report = {}
errors = []

with sync_playwright() as p:
    browser = p.chromium.launch(args=["--no-sandbox"])
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
    page.on("console", lambda m: errors.append(f"console.{m.type}: {m.text[:160]}")
            if m.type in ("error", "warning") else None)

    requested = []
    page.on("request", lambda r: requested.append(r.url)
            if "queue_times" in r.url or "queue-times" in r.url else None)

    page.goto(BASE, wait_until="domcontentloaded")
    page.wait_for_timeout(1500)
    page.evaluate("() => document.getElementById('site-tour')?.remove()")

    for park in PARKS:
        requested.clear()
        page.evaluate("() => document.getElementById('site-title-btn').click()")
        page.click(f"#park-menu [data-park='{park}']")
        # Allow the proxy chain to run through its fallbacks.
        page.wait_for_timeout(12000)
        report[park] = page.evaluate("""() => ({
            queueId: PARKS[activePark].queueId,
            liveEntries: Object.keys(liveQueueMap).length,
            status: document.getElementById('live-status')?.textContent.trim().slice(0, 90),
            dotText: document.getElementById('live-dot-text')?.textContent.trim(),
            dotOn: document.getElementById('live-dot')?.classList.contains('on'),
        })""")
        report[park]["parkUrlsRequested"] = sorted({
            u.split("parks/")[1].split("/")[0]
            for u in requested if "parks/" in u
        })

    report["errors"] = errors or "none"
    browser.close()

print(json.dumps(report, indent=2, ensure_ascii=False))
