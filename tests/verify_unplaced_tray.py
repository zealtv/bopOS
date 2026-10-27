"""Real dashboard: the Seats map's UNPLACED tray grows to hold every Seat.

Unplaced Seats used to sit in one row at 1.7 m spacing that never wrapped, so
in a 10 m room the seventh one onwards fell outside the tray and the svg and
could not be seen or dragged (81-seats-tab/1-unplaced-tray-wraps).
"""
import json
import os
import socket
import subprocess
import sys
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright
from verify_log_destination import free_port, physical_host, wait_http, stop, write_fixture, ROOT
from project_fixture import data_root

UNPLACED = 15
SHOTS = os.environ.get("BOPOS_SHOTS")


def write_tray_fixture(root):
    patches, assets, state, manifest = write_fixture(root)
    data = json.loads(Path(state).read_text(encoding="utf-8"))
    data["room"] = {"width": 10, "depth": 8, "origin": [0, 0]}
    data["seats"] = {
        str(seat): {"id": seat, "name": f"Seat {seat}", "bound": None,
                    "positions": [], "params": {}}
        for seat in range(UNPLACED)}
    Path(state).write_text(json.dumps(data), encoding="utf-8")
    return patches, assets, state


def outside_svg(page):
    """Seat ids whose dot lies outside the visible svg box."""
    return page.evaluate("""() => {
        const box = document.querySelector('#spatial').getBoundingClientRect();
        return [...document.querySelectorAll('#spatial g[data-seat-id] .element-dot')]
          .filter(dot => { const r = dot.getBoundingClientRect();
            return r.left < box.left || r.right > box.right || r.top < box.top || r.bottom > box.bottom; })
          .map(dot => dot.closest('g[data-seat-id]').dataset.seatId);
    }""")


def main():
    failures = []

    def check(label, condition, detail=""):
        print(("PASS " if condition else "FAIL ") + label + (f" — {detail}" if detail and not condition else ""))
        if not condition:
            failures.append(label)

    with tempfile.TemporaryDirectory(prefix="bopos-tray-") as root:
        patches, assets, state = write_tray_fixture(root)
        host = physical_host()
        http_port = free_port(socket.SOCK_STREAM)
        base = f"http://127.0.0.1:{http_port}"
        with (Path(root) / "dashboard.log").open("w") as output:
            dashboard = subprocess.Popen([
                sys.executable, str(ROOT / "dashboard/server.py"),
                "--host", "127.0.0.1", "--port", str(http_port),
                "--listen-port", str(free_port(socket.SOCK_DGRAM)),
                "--send-port", str(free_port(socket.SOCK_DGRAM, host)),
                "--input-port", str(free_port(socket.SOCK_DGRAM)),
                "--stream-port", str(free_port(socket.SOCK_DGRAM)),
                "--osc-target", host, "--data-dir", data_root(str(state)),
                "--assets-dir", str(assets), "--patches-dir", str(patches),
                "--public-url", base,
            ], cwd=ROOT, stdout=output, stderr=subprocess.STDOUT)
            try:
                wait_http(base, dashboard)
                with sync_playwright() as playwright:
                    browser = playwright.chromium.launch(headless=True)
                    page = browser.new_page(viewport={"width": 1440, "height": 1000})
                    errors = []
                    page.on("pageerror", lambda error: errors.append(str(error)))
                    page.goto(base + "#seats")
                    page.wait_for_function(
                        "n => document.querySelectorAll('#spatial g[data-seat-id]').length === n",
                        arg=UNPLACED)

                    check("every unplaced Seat sits inside the map at desktop width",
                          outside_svg(page) == [], repr(outside_svg(page)))
                    rows = page.evaluate("""() => new Set([...document.querySelectorAll(
                        '#spatial g[data-seat-id] g.element')].map(g => g.getAttribute('transform')
                        .match(/ ([\\d.]+)\\)/)[1])).size""")
                    check("15 Seats in a 10 m room wrap into three rows", rows == 3, f"{rows} rows")
                    tray_inside = page.evaluate("""() => {
                        const tray = document.querySelector('#spatial .tray').getBBox();
                        return [...document.querySelectorAll('#spatial g[data-seat-id] g.element')].every(g => {
                          const [x, y] = g.getAttribute('transform').match(/[\\d.]+/g).map(Number);
                          return x > tray.x && x < tray.x + tray.width && y > tray.y && y < tray.y + tray.height; });
                    }""")
                    check("the tray rect encloses every unplaced Seat", tray_inside)
                    if SHOTS:
                        page.locator("#spatial").screenshot(path=os.path.join(SHOTS, "tray-desktop.png"))

                    last = page.locator(f'#spatial g[data-seat-id="{UNPLACED - 1}"] .element-dot')
                    start = last.bounding_box()
                    room = page.locator("#spatial .room").bounding_box()
                    page.mouse.move(start["x"] + start["width"] / 2, start["y"] + start["height"] / 2)
                    page.mouse.down()
                    page.mouse.move(room["x"] + room["width"] / 2, room["y"] + room["height"] / 2, steps=8)
                    page.mouse.up()
                    page.wait_for_function(
                        "id => (installation.seats[id]?.positions || []).length === 1", arg=str(UNPLACED - 1))
                    check("a Seat dragged from the last row into the room is placed", True)

                    placed = page.locator(f'#spatial g[data-seat-id="{UNPLACED - 1}"] .element-dot').bounding_box()
                    tray = page.locator("#spatial .tray").bounding_box()
                    page.mouse.move(placed["x"] + placed["width"] / 2, placed["y"] + placed["height"] / 2)
                    page.mouse.down()
                    page.mouse.move(tray["x"] + tray["width"] - 10, tray["y"] + tray["height"] - 10, steps=8)
                    page.mouse.up()
                    page.wait_for_function(
                        "id => (installation.seats[id]?.positions || []).length === 0", arg=str(UNPLACED - 1))
                    check("dropping it on the tray's bottom row unplaces it again", True)

                    page.set_viewport_size({"width": 390, "height": 844})
                    page.wait_for_timeout(150)
                    check("every unplaced Seat sits inside the map at 390 px",
                          outside_svg(page) == [], repr(outside_svg(page)))
                    check("no horizontal scroll at 390 px",
                          page.evaluate("document.documentElement.scrollWidth <= innerWidth"))
                    if SHOTS:
                        page.locator("#spatial").screenshot(path=os.path.join(SHOTS, "tray-390.png"))
                    check("the map emitted no page errors", not errors, repr(errors))
                    browser.close()
            finally:
                stop(dashboard)
    if failures:
        raise SystemExit(f"{len(failures)} tray check(s) failed")
    print("Unplaced tray checks passed")


if __name__ == "__main__":
    main()
