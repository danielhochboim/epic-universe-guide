# QA harness

Real headless-Chromium checks for the guide. These exist because DOM snapshots
reported "looks fine" while the page was actually throwing a `pageerror` that
aborted park switching — only a real browser listening to `pageerror` caught it.

## Setup

```bash
uv venv /tmp/qavenv --python 3.11
/home/ubuntu/.hermes/bin/uv pip install --python /tmp/qavenv/bin/python playwright
```

Chromium is already present under `~/.cache/ms-playwright`.

## Run

Serve the site, then run both scripts:

```bash
python3 -m http.server 4173 --bind 127.0.0.1   # from the repo root
/tmp/qavenv/bin/python qa/map_qa.py
/tmp/qavenv/bin/python qa/interaction_qa.py
```

## What they assert

`map_qa.py` — per park: marker count, markers inside the map viewport, basemap
tile host, broken tiles, land-filter options, dataset coordinate sanity, and
any console/page errors.

`interaction_qa.py` — per park: ride cards, "show on map" buttons, that
clicking one switches to the map and opens a popup, land filter, search, the
nearby panel, plus tab/park persistence across reload.

## Expected baseline

| park | rides | markers | basemap |
|---|---|---|---|
| epic | 19 | 19 | services.universalorlando.com |
| studios | 22 | 22 | tile.openstreetmap.org |
| islands | 25 | 25 | tile.openstreetmap.org |

`pageErrors` must be `none`. The Universal tile service 404s outside Epic
Universe, which is why the other two parks use the OSM fallback layer.
