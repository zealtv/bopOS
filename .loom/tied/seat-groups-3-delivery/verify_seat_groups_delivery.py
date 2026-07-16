#!/usr/bin/env python3
"""Real-dashboard browser verification for Seat-group delivery."""

import json
import os
import random
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

from playwright.sync_api import sync_playwright

sys.dont_write_bytecode = True
HERE = os.path.realpath(os.path.dirname(__file__))
REPO = HERE
while not os.path.isfile(os.path.join(REPO, "tools", "simfleet.py")):
    parent = os.path.dirname(REPO)
    if parent == REPO:
        raise SystemExit("cannot locate bopOS repository")
    REPO = parent

FAILURES = []


def check(label, condition, detail=""):
    print("[{}] {}{}".format("PASS" if condition else "FAIL", label,
                              " -- " + detail if detail and not condition else ""),
          flush=True)
    if not condition:
        FAILURES.append(label)


def free_port(kind):
    for _attempt in range(256):
        port = random.SystemRandom().randrange(20000, 60000)
        probe = socket.socket(socket.AF_INET, kind)
        try:
            probe.bind(("127.0.0.1", port))
        except OSError:
            probe.close()
            continue
        probe.close()
        return port
    raise RuntimeError("could not reserve a local port")


def stop(process):
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def wait_http(url, process):
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("dashboard exited before serving HTTP")
        try:
            urllib.request.urlopen(url, timeout=.5).close()
            return
        except OSError:
            time.sleep(.1)
    raise RuntimeError("dashboard did not serve HTTP")


