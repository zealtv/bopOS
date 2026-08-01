#!/usr/bin/env python3
"""Capture dashboard screenshots for the documentation set.

Launches the real dashboard/server.py plus tools/simfleet.py on non-default
ports with a seeded five-seat installation, then captures one screenshot per
tab into docs/images/.
"""
import json
import os
import subprocess
import sys
import tempfile
import time

sys.dont_write_bytecode = True
from playwright.sync_api import sync_playwright

HERE = os.path.realpath(os.path.dirname(__file__))
REPO = "/home/user/bopOS"
if not os.path.isfile(os.path.join(REPO, "tools", "simfleet.py")):
    raise SystemExit("cannot locate the bopOS repo root")
OUT = os.path.join(REPO, "docs", "images")
os.makedirs(OUT, exist_ok=True)

HTTP, LISTEN, SEND = 18310, 15310, 16310
SEATS = [
    # uid suffix index, id, name, positions
    (1, 0, "willow", [2.0, 2.0]),
    (2, 1, "birch", [4.5, 2.5]),
    (3, 2, "rowan", [7.0, 2.0]),
    (4, 3, "alder", [3.0, 5.5, 5.0, 6.0]),
]


def uid(index):
    return f"02:53:49:4d:{(index >> 8) & 255:02x}:{index & 255:02x}"


def main():
    with tempfile.TemporaryDirectory() as temp:
        state_file = os.path.join(temp, "installation.json")
        node_state = os.path.join(temp, "nodes")
        os.makedirs(node_state)
        seats = {}
        for index, seat_id, name, pos in SEATS:
            pairs = [pos[i:i + 2] for i in range(0, len(pos), 2)]
            seats[str(seat_id)] = {"id": seat_id, "name": name, "params": {},
                                   "groups": [0] if seat_id < 3 else [],
                                   "positions": pairs, "bound": uid(index)}
            with open(os.path.join(node_state, uid(index).replace(":", "-") + ".json"),
                      "w", encoding="utf-8") as target:
                json.dump({"id": seat_id, "name": name, "positions": pos}, target)
        with open(state_file, "w", encoding="utf-8") as target:
            json.dump({
                "schema": 1,
                "name": "docs-screenshots",
                "room": {"width": 10, "depth": 8, "units": "m", "origin": [0, 0]},
                "groups": {"0": {"id": 0, "name": "ring"}},
                "seats": seats,
            }, target)
        server = subprocess.Popen([
            sys.executable, os.path.join(REPO, "dashboard/server.py"),
            "--port", str(HTTP), "--listen-port", str(LISTEN),
            "--send-port", str(SEND), "--osc-target", "127.0.0.1",
            "--state-file", state_file,
        ], cwd=REPO, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        fleet = subprocess.Popen([
            sys.executable, os.path.join(REPO, "tools/simfleet.py"),
            "--devices", "5", "--unassigned", "1",
            "--state-dir", node_state, "--target", "127.0.0.1",
            "--report-port", str(LISTEN), "--cmd-port", str(SEND),
            "--hb-interval", "0.5",
        ], cwd=REPO, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        try:
            time.sleep(3)
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(
                    executable_path="/opt/pw-browsers/chromium")
                page = browser.new_page(viewport={"width": 1440, "height": 960})
                page.goto(f"http://127.0.0.1:{HTTP}/")
                page.wait_for_selector('.device-row', state="attached",
                                       timeout=15000)
                page.wait_for_timeout(2500)
                for tab in ("dashboard", "seats", "devices", "patches", "assets"):
                    page.click(f'#tab-button-{tab}')
                    page.wait_for_timeout(1200)
                    page.evaluate("window.scrollTo(0,0)")
                    page.screenshot(path=os.path.join(OUT, f"tab-{tab}.png"))
                    print("captured", f"tab-{tab}.png")
                try:
                    page.click('#tab-button-dashboard')
                    page.wait_for_timeout(600)
                    frame = page.frame_locator('#dashboard-live-view')
                    frame.locator('button', has_text="Seats").first.click()
                    page.wait_for_timeout(1200)
                    page.evaluate("window.scrollTo(0,0)")
                    page.screenshot(path=os.path.join(OUT, "tab-dashboard-seats.png"))
                    print("captured tab-dashboard-seats.png")
                except Exception as error:
                    print("dashboard Seats sub-tab skipped:", error)
                browser.close()
        finally:
            for proc in (fleet, server):
                proc.terminate()
            for proc in (fleet, server):
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
    print("done ->", OUT)


if __name__ == "__main__":
    main()
