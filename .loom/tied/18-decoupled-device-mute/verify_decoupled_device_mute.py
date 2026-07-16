#!/usr/bin/env python3
"""Real Dashboard + simfleet verification for independent mute layers."""

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
    with tempfile.TemporaryDirectory(prefix="bopos-decoupled-mute-") as root:
        patches, assets, state_dir, manifest_path, state_path, uids = make_fixture(root)
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
                "--devices", "2", "--target", "127.0.0.1",
                "--report-port", str(listen_port), "--cmd-port", str(send_port),
                "--hb-interval", "0.2", "--boot-secs", "0.2",
                "--state-dir", str(state_dir), "--manifest", str(manifest_path),
                "--patches-dir", str(patches), "--assets-dir", str(assets),
            ], cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                context = browser.new_context(viewport={"width": 1024, "height": 768})
                page = context.new_page()
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.goto(base_url)
                page.wait_for_function("() => Object.keys(installation.devices||{}).length === 2")
                page.click("#tab-button-devices")
                row = page.locator(f'#device-roster .device-row[data-uid="{uids[0]}"]')
                row.click()
                page.wait_for_selector("#device-mute-toggle")
                page.wait_for_function(
                    "uid => installation.devices[uid]?.mute_status === 'current'", arg=uids[0])

                page.click("#mute-all")
                page.wait_for_function("() => installation.muted === true")
                check("fleet safety no longer disables exact-device mute",
                      not page.locator("#device-mute-toggle").is_disabled())
                indicator = row.locator("[data-device-mute-indicator]")
                check("fleet overlay does not alter the device-specific roster indicator",
                      indicator.get_attribute("aria-label").startswith("Device unmuted")
                      and "fleet" not in indicator.get_attribute("class")
                      and indicator.locator("svg path").count() == 2)

                page.click("#device-mute-toggle")
                page.wait_for_function(
                    "uid => installation.devices[uid]?.device_muted === true && "
                    "installation.devices[uid]?.mute_status === 'current' && "
                    "installation.devices[uid]?.effective_muted === true", arg=uids[0])
                check("device mute can be established while fleet safety is active",
                      page.locator("#device-mute-toggle").inner_text() == "Unmute"
                      and indicator.get_attribute("aria-label").startswith("Device muted")
                      and indicator.locator("svg path").count() == 3)

                page.click("#mute-all")
                page.wait_for_function(
                    "uid => installation.muted === false && "
                    "installation.devices[uid]?.device_muted === true && "
                    "installation.devices[uid]?.effective_muted === true", arg=uids[0])
                check("releasing fleet safety leaves persistent device mute on",
                      indicator.get_attribute("aria-label").startswith("Device muted"))

                page.click("#mute-all")
                page.wait_for_function("() => installation.muted === true")
                page.click("#device-mute-toggle")
                page.wait_for_function(
                    "uid => installation.devices[uid]?.device_muted === false && "
                    "installation.devices[uid]?.mute_status === 'current' && "
                    "installation.devices[uid]?.effective_muted === true", arg=uids[0])
                check("device unmute changes persistent intent while fleet keeps output safe",
                      indicator.get_attribute("aria-label").startswith("Device unmuted")
                      and indicator.locator("svg path").count() == 2)
                page.click("#mute-all")
                page.wait_for_function(
                    "uid => installation.muted === false && "
                    "installation.devices[uid]?.device_muted === false && "
                    "installation.devices[uid]?.effective_muted === false", arg=uids[0])
                check("fleet release exposes the independently prepared unmuted state",
                      page.locator("#device-mute-toggle").inner_text() == "Mute")
                page.screenshot(
                    path=str(Path(__file__).resolve().parent / "decoupled-device-mute.png"),
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
