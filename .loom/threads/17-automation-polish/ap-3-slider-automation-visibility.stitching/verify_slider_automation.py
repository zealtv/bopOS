#!/usr/bin/env python3
"""Marker range/rate fix, highlight band, and fades moving the real slider."""

import json
import random
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright
from pythonosc.osc_message import OscMessage

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


class DatagramProxy:
    """Record Dashboard datagrams and forward them unchanged to simfleet."""

    def __init__(self, listen_port, target_port):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("127.0.0.1", listen_port))
        self.sock.settimeout(.1)
        self.target = ("127.0.0.1", target_port)
        self.messages = []
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)

    def start(self):
        self.thread.start()

    def _run(self):
        while self.running:
            try:
                data, _source = self.sock.recvfrom(65535)
            except socket.timeout:
                continue
            except OSError:
                break
            try:
                message = OscMessage(data)
                self.messages.append(
                    (message.address, list(message.params), time.monotonic()))
            except Exception:
                pass
            self.sock.sendto(data, self.target)

    def close(self):
        self.running = False
        self.sock.close()
        self.thread.join(timeout=1)


def make_fixture(root):
    root = Path(root)
    patches, assets = root / "patches", root / "assets"
    state_dir, shows = root / "fleet-state", root / "shows"
    patch = patches / "vis"
    patch.mkdir(parents=True)
    assets.mkdir()
    state_dir.mkdir()
    shows.mkdir()
    (patch / "main.bin").write_bytes(b"vis")
    manifest = {
        "engine": "test", "entrypoint": "main.bin", "caps": [], "slots": [],
        "params": [
            {"name": "gain", "type": "f", "min": 0, "max": 1,
             "default": 0, "dashboard": True},
            {"name": "fade", "type": "f", "min": 0, "max": 1,
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
        "schema": 1, "name": "Slider automation verifier",
        "current_show": "vis", "params_patch": "vis",
        "fleet_patch": {"name": "vis", "fingerprint": "a" * 64,
                        "staged_at": time.time(), "previous": None},
        "seats": {"0": {"id": 0, "name": "Zero", "positions": [[1, 1]],
                        "groups": [], "bound": uid, "patch": "vis",
                        "params": {"gain": 0, "fade": 0}}},
        "groups": {}, "next_group_id": 0,
    }
    messages = [
        {"uid": "aaaa0001", "alias": "sine", "address": "/p/gain", "target": ["0"],
         "args": [{"type": "s", "value": "lfo"}, {"type": "s", "value": "sine"},
                  {"type": "f", "value": 0}, {"type": "f", "value": 1},
                  {"type": "s", "value": "10s"}]},
        {"uid": "aaaa0002", "alias": "fade", "address": "/p/fade", "target": ["0"],
         "args": [{"type": "f", "value": .9}, {"type": "s", "value": "30s"}]},
    ]
    show = {"schema": 1, "name": "vis", "items": [{
        "kind": "step", "uid": "11111111", "alias": "vis",
        "messages": messages, "duration_s": 60, "play_count": 1,
        "then_actions": [{"type": "stop"}],
    }]}
    state_path = root / "installation.json"
    (shows / "vis.json").write_text(json.dumps(show, indent=2) + "\n",
                                    encoding="utf-8")
    state_path.write_text(json.dumps(state), encoding="utf-8")
    return patches, assets, state_dir, manifest_path, state_path, devices_path


GAIN = '.seat-card[data-live-id="0"] label[data-param-path="gain"]'
FADE = '.seat-card[data-live-id="0"] label[data-param-path="fade"]'


def open_facilitator(browser, base_url, errors, **context_kwargs):
    context = browser.new_context(
        viewport={"width": 1180, "height": 1000}, **context_kwargs)
    page = context.new_page()
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on("console", lambda message: errors.append(message.text)
            if message.type == "error" else None)
    page.goto(base_url + "/facilitator.html")
    page.wait_for_selector("#ws-status.online", state="attached")
    page.click("#live-scope-seats")
    return context, page


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-slider-auto-") as root:
        (patches, assets, state_dir, manifest_path, state_path,
         devices_path) = make_fixture(root)
        http_port = free_port(socket.SOCK_STREAM)
        listen_port = free_port(socket.SOCK_DGRAM)
        proxy_port = free_port(socket.SOCK_DGRAM)
        fleet_port = free_port(socket.SOCK_DGRAM)
        base_url = f"http://127.0.0.1:{http_port}"
        server_log_path = Path(root, "server.log")
        fleet_log_path = Path(root, "fleet.log")
        server_log = server_log_path.open("w", encoding="utf-8")
        fleet_log = fleet_log_path.open("w", encoding="utf-8")
        server = fleet = proxy = None
        try:
            proxy = DatagramProxy(proxy_port, fleet_port)
            proxy.start()
            server = subprocess.Popen([
                sys.executable, str(ROOT / "dashboard" / "server.py"),
                "--host", "127.0.0.1", "--port", str(http_port),
                "--listen-port", str(listen_port), "--send-port", str(proxy_port),
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
                context, page = open_facilitator(browser, base_url, errors)
                page.wait_for_function(
                    "() => Object.keys(installation.devices || {}).length >= 1")
                page.evaluate("() => ws.send('step_start', {uid: '11111111'})")

                marker = GAIN + " .live-param-marker"
                page.wait_for_selector(marker)

                # --- Part 1: the LFO marker sweeps the full authored range.
                # Sample the animated transform for one 10s period.
                geometry = page.evaluate("""sel => {
                    const el = document.querySelector(sel);
                    const s = getComputedStyle(el);
                    const after = getComputedStyle(el, '::after');
                    return {width: el.getBoundingClientRect().width,
                            z: s.zIndex, duration: s.animationDuration,
                            bandW: after.width, bandH: after.height};
                }""", marker)
                check("marker animation uses the authored 10s period",
                      geometry["duration"] == "10s", repr(geometry))
                samples = []
                start = time.monotonic()
                while time.monotonic() - start < 10.5:
                    tx = page.evaluate(
                        """sel => { const el = document.querySelector(sel);
                             if (!el) return null;
                             const t = getComputedStyle(el).transform;
                             if (!t || t === 'none') return 0;
                             return new DOMMatrixReadOnly(t).m41; }""", marker)
                    if tx is not None:
                        samples.append(tx)
                    time.sleep(.25)
                width = geometry["width"]
                check("sine marker reaches the low extreme",
                      min(samples) < width * .08, f"min={min(samples)} w={width}")
                check("sine marker reaches the high extreme",
                      max(samples) > width * .9, f"max={max(samples)} w={width}")
                mids = sum(1 for value in samples
                           if width * .25 < value < width * .75)
                check("sine marker spends real time mid-range (no darting)",
                      mids >= len(samples) * .25, f"{mids}/{len(samples)}")

                # --- Part 3: the band geometry and layering.
                check("marker band is 12px wide and 34px tall",
                      geometry["bandW"] == "12px" and geometry["bandH"] == "34px",
                      repr(geometry))
                check("marker band sits behind the slider (z-index 1)",
                      geometry["z"] == "1", repr(geometry))
                check("fade progress element is retired",
                      page.locator("[data-auto-fade-progress]").count() == 0)
                page.locator('.seat-card[data-live-id="0"]').screenshot(
                    path=str(STITCH / "band-live.png"))

                # --- Part 2: the fade moves the real slider thumb.
                fade_input = FADE + ' input[type="range"]'
                page.wait_for_selector(FADE + "[class*=automated]")
                v1 = float(page.locator(fade_input).input_value())
                time.sleep(2)
                v2 = float(page.locator(fade_input).input_value())
                time.sleep(2)
                v3 = float(page.locator(fade_input).input_value())
                check("fade thumb moves monotonically toward the target",
                      v1 < v2 < v3 <= .9, f"{v1} {v2} {v3}")

                # Take-over mid-fade: pointer down freezes, drag sends one
                # plain value, automation clears.
                baseline = len([m for m in proxy.messages
                                if m[0] == "/0/p/fade"])
                page.evaluate(
                    "sel => document.querySelector(sel).scrollIntoView({block: 'center'})",
                    fade_input)
                box = page.locator(fade_input).bounding_box()
                page.mouse.move(box["x"] + box["width"] * .5,
                                box["y"] + box["height"] / 2)
                page.mouse.down()
                frozen1 = float(page.locator(fade_input).input_value())
                time.sleep(.6)
                frozen2 = float(page.locator(fade_input).input_value())
                check("finger freezes the fade animator",
                      abs(frozen2 - frozen1) < .005, f"{frozen1} -> {frozen2}")
                page.mouse.move(box["x"] + box["width"] * .3,
                                box["y"] + box["height"] / 2, steps=6)
                page.mouse.up()
                page.wait_for_function(
                    "sel => !document.querySelector(sel)?.classList.contains('automated')",
                    arg=FADE)
                takeover = [m for m in proxy.messages
                            if m[0] == "/0/p/fade"][baseline:]
                check("take-over sends exactly one plain datagram",
                      len(takeover) == 1 and len(takeover[0][1]) == 1,
                      repr(takeover))

                # The animation itself emits no OSC (LFO still running).
                before_idle = len([m for m in proxy.messages if "/p/" in m[0]])
                time.sleep(1)
                after_idle = len([m for m in proxy.messages if "/p/" in m[0]])
                check("animator emits zero parameter OSC",
                      before_idle == after_idle,
                      f"{before_idle} -> {after_idle}")
                context.close()

                # --- Reduced motion: band hidden, fade values step coarsely.
                page.evaluate = None  # guard against accidental reuse
                rcontext, rpage = open_facilitator(
                    browser, base_url, errors, reduced_motion="reduce")
                rpage.wait_for_selector(GAIN + " .live-param-glyph")
                band_opacity = rpage.locator(GAIN + " .live-param-marker") \
                    .evaluate("el => getComputedStyle(el).opacity")
                check("reduced motion hides the band", band_opacity == "0",
                      band_opacity)
                rcontext.close()

                check("browser emitted no console errors", not errors,
                      repr(errors))
                browser.close()
        finally:
            stop(fleet)
            stop(server)
            if proxy is not None:
                proxy.close()
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
    print("\nAll slider automation checks passed.")


if __name__ == "__main__":
    main()
