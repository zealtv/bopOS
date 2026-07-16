#!/usr/bin/env python3
"""Real Dashboard browser verification for the bounded Seat roster filter."""

import json
import socket
import subprocess
import sys
import tempfile
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
BASE = ROOT / ".loom" / "tied" / "12-dashboard-live-controls"
sys.path.insert(0, str(BASE))
from verify_live_controls_browser import free_port, make_fixture, stop, wait_http  # noqa: E402

FAILURES = []


def check(label, condition, detail=""):
    print(f"[{'PASS' if condition else 'FAIL'}] {label}"
          + (f" -- {detail}" if detail and not condition else ""))
    if not condition:
        FAILURES.append(label)


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-seat-roster-") as root:
        patches, assets, state_dir, manifest_path, state_path, _uids = make_fixture(root)
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state["seats"] = {
            str(index): {
                "id": index,
                "name": f"Front {index}" if index <= 4 else f"Balcony {index}",
                "positions": [[index, 1]], "groups": [], "bound": None,
                "patch": "alpha", "params": {},
            }
            for index in range(1, 15)
        }
        state_path.write_text(json.dumps(state), encoding="utf-8")
        http_port = free_port(socket.SOCK_STREAM)
        listen_port = free_port(socket.SOCK_DGRAM)
        send_port = free_port(socket.SOCK_DGRAM)
        base_url = f"http://127.0.0.1:{http_port}"
        server = subprocess.Popen([
            sys.executable, str(ROOT / "dashboard" / "server.py"),
            "--host", "127.0.0.1", "--port", str(http_port),
            "--listen-port", str(listen_port), "--send-port", str(send_port),
            "--osc-target", "127.0.0.1", "--state-file", str(state_path),
            "--assets-dir", str(assets), "--patches-dir", str(patches),
            "--public-url", base_url,
        ], cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        fleet = None
        try:
            wait_http(base_url, server)
            fleet = subprocess.Popen([
                sys.executable, str(ROOT / "tools" / "simfleet.py"),
                "--devices", "14", "--target", "127.0.0.1",
                "--report-port", str(listen_port), "--cmd-port", str(send_port),
                "--hb-interval", "0.2", "--boot-secs", "0.2",
                "--state-dir", str(state_dir), "--manifest", str(manifest_path),
                "--patches-dir", str(patches), "--assets-dir", str(assets),
            ], cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                context = browser.new_context(
                    viewport={"width": 768, "height": 1024},
                    has_touch=True, is_mobile=True, device_scale_factor=1,
                )
                page = context.new_page()
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.goto(base_url + "/#seats")
                page.wait_for_selector("#assigned .seat-row")
                metrics = page.locator("#assigned").evaluate(
                    "el => ({client:el.clientHeight,scroll:el.scrollHeight,overflow:getComputedStyle(el).overflowY})")
                check("long Seat roster is contained and internally scrollable",
                      metrics["client"] <= 432 and metrics["scroll"] > metrics["client"]
                      and metrics["overflow"] == "auto", repr(metrics))
                check("roster keeps numeric Seat order",
                      page.locator("#assigned .seat-row").evaluate_all(
                          "rows => rows.map(row => Number(row.dataset.seatId))")
                      == list(range(1, 15)))

                page.fill("#seat-roster-filter", "Front")
                visible = page.locator("#assigned .seat-row:not([hidden])")
                check("prefix filter updates while typing",
                      visible.count() == 4
                      and all(name.startswith("Front") for name in visible.locator("[data-seat-name]").evaluate_all(
                          "inputs => inputs.map(input => input.value)")))
                check("filter mirrors Group inspector wording and has no false empty state",
                      page.locator("#seat-roster-filter").get_attribute("placeholder") == "Names beginning with…"
                      and page.locator("#seat-roster-filter-empty").is_hidden())

                page.fill("#seat-roster-filter", "Missing")
                check("no-match state is explicit",
                      visible.count() == 0 and page.locator("#seat-roster-filter-empty").is_visible())
                page.fill("#seat-roster-filter", "")
                check("clearing filter restores the complete roster",
                      visible.count() == 14 and page.locator("#seat-roster-filter-empty").is_hidden())
                page.click("#tab-button-devices")
                page.wait_for_function("() => document.querySelectorAll('#device-roster .device-row').length === 14")
                device_metrics = page.locator("#device-roster").evaluate(
                    "el => ({client:el.clientHeight,scroll:el.scrollHeight,overflow:getComputedStyle(el).overflowY})")
                check("Physical devices roster uses the same bounded-scroll pattern",
                      device_metrics["client"] <= 432
                      and device_metrics["scroll"] > device_metrics["client"]
                      and device_metrics["overflow"] == "auto", repr(device_metrics))
                check("Physical devices keeps its categorical dropdown without name search",
                      page.locator("#device-filter").count() == 1
                      and page.locator(".device-sidebar input[type=search], .device-sidebar input[type=text]").count() == 0)
                page.click("#tab-button-seats")
                page.screenshot(
                    path=str(Path(__file__).resolve().parent / "seat-roster-filter-ipad.png"),
                    full_page=True)
                check("browser emitted no page errors", not errors, repr(errors))
                browser.close()
        finally:
            stop(fleet)
            stop(server)

    print(f"\n{len(FAILURES)} failure(s)")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(main())
