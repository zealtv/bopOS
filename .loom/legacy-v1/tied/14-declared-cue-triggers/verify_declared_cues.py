#!/usr/bin/env python3
"""Real Dashboard + Playwright verification for declared live cue triggers."""

import json
import socket
import subprocess
import sys
import tempfile
from pathlib import Path

from pyOSC3 import decodeOSC
from playwright.sync_api import sync_playwright

sys.dont_write_bytecode = True


def repo_root():
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "dashboard" / "server.py").is_file():
            return parent
    raise RuntimeError("cannot locate repository")


ROOT = repo_root()
BASE = ROOT / ".loom" / "tied" / "12-dashboard-live-controls"
sys.path.insert(0, str(BASE))
from verify_live_controls_browser import free_port, make_fixture, stop, wait_http  # noqa: E402

FAILURES = []


def check(label, condition, detail=""):
    print(f"[{'PASS' if condition else 'FAIL'}] {label}"
          + (f" -- {detail}" if detail and not condition else ""))
    if not condition:
        FAILURES.append(label)


def cue_datagram(receiver):
    receiver.settimeout(2)
    while True:
        decoded = decodeOSC(receiver.recvfrom(65535)[0])
        if decoded and decoded[0] == "/cue":
            return decoded


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-declared-cues-") as root:
        patches, assets, _state_dir, manifest_path, state_path, _uids = make_fixture(root)
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["cues"] = [
            {"id": "snap", "label": "Snap", "description": "Short noise accent"},
            {"id": "lights-out"},
        ]
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

        http_port = free_port(socket.SOCK_STREAM)
        listen_port = free_port(socket.SOCK_DGRAM)
        send_port = free_port(socket.SOCK_DGRAM)
        receiver = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        receiver.bind(("127.0.0.1", send_port))
        base_url = f"http://127.0.0.1:{http_port}"
        server = subprocess.Popen([
            sys.executable, str(ROOT / "dashboard" / "server.py"),
            "--host", "127.0.0.1", "--port", str(http_port),
            "--listen-port", str(listen_port), "--send-port", str(send_port),
            "--osc-target", "127.0.0.1", "--state-file", str(state_path),
            "--assets-dir", str(assets), "--patches-dir", str(patches),
            "--public-url", base_url,
        ], cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        try:
            wait_http(base_url, server)
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                context = browser.new_context(
                    viewport={"width": 768, "height": 1024},
                    has_touch=True, is_mobile=True, device_scale_factor=1,
                )
                page = context.new_page()
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.goto(base_url + "/facilitator")
                page.wait_for_selector("#cue-panel:not([hidden])")
                buttons = page.locator("[data-live-cue]")
                check("declared cues render in manifest order",
                      buttons.count() == 2
                      and buttons.nth(0).get_attribute("data-live-cue") == "snap"
                      and buttons.nth(1).get_attribute("data-live-cue") == "lights-out")
                check("label, description, and distinct cue ID keep their hierarchy",
                      buttons.nth(0).locator("span").inner_text() == "Snap"
                      and buttons.nth(0).locator(".cue-description").inner_text() == "Short noise accent"
                      and buttons.nth(0).locator(".cue-id").inner_text() == "snap"
                      and buttons.nth(1).locator(".cue-id").count() == 0)
                check("live Dashboard has no free-text cue firing or idle status copy",
                      page.locator("#cue-id, #cue-fire").count() == 0
                      and page.locator("#cue-status").inner_text() == ""
                      and "scheduled against the shared clock" not in page.locator("body").inner_text().lower())
                dimensions = buttons.evaluate_all(
                    "els => els.map(el => ({w:el.getBoundingClientRect().width, h:el.getBoundingClientRect().height}))")
                check("iPad cue grid uses two columns with 44px touch targets",
                      len(dimensions) == 2
                      and all(item["w"] >= 44 and item["h"] >= 44 for item in dimensions)
                      and abs(dimensions[0]["w"] - dimensions[1]["w"]) < 1,
                      repr(dimensions))

                page.fill("#cue-lead", "650")
                buttons.nth(0).tap()
                page.wait_for_function("() => document.querySelector('#cue-status').value.includes('Snap scheduled · 650 ms')")
                packet = cue_datagram(receiver)
                check("one tap sends the exact declared ID through the scheduled cue wire path",
                      packet[0] == "/cue" and packet[2] == "snap"
                      and isinstance(packet[3], str) and packet[3].isdigit(), repr(packet))
                check("fired button exposes a textual transient scheduled state",
                      buttons.nth(0).is_disabled()
                      and buttons.nth(0).locator("span").inner_text() == "Scheduled")
                page.screenshot(path=str(Path(__file__).resolve().parent / "declared-cues-ipad.png"), full_page=True)

                main_page = context.new_page()
                main_page.goto(base_url)
                main_page.wait_for_selector("#dashboard-live-view")
                frame = main_page.frame_locator("#dashboard-live-view")
                frame.locator("#cue-panel:not([hidden])").wait_for()
                check("embedded Dashboard exposes one cue panel without an outer duplicate",
                      main_page.locator("#cue-panel").count() == 0
                      and frame.locator("#cue-panel").count() == 1)

                manifest["cues"] = []
                manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
                empty_page = context.new_page()
                empty_page.goto(base_url + "/facilitator")
                empty_page.wait_for_selector("#live-scope-tabs")
                check("zero declared cues hide the entire panel without empty prose",
                      empty_page.locator("#cue-panel").is_hidden()
                      and "no cues" not in empty_page.locator("body").inner_text().lower())
                check("browser emitted no page errors", not errors, repr(errors))
                browser.close()
        finally:
            stop(server)
            receiver.close()

    print(f"\n{len(FAILURES)} failure(s)")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(main())
