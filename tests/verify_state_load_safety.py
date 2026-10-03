#!/usr/bin/env python3
"""Real-dashboard journey: failed state loads are visible and cannot wipe files."""
import json
from pathlib import Path
import subprocess
import socket
import sys
import tempfile
import time

sys.dont_write_bytecode = True

from playwright.sync_api import sync_playwright
from verify_show_targets import free_port, wait_http, ROOT


def run_phase(root, page, invalid_start):
    state_path = root / "installation.json"
    venue = root / "installations" / "broken.json"
    original = state_path.read_bytes()
    venue_original = venue.read_bytes()
    port = free_port(socket.SOCK_STREAM)
    base = f"http://127.0.0.1:{port}"
    log_path = root / ("invalid.log" if invalid_start else "repaired.log")
    with log_path.open("w") as log:
        server = subprocess.Popen([
            sys.executable, str(ROOT / "dashboard/server.py"),
            "--host", "127.0.0.1", "--port", str(port),
            "--listen-port", str(free_port(socket.SOCK_DGRAM)),
            "--send-port", str(free_port(socket.SOCK_DGRAM)),
            "--osc-target", "127.0.0.1", "--state-file", str(state_path),
            "--assets-dir", str(root / "assets"),
            "--patches-dir", str(root / "patches"),
        ], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
        try:
            wait_http(base, server)
            page.goto(base)
            page.wait_for_selector("#ws-status.online", state="attached")
            page.click("#tab-button-show")
            page.wait_for_selector("#show-create-form")
            if invalid_start:
                notice = page.locator("#show-root .show-warning-list")
                notice.wait_for(state="visible")
                assert "saving is blocked" in notice.inner_text().lower()
                assert str(state_path) in notice.inner_text()
                print("[PASS] failed startup is visible even without a loaded Show")
                page.evaluate("""() => {
                    window.masterResult = null;
                    ws.on('master', data => window.masterResult = data.value);
                    ws.send('set_master', {value: 0.35});
                }""")
                page.wait_for_function("window.masterResult === 0.35")
                time.sleep(1.2)  # Past the normal debounced-write deadline.
                assert state_path.read_bytes() == original
                print("[PASS] an ordinary master change preserves original bytes")
            else:
                assert page.locator("#show-root .show-warning-list").count() == 0
                page.evaluate("""() => {
                    window.masterResult = null;
                    ws.on('master', data => window.masterResult = data.value);
                    ws.send('set_master', {value: 0.6});
                }""")
                page.wait_for_function("window.masterResult === 0.6")
                deadline = time.monotonic() + 5
                while json.loads(state_path.read_text()).get("master") != 0.6:
                    assert time.monotonic() < deadline, "repaired state did not save"
                    time.sleep(.1)
                original = state_path.read_bytes()
                print("[PASS] repaired startup permits ordinary saves again")
                page.evaluate("ws.send('load_venue', {name: 'broken'})")
                notice = page.locator("#show-root .show-warning-list")
                notice.wait_for(state="visible")
                assert str(venue) in notice.inner_text()
                assert state_path.read_bytes() == original
                print("[PASS] rejected venue is broadcast as a visible notice without changing current state")

            page.evaluate("""() => {
                window.saveError = '';
                ws.on('error', data => window.saveError = data.message);
                ws.send('save_venue', {name: 'broken'});
            }""")
            page.wait_for_function("window.saveError.includes('could not be saved')")
            assert venue.read_bytes() == venue_original
            assert state_path.read_bytes() == original
            print("[PASS] saving over the invalid venue is refused without changing either file")
            if invalid_start:
                page.reload()
                page.wait_for_selector("#show-root .show-warning-list", state="visible")
                assert "saving is blocked" in page.locator("#show-root .show-warning-list").inner_text()
                print("[PASS] reconnect retains the startup notice")
        except Exception:
            print(log_path.read_text())
            raise
        finally:
            page.goto("about:blank")
            server.terminate()
            try:
                server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait(timeout=5)
    assert state_path.read_bytes() == original
    assert venue.read_bytes() == venue_original
    print("[PASS] shutdown preserves both source files")


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-load-safety-") as temporary:
        root = Path(temporary)
        for name in ("assets", "patches", "installations"):
            (root / name).mkdir()
        invalid = {"schema": 1, "name": "Room", "seats": {
            "2": {"id": 2, "groups": [99], "positions": [[1, 2]]}}}
        (root / "installation.json").write_text(json.dumps(invalid))
        (root / "installations/broken.json").write_text(json.dumps(invalid))
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            run_phase(root, page, invalid_start=True)
            invalid["seats"]["2"]["groups"] = []
            invalid["device_registry"] = {}
            (root / "installation.json").write_text(json.dumps(invalid))
            run_phase(root, page, invalid_start=False)
            assert not errors, errors
            print("[PASS] repairing the file and restarting clears the startup lock and notice")
            browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
