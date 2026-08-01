#!/usr/bin/env python3
"""A one-segment fade preview must be a straight ramp with no false tail."""

import json
import random
import re
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
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
STITCH = Path(__file__).resolve().parent
FAILURES = []
RESERVED = set()


def check(label, condition, detail=""):
    print(f"[{'PASS' if condition else 'FAIL'}] {label}"
          + (f" -- {detail}" if detail and not condition else ""))
    if not condition:
        FAILURES.append(label)


def free_port(kind):
    for _attempt in range(256):
        port = random.SystemRandom().randrange(20000, 60000)
        if (kind, port) in RESERVED:
            continue
        probe = socket.socket(socket.AF_INET, kind)
        try:
            probe.bind(("127.0.0.1", port))
        except OSError:
            probe.close()
            continue
        probe.close()
        RESERVED.add((kind, port))
        return port
    raise RuntimeError("cannot reserve loopback port")


def wait_http(url, process):
    deadline = time.monotonic() + 12
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("dashboard exited before serving HTTP")
        try:
            urllib.request.urlopen(url, timeout=.5).close()
            return
        except OSError:
            time.sleep(.1)
    raise RuntimeError("dashboard did not serve HTTP")


def stop(process):
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def make_fixture(root):
    root = Path(root)
    patches, assets = root / "patches", root / "assets"
    state_dir, shows = root / "fleet-state", root / "shows"
    patch = patches / "tail"
    patch.mkdir(parents=True)
    assets.mkdir()
    state_dir.mkdir()
    shows.mkdir()
    (patch / "main.bin").write_bytes(b"fade-tail")
    manifest = {
        "engine": "test", "entrypoint": "main.bin", "caps": [], "slots": [],
        "params": [
            {"name": "gain", "type": "f", "min": 0, "max": 1,
             "default": 0, "dashboard": True},
            {"name": "level", "type": "f", "min": 0, "max": 1,
             "default": 0, "dashboard": True},
        ],
        "cues": [],
    }
    manifest_path = patch / "bopos.patch.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    uid = "02:53:49:4d:00:01"
    devices_path = root / "devices.csv"
    devices_path.write_text(f"mac,hostname,id\n{uid},sim0,0\n", encoding="utf-8")
    state = {
        "schema": 1, "name": "Fade tail verifier",
        "current_show": "tail", "params_patch": "tail",
        "fleet_patch": {"name": "tail", "fingerprint": "a" * 64,
                        "staged_at": time.time(), "previous": None},
        "seats": {"0": {"id": 0, "name": "Zero", "positions": [[1, 1]],
                        "groups": [], "bound": uid, "patch": "tail",
                        "params": {"gain": 0, "level": .25}}},
        "groups": {}, "next_group_id": 0,
    }
    messages = [
        {"uid": "aaaa0001", "alias": "one", "address": "/p/gain", "target": ["0"],
         "args": [{"type": "f", "value": 1}, {"type": "s", "value": "5s"}]},
        {"uid": "aaaa0002", "alias": "two", "address": "/p/gain", "target": ["0"],
         "args": [{"type": "f", "value": 1}, {"type": "s", "value": "5s"},
                  {"type": "f", "value": .5}, {"type": "s", "value": "5s"}]},
        {"uid": "aaaa0003", "alias": "loop", "address": "/p/level", "target": ["0"],
         "args": [{"type": "s", "value": "loop"},
                  {"type": "f", "value": .8}, {"type": "s", "value": "2s"},
                  {"type": "f", "value": .2}, {"type": "s", "value": "2s"}]},
    ]
    show = {"schema": 1, "name": "tail", "items": [{
        "kind": "step", "uid": "11111111", "alias": "tail",
        "messages": messages, "duration_s": 30, "play_count": 1,
        "then_actions": [{"type": "stop"}],
    }]}
    state_path = root / "installation.json"
    (shows / "tail.json").write_text(json.dumps(show, indent=2) + "\n",
                                     encoding="utf-8")
    state_path.write_text(json.dumps(state), encoding="utf-8")
    return patches, assets, state_dir, manifest_path, state_path, devices_path


def preview_points(page):
    d = page.locator("[data-param-preview] .show-param-preview-line") \
        .get_attribute("d")
    points = [tuple(float(part) for part in pair)
              for pair in re.findall(r"[ML]([\d.]+) ([\d.]+)", d)]
    if len(points) < 2:
        raise RuntimeError(f"degenerate preview path: {d!r}")
    return points


def preview_value(y):
    # renderParamPreview maps value v in [low, high] to y = 64 - v_norm * 56.
    return (64 - y) / 56


