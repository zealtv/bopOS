#!/usr/bin/env python3
"""Probe: sample the LFO marker's animated transform over time."""

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

ROOT = Path("/Users/bob/repos/bopOS")
RESERVED = set()


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
    raise RuntimeError("no port")


def wait_http(url, process):
    deadline = time.monotonic() + 12
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("server exited")
        try:
            urllib.request.urlopen(url, timeout=.5).close()
            return
        except OSError:
            time.sleep(.1)
    raise RuntimeError("no http")


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-marker-probe-") as root:
        root = Path(root)
        patches, assets = root / "patches", root / "assets"
        state_dir, shows = root / "fleet-state", root / "shows"
        patch = patches / "probe"
        patch.mkdir(parents=True)
        assets.mkdir(); state_dir.mkdir(); shows.mkdir()
        (patch / "main.bin").write_bytes(b"probe")
        manifest = {"engine": "test", "entrypoint": "main.bin", "caps": [],
                    "slots": [], "params": [
                        {"name": "gain", "type": "f", "min": 0, "max": 1,
                         "default": 0, "dashboard": True}], "cues": []}
        manifest_path = patch / "bopos.patch.json"
        manifest_path.write_text(json.dumps(manifest))
        uid = "02:53:49:4d:00:01"
        devices_path = root / "devices.csv"
        devices_path.write_text(f"mac,hostname,id\n{uid},sim0,0\n")
        state = {"schema": 1, "name": "probe", "current_show": "probe",
                 "params_patch": "probe",
                 "fleet_patch": {"name": "probe", "fingerprint": "a" * 64,
                                 "staged_at": time.time(), "previous": None},
                 "seats": {"0": {"id": 0, "name": "Zero", "positions": [[1, 1]],
                                 "groups": [], "bound": uid, "patch": "probe",
                                 "params": {"gain": 0}}},
                 "groups": {}, "next_group_id": 0}
        show = {"schema": 1, "name": "probe", "items": [{
            "kind": "step", "uid": "11111111", "alias": "probe",
            "messages": [
                {"uid": "aaaa0001", "alias": "sine", "address": "/p/gain",
                 "target": ["0"],
                 "args": [{"type": "s", "value": "lfo"},
                          {"type": "s", "value": "sine"},
                          {"type": "f", "value": 0}, {"type": "f", "value": 1},
                          {"type": "s", "value": "10s"}]}],
            "duration_s": 60, "play_count": 1,
            "then_actions": [{"type": "stop"}]}]}
        state_path = root / "installation.json"
        (shows / "probe.json").write_text(json.dumps(show))
        state_path.write_text(json.dumps(state))
        http_port = free_port(socket.SOCK_STREAM)
        listen_port = free_port(socket.SOCK_DGRAM)
        fleet_port = free_port(socket.SOCK_DGRAM)
        base_url = f"http://127.0.0.1:{http_port}"
        log = (root / "log.txt").open("w")
        server = subprocess.Popen([
            sys.executable, str(ROOT / "dashboard" / "server.py"),
            "--host", "127.0.0.1", "--port", str(http_port),
            "--listen-port", str(listen_port), "--send-port", str(fleet_port),
            "--osc-target", "127.0.0.1", "--state-file", str(state_path),
            "--assets-dir", str(assets), "--patches-dir", str(patches),
            "--public-url", base_url], cwd=ROOT, stdout=log,
            stderr=subprocess.STDOUT)
        fleet = subprocess.Popen([
            sys.executable, str(ROOT / "tools" / "simfleet.py"),
            "--devices", "1", "--devices-file", str(devices_path),
            "--target", "127.0.0.1", "--report-port", str(listen_port),
            "--cmd-port", str(fleet_port), "--hb-interval", "0.2",
            "--boot-secs", "0.2", "--state-dir", str(state_dir),
            "--manifest", str(manifest_path), "--patches-dir", str(patches),
            "--assets-dir", str(assets)], cwd=ROOT, stdout=log,
            stderr=subprocess.STDOUT)
        try:
            wait_http(base_url, server)
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page(viewport={"width": 1180, "height": 1000})
                page.goto(base_url)
                page.wait_for_selector("#ws-status.online", state="attached")
                page.wait_for_function(
                    "() => Object.keys(installation.devices || {}).length >= 1")
                page.evaluate("() => ws.send('step_start', {uid: '11111111'})")
                fpage = browser.new_page(viewport={"width": 1180, "height": 1000})
                fpage.goto(base_url + "/facilitator.html")
                fpage.wait_for_selector("#ws-status.online", state="attached")
                fpage.click("#live-scope-seats")
                sel = ('.seat-card[data-live-id="0"] '
                       'label[data-param-path="gain"] .live-param-marker')
                fpage.wait_for_selector(sel)
                info = fpage.locator(sel).evaluate("""el => {
                    const s = getComputedStyle(el);
                    const wrap = el.parentElement.getBoundingClientRect();
                    return {width: el.getBoundingClientRect().width,
                            wrap: wrap.width,
                            style: el.getAttribute('style'),
                            name: s.animationName, dur: s.animationDuration,
                            delay: s.animationDelay};
                }""")
                print("marker info:", json.dumps(info, indent=1))
                samples = []
                start = time.monotonic()
                while time.monotonic() - start < 11:
                    tx = fpage.locator(sel).evaluate(
                        "el => getComputedStyle(el).transform")
                    samples.append((round(time.monotonic() - start, 2), tx))
                    time.sleep(.4)
                for t, tx in samples:
                    print(t, tx)
                browser.close()
        finally:
            for p in (fleet, server):
                p.terminate()
            log.close()


if __name__ == "__main__":
    main()
