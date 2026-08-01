#!/usr/bin/env python3
"""Real Dashboard + simfleet verification for the bop accent token pass."""

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
FAILURES = []
RESERVED = set()
TOKENS = {
    "dark": {
        "--accent": "#8a82d8", "--accent-bright": "#b9aff2",
        "--accent-soft": "#c9c3f2", "--accent-cyan": "#8fe3de",
        "--accent-cyan-soft": "#c9f2f0", "--accent-warm": "#f2e4b0",
        "--sim": "#6fb3e6",
    },
    "light": {
        "--accent": "#5a4fb8", "--accent-bright": "#6a5fcf",
        "--accent-soft": "#4b41a8", "--accent-cyan": "#1e8a84",
        "--accent-cyan-soft": "#157773", "--accent-warm": "#8a6d12",
        "--sim": "#2464a8",
    },
}


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
    patches = root / "patches"
    assets = root / "assets"
    state_dir = root / "fleet-state"
    shows = root / "shows"
    patch = patches / "accent-test"
    patch.mkdir(parents=True)
    assets.mkdir()
    state_dir.mkdir()
    shows.mkdir()
    (patch / "main.bin").write_bytes(b"accent-test")
    manifest_path = patch / "bopos.patch.json"
    manifest_path.write_text(json.dumps({
        "engine": "test", "entrypoint": "main.bin", "caps": [],
        "slots": [], "params": [], "cues": [],
    }), encoding="utf-8")
    uid = "02:53:49:4d:00:01"
    devices_path = root / "devices.csv"
    devices_path.write_text(
        f"mac,hostname,id\n{uid},sim0,0\n", encoding="utf-8")
    state_path = root / "installation.json"
    state_path.write_text(json.dumps({
        "schema": 1, "name": "Accent verifier", "current_show": None,
        "params_patch": "accent-test",
        "fleet_patch": {
            "name": "accent-test", "fingerprint": "a" * 64,
            "staged_at": time.time(), "previous": None,
        },
        "seats": {
            "0": {"id": 0, "name": "Zero", "positions": [[1, 1]],
                  "groups": [], "bound": uid, "patch": "accent-test",
                  "params": {}},
        },
        "groups": {}, "next_group_id": 0,
    }), encoding="utf-8")
    return patches, assets, state_dir, manifest_path, state_path, devices_path


def token_values(page, theme):
    page.evaluate("theme => document.documentElement.dataset.theme = theme", theme)
    return page.evaluate("""names => {
        const style = getComputedStyle(document.documentElement);
        return Object.fromEntries(names.map(name =>
            [name, style.getPropertyValue(name).trim().toLowerCase()]));
    }""", list(TOKENS[theme]))


def property_matches_token(locator, property_name, token):
    return locator.evaluate("""(element, args) => {
        const probe = document.createElement('span');
        probe.style.color = `var(${args.token})`;
        document.body.appendChild(probe);
        const expected = getComputedStyle(probe).color;
        probe.remove();
        return {
            actual: getComputedStyle(element)[args.propertyName], expected,
        };
    }""", {"propertyName": property_name, "token": token})


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-accent-verify-") as root:
        (patches, assets, state_dir, manifest_path,
         state_path, devices_path) = make_fixture(root)
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
                context = browser.new_context(viewport={"width": 1180, "height": 900})
                dashboard = context.new_page()
                dashboard_errors = []
                dashboard.on("pageerror", lambda error: dashboard_errors.append(str(error)))
                dashboard.on("console", lambda message: dashboard_errors.append(message.text)
                             if message.type == "error" else None)
                dashboard.goto(base_url + "/")
                dashboard.wait_for_selector("#ws-status.online", state="attached")

                facilitator = context.new_page()
                facilitator_errors = []
                facilitator.on("pageerror", lambda error: facilitator_errors.append(str(error)))
                facilitator.on("console", lambda message: facilitator_errors.append(message.text)
                               if message.type == "error" else None)
                facilitator.goto(base_url + "/facilitator.html")
                facilitator.wait_for_selector("#ws-status.online", state="attached")

                for page_name, page in (("dashboard", dashboard),
                                        ("facilitator", facilitator)):
                    for theme in ("dark", "light"):
                        values = token_values(page, theme)
                        check(f"{page_name} exposes all {theme} accent tokens",
                              values == TOKENS[theme], repr(values))

                token_values(dashboard, "dark")
                focused = dashboard.locator("#tab-button-dashboard")
                focused.focus()
                outline = property_matches_token(
                    focused, "outlineColor", "--accent-bright")
                check("focused button outline resolves to --accent-bright",
                      outline["actual"] == outline["expected"], repr(outline))

                selected = property_matches_token(
                    dashboard.locator('#primary-tabs button[aria-selected="true"]'),
                    "borderColor", "--accent")
                check("dashboard selected tab border resolves to --accent",
                      selected["actual"] == selected["expected"], repr(selected))

                token_values(facilitator, "dark")
                active = property_matches_token(
                    facilitator.locator(
                        '#live-scope-tabs button[aria-selected="true"]'),
                    "borderColor", "--accent")
                check("facilitator active scope border resolves to --accent",
                      active["actual"] == active["expected"], repr(active))

                check("dashboard emitted no console errors",
                      not dashboard_errors, repr(dashboard_errors))
                check("facilitator emitted no console errors",
                      not facilitator_errors, repr(facilitator_errors))
                browser.close()
        finally:
            stop(fleet)
            stop(server)
            server_log.close()
            fleet_log.close()

        if FAILURES:
            print("\nserver log tail:\n", server_log_path.read_text(encoding="utf-8")[-4000:])
            print("\nfleet log tail:\n", fleet_log_path.read_text(encoding="utf-8")[-4000:])

    if FAILURES:
        print(f"\n{len(FAILURES)} failure(s): {', '.join(FAILURES)}")
        raise SystemExit(1)
    print("\nAll bop accent checks passed.")


if __name__ == "__main__":
    main()