def focus_message(page, uid):
    page.locator(f'[data-show-message-focus="{uid}"]').click()
    page.wait_for_selector("[data-param-preview] svg")


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-fade-tail-") as root:
        (patches, assets, state_dir, manifest_path, state_path,
         devices_path) = make_fixture(root)
        http_port = free_port(socket.SOCK_STREAM)
        listen_port = free_port(socket.SOCK_DGRAM)
        fleet_port = free_port(socket.SOCK_DGRAM)
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
                "--listen-port", str(listen_port), "--send-port", str(fleet_port),
                "--osc-target", "127.0.0.1", "--state-file", str(state_path),
                "--assets-dir", str(assets), "--patches-dir", str(patches),
                "--public-url", base_url,
            ], cwd=ROOT, stdout=server_log, stderr=subprocess.STDOUT)
            wait_http(base_url, server)
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
                context = browser.new_context(viewport={"width": 1280, "height": 1000})
                page = context.new_page()
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.on("console", lambda message: errors.append(message.text)
                        if message.type == "error" else None)
                page.goto(base_url)
                page.wait_for_selector("#ws-status.online", state="attached")
                page.click("#tab-button-show")
                page.wait_for_selector('[data-show-step-row="11111111"]')

                # One segment 0 -> 1 over 5s: straight monotonic ramp,
                # ending at the destination — no tail back to start.
                focus_message(page, "aaaa0001")
                points = preview_points(page)
                xs = [point[0] for point in points]
                values = [preview_value(point[1]) for point in points]
                check("one segment: time axis is strictly non-decreasing",
                      all(b >= a - .01 for a, b in zip(xs, xs[1:])), repr(xs))
                check("one segment: value never decreases (no tail)",
                      all(b >= a - .02 for a, b in zip(values, values[1:])),
                      repr(values))
                check("one segment: preview ends at the destination value",
                      abs(values[-1] - 1) < .03, repr(values[-1]))
                check("one segment: preview spans the full time axis",
                      abs(xs[-1] - 232) < 1 and abs(xs[0] - 8) < 1, repr(xs))
                page.locator("[data-param-preview]").screenshot(
                    path=str(STITCH / "preview-one-segment.png"))

                # Two segments 0 ->1 (5s) -> .5 (5s): the midpoint boundary
                # must reach 1 exactly, the end must sit at .5.
                focus_message(page, "aaaa0002")
                points = preview_points(page)
                values = [preview_value(point[1]) for point in points]
                mid = [preview_value(y) for x, y in points
                       if abs(x - (8 + 112)) < 4]
                check("two segments: boundary sample reaches segment one's destination",
                      mid and max(mid) > .97, repr(mid))
                check("two segments: preview ends at segment two's destination",
                      abs(values[-1] - .5) < .03, repr(values[-1]))
                check("two segments: no sample dips below the travel range",
                      min(values) > -.02, repr(min(values)))
                page.locator("[data-param-preview]").screenshot(
                    path=str(STITCH / "preview-two-segments.png"))

                # Facilitator loop marker easing had the same saw(1)=0 wrap:
                # each segment's boundary sample must equal its destination.
                page.evaluate("() => ws.send('step_start', {uid: '11111111'})")
                fpage = context.new_page()
                fpage.on("pageerror", lambda error: errors.append(str(error)))
                fpage.on("console", lambda message: errors.append(message.text)
                         if message.type == "error" else None)
                fpage.goto(base_url + "/facilitator.html")
                fpage.wait_for_selector("#ws-status.online", state="attached")
                fpage.click("#live-scope-seats")
                marker = ('.seat-card[data-live-id="0"] '
                          'label[data-param-path="level"] .live-param-marker')
                fpage.wait_for_selector(marker)
                easing = fpage.locator(marker).evaluate(
                    "el => getComputedStyle(el).animationTimingFunction")
                samples = [tuple(float(v) for v in match)
                           for match in re.findall(
                               r"([\d.]+)(?:\s+([\d.]+)%)?", easing) if match[0]]
                stops = [(float(pct), float(val))
                         for val, pct in re.findall(r"([\d.eE+-]+) ([\d.]+)%",
                                                    easing)]
                near_half = [val for pct, val in stops if abs(pct - 50) < 3]
                check("loop easing: 50% boundary holds segment one's destination (.8)",
                      near_half and max(near_half) > .77, f"{easing[:160]}...")
                check("loop easing is a linear() sample list",
                      easing.startswith("linear("), easing[:60])

                check("browser emitted no console errors", not errors,
                      repr(errors))
                browser.close()
        finally:
            stop(fleet)
            stop(server)
            server_log.close()
            fleet_log.close()

        if FAILURES:
            print("\nserver log tail:\n",
                  server_log_path.read_text(encoding="utf-8")[-4000:])
            print("\nfleet log tail:\n",
                  fleet_log_path.read_text(encoding="utf-8")[-4000:])

    if FAILURES:
        print(f"\n{len(FAILURES)} failure(s): {', '.join(FAILURES)}")
        raise SystemExit(1)
    print("\nAll fade preview tail checks passed.")


if __name__ == "__main__":
    main()
