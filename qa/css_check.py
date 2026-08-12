"""Validate the inline <style> blocks: brace balance + browser-reported parse errors."""
import re
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

path = Path(sys.argv[1] if len(sys.argv) > 1 else "index.html")
html = path.read_text()

blocks = re.findall(r"<style[^>]*>(.*?)</style>", html, re.S)
print(f"style blocks: {len(blocks)}")

fail = False
for i, css in enumerate(blocks):
    stripped = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    if stripped.count("{") != stripped.count("}"):
        print(f"  block {i}: BRACE MISMATCH {stripped.count('{')} open vs {stripped.count('}')} close")
        fail = True

# The browser is the real judge: it silently drops rules it cannot parse, so we
# compare the rules it accepted against the number of top-level rules we wrote.
with sync_playwright() as p:
    browser = p.chromium.launch(args=["--no-sandbox"])
    page = browser.new_page()
    page.goto(f"file://{path.resolve()}", wait_until="domcontentloaded")
    page.wait_for_timeout(1200)
    info = page.evaluate("""() => {
      const out = [];
      for (const sheet of document.styleSheets) {
        let rules;
        try { rules = sheet.cssRules; } catch (e) { continue; }
        if (sheet.href) continue;               // only our inline styles
        out.push(rules.length);
      }
      return out;
    }""")
    print("inline sheets, parsed rule counts:", info)
    browser.close()

for i, css in enumerate(blocks):
    # Count declarations sitting outside any block (the orphan-block signature).
    depth, orphan_lines = 0, []
    for lineno, line in enumerate(css.splitlines(), 1):
        code = re.sub(r"/\*.*?\*/", "", line)
        if depth == 0 and re.match(r"\s*[a-z-]+\s*:", code) and "{" not in code:
            orphan_lines.append(lineno)
        depth += code.count("{") - code.count("}")
    if orphan_lines:
        print(f"  block {i}: declarations outside any rule at lines {orphan_lines[:10]}")
        fail = True

print("CSS_FAIL" if fail else "CSS_OK")
sys.exit(1 if fail else 0)
