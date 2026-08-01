#!/usr/bin/env python3
"""Verify the initial loading overlay against the real Dashboard and simfleet."""

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
ARTIFACT_DIR = Path(__file__).resolve().parent
FAILURES = []


def check(label, condition, detail=""):
    print(f"[{'PASS' if condition else 'FAIL'}] {label}"
          + (f" -- {detail}" if detail and not condition else ""))
    if not condition:
        FAILURES.append(label)


def free_port(kind):
    for _ in range(256):
        port = random.SystemRandom().randrange(20000, 60000)
        probe = socket.socket(socket.AF_INET, kind)
        try:
            probe.bind(("127.0.0.1", port))
        except OSError:
            probe.close()
            continue
        probe.close()
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


def fixture(root):
    root = Path(root)
    patches, assets = root / "patches", root / "assets"
    state_dir = root / "fleet-state"
    patch = patches / "spinner"
    patch.mkdir(parents=True)
    assets.mkdir()
    state_dir.mkdir()
    (patch / "main.bin").write_bytes(b"spinner")
    manifest = {"engine": "test", "entrypoint": "main.bin", "caps": [],
                "slots": [], "params": [], "cues": []}
    manifest_path = patch / "bopos.patch.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    uid = "02:53:49:4d:00:01"
    devices_path = root / "devices.csv"
    devices_path.write_text(f"mac,hostname,id\n{uid},sim0,0\n", encoding="utf-8")
    state = {"schema": 1, "name": "Spinner verifier", "current_show": "spinner",
             "params_patch": "spinner", "seats": {}, "groups": {},
             "next_group_id": 0}
    state_path = root / "installation.json"
    state_path.write_text(json.dumps(state), encoding="utf-8")
    return patches, assets, state_dir, manifest_path, state_path, devices_path


def delayed_page(context, url, name, screenshot=False):
    page = context.new_page()
    queued = []
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on("console", lambda message: errors.append(message.text)
            if message.type == "error" else None)

    def intercept(client):
        server = client.connect_to_server()
        client.on_message(lambda message: server.send(message))

        def incoming(message):
            try:
                is_state = json.loads(message).get("type") == "state"
            except (json.JSONDecodeError, AttributeError, TypeError):
                is_state = False
            if is_state:
                queued.append((client, message))
            else:
                client.send(message)

        server.on_message(incoming)

    page.route_web_socket("**/ws", intercept)
    page.goto(url)
    page.wait_for_selector("#initial-loading")
    deadline = time.monotonic() + 5
    while not queued and time.monotonic() < deadline:
        page.wait_for_timeout(20)
    check(f"{name} spinner precedes first state", bool(queued))
    check(f"{name} spinner covers the initial viewport",
          page.locator("#initial-loading").evaluate("""element => {
              const box = element.getBoundingClientRect();
              return box.left === 0 && box.top === 0
                  && box.width === innerWidth && box.height === innerHeight;
          }"""))
    if screenshot:
        page.screenshot(path=ARTIFACT_DIR / "review-spinner.png")
    animation = page.locator(".bop-beats i").first.evaluate(
        "element => getComputedStyle(element).animationName")
    check(f"{name} spinner bops with CSS motion", animation == "bop-beat", animation)
    for client, message in queued:
        client.send(message)
    queued.clear()
    page.wait_for_selector("#initial-loading", state="hidden")
    check(f"{name} spinner dismisses after state application", True)
    page.wait_for_timeout(650)
    check(f"{name} spinner stays dismissed in steady state",
          page.locator("#initial-loading").is_hidden())
    check(f"{name} has no console errors", not errors, repr(errors))
    page.close()


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-spinner-verify-") as root:
        patches, assets, state_dir, manifest, state, devices = fixture(root)
        http_port = free_port(socket.SOCK_STREAM)
        listen_port = free_port(socket.SOCK_DGRAM)
        send_port = free_port(socket.SOCK_DGRAM)
        base = f"http://127.0.0.1:{http_port}"
        server_log = Path(root, "server.log").open("w", encoding="utf-8")
        fleet_log = Path(root, "fleet.log").open("w", encoding="utf-8")
        server = fleet = None
        try:
            server = subprocess.Popen([
                sys.executable, str(ROOT / "dashboard/server.py"), "--host", "127.0.0.1",
                "--port", str(http_port), "--listen-port", str(listen_port),
                "--send-port", str(send_port), "--osc-target", "127.0.0.1",
                "--state-file", str(state), "--assets-dir", str(assets),
                "--patches-dir", str(patches), "--public-url", base,
            ], cwd=ROOT, stdout=server_log, stderr=subprocess.STDOUT)
            wait_http(base, server)
            fleet = subprocess.Popen([
                sys.executable, str(ROOT / "tools/simfleet.py"), "--devices", "1",
                "--devices-file", str(devices), "--target", "127.0.0.1",
                "--report-port", str(listen_port), "--cmd-port", str(send_port),
                "--hb-interval", "0.2", "--boot-secs", "0.2",
                "--state-dir", str(state_dir), "--manifest", str(manifest),
                "--patches-dir", str(patches), "--assets-dir", str(assets),
            ], cwd=ROOT, stdout=fleet_log, stderr=subprocess.STDOUT)
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                context = browser.new_context(viewport={"width": 1180, "height": 820})
                delayed_page(context, base + "/", "technical page", screenshot=True)
                delayed_page(context, base + "/facilitator.html", "facilitator page")
                reduced = browser.new_context(viewport={"width": 900, "height": 700},
                                              reduced_motion="reduce")
                page = reduced.new_page()
                page.route_web_socket("**/ws", lambda client: None)
                page.goto(base + "/")
                page.wait_for_selector("#initial-loading")
                animation = page.locator(".bop-beats i").first.evaluate(
                    "element => getComputedStyle(element).animationName")
                check("reduced motion renders a static treatment", animation == "none", animation)
                browser.close()
        finally:
            stop(fleet)
            stop(server)
            server_log.close()
            fleet_log.close()
    if FAILURES:
        raise SystemExit(f"{len(FAILURES)} failure(s): {', '.join(FAILURES)}")
    print("All loading spinner checks passed.")


if __name__ == "__main__":
    main()
