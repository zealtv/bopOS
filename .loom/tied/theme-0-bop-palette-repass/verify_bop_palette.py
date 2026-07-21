#!/usr/bin/env python3
"""Real Dashboard + simfleet verification for the ratified bop palette repass."""

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
    patch = patches / "palette"
    patch.mkdir(parents=True)
    assets.mkdir()
    state_dir.mkdir()
    shows.mkdir()
    (patch / "main.bin").write_bytes(b"palette-test")
    manifest = {
        "engine": "test", "entrypoint": "main.bin", "caps": [], "slots": [],
        "params": [
            {"name": "gain", "type": "f", "min": 0, "max": 1,
             "default": 0.5, "dashboard": True},
            {"name": "enabled", "type": "i", "min": 0, "max": 1,
             "default": 1, "dashboard": True},
        ],
        "cues": [],
    }
    manifest_path = patch / "bopos.patch.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    uid = "02:53:49:4d:00:01"
    devices_path = root / "devices.csv"
    devices_path.write_text(
        f"mac,hostname,id\n{uid},sim0,0\n", encoding="utf-8")
    state = {
        "schema": 1, "name": "Palette verifier", "current_show": "palette",
        "params_patch": "palette",
        "fleet_patch": {
            "name": "palette", "fingerprint": "a" * 64,
            "staged_at": time.time(), "previous": None,
        },
        "seats": {
            "0": {"id": 0, "name": "Zero", "positions": [[1, 1]],
                  "groups": [], "bound": uid, "patch": "palette",
                  "params": {"gain": 0.5, "enabled": 1}},
        },
        "groups": {}, "next_group_id": 0,
    }
    show = {
        "schema": 1, "name": "palette", "items": [{
            "kind": "step", "uid": "11111111", "alias": "palette",
            "messages": [
                {"uid": "aaaa0001", "alias": "warm", "address": "/p/gain",
                 "target": ["0"], "args": [{"type": "f", "value": 0.25}]},
                {"uid": "aaaa0002", "alias": "two", "address": "/p/enabled",
                 "target": ["0"], "args": [{"type": "i", "value": 1}]},
            ],
            "duration_s": 5, "play_count": 1,
            "then_actions": [{"type": "stop"}],
        }],
    }
    state_path = root / "installation.json"
    state_path.write_text(json.dumps(state), encoding="utf-8")
    (shows / "palette.json").write_text(
        json.dumps(show, indent=2) + "\n", encoding="utf-8")
    return patches, assets, state_dir, manifest_path, state_path, devices_path


def property_matches_token(locator, property_name, token):
    return locator.evaluate("""(element, args) => {
        const probe = document.createElement('span');
        probe.style.color = `var(${args.token})`;
        document.body.appendChild(probe);
        const expected = getComputedStyle(probe).color;
        probe.remove();
        return {actual: getComputedStyle(element)[args.propertyName], expected};
    }""", {"propertyName": property_name, "token": token})


def scroll_and_box(page, selector):
    page.evaluate(
        "sel => document.querySelector(sel)?.scrollIntoView({block: 'center'})",
        selector)
    return page.locator(selector).bounding_box()


def computed_trio(locator):
    return locator.evaluate("""element => {
        const style = getComputedStyle(element);
        return {border: style.borderColor, background: style.backgroundColor,
                color: style.color};
    }""")


