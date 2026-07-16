#!/usr/bin/env python3
"""Browser verification for the post-delivery Seat/Group sidebar revisions."""

import importlib.util
import json
import os
import socket
import subprocess
import sys
import tempfile

from playwright.sync_api import sync_playwright

sys.dont_write_bytecode = True
HERE = os.path.realpath(os.path.dirname(__file__))
REPO = HERE
while not os.path.isfile(os.path.join(REPO, "tools", "simfleet.py")):
    parent = os.path.dirname(REPO)
    if parent == REPO:
        raise SystemExit("cannot locate bopOS repository")
    REPO = parent

BASE_VERIFY = os.path.join(
    REPO, ".loom", "tied", "seat-groups-3-delivery",
    "verify_seat_groups_delivery.py")
spec = importlib.util.spec_from_file_location("seat_group_delivery_verify", BASE_VERIFY)
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)

FAILURES = []


def check(label, condition, detail=""):
    print("[{}] {}{}".format("PASS" if condition else "FAIL", label,
                              " -- " + detail if detail and not condition else ""),
          flush=True)
    if not condition:
        FAILURES.append(label)


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-seat-group-revisions-") as temp:
        state = base.installation_fixture()
        state["seats"]["0"]["name"] = "Front 1"
        state["seats"]["1"]["name"] = "Front 2"
        state["seats"]["2"]["name"] = "Back Front"
        state["seats"]["3"]["name"] = "FRONT 3"
        state_path = os.path.join(temp, "installation.json")
        assets, patches = os.path.join(temp, "assets"), os.path.join(temp, "patches")
        os.makedirs(assets); os.makedirs(patches)
        with open(state_path, "w", encoding="utf-8") as target:
            json.dump(state, target)

        http_port = base.free_port(socket.SOCK_STREAM)
        listen_port = base.free_port(socket.SOCK_DGRAM)
        send_port = base.free_port(socket.SOCK_DGRAM)
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
            base.wait_http(base_url, server)
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page(viewport={"width": 1440, "height": 1000})
                page.set_default_timeout(10000)
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.on("dialog", lambda dialog: dialog.accept())
                page.goto(base_url + "/#seats")
                page.wait_for_selector("#ws-status.online")
                page.wait_for_function(
                    "() => Object.keys(installation.seats||{}).length === 100")

                check("Sidebar presents Seats and Groups as peer local tabs",
                      page.locator("#seat-sidebar-tabs [role=tab]").all_inner_texts()
                      == ["Seats", "Groups"]
                      and page.locator("#seat-sidebar-tab").get_attribute(
                          "aria-selected") == "true")
                check("Seats is the default editor and Groups is initially hidden",
                      page.locator("#seat-sidebar-panel").is_visible()
                      and page.locator("#group-sidebar-panel").is_hidden())
                check("Listener degrees and duplicate Simulation status are absent",
                      page.locator("#listener-heading-readout, #simulate-panel").count() == 0
                      and "listener" not in page.locator(
                          "#spatial-section > .section-head").inner_text().lower())

                page.locator('.seat-row[data-seat-id="0"] .dot').click()
                check("Seat detail keeps membership editing without group search",
                      page.locator("#seat-detail [data-seat-group]").count() == 5
                      and page.locator("#seat-group-search").count() == 0)

                page.click("#group-sidebar-tab")
                check("Groups tab swaps to the group catalog and editor",
                      page.locator("#group-sidebar-panel").is_visible()
                      and page.locator("#seat-sidebar-panel").is_hidden()
                      and page.locator("#group-create").is_visible()
                      and page.locator("[data-group-row]").count() == 5)
                check("Group catalog has no search control",
                      page.locator("#group-search").count() == 0)
                check("Venue remains a shared sidebar utility outside both tabs",
                      page.locator("#venue-bar").is_visible())

                page.click('[data-group-focus="1"]')
                page.wait_for_selector("#group-member-filter")
                filter_label = page.locator("label.group-filter").inner_text()
                check("Selected group exposes a filter, not a search",
                      filter_label.startswith("Filter Seats")
                      and page.locator("#group-member-filter").get_attribute("type")
                      == "text"
                      and "beginning" in page.locator(
                          "#group-member-filter").get_attribute("placeholder").lower())

                page.fill("#group-member-filter", "front")
                visible_names = page.locator(
                    '#groups-content [data-group-member-filter]:visible strong'
                ).all_inner_texts()
                check("Seat filter is case-insensitive prefix matching",
                      visible_names == ["Front 1", "Front 2", "FRONT 3"],
                      repr(visible_names))
                page.evaluate("() => render()")
                visible_after_render = page.locator(
                    '#groups-content [data-group-member-filter]:visible strong'
                ).all_inner_texts()
                check("Filter survives live dashboard rerenders while typing",
                      page.locator("#group-member-filter").input_value() == "front"
                      and page.evaluate(
                          "() => document.activeElement?.id") == "group-member-filter"
                      and visible_after_render == ["Front 1", "Front 2", "FRONT 3"],
                      repr(visible_after_render))
                page.fill("#group-member-filter", "front 2")
                page.press("#group-member-filter", "Enter")
                check("More filter text narrows the prefix result",
                      page.locator(
                          '#groups-content [data-group-member-filter]:visible strong'
                      ).all_inner_texts() == ["Front 2"])
                page.fill("#group-member-filter", "missing")
                check("No prefix matches produce explicit empty feedback",
                      not page.locator("#group-filter-empty").is_hidden())

                page.fill("#group-member-filter", "")
                page.check('#groups-content [data-group-member="1"]')
                page.wait_for_function("() => installation.seats['1'].groups.includes(1)")
                check("Filtered Group editor still authors canonical membership", True)
                check("Group focus still renders the ratified map overlay",
                      page.locator(
                          '#spatial .membership-rail[data-group-id="1"]:not(.back)'
                      ).count() > 0
                      and not page.locator("#group-map-bar").is_hidden())

                page.locator('#spatial [data-seat-id="0"] .element-hit').click(force=True)
                check("Selecting a Seat on the map returns to the Seats editor",
                      page.locator("#seat-sidebar-tab").get_attribute(
                          "aria-selected") == "true"
                      and page.locator("#seat-sidebar-panel").is_visible())
                page.click("#group-sidebar-tab")
                page.press("#group-sidebar-tab", "ArrowLeft")
                check("Local tabs support arrow-key switching",
                      page.locator("#seat-sidebar-tab").get_attribute(
                          "aria-selected") == "true")

                page.click("#group-sidebar-tab")
                page.fill("#group-member-filter", "front")
                page.screenshot(path=os.path.join(HERE, "seat-group-tabs.png"),
                                full_page=True)
                check("Browser emitted no page errors", not errors, repr(errors))
                browser.close()
        finally:
            base.stop(server)
            log.close()

        if FAILURES:
            with open(log_path, encoding="utf-8") as source:
                print("\nserver log tail:\n", source.read()[-3000:])
    print()
    if FAILURES:
        print("FAILED:", ", ".join(FAILURES))
        return 1
    print("Seat-group UI revision browser checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
