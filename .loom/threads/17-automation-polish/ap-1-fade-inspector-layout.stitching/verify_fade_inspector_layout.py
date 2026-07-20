#!/usr/bin/env python3
"""Fade segment row must not overlap in the narrow (300px) Show inspector."""

import json
import random
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
    patch = patches / "layout"
    patch.mkdir(parents=True)
    assets.mkdir()
    state_dir.mkdir()
    shows.mkdir()
    (patch / "main.bin").write_bytes(b"fade-layout")
    manifest = {
        "engine": "test", "entrypoint": "main.bin", "caps": [], "slots": [],
        "params": [
            {"name": "gain", "type": "f", "min": 0, "max": 1,
             "default": .25, "dashboard": True},
        ],
        "cues": [],
    }
    manifest_path = patch / "bopos.patch.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    uid = "02:53:49:4d:00:01"
    devices_path = root / "devices.csv"
    devices_path.write_text(f"mac,hostname,id\n{uid},sim0,0\n", encoding="utf-8")
    state = {
        "schema": 1, "name": "Fade layout verifier",
        "current_show": "layout", "params_patch": "layout",
        "fleet_patch": {"name": "layout", "fingerprint": "a" * 64,
                        "staged_at": time.time(), "previous": None},
        "seats": {"0": {"id": 0, "name": "Zero", "positions": [[1, 1]],
                        "groups": [], "bound": uid, "patch": "layout",
                        "params": {"gain": .25}}},
        "groups": {}, "next_group_id": 0,
    }
    messages = [
        {"uid": "aaaa0001", "alias": "fade", "address": "/p/gain", "target": ["0"],
         "args": [{"type": "f", "value": 1}, {"type": "s", "value": "5s"}]},
        {"uid": "aaaa0002", "alias": "lfo", "address": "/p/gain", "target": ["0"],
         "args": [{"type": "s", "value": "lfo"}, {"type": "s", "value": "sine"},
                  {"type": "f", "value": 0}, {"type": "f", "value": 1},
                  {"type": "s", "value": "2s"}]},
    ]
    show = {"schema": 1, "name": "layout", "items": [{
        "kind": "step", "uid": "11111111", "alias": "layout",
        "messages": messages, "duration_s": 10, "play_count": 1,
        "then_actions": [{"type": "stop"}],
    }]}
    state_path = root / "installation.json"
    (shows / "layout.json").write_text(json.dumps(show, indent=2) + "\n",
                                       encoding="utf-8")
    state_path.write_text(json.dumps(state), encoding="utf-8")
    return patches, assets, state_dir, manifest_path, state_path, devices_path


def boxes_overlap(a, b):
    return not (a["x"] + a["width"] <= b["x"] + .5
                or b["x"] + b["width"] <= a["x"] + .5
                or a["y"] + a["height"] <= b["y"] + .5
                or b["y"] + b["height"] <= a["y"] + .5)


def box(page, selector):
    page.evaluate(
        "sel => document.querySelector(sel)?.scrollIntoView({block: 'center'})",
        selector)
    result = page.locator(selector).bounding_box()
    if result is None:
        raise RuntimeError(f"no box for {selector}")
    return result


SEGMENT = '[data-param-segment="0"]'
DEST = SEGMENT + " [data-param-segment-value]"
DUR = SEGMENT + " [data-param-segment-duration]"
UNIT = SEGMENT + " [data-param-segment-unit]"
REMOVE = SEGMENT + " [data-remove-param-segment]"
LABELS = SEGMENT + " label"


def open_fade_inspector(page, base_url):
    page.goto(base_url)
    page.wait_for_selector("#ws-status.online", state="attached")
    page.click("#tab-button-show")
    page.wait_for_selector('[data-show-step-row="11111111"]')
    page.locator('[data-show-message-focus="aaaa0001"]').click()
    page.wait_for_selector(SEGMENT)


def audit_row(page, tag):
    # One evaluate, one scroll state: per-element scrollIntoView would make
    # the viewport-relative rects incomparable.
    raw = page.evaluate(
        """sels => Object.fromEntries(Object.entries(sels).map(([name, sel]) =>
             [name, document.querySelector(sel).getBoundingClientRect().toJSON()]))""",
        {"destination": DEST, "duration": DUR, "unit": UNIT, "remove": REMOVE})
    pieces = {name: {"x": rect["x"], "y": rect["y"], "width": rect["width"],
                     "height": rect["height"]} for name, rect in raw.items()}
    names = list(pieces)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            check(f"{tag}: {a} and {b} do not overlap",
                  not boxes_overlap(pieces[a], pieces[b]),
                  f"{a}={pieces[a]} {b}={pieces[b]}")
    for name in ("destination", "duration"):
        check(f"{tag}: {name} input has usable width",
              pieces[name]["width"] >= 40, repr(pieces[name]))
    label_boxes = page.locator(LABELS).evaluate_all(
        "els => els.map(el => el.getBoundingClientRect().toJSON())")
    for i, a in enumerate(label_boxes):
        for b in label_boxes[i + 1:]:
            check(f"{tag}: field labels do not overlap",
                  not boxes_overlap(a, b), f"{a} vs {b}")
    return pieces


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-fade-layout-") as root:
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
                errors = []

                # Desktop: workspace is `1fr 300px`, so the inspector is a
                # narrow fixed column — the shipped overlap case.
                desktop = browser.new_context(viewport={"width": 1280, "height": 1000})
                page = desktop.new_page()
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.on("console", lambda message: errors.append(message.text)
                        if message.type == "error" else None)
                open_fade_inspector(page, base_url)
                shell_width = page.locator(".show-inspector-shell").evaluate(
                    "el => el.getBoundingClientRect().width")
                check("desktop inspector is the narrow fixed column",
                      280 <= shell_width <= 320, repr(shell_width))
                pieces = audit_row(page, "narrow")
                check("narrow: rows are stacked (duration below destination)",
                      pieces["duration"]["y"] > pieces["destination"]["y"] + 10,
                      repr(pieces))
                page.locator(".show-inspector-shell").screenshot(
                    path=str(STITCH / "inspector-narrow.png"))

                # LFO fields share the container fix; sanity-check no overlap.
                # (Focus the dedicated LFO message — switching the generator
                # select would rewrite the fade message's persisted args.)
                page.locator('[data-show-message-focus="aaaa0002"]').click()
                page.wait_for_selector('[data-param-lfo="period"]')
                lfo_period = box(page, '[data-param-lfo="period"]')
                check("narrow: lfo period input has usable width",
                      lfo_period["width"] >= 40, repr(lfo_period))

                # Under 1020px the workspace stacks and the inspector is
                # full width — the three-column row must come back.
                wide = browser.new_context(viewport={"width": 960, "height": 1100})
                wpage = wide.new_page()
                wpage.on("pageerror", lambda error: errors.append(str(error)))
                wpage.on("console", lambda message: errors.append(message.text)
                         if message.type == "error" else None)
                open_fade_inspector(wpage, base_url)
                wide_pieces = audit_row(wpage, "wide")
                check("wide: destination and duration share a row",
                      abs(wide_pieces["duration"]["y"]
                          - wide_pieces["destination"]["y"]) < 8,
                      repr(wide_pieces))
                wpage.locator(".show-inspector-shell").screenshot(
                    path=str(STITCH / "inspector-wide.png"))

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
    print("\nAll fade inspector layout checks passed.")


if __name__ == "__main__":
    main()
