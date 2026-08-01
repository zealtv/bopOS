#!/usr/bin/env python3
"""Real Dashboard + simfleet verification for waveform markers and previews."""

import json
import math
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


def wait_for(predicate, timeout=6):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(.1)
    return False


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
                self.messages.append((message.address, list(message.params), time.monotonic()))
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
    patch = patches / "automation"
    patch.mkdir(parents=True)
    assets.mkdir()
    state_dir.mkdir()
    shows.mkdir()
    (patch / "main.bin").write_bytes(b"waveform-marker")
    manifest = {
        "engine": "test", "entrypoint": "main.bin", "caps": [], "slots": [],
        "params": [
            {"name": "gain", "type": "f", "min": 0, "max": 1,
             "default": .25, "dashboard": True},
            {"name": "random", "type": "f", "min": 0, "max": 1,
             "default": .25, "dashboard": True},
            {"name": "fade", "type": "f", "min": 0, "max": 1,
             "default": .1, "dashboard": True},
            {"name": "preview", "type": "f", "min": 0, "max": 1,
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
        "schema": 1, "name": "Waveform marker verifier",
        "current_show": "automation", "params_patch": "automation",
        "fleet_patch": {"name": "automation", "fingerprint": "a" * 64,
                        "staged_at": time.time(), "previous": None},
        "seats": {"0": {"id": 0, "name": "Zero", "positions": [[1, 1]],
                          "groups": [], "bound": uid, "patch": "automation",
                          "params": {"gain": .25, "random": .25, "fade": .1,
                                     "preview": .25}}},
        "groups": {}, "next_group_id": 0,
    }
    messages = [
        {"uid": "aaaa0001", "alias": "sine", "address": "/p/gain", "target": ["0"],
         "args": [{"type": "s", "value": "lfo"}, {"type": "s", "value": "sine"},
                  {"type": "f", "value": .1}, {"type": "f", "value": .9},
                  {"type": "s", "value": "2s"}, {"type": "s", "value": "p:0.25"}]},
        {"uid": "aaaa0002", "alias": "random", "address": "/p/random", "target": ["0"],
         "args": [{"type": "s", "value": "lfo"}, {"type": "s", "value": "sh"},
                  {"type": "f", "value": 0}, {"type": "f", "value": 1},
                  {"type": "s", "value": "1s"}]},
        {"uid": "aaaa0003", "alias": "fade", "address": "/p/fade", "target": ["0"],
         "args": [{"type": "f", "value": .9}, {"type": "s", "value": "1800ms"}]},
        {"uid": "aaaa0004", "alias": "preview", "address": "/p/preview", "target": ["all"],
         "args": [{"type": "f", "value": .25}]},
    ]
    show = {"schema": 1, "name": "automation", "items": [{
        "kind": "step", "uid": "11111111", "alias": "automation",
        "messages": messages, "duration_s": 10, "play_count": 1,
        "then_actions": [{"type": "stop"}],
    }]}
    state_path = root / "installation.json"
    show_path = shows / "automation.json"
    state_path.write_text(json.dumps(state), encoding="utf-8")
    show_path.write_text(json.dumps(show, indent=2) + "\n", encoding="utf-8")
    return (patches, assets, state_dir, manifest_path, state_path,
            devices_path, show_path)


def saved_args(show_path, uid):
    show = json.loads(show_path.read_text(encoding="utf-8"))
    messages = show["items"][0]["messages"]
    return next(message["args"] for message in messages if message["uid"] == uid)


def param_messages(proxy, address):
    return [(args, stamp) for seen, args, stamp in proxy.messages if seen == address]


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-waveform-marker-") as root:
        (patches, assets, state_dir, manifest_path, state_path,
         devices_path, show_path) = make_fixture(root)
        http_port = free_port(socket.SOCK_STREAM)
        listen_port = free_port(socket.SOCK_DGRAM)
        proxy_port = free_port(socket.SOCK_DGRAM)
        fleet_port = free_port(socket.SOCK_DGRAM)
        base_url = f"http://127.0.0.1:{http_port}"
        server_log_path, fleet_log_path = Path(root, "server.log"), Path(root, "fleet.log")
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
                context = browser.new_context(viewport={"width": 1180, "height": 1000})
                page = context.new_page()
                browser_errors = []
                page.on("pageerror", lambda error: browser_errors.append(str(error)))
                page.on("console", lambda message: browser_errors.append(message.text)
                        if message.type == "error" else None)
                page.goto(base_url + "/facilitator.html")
                page.wait_for_selector("#ws-status.online", state="attached")
                page.wait_for_function("() => Object.keys(installation.devices || {}).length >= 1")
                page.evaluate("() => ws.send('step_start', {uid: '11111111'})")
                page.click("#live-scope-seats")

                gain = '.seat-card[data-live-id="0"] label[data-param-path="gain"]'
                random_row = '.seat-card[data-live-id="0"] label[data-param-path="random"]'
                fade = '.seat-card[data-live-id="0"] label[data-param-path="fade"]'
                page.wait_for_selector(gain + " .live-param-marker")
                marker_style = page.locator(gain + " .live-param-marker").evaluate(
                    "el => { const s=getComputedStyle(el); return {name:s.animationName,duration:s.animationDuration,delay:s.animationDelay}; }")
                check("sine LFO has the sine marker animation", marker_style["name"] == "auto-sine")
                check("sine LFO marker uses the declared period", marker_style["duration"] == "2s",
                      repr(marker_style))
                check("sine LFO marker is phase anchored with a negative delay",
                      marker_style["delay"].startswith("-"), repr(marker_style))
                check("sh keeps its glyph", page.locator(random_row + " .live-param-glyph").count() == 1)
                check("sh has no fabricated marker", page.locator(random_row + " .live-param-marker").count() == 0)

                # SUPERSEDED by 23-waveform-marker-guard-regression: the CSS fade
                # PROGRESS BAR this used to assert was deliberately retired by
                # `fbea2b0` (17-automation-polish, "Automated sliders finally move
                # like they mean it", 2026-07-20, design authority in that stitch's
                # design.md amending the automation-4 judgment at Bob's request).
                # A deterministic fade now moves the REAL slider thumb from a
                # rAF animator driven by data-fade-* attributes on the input, so
                # there is no [data-auto-fade-progress] element and no CSS
                # animation to read a duration off. Same subject, new mechanism:
                # an in-flight fade is annotated with a finite duration, and the
                # annotation is cleared when the fade completes.
                fade_input = fade + " input[data-fade-anchor]"
                page.wait_for_selector(fade_input, timeout=15000)
                fade_data = page.locator(fade_input).evaluate(
                    "el => ({duration: Number(el.dataset.fadeDuration),"
                    " anchor: Number(el.dataset.fadeAnchor),"
                    " segments: el.dataset.fadeSegments})")
                check("in-flight fade carries a finite duration",
                      fade_data["duration"] > 0 and math.isfinite(fade_data["duration"]),
                      repr(fade_data))
                check("in-flight fade is phase anchored to a real start time",
                      fade_data["anchor"] > 0, repr(fade_data))
                check("in-flight fade carries its segment ramp",
                      fade_data["segments"] and fade_data["segments"] != "[]",
                      repr(fade_data))
                page.wait_for_function(
                    "selector => !document.querySelector(selector + ' input[data-fade-anchor]')"
                    " && !document.querySelector(selector)?.classList.contains('automated')",
                    arg=fade, timeout=8000)
                check("completed fade clears to a plain control", True)

                before_idle = len([item for item in proxy.messages if "/p/" in item[0]])
                time.sleep(.45)
                after_idle = len([item for item in proxy.messages if "/p/" in item[0]])
                check("CSS animation emits zero extra parameter OSC",
                      before_idle == after_idle, f"{before_idle} -> {after_idle}")

                reduced = browser.new_context(
                    viewport={"width": 900, "height": 900}, reduced_motion="reduce")
                reduced_page = reduced.new_page()
                reduced_errors = []
                reduced_page.on("pageerror", lambda error: reduced_errors.append(str(error)))
                reduced_page.on("console", lambda message: reduced_errors.append(message.text)
                                if message.type == "error" else None)
                reduced_page.goto(base_url + "/facilitator.html")
                reduced_page.wait_for_selector("#ws-status.online", state="attached")
                reduced_page.click("#live-scope-seats")
                reduced_page.wait_for_selector(gain + " .live-param-glyph")
                reduced_animation = reduced_page.locator(gain + " .live-param-marker").evaluate(
                    "el => getComputedStyle(el).animationName")
                check("reduced motion disables marker animation", reduced_animation == "none",
                      reduced_animation)
                check("reduced motion keeps the static glyph",
                      reduced_page.locator(gain + " .live-param-glyph").count() == 1)
                reduced.close()

                baseline = len(param_messages(proxy, "/0/p/gain"))
                slider = page.locator(gain + ' input[type="range"]')
                # scroll_into_view_if_needed waits for stability, but heartbeat
                # broadcasts re-render the cards and detach the node mid-wait;
                # a one-shot JS scroll plus a fresh bounding box is stable.
                page.evaluate(
                    "sel => document.querySelector(sel).scrollIntoView({block: 'center'})",
                    gain + ' input[type="range"]')
                box = slider.bounding_box()
                page.mouse.move(box["x"] + box["width"] * .25, box["y"] + box["height"] / 2)
                page.mouse.down()
                paused = page.locator(gain + " .live-param-marker").evaluate(
                    "el => getComputedStyle(el).animationPlayState")
                check("take-over pauses the marker under the pointer", paused == "paused", paused)
                page.mouse.move(box["x"] + box["width"] * .7,
                                box["y"] + box["height"] / 2, steps=8)
                page.mouse.up()
                page.wait_for_function("() => !installation.automation?.['0']?.gain")
                page.wait_for_function(
                    "selector => !document.querySelector(selector + ' .live-param-marker')",
                    arg=gain)
                takeover = param_messages(proxy, "/0/p/gain")[baseline:]
                check("take-over sends one plain datagram and clears the marker",
                      len(takeover) == 1 and len(takeover[0][0]) == 1, repr(takeover))

                page.goto(base_url)
                page.wait_for_selector("#ws-status.online", state="attached")
                page.click("#tab-button-show")
                page.wait_for_selector('[data-show-step-row="11111111"]')
                page.locator('[data-show-message-focus="aaaa0004"]').click()
                page.select_option("#show-param-generator", "lfo")
                page.wait_for_selector("[data-param-preview] svg")
                check("Show inspector renders exactly one static SVG preview",
                      page.locator("[data-param-preview] svg").count() == 1
                      and page.locator("[data-param-preview] svg animate").count() == 0)
                persisted = wait_for(
                    lambda: saved_args(show_path, "aaaa0004")[0]["value"] == "lfo")
                check("authored LFO persists before reload", persisted)
                authored_args = saved_args(show_path, "aaaa0004")
                page.reload()
                page.wait_for_selector("#ws-status.online", state="attached")
                page.click("#tab-button-show")
                page.locator('[data-show-message-focus="aaaa0004"]').click()
                page.wait_for_selector("[data-param-preview] svg")
                check("preview reload/refocus does not rewrite message args",
                      saved_args(show_path, "aaaa0004") == authored_args)
                page.select_option('[data-param-lfo="shape"]', "sh")
                check("sh authoring shows the honest no-preview label",
                      "not previewable" in page.locator("[data-param-preview-random]").inner_text().lower()
                      and page.locator("[data-param-preview] svg").count() == 0)

                check("browser emitted no console errors",
                      not browser_errors and not reduced_errors,
                      repr(browser_errors + reduced_errors))
                browser.close()
        finally:
            stop(fleet)
            stop(server)
            if proxy is not None:
                proxy.close()
            server_log.close()
            fleet_log.close()

        if FAILURES:
            print("\nserver log tail:\n", server_log_path.read_text(encoding="utf-8")[-4000:])
            print("\nfleet log tail:\n", fleet_log_path.read_text(encoding="utf-8")[-4000:])

    if FAILURES:
        print(f"\n{len(FAILURES)} failure(s): {', '.join(FAILURES)}")
        raise SystemExit(1)
    print("\nAll waveform marker checks passed.")


if __name__ == "__main__":
    main()
