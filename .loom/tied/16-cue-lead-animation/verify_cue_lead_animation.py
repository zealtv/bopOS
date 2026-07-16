#!/usr/bin/env python3
"""Touch-browser timing verification for cue lead and trigger animation."""

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
    with tempfile.TemporaryDirectory(prefix="bopos-cue-lead-") as root:
        patches, assets, _state_dir, manifest_path, state_path, _uids = make_fixture(root)
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["cues"] = [{"id": "snap", "label": "Snap"}]
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
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
                cue = page.locator('[data-live-cue="snap"]')
                cue.wait_for()

                page.fill("#cue-lead", "400")
                cue.tap()
                style = cue.evaluate("el => ({name:getComputedStyle(el).animationName,duration:getComputedStyle(el).animationDuration,custom:el.style.getPropertyValue('--cue-lead-duration')})")
                check("selected Lead controls the scheduling animation duration",
                      style == {"name": "cue-lead", "duration": "0.4s", "custom": "400ms"},
                      repr(style))
                page.wait_for_timeout(220)
                check("button remains in countdown state before scheduled trigger",
                      cue.get_attribute("class") == "scheduling"
                      and cue.inner_text() == "Snap")
                page.wait_for_function("() => document.querySelector('[data-live-cue=snap]').classList.contains('triggered')")
                check("lead completion changes to a bright trigger flash",
                      cue.evaluate("el => getComputedStyle(el).animationName") == "cue-trigger"
                      and cue.inner_text() == "Snap")
                page.screenshot(
                    path=str(Path(__file__).resolve().parent / "cue-trigger-flash-ipad.png"),
                    full_page=True)
                page.wait_for_function("() => !document.querySelector('[data-live-cue=snap]').disabled")

                page.fill("#cue-lead", "900")
                cue.tap()
                page.wait_for_timeout(550)
                classes = (cue.get_attribute("class") or "").split()
                check("a longer Lead extends countdown rather than using a fixed animation",
                      classes.count("scheduling") == 1 and "triggered" not in classes
                      and cue.evaluate("el => getComputedStyle(el).animationDuration") == "0.9s")
                page.wait_for_function("() => document.querySelector('[data-live-cue=snap]').classList.contains('triggered')")

                reduced = browser.new_context(
                    viewport={"width": 768, "height": 1024},
                    reduced_motion="reduce",
                )
                reduced_page = reduced.new_page()
                reduced_page.goto(base_url + "/facilitator")
                reduced_cue = reduced_page.locator('[data-live-cue="snap"]')
                reduced_cue.wait_for()
                reduced_page.fill("#cue-lead", "200")
                reduced_cue.click()
                check("reduced-motion mode uses a static countdown state",
                      reduced_cue.evaluate("el => getComputedStyle(el).animationName") == "none")
                reduced_page.wait_for_function("() => document.querySelector('[data-live-cue=snap]').classList.contains('triggered')")
                check("reduced-motion mode still marks the trigger moment without motion",
                      reduced_cue.evaluate("el => getComputedStyle(el).animationName") == "none"
                      and reduced_cue.inner_text() == "Snap")
                reduced.close()
                check("browser emitted no page errors", not errors, repr(errors))
                browser.close()
        finally:
            stop(server)

    print(f"\n{len(FAILURES)} failure(s)")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(main())
