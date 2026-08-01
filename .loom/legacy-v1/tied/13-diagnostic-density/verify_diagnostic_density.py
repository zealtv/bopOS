#!/usr/bin/env python3
"""Real Dashboard + simfleet browser verification for diagnostic density."""

import importlib.util
import json
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.dont_write_bytecode = True


def repo_root():
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "dashboard" / "server.py").is_file():
            return parent
    raise RuntimeError("cannot locate repository")


ROOT = repo_root()
HERE = Path(__file__).resolve().parent
BASE_VERIFY = ROOT / ".loom" / "tied" / "12-dashboard-live-controls" / "verify_live_controls_browser.py"
spec = importlib.util.spec_from_file_location("live_verify_helpers", BASE_VERIFY)
helpers = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helpers)

FAILURES = []


def check(label, condition, detail=""):
    print(f"[{'PASS' if condition else 'FAIL'}] {label}"
          + (f" -- {detail}" if detail and not condition else ""))
    if not condition:
        FAILURES.append(label)


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-density-") as root:
        patches, assets, state_dir, manifest_path, state_path, uids = helpers.make_fixture(root)
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state["seats"]["1"]["positions"] = [[1, 1], [2, 1]]
        state["seats"]["2"]["positions"] = [[3, 1], [4, 1], [5, 1]]
        state_path.write_text(json.dumps(state), encoding="utf-8")

        http_port = helpers.free_port(socket.SOCK_STREAM)
        listen_port = helpers.free_port(socket.SOCK_DGRAM)
        send_port = helpers.free_port(socket.SOCK_DGRAM)
        base_url = f"http://127.0.0.1:{http_port}"
        server_log_path = Path(root, "server.log")
        fleet_log_path = Path(root, "fleet.log")
        server_log = server_log_path.open("w", encoding="utf-8")
        fleet_log = fleet_log_path.open("w", encoding="utf-8")
        server = fleet = None
        try:
            server = subprocess.Popen([
                sys.executable, str(ROOT / "dashboard" / "server.py"),
                "--host", "127.0.0.1", "--port", str(http_port),
                "--listen-port", str(listen_port), "--send-port", str(send_port),
                "--osc-target", "127.0.0.1", "--state-file", str(state_path),
                "--assets-dir", str(assets), "--patches-dir", str(patches),
                "--public-url", base_url,
            ], cwd=ROOT, stdout=server_log, stderr=subprocess.STDOUT)
            helpers.wait_http(base_url, server)
            fleet = subprocess.Popen([
                sys.executable, str(ROOT / "tools" / "simfleet.py"),
                "--devices", "2", "--target", "127.0.0.1",
                "--report-port", str(listen_port), "--cmd-port", str(send_port),
                "--hb-interval", "0.2", "--boot-secs", "0.2",
                "--state-dir", str(state_dir), "--manifest", str(manifest_path),
                "--patches-dir", str(patches), "--assets-dir", str(assets),
            ], cwd=ROOT, stdout=fleet_log, stderr=subprocess.STDOUT)

            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                context = browser.new_context(
                    viewport={"width": 768, "height": 1024}, has_touch=True,
                    is_mobile=True, device_scale_factor=1,
                    permissions=["clipboard-read", "clipboard-write"],
                )
                page = context.new_page()
                page_errors = []
                page.on("pageerror", lambda error: page_errors.append(str(error)))
                page.goto(base_url)
                page.wait_for_selector("#ws-status.online")
                page.wait_for_function("() => Object.keys(installation.devices||{}).length === 2")

                version = page.locator("#host-version").inner_text().strip()
                check("host checkout shorthand sits beside the bopOS wordmark",
                      7 <= len(version) <= 12
                      and page.locator("header h1 #host-version").count() == 1,
                      version)

                frame = page.locator("#dashboard-live-view").content_frame
                frame.locator("#live-scope-tabs").wait_for()
                check("embedded live surface removes the stray Seat presets footer",
                      frame.locator("#preset-section").is_hidden()
                      and "seat presets" not in frame.locator("body").inner_text().lower())
                check("aggregate mode is the default and excludes individual Seats",
                      frame.locator('.live-card[data-live-scope="all"]').count() == 1
                      and frame.locator('.live-card[data-live-scope="group"]').count() == 2
                      and frame.locator('.live-card[data-live-scope="seat"]').count() == 0)
                tab_boxes = frame.locator("#live-scope-tabs [role=tab]").evaluate_all(
                    "tabs => tabs.map(tab => tab.getBoundingClientRect())")
                check("subordinate live tabs provide two equal 44px touch targets",
                      len(tab_boxes) == 2 and all(box["height"] >= 44 for box in tab_boxes)
                      and abs(tab_boxes[0]["width"] - tab_boxes[1]["width"]) < 2,
                      repr(tab_boxes))
                page.screenshot(path=str(HERE / "live-aggregate-ipad.png"), full_page=True)
                frame.locator("#live-scope-seats").tap()
                check("Seats mode excludes aggregate cards and keeps numeric Seat order",
                      frame.locator('.live-card[data-live-scope="all"],.live-card[data-live-scope="group"]').count() == 0
                      and frame.locator('.live-card[data-live-scope="seat"]').count() == 2
                      and frame.locator('.live-card[data-live-scope="seat"]').evaluate_all(
                          "cards => cards.map(card => Number(card.dataset.liveId))") == [1, 2])
                page.locator("#dashboard-live-view").screenshot(
                    path=str(HERE / "live-seats-ipad.png"))
                page.wait_for_timeout(450)
                check("live tab selection survives state and device rerenders",
                      frame.locator("#live-scope-seats").get_attribute("aria-selected") == "true"
                      and frame.locator('.live-card[data-live-scope="seat"]').count() == 2)
                frame.locator("#live-scope-seats").press("ArrowLeft")
                check("live tabs support keyboard arrow navigation",
                      frame.locator("#live-scope-aggregate").get_attribute("aria-selected") == "true"
                      and frame.locator('.live-card[data-live-scope="all"]').count() == 1)

                page.click("#tab-button-seats")
                page.locator('.seat-row[data-seat-id="1"] small').click()
                page.wait_for_selector("#seat-detail .seat-inspector-section")
                headings = [value.lower() for value in page.locator(
                    "#seat-detail .seat-inspector-section h3").all_inner_texts()]
                check("Seat inspector has divided workspace, Elements, Groups, and Physical device sections",
                      headings == ["seat workspace", "elements", "groups", "physical device"],
                      repr(headings))
                check("Venue is a separate divided inspector section",
                      page.locator("#venue-bar.seat-inspector-section").count() == 1)
                check("two-element Seat disables further UI authoring",
                      page.locator("#seat-element-add").is_disabled()
                      and page.locator("[data-seat-element]").count() == 2)
                page.locator('.seat-row[data-seat-id="2"] small').click()
                check("legacy Seat above the UI cap is preserved without truncation",
                      page.locator("#seat-element-add").is_disabled()
                      and page.locator("[data-seat-element]").count() == 3)
                page.locator('.seat-row[data-seat-id="1"] small').click()
                page.wait_for_function("() => document.querySelector('.seat-binding-note')?.innerText.includes('127.0.0.1')")
                binding_text = page.locator(".seat-binding-note").inner_text()
                check("Seat Physical device detail exposes IP but not hostname or UID",
                      "127.0.0.1" in binding_text and "sim1" not in binding_text
                      and uids[0] not in binding_text, binding_text)

                page.click("#tab-button-devices")
                page.locator(f'#device-roster .device-row[data-uid="{uids[0]}"]').click()
                page.wait_for_selector("#patch-diagnostics")
                terms = page.locator("#patch-diagnostics dt").all_inner_texts()
                desired_index = terms.index("Desired fingerprint")
                check("desired and reported patch identities are vertically adjacent",
                      terms[desired_index + 1] == "Reported content identity", repr(terms))
                identity_buttons = page.locator("#patch-diagnostics [data-copy-identity]")
                first_identity = identity_buttons.first
                shown = first_identity.locator("code").inner_text()
                full = first_identity.get_attribute("data-copy-identity")
                check("diagnostic identities show only a 10-character tail",
                      shown == f"…{full[-10:]}" and first_identity.get_attribute("title") == full,
                      repr((shown, full)))
                first_identity.click()
                page.wait_for_function(
                    "() => document.querySelector('#patch-diagnostics .copy-feedback')?.textContent === 'Copied'")
                check("identity click provides copy feedback",
                      first_identity.locator(".copy-feedback").inner_text() == "Copied")

                body = page.locator("body").inner_text()
                removed = (
                    "Two short words using letters A–Z",
                    "Seat naming, IDs, positions and assignment live",
                    "Drag the listener puck",
                    "Choose the one desired production patch",
                    "Launch a valid host patch through the managed audition runtime",
                    "Edit the dashboard-facing declarations",
                    "Actions always address exactly one online",
                    "Compare the host catalog with one assigned physical device",
                )
                check("ratified extraneous copy is absent without replacement prose",
                      all(phrase not in body for phrase in removed), body)
                check("browser emitted no page errors", not page_errors, repr(page_errors))
                page.screenshot(path=str(HERE / "diagnostic-density-ipad.png"), full_page=True)
                browser.close()
        finally:
            helpers.stop(fleet)
            helpers.stop(server)
            server_log.close()
            fleet_log.close()

        if FAILURES:
            print("\nserver log tail:\n", server_log_path.read_text(encoding="utf-8")[-4000:])
            print("\nfleet log tail:\n", fleet_log_path.read_text(encoding="utf-8")[-4000:])

    print(f"\n{len(FAILURES)} failure(s)")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(main())
