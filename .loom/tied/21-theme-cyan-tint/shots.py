#!/usr/bin/env python3
"""Light-theme screenshot harness for stitch 21-theme-cyan-tint.

Boots the real dashboard/server.py + tools/simfleet.py on free loopback ports
with a Show/seat/group fixture, stamps data-theme=light, and captures every tab
plus the facilitator page. Run once before the token retune and once after:

    ~/.venvs/bopos/bin/python shots.py before
    ~/.venvs/bopos/bin/python shots.py after

Writes <label>-<tab>.png inside the stitch directory.
"""

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
    for parent in Path(__file__).resolve().parents:
        if (parent / "tools" / "simfleet.py").is_file():
            return parent
    raise RuntimeError("cannot locate repository")


ROOT = repo_root()
HERE = Path(__file__).resolve().parent
RESERVED = set()


def free_port(kind):
    for _ in range(256):
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
    deadline = time.monotonic() + 15
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
    patches = Path(root, "patches")
    assets = Path(root, "assets")
    state_dir = Path(root, "sim-state")
    shows_dir = Path(root, "shows")
    patch = patches / "alpha"
    patch.mkdir(parents=True)
    assets.mkdir()
    state_dir.mkdir()
    shows_dir.mkdir()
    (patch / "main.bin").write_bytes(b"cyan-tint-shots")
    manifest = {
        "engine": "test", "entrypoint": "main.bin",
        "params": [
            {"name": "gain", "type": "f", "min": 0, "max": 1,
             "default": .4, "facilitator": True, "dashboard": True},
            {"name": "tone", "type": "f", "min": 0, "max": 1,
             "default": .7, "facilitator": True, "dashboard": True},
        ],
        "cues": [{"id": "snap", "label": "Snap"}], "caps": [], "slots": [],
    }
    manifest_path = patch / "bopos.patch.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    state = {
        "schema": 1, "name": "Cyan tint review",
        "current_show": "opening-set",
        "fleet_patch": {"name": "alpha", "fingerprint": "a" * 64,
                        "staged_at": time.time(), "previous": None},
        "params_patch": "alpha",
        "seats": {
            "0": {"id": 0, "name": "Front left", "positions": [[1, 1]],
                  "groups": [0], "bound": None, "patch": "alpha", "params": {}},
            "1": {"id": 1, "name": "Front right", "positions": [[4, 1]],
                  "groups": [0], "bound": None, "patch": "alpha", "params": {}},
            "2": {"id": 2, "name": "Rear", "positions": [[2.5, 4]],
                  "groups": [1], "bound": None, "patch": "alpha", "params": {}},
        },
        "groups": {"0": {"id": 0, "name": "Front pair", "seats": [0, 1]},
                   "1": {"id": 1, "name": "Rear", "seats": [2]}},
        "next_group_id": 2,
    }

    def step(uid, alias, dur=5, muid="aaaa0000"):
        return {"kind": "step", "uid": uid, "alias": alias,
                "messages": [
                    {"uid": muid, "alias": "house-fade",
                     "address": "/p/gain",
                     "args": [{"type": "f", "value": 0.61}], "target": ["all"]},
                ],
                "duration_s": dur, "play_count": 1, "then_actions": []}

    show = {
        "schema": 1, "name": "opening-set",
        "items": [
            {"kind": "divider", "uid": "d0000001", "alias": "MOVEMENT ONE"},
            step("00000000", "opening", 5, "aaaa0001"),
            step("00000001", "swell", 8, "aaaa0002"),
            {"kind": "divider", "uid": "d0000002"},
            step("00000002", "third", 5, "aaaa0003"),
            step("00000003", "coda", 12, "aaaa0004"),
        ],
    }
    state_path = Path(root, "installation.json")
    state_path.write_text(json.dumps(state), encoding="utf-8")
    (shows_dir / "opening-set.json").write_text(
        json.dumps(show, indent=2) + "\n", encoding="utf-8")
    return patches, assets, state_dir, manifest_path, state_path


TABS = ["dashboard", "devices", "seats", "patches", "assets", "show"]


def main():
    label = sys.argv[1] if len(sys.argv) > 1 else "before"
    outdir = HERE
    with tempfile.TemporaryDirectory(prefix="bopos-cyan-shots-") as root:
        patches, assets, state_dir, manifest_path, state_path = make_fixture(root)
        http_port = free_port(socket.SOCK_STREAM)
        listen_port = free_port(socket.SOCK_DGRAM)
        send_port = free_port(socket.SOCK_DGRAM)
        base_url = f"http://127.0.0.1:{http_port}"
        server_log = Path(root, "server.log").open("w", encoding="utf-8")
        fleet_log = Path(root, "fleet.log").open("w", encoding="utf-8")
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
            wait_http(base_url, server)
            fleet = subprocess.Popen([
                sys.executable, str(ROOT / "tools" / "simfleet.py"),
                "--devices", "3", "--target", "127.0.0.1",
                "--report-port", str(listen_port), "--cmd-port", str(send_port),
                "--hb-interval", "0.12", "--boot-secs", "0.1",
                "--state-dir", str(state_dir), "--manifest", str(manifest_path),
                "--patches-dir", str(patches), "--assets-dir", str(assets),
            ], cwd=ROOT, stdout=fleet_log, stderr=subprocess.STDOUT)

            with sync_playwright() as pw:
                browser = pw.chromium.launch(headless=True)
                context = browser.new_context(viewport={"width": 1440, "height": 1000})
                page = context.new_page()
                page.on("dialog", lambda d: (d.accept("shots")
                                             if d.type == "prompt" else d.accept()))
                page.goto(base_url)
                page.wait_for_selector("#ws-status.online", state="attached")
                page.select_option("#theme-select", "light")
                page.wait_for_function(
                    "() => document.documentElement.getAttribute('data-theme') === 'light'")
                page.wait_for_timeout(1200)
                for tab in TABS:
                    page.click(f"#tab-button-{tab}")
                    page.wait_for_timeout(700)
                    page.evaluate("() => window.scrollTo(0, 0)")
                    page.screenshot(path=str(outdir / f"{label}-{tab}.png"), full_page=True)
                    print("wrote", outdir / f"{label}-{tab}.png")

                fac = context.new_page()
                fac.goto(base_url + "/facilitator")
                fac.wait_for_selector("#ws-status", state="attached")
                fac.wait_for_timeout(1500)
                fac.evaluate(
                    "() => document.documentElement.setAttribute('data-theme','light')")
                fac.wait_for_timeout(600)
                fac.screenshot(path=str(outdir / f"{label}-facilitator.png"), full_page=True)
                print("wrote", outdir / f"{label}-facilitator.png")
                browser.close()
        finally:
            stop(fleet)
            stop(server)
            server_log.close()
            fleet_log.close()


if __name__ == "__main__":
    main()
