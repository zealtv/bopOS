#!/usr/bin/env python3
"""Browser regression: an identical synchronized LFO resend stays continuous."""

import importlib.util
import json
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
        if (parent / "tools" / "simfleet.py").is_file():
            return parent
    raise RuntimeError("cannot locate repository")


ROOT = repo_root()
BASE_PATH = ROOT / ".loom" / "tied" / "ap-3-slider-automation-visibility" / "verify_slider_automation.py"
SPEC = importlib.util.spec_from_file_location("slider_automation_verify", BASE_PATH)
base = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(base)


def check(label, condition, detail=""):
    print(f"[{'PASS' if condition else 'FAIL'}] {label}"
          + (f" -- {detail}" if detail and not condition else ""))
    if not condition:
        raise AssertionError(label)


def looping_show(root):
    message = {
        "uid": "aaaa0001", "alias": "triangle", "address": "/p/gain",
        "target": ["0"], "args": [
            {"type": "s", "value": "lfo"},
            {"type": "s", "value": "tri"},
            {"type": "f", "value": 0}, {"type": "f", "value": 1},
            {"type": "s", "value": "1s"},
        ],
    }
    show = {"schema": 1, "name": "vis", "items": [{
        "kind": "step", "uid": "11111111", "alias": "loop",
        "messages": [message], "duration_s": 2.5, "play_count": 1,
        "then_actions": [{"type": "play_again"}],
    }]}
    Path(root, "shows", "vis.json").write_text(
        json.dumps(show, indent=2) + "\n", encoding="utf-8")


def marker_x(page, selector):
    return page.evaluate("""sel => {
      const el = document.querySelector(sel);
      if (!el) return null;
      const transform = getComputedStyle(el).transform;
      return !transform || transform === "none" ? 0 : new DOMMatrixReadOnly(transform).m41;
    }""", selector)


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-lfo-retrigger-") as root:
        (patches, assets, state_dir, manifest_path, state_path,
         devices_path) = base.make_fixture(root)
        looping_show(root)
        http_port = base.free_port(base.socket.SOCK_STREAM)
        listen_port = base.free_port(base.socket.SOCK_DGRAM)
        proxy_port = base.free_port(base.socket.SOCK_DGRAM)
        fleet_port = base.free_port(base.socket.SOCK_DGRAM)
        base_url = f"http://127.0.0.1:{http_port}"
        server_log = Path(root, "server.log").open("w", encoding="utf-8")
        fleet_log = Path(root, "fleet.log").open("w", encoding="utf-8")
        server = fleet = proxy = None
        try:
            proxy = base.DatagramProxy(proxy_port, fleet_port)
            proxy.start()
            server = subprocess.Popen([
                sys.executable, str(ROOT / "dashboard" / "server.py"),
                "--host", "127.0.0.1", "--port", str(http_port),
                "--listen-port", str(listen_port), "--send-port", str(proxy_port),
                "--osc-target", "127.0.0.1", "--state-file", str(state_path),
                "--assets-dir", str(assets), "--patches-dir", str(patches),
                "--public-url", base_url,
            ], cwd=ROOT, stdout=server_log, stderr=subprocess.STDOUT)
            base.wait_http(base_url, server)
            fleet = subprocess.Popen([
                sys.executable, str(ROOT / "tools" / "simfleet.py"),
                "--devices", "1", "--devices-file", str(devices_path),
                "--target", "127.0.0.1", "--report-port", str(listen_port),
                "--cmd-port", str(fleet_port), "--hb-interval", "0.2",
                "--boot-secs", "0.2", "--state-dir", str(state_dir),
                "--manifest", str(manifest_path), "--patches-dir", str(patches),
                "--assets-dir", str(assets),
            ], cwd=ROOT, stdout=fleet_log, stderr=subprocess.STDOUT)

            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                errors = []
                context, page = base.open_facilitator(browser, base_url, errors)
                page.wait_for_function(
                    "() => Object.keys(installation.devices || {}).length >= 1")
                page.evaluate("() => ws.send('step_start', {uid: '11111111'})")
                marker = base.GAIN + " .live-param-marker"
                page.wait_for_selector(marker)
                width = page.locator(marker).evaluate("el => el.getBoundingClientRect().width")
                samples = []
                deadline = time.monotonic() + 3.3
                while time.monotonic() < deadline:
                    value = marker_x(page, marker)
                    if value is not None:
                        samples.append((time.monotonic(), value))
                    time.sleep(.02)
                sends = [(stamp, args) for address, args, stamp in proxy.messages
                         if address == "/0/p/gain"]
                check("looping step resent the identical LFO", len(sends) >= 2,
                      repr(sends))
                retrigger = sends[1][0]
                around = [(stamp, value) for stamp, value in samples
                          if retrigger - .3 <= stamp <= retrigger + .5]
                jumps = [abs(right[1] - left[1])
                         for left, right in zip(around, around[1:])]
                check("visual marker stays continuous across the half-cycle retrigger",
                      jumps and max(jumps) < width * .18,
                      f"max jump={max(jumps) if jumps else None}, width={width}")
                check("browser emitted no console errors", not errors, repr(errors))
                context.close()
                browser.close()
        finally:
            base.stop(fleet)
            base.stop(server)
            if proxy is not None:
                proxy.close()
            server_log.close()
            fleet_log.close()
    print("\n3/3 passed")


if __name__ == "__main__":
    main()
