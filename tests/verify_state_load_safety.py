#!/usr/bin/env python3
from project_fixture import project_path, data_root
"""Real-dashboard journey: failed state loads are visible and cannot wipe files."""
import argparse
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


def check_notice_themes(page, surface, artifact_dir):
    """Check the rendered warning tint and normal-text AA contrast in both themes."""
    original_theme = page.evaluate("document.documentElement.dataset.theme")
    for theme in ("light", "dark"):
        page.evaluate("theme => document.documentElement.dataset.theme = theme", theme)
        colors = page.locator("#installation-notice").evaluate("""notice => {
            const style = getComputedStyle(notice);
            const probe = document.createElement('span');
            probe.style.backgroundColor = 'var(--warning-bg)';
            notice.append(probe);
            const tint = getComputedStyle(probe).backgroundColor;
            probe.remove();
            return {text: style.color, background: style.backgroundColor, tint};
        }""")
        assert colors["background"] == colors["tint"], colors

        def luminance(rgb):
            channels = [float(value) / 255 for value in rgb[rgb.index("(") + 1:-1].split(",")]
            assert len(channels) == 3, rgb  # Opaque theme colors; no hidden blending.
            linear = [value / 12.92 if value <= .04045 else ((value + .055) / 1.055) ** 2.4
                      for value in channels]
            return sum(value * weight for value, weight in zip(linear, (.2126, .7152, .0722)))

        values = sorted((luminance(colors["text"]), luminance(colors["background"])))
        contrast = (values[1] + .05) / (values[0] + .05)
        assert contrast >= 4.5, (surface, theme, colors, contrast)
        if artifact_dir:
            page.screenshot(path=str(artifact_dir / f"notice-{surface}-{theme}.png"))
        print(f"[PASS] {surface} {theme} warning tint has {contrast:.2f}:1 text contrast")
    page.evaluate("theme => document.documentElement.dataset.theme = theme", original_theme)


def run_phase(root, page, invalid_start, artifact_dir=None):
    state_path = project_path(root)
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
            "--osc-target", "127.0.0.1", "--data-dir", data_root(state_path),
            "--assets-dir", str(root / "assets"),
            "--patches-dir", str(root / "patches"),
        ], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
        try:
            wait_http(base, server)
            page.goto(base)
            page.wait_for_selector("#ws-status.online", state="attached")
            page.wait_for_function("document.querySelector('#initial-loading').hidden")
            notice = page.locator("#installation-notice")
            for tab in ("control", "seats", "devices", "patches", "assets", "show"):
                page.click(f"#tab-button-{tab}")
                page.wait_for_selector(f"#tab-{tab}", state="visible")
                assert notice.count() == 1
                assert notice.get_attribute("role") == "status"
                assert notice.locator("button, a").count() == 0
                if invalid_start:
                    notice.wait_for(state="visible")
                    assert "saving is blocked" in notice.inner_text().lower()
                    assert str(state_path) in notice.inner_text()
                    assert page.locator("#show-root .show-warning-list").count() == 0
                    assert page.evaluate("""() => {
                        const notice = document.querySelector('#installation-notice');
                        return notice.previousElementSibling.classList.contains('primary-tabs')
                            && notice.nextElementSibling.classList.contains('tab-stage')
                            && !notice.closest('[role=tabpanel]');
                    }""")
                else:
                    assert notice.is_hidden()
                if invalid_start and tab in ("control", "seats"):
                    check_notice_themes(page, tab, artifact_dir)
                print(f"[PASS] {tab} has one visible load notice" if invalid_start
                      else f"[PASS] {tab} has no load notice after a valid load")

            remote = page.context.new_page()
            try:
                remote.goto(base + "/facilitator")
                remote.wait_for_selector("#ws-status.online", state="attached")
                remote.wait_for_function("document.querySelector('#initial-loading').hidden")
                remote_notice = remote.locator("#installation-notice")
                assert remote_notice.count() == 1
                assert remote_notice.get_attribute("role") == "status"
                assert remote_notice.locator("button, a").count() == 0
                assert remote.evaluate("""() =>
                    document.querySelector('#installation-notice').previousElementSibling.tagName === 'HEADER'
                """)
                if invalid_start:
                    remote_notice.wait_for(state="visible")
                    assert "saving is blocked" in remote_notice.inner_text().lower()
                    assert str(state_path) in remote_notice.inner_text()
                    remote.reload()
                    remote_notice.wait_for(state="visible")
                    assert str(state_path) in remote_notice.inner_text()
                else:
                    assert remote_notice.is_hidden()
                if invalid_start:
                    remote.set_viewport_size({"width": 768, "height": 1024})
                    check_notice_themes(remote, "remote", artifact_dir)
                print("[PASS] Remote follows the same notice rule below its header, including reload")
            finally:
                remote.close()

            page.wait_for_selector(".show-edit-bar", state="attached")
            if invalid_start:
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
                assert page.locator("#installation-notice").is_hidden()
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
                notice = page.locator("#installation-notice")
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
                page.wait_for_selector("#installation-notice", state="visible")
                assert "saving is blocked" in page.locator("#installation-notice").inner_text()
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
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-dir", type=Path)
    args = parser.parse_args()
    if args.artifact_dir:
        args.artifact_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="bopos-load-safety-") as temporary:
        root = Path(temporary)
        for name in ("assets", "patches", "installations"):
            (root / name).mkdir()
        invalid = {"schema": 1, "name": "Room", "seats": {
            "2": {"id": 2, "groups": [99], "positions": [[1, 2]]}}}
        (project_path(root)).write_text(json.dumps(invalid))
        (root / "installations/broken.json").write_text(json.dumps(invalid))
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1280, "height": 900})
            errors = []
            context.on("page", lambda page: page.on("pageerror", lambda error: errors.append(str(error))))
            page = context.new_page()
            run_phase(root, page, invalid_start=True, artifact_dir=args.artifact_dir)
            invalid["seats"]["2"]["groups"] = []
            invalid["device_registry"] = {}
            (project_path(root)).write_text(json.dumps(invalid))
            run_phase(root, page, invalid_start=False)
            assert not errors, errors
            print("[PASS] repairing the file and restarting clears the startup lock and notice")
            browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
