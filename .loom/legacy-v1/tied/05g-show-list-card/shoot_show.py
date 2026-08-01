#!/usr/bin/env python3
"""Screenshot the Show tab's step list, both themes. §12 is a visual invariant.

    python shoot_show.py before
    python shoot_show.py after

Sets BOTH theme storage keys: `.loom/tied/03-chrome-reclamation` found that
`shoot.py` wrote `bopos.theme` while `theme.js` reads `bopos-theme`, which is why
every dark shot in stitch 02 came out light.
"""
import os
import subprocess
import sys
import time

REPO = os.path.realpath(os.path.dirname(__file__))
while not os.path.isfile(os.path.join(REPO, "tools", "simfleet.py")):
    parent = os.path.dirname(REPO)
    if parent == REPO:
        raise SystemExit("cannot locate bopOS repository")
    REPO = parent

STAGE = sys.argv[1] if len(sys.argv) > 1 else "shot"
OUT = os.path.dirname(os.path.realpath(__file__))
PY = os.path.expanduser("~/.venvs/bopos/bin/python")
PORT, OSC_IN, OSC_OUT = 8391, 6691, 5591


def main():
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    server = subprocess.Popen(
        [PY, os.path.join(REPO, "dashboard", "server.py"),
         "--port", str(PORT), "--listen-port", str(OSC_OUT),
         "--send-port", str(OSC_IN)],
        cwd=REPO, env=env,
        stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    time.sleep(4)
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            for theme in ("light", "dark"):
                page = browser.new_page(
                    viewport={"width": 1440, "height": 1000})
                page.set_default_timeout(15000)
                page.on("dialog", lambda d: d.dismiss())
                page.goto(f"http://127.0.0.1:{PORT}")
                page.evaluate(
                    "t => { localStorage.setItem('bopos-theme', t);"
                    " localStorage.setItem('bopos.theme', t);"
                    " document.documentElement.dataset.theme = t; }", theme)
                page.click("#tab-button-show")
                time.sleep(2.0)
                page.screenshot(
                    path=os.path.join(OUT, f"{STAGE}-show-{theme}.png"))
                box = page.query_selector(".show-rows-box")
                if box:
                    box.screenshot(
                        path=os.path.join(OUT, f"{STAGE}-list-{theme}.png"))
                page.close()
            browser.close()
    finally:
        server.terminate()
    print("wrote", STAGE, "shots to", OUT)


if __name__ == "__main__":
    main()