def installation_fixture():
    groups = {
        "1": {"id": 1, "name": "Front row"},
        "2": {"id": 2, "name": "Guitars"},
        "7": {"id": 7, "name": "Roving"},
        "9": {"id": 9, "name": "Choir"},
        "12": {"id": 12, "name": "Empty study"},
    }
    seats = {}
    for seat_id in range(100):
        memberships = []
        for group_id, divisor in ((1, 2), (2, 3), (7, 5), (9, 7)):
            if seat_id % divisor == 0:
                memberships.append(group_id)
        seats[str(seat_id)] = {
            "id": seat_id,
            "name": f"Seat {seat_id}",
            "positions": [[.45 + (seat_id % 10) * 1.0,
                           .4 + (seat_id // 10) * .75]],
            "params": {}, "groups": memberships, "bound": None,
        }
    return {"schema": 1, "name": "Group delivery rig", "seats": seats,
            "groups": groups, "next_group_id": 13,
            "room": {"width": 10, "depth": 8, "units": "m", "origin": [0, 0]}}


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-seat-groups-ui-") as temp:
        state_path = os.path.join(temp, "installation.json")
        assets, patches = os.path.join(temp, "assets"), os.path.join(temp, "patches")
        os.makedirs(assets); os.makedirs(patches)
        with open(state_path, "w", encoding="utf-8") as target:
            json.dump(installation_fixture(), target)
        http_port = free_port(socket.SOCK_STREAM)
        listen_port = free_port(socket.SOCK_DGRAM)
        send_port = free_port(socket.SOCK_DGRAM)
        base_url = f"http://127.0.0.1:{http_port}"
        log_path = os.path.join(temp, "server.log")
        log = open(log_path, "w", encoding="utf-8")
        server = None
        try:
            server = subprocess.Popen([
                sys.executable, os.path.join(REPO, "dashboard", "server.py"),
                "--host", "127.0.0.1", "--port", str(http_port),
                "--listen-port", str(listen_port), "--send-port", str(send_port),
                "--osc-target", "127.0.0.1", "--state-file", state_path,
                "--assets-dir", assets, "--patches-dir", patches,
            ], cwd=REPO, stdout=log, stderr=subprocess.STDOUT)
            wait_http(base_url, server)
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page(viewport={"width": 1440, "height": 1100})
                page.set_default_timeout(10000)
                page_errors = []
                page.on("pageerror", lambda error: page_errors.append(str(error)))

                def dialog(dialog):
                    if dialog.type == "prompt":
                        answer = "Strings" if "Rename" in dialog.message else "Percussion"
                        dialog.accept(answer)
                    else:
                        dialog.accept()
                page.on("dialog", dialog)
                page.goto(base_url + "/#seats")
                page.wait_for_selector("#ws-status.online")
                page.wait_for_function("() => Object.keys(installation.seats||{}).length === 100")
                page.wait_for_selector("#tab-seats:not([hidden])")

                order = page.eval_on_selector_all(
                    ".seat-sidebar > *", "els => els.map(el => el.id)")
                check("Groups is subordinate after Seat detail and before utilities",
                      order.index("seat-detail") < order.index("groups-panel")
                      < order.index("simulate-panel"), repr(order))
                check("Collapsed summary exposes quiet visibility and catalog counts",
                      page.locator("#groups-summary").inner_text() == "0 shown · 5 total")
                eye = page.locator('[data-group-eye="1"]')
                check("Eye-off icon and action label expose hidden layer state",
                      eye.get_attribute("aria-pressed") == "false"
                      and "Show Front row on map" == eye.get_attribute("aria-label")
                      and eye.locator("path").count() == 2)

                page.click('[data-group-focus="1"]')
                page.wait_for_selector('#group-map-bar:not([hidden])')
                check("Focus ensures visibility and renders member rails",
                      page.locator('#spatial .membership-rail[data-group-id="1"]:not(.back)').count() == 50
                      and page.locator('[data-group-row="1"]').get_attribute("class").find("focused") >= 0)
                check("Legend keeps canonical name and token above the map",
                      "front row" in page.locator("#group-map-legend").inner_text().lower()
                      and "g1" in page.locator("#group-map-legend").inner_text().lower())
                hit = page.locator('#spatial [data-seat-id="0"] .element-hit').bounding_box()
                check("Dense 100-Seat map retains a touch-sized invisible hit target",
                      hit and hit["width"] >= 44 and hit["height"] >= 44, repr(hit))
                contrast = page.evaluate("""() => {
                  const rgb=s=>s.match(/\\d+/g).slice(0,3).map(Number);
                  const lum=v=>{v/=255;return v<=.04045?v/12.92:Math.pow((v+.055)/1.055,2.4)};
                  const L=s=>{const [r,g,b]=rgb(s).map(lum);return .2126*r+.7152*g+.0722*b};
                  const a=L(getComputedStyle(document.querySelector('.membership-rail:not(.back)')).stroke);
                  const b=L('rgb(18, 23, 28)'); return (Math.max(a,b)+.05)/(Math.min(a,b)+.05);
                }""")
                check("First rail exceeds 3:1 graphical contrast on the room", contrast >= 3, str(contrast))

                page.keyboard.press("Escape")
                focus_class = page.locator('[data-group-row="1"]').get_attribute("class")
                first_escape = "focused" not in focus_class and not page.locator("#group-map-bar").is_hidden()
                page.keyboard.press("Escape")
                check("Escape removes focus first, then comparison overlays",
                      first_escape and page.locator("#group-map-bar").is_hidden())
                page.click('[data-group-focus="1"]')

                for group_id in (2, 7, 9):
                    page.click(f'[data-group-eye="{group_id}"]')
                check("Four-group overlap uses four separate numbered rail slots",
                      page.locator('#spatial [data-seat-id="0"] .membership-rail:not(.back)').count() == 4
                      and page.locator("#group-map-legend .group-slot").all_inner_texts() == ["1", "2", "3", "4"])
                page.click('[data-group-eye="2"]')
                stable = (page.locator('[data-group-row="7"] .group-slot').inner_text() == "3"
                          and page.locator('[data-group-row="9"] .group-slot').inner_text() == "4")
                page.click('[data-group-eye="2"]')
                check("Hiding one group does not renumber other visible rail slots", stable)
                page.click('[data-group-eye="12"]')
                check("Fifth visible group is rejected without replacing context",
                      not page.locator("#group-limit").is_hidden()
                      and page.locator("#groups-summary").inner_text().startswith("4 shown"))

                page.click('[data-group-eye="9"]')
                page.click('[data-group-focus="12"]')
                check("Empty focused group has an explicit map state",
                      not page.locator("#group-map-message").is_hidden()
                      and "No Seats" in page.locator("#group-map-message").inner_text())
                page.click("#group-view-clear")
                check("Clear view preserves membership while removing all overlays",
                      page.locator("#group-map-bar").is_hidden()
                      and page.locator("#spatial .membership-rail").count() == 0
                      and page.evaluate("() => installation.seats['0'].groups.join(',')")
                      == "1,2,7,9")

                page.locator('.seat-row[data-seat-id="1"] .dot').click()
                page.wait_for_selector('#seat-detail [data-seat-group="1"]')
                page.check('#seat-detail [data-seat-group="1"]')
                page.wait_for_function("() => installation.seats['1'].groups.includes(1)")
                check("Seat checklist authors multi-group membership", True)

                page.click('[data-group-focus="2"]')
                page.wait_for_selector('#groups-content [data-group-member="1"]')
                page.check('#groups-content [data-group-member="1"]')
                page.wait_for_function("() => installation.seats['1'].groups.includes(2)")
                check("Group checklist updates the same canonical Seat membership", True)

                page.click("#group-create")
                page.wait_for_function("() => installation.groups?.['13']?.name === 'Percussion'")
                page.click('[data-group-row="13"] .group-overflow > summary')
                page.click('[data-group-rename="13"]')
                page.wait_for_function("() => installation.groups?.['13']?.name === 'Strings'")
                page.click('[data-group-row="13"] .group-overflow > summary')
                page.click('[data-group-delete="13"]')
                page.wait_for_function("() => !installation.groups?.['13']")
                check("Create, rename and delete preserve immutable group ID semantics", True)

                if page.locator("#groups-panel").get_attribute("open") is not None:
                    page.click("#groups-panel > summary")
                check("Collapsing Groups leaves active map comparison state intact",
                      page.locator("#groups-summary").inner_text().startswith("1 shown")
                      and not page.locator("#group-map-bar").is_hidden())
                page.screenshot(path=os.path.join(HERE, "seat-groups-delivery.png"),
                                full_page=True)
                check("Browser emitted no page errors", not page_errors, repr(page_errors))
                touch_context = browser.new_context(
                    viewport={"width": 768, "height": 1024}, has_touch=True,
                    is_mobile=True)
                touch = touch_context.new_page()
                touch.goto(base_url + "/#seats")
                touch.wait_for_selector("#ws-status.online")
                touch.wait_for_function(
                    "() => Object.keys(installation.seats||{}).length === 100")
                touch.locator('[data-group-eye="1"]').tap()
                eye_box = touch.locator('[data-group-eye="1"]').bounding_box()
                map_box = touch.locator("#spatial-section").bounding_box()
                side_box = touch.locator(".seat-sidebar").bounding_box()
                check("Touch layout stacks the sidebar and keeps 44px eye controls",
                      eye_box and eye_box["width"] >= 44 and eye_box["height"] >= 44
                      and map_box and side_box
                      and side_box["y"] >= map_box["y"] + map_box["height"] - 1,
                      repr((eye_box, map_box, side_box)))
                check("Touch eye control reveals the same comparison layer",
                      touch.locator('[data-group-eye="1"]').get_attribute("aria-pressed")
                      == "true" and not touch.locator("#group-map-bar").is_hidden())
                touch_context.close()
                browser.close()
        finally:
            stop(server)
            log.close()

        if FAILURES:
            with open(log_path, encoding="utf-8") as source:
                print("\nserver log tail:\n", source.read()[-3000:])
    print()
    if FAILURES:
        print("FAILED:", ", ".join(FAILURES))
        return 1
    print("Seat-group delivery browser checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