def main():
    style_paths = [ROOT / "dashboard/static/css/style.css",
                   ROOT / "dashboard/static/css/facilitator.css"]
    green_accent = sum(path.read_text(encoding="utf-8").count(
        "accent-color:var(--green)") for path in style_paths)
    check("no stylesheet keeps green accent-color", green_accent == 0,
          str(green_accent))

    with tempfile.TemporaryDirectory(prefix="bopos-palette-verify-") as root:
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
                context = browser.new_context(viewport={"width": 1280, "height": 1000})

                dashboard = context.new_page()
                dashboard_errors = []
                dashboard.on("pageerror", lambda error: dashboard_errors.append(str(error)))
                dashboard.on("console", lambda message: dashboard_errors.append(message.text)
                             if message.type == "error" else None)
                dashboard.goto(base_url + "/")
                dashboard.wait_for_selector("#ws-status.online", state="attached")
                dashboard.wait_for_function(
                    "() => Object.keys(installation.devices || {}).length >= 1")
                dashboard.wait_for_selector(".dot.online", state="attached")

                facilitator = context.new_page()
                facilitator_errors = []
                facilitator.on("pageerror", lambda error: facilitator_errors.append(str(error)))
                facilitator.on("console", lambda message: facilitator_errors.append(message.text)
                               if message.type == "error" else None)
                facilitator.goto(base_url + "/facilitator.html")
                facilitator.wait_for_selector("#ws-status.online", state="attached")
                facilitator.click("#live-scope-seats")
                range_selector = '.live-param[data-param-path="gain"] input[type="range"]'
                check_selector = '.live-param[data-param-path="enabled"] input[type="checkbox"]'
                facilitator.wait_for_selector(range_selector)
                facilitator.wait_for_selector(check_selector)
                facilitator.evaluate(
                    "document.documentElement.dataset.theme = 'dark'")

                range_accent = property_matches_token(
                    facilitator.locator(range_selector), "accentColor", "--accent-cyan")
                check("facilitator range uses --accent-cyan",
                      range_accent["actual"] == range_accent["expected"],
                      repr(range_accent))
                checkbox_accent = property_matches_token(
                    facilitator.locator(check_selector), "accentColor", "--accent-warm")
                check("facilitator live checkbox uses --accent-warm",
                      checkbox_accent["actual"] == checkbox_accent["expected"],
                      repr(checkbox_accent))
                live_output = property_matches_token(
                    facilitator.locator(
                        '.live-param[data-param-path="gain"] output'),
                    "color", "--accent-cyan-soft")
                check("facilitator live output uses --accent-cyan-soft",
                      live_output["actual"] == live_output["expected"],
                      repr(live_output))

                master_accent = property_matches_token(
                    dashboard.locator("#master-control input"),
                    "accentColor", "--accent-cyan")
                check("dashboard master uses --accent-cyan",
                      master_accent["actual"] == master_accent["expected"],
                      repr(master_accent))
                master_output = property_matches_token(
                    dashboard.locator("#master-control output"),
                    "color", "--accent-cyan-soft")
                check("dashboard master output uses --accent-cyan-soft",
                      master_output["actual"] == master_output["expected"],
                      repr(master_output))
                eyebrow = property_matches_token(
                    dashboard.locator(".eyebrow").first, "color", "--accent-soft")
                check("dashboard eyebrow uses --accent-soft",
                      eyebrow["actual"] == eyebrow["expected"], repr(eyebrow))
                online = property_matches_token(
                    dashboard.locator(".dot.online").first, "backgroundColor", "--green")
                check("dashboard online dot remains --green",
                      online["actual"] == online["expected"], repr(online))

                facilitator.evaluate(
                    "document.documentElement.dataset.theme = 'light'")
                light_range = property_matches_token(
                    facilitator.locator(range_selector), "accentColor", "--accent-cyan")
                check("light theme flips range to light --accent-cyan",
                      light_range["actual"] == light_range["expected"]
                      # Retuned by 21-theme-cyan-tint (light --accent-cyan
                      # #147772 -> #0E728C). Note the literal pinned here was
                      # already stale: rgb(30,138,132) never matched #147772
                      # (rgb(20,119,114)), so this check was red on main.
                      == "rgb(14, 114, 140)"
                      and light_range["actual"] != range_accent["actual"],
                      repr({"dark": range_accent, "light": light_range}))

                # theme-1 made pages follow the system preference and headless
                # Chromium reports light, so the dark pill trios below no longer
                # matched. Stamp the theme this check was written against.
                # Guard-mechanics repair only, no colour ruling
                # (21-theme-cyan-tint).
                dashboard.evaluate(
                    "document.documentElement.dataset.theme = 'dark'")
                dashboard.evaluate(
                    "document.querySelector('#tab-button-show').click()")
                dashboard.wait_for_selector('.show-pill-0')
                dashboard.wait_for_selector('.show-pill-1')
                pill0_box = scroll_and_box(dashboard, ".show-pill-0")
                pill1_box = scroll_and_box(dashboard, ".show-pill-1")
                check("both Show palette pills render",
                      pill0_box is not None and pill1_box is not None,
                      repr((pill0_box, pill1_box)))
                pill0 = computed_trio(dashboard.locator(".show-pill-0"))
                check("Show pill-0 uses the ratified cyan trio", pill0 == {
                    "border": "rgb(46, 138, 132)",
                    "background": "rgb(15, 43, 41)",
                    "color": "rgb(168, 235, 230)",
                }, repr(pill0))
                pill1 = computed_trio(dashboard.locator(".show-pill-1"))
                check("Show pill-1 remains unchanged", pill1 == {
                    "border": "rgb(163, 118, 42)",
                    "background": "rgb(51, 38, 15)",
                    "color": "rgb(245, 207, 138)",
                }, repr(pill1))

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
            print("\nserver log tail:\n", server_log_path.read_text(
                encoding="utf-8")[-4000:])
            print("\nfleet log tail:\n", fleet_log_path.read_text(
                encoding="utf-8")[-4000:])

    if FAILURES:
        print(f"\n{len(FAILURES)} failure(s): {', '.join(FAILURES)}")
        raise SystemExit(1)
    print("\nAll bop palette checks passed.")


if __name__ == "__main__":
    main()
