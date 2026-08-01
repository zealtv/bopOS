#!/usr/bin/env python3
"""Real Dashboard + simfleet verification for light/dark surfaces and toggle."""

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
ARTIFACT_DIR = Path(__file__).resolve().parent
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
        const cssName = args.propertyName.replace(/[A-Z]/g, letter => `-${letter.toLowerCase()}`);
        const computed = getComputedStyle(element);
        return {actual: computed.getPropertyValue(cssName) || computed[args.propertyName], expected};
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


def css_tokens(page, names):
    return page.evaluate("""names => {
        const style = getComputedStyle(document.documentElement);
        return Object.fromEntries(names.map(name => [name, style.getPropertyValue(name).trim()]));
    }""", names)


def contrast_ratio(first, second):
    def luminance(value):
        channels = [int(part) / 255 for part in re.findall(r"\d+", value)[:3]]
        channels = [part / 12.92 if part <= .04045
                    else ((part + .055) / 1.055) ** 2.4 for part in channels]
        return .2126 * channels[0] + .7152 * channels[1] + .0722 * channels[2]
    high, low = sorted((luminance(first), luminance(second)), reverse=True)
    return (high + .05) / (low + .05)


def check_contrast(page, theme):
    names = ["--bg", "--panel", "--input", "--control", "--text", "--dim",
             "--line", "--accent", "--auto"]
    raw = css_tokens(page, names)
    resolved = page.evaluate("""values => Object.fromEntries(
        Object.entries(values).map(([name, value]) => {
            const probe = document.createElement('span');
            probe.style.color = value;
            document.body.appendChild(probe);
            const color = getComputedStyle(probe).color;
            probe.remove();
            return [name, color];
        }))""", raw)
    for foreground in ("--text", "--dim"):
        for background in ("--bg", "--panel", "--input", "--control"):
            ratio = contrast_ratio(resolved[foreground], resolved[background])
            check(f"{theme} {foreground} on {background} >= 4.5:1", ratio >= 4.5,
                  f"{ratio:.2f}:1 {resolved[foreground]} on {resolved[background]}")
    for foreground in ("--line", "--accent", "--auto"):
        ratio = contrast_ratio(resolved[foreground], resolved["--panel"])
        check(f"{theme} {foreground} mark on --panel >= 3:1", ratio >= 3,
              f"{ratio:.2f}:1 {resolved[foreground]} on {resolved['--panel']}")


def main():
    style_paths = [ROOT / "dashboard/static/css/style.css",
                   ROOT / "dashboard/static/css/facilitator.css"]
    surface_literals = {"#101316", "#191e23", "#10161b", "#14191d",
                        "#12171c", "#273039", "#45515b", "#252d34"}
    implementation_css = "\n".join(
        "\n".join(path.read_text(encoding="utf-8").splitlines()[offset:])
        for path, offset in zip(style_paths, (5, 9)))
    leaked_surfaces = sorted(value for value in surface_literals
                             if value.lower() in implementation_css.lower())
    check("core surfaces are tokens outside the theme declarations",
          not leaked_surfaces, repr(leaked_surfaces))
    check("dark-only color-scheme pin is retired",
          all("dark only" not in path.read_text(encoding="utf-8")
              for path in style_paths))
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
                dashboard.emulate_media(color_scheme="light")
                dashboard_errors = []
                dashboard.on("pageerror", lambda error: dashboard_errors.append(str(error)))
                dashboard.on("console", lambda message: dashboard_errors.append(message.text)
                             if message.type == "error" else None)
                dashboard.goto(base_url + "/")
                dashboard.wait_for_selector("#ws-status.online", state="attached")
                dashboard.wait_for_function(
                    "() => Object.keys(installation.devices || {}).length >= 1")
                dashboard.wait_for_selector(".dot.online", state="attached")

                initial_theme = dashboard.evaluate("""() => ({
                    theme: document.documentElement.dataset.theme,
                    preference: document.documentElement.dataset.themePreference,
                    selected: document.querySelector('#theme-select').value,
                    stored: localStorage.getItem('bopos-theme'),
                    meta: document.querySelector('meta[name="theme-color"]').content,
                    body: getComputedStyle(document.body).backgroundColor,
                    accent: getComputedStyle(document.documentElement).getPropertyValue('--accent-cyan').trim()
                })""")
                check("system preference defaults to emulated light", initial_theme == {
                    "theme": "light", "preference": "system", "selected": "system",
                    "stored": None, "meta": "#f4f1f8", "body": "rgb(244, 241, 248)",
                    # 21-theme-cyan-tint retuned light --accent-cyan.
                    "accent": "#0E728C",
                }, repr(initial_theme))
                check_contrast(dashboard, "light")

                dashboard.select_option("#theme-select", "dark")
                dark_theme = dashboard.evaluate("""() => ({
                    theme: document.documentElement.dataset.theme,
                    stored: localStorage.getItem('bopos-theme'),
                    meta: document.querySelector('meta[name="theme-color"]').content,
                    body: getComputedStyle(document.body).backgroundColor,
                    accent: getComputedStyle(document.documentElement).getPropertyValue('--accent-cyan').trim()
                })""")
                check("dashboard toggle applies dark surfaces and metadata", dark_theme == {
                    "theme": "dark", "stored": "dark", "meta": "#101316",
                    "body": "rgb(16, 19, 22)", "accent": "#8FE3DE",
                }, repr(dark_theme))
                check_contrast(dashboard, "dark")
                dashboard.reload()
                check("explicit theme persists across reload",
                      dashboard.get_attribute("html", "data-theme") == "dark"
                      and dashboard.locator("#theme-select").input_value() == "dark")

                facilitator = context.new_page()
                facilitator.emulate_media(color_scheme="light")
                facilitator_errors = []
                facilitator.on("pageerror", lambda error: facilitator_errors.append(str(error)))
                facilitator.on("console", lambda message: facilitator_errors.append(message.text)
                               if message.type == "error" else None)
                facilitator.goto(base_url + "/facilitator.html")
                facilitator.wait_for_selector("#ws-status.online", state="attached")
                check("facilitator shares the persisted explicit theme",
                      facilitator.get_attribute("html", "data-theme") == "dark"
                      and facilitator.locator("#theme-select").input_value() == "dark")
                facilitator.select_option("#theme-select", "system")
                system_light = facilitator.evaluate("""() => ({
                    theme: document.documentElement.dataset.theme,
                    preference: document.documentElement.dataset.themePreference,
                    stored: localStorage.getItem('bopos-theme'),
                    meta: document.querySelector('meta[name="theme-color"]').content
                })""")
                check("System clears persistence and follows light media", system_light == {
                    "theme": "light", "preference": "system", "stored": None,
                    "meta": "#f4f1f8",
                }, repr(system_light))
                facilitator.emulate_media(color_scheme="dark")
                facilitator.wait_for_function(
                    "() => document.documentElement.dataset.theme === 'dark'")
                check("System responds to a live preference change",
                      facilitator.locator("#theme-select").input_value() == "system"
                      and facilitator.get_attribute(
                          'meta[name="theme-color"]', "content") == "#101316")
                facilitator.click("#live-scope-seats")
                range_selector = '.live-param[data-param-path="gain"] input[type="range"]'
                check_selector = '.live-param[data-param-path="enabled"] input[type="checkbox"]'
                facilitator.wait_for_selector(range_selector)
                facilitator.wait_for_selector(check_selector)
                facilitator.select_option("#theme-select", "dark")

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

                facilitator.select_option("#theme-select", "light")
                light_range = property_matches_token(
                    facilitator.locator(range_selector), "accentColor", "--accent-cyan")
                check("light theme flips range to light --accent-cyan",
                      light_range["actual"] == light_range["expected"]
                      # Retuned by 21-theme-cyan-tint: light --accent-cyan
                      # #147772 -> #0E728C (green-leaning teal -> true cyan).
                      == "rgb(14, 114, 140)"
                      and light_range["actual"] != range_accent["actual"],
                      repr({"dark": range_accent, "light": light_range}))

                # The pill trios below were written against the dark theme, but
                # by this point the dashboard page is following the system
                # preference (headless Chromium reports light). Select dark
                # explicitly -- guard mechanics, no colour ruling
                # (21-theme-cyan-tint).
                dashboard.select_option("#theme-select", "dark")
                dashboard.wait_for_function(
                    "() => document.documentElement.getAttribute('data-theme') === 'dark'")
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

                for theme in ("dark", "light"):
                    dashboard.select_option("#theme-select", theme)
                    dashboard.wait_for_function("""theme =>
                        document.querySelector('#dashboard-live-view').contentDocument
                            ?.documentElement.dataset.theme === theme""", arg=theme)
                    check(f"embedded Dashboard follows {theme} selection",
                          dashboard.get_attribute("html", "data-theme") == theme)
                    for tab in ("dashboard", "seats", "devices", "patches", "assets", "show"):
                        dashboard.click(f"#tab-button-{tab}")
                        dashboard.screenshot(
                            path=ARTIFACT_DIR / f"review-{theme}-{tab}.png",
                            full_page=True)
                    facilitator.select_option("#theme-select", theme)
                    facilitator.screenshot(
                        path=ARTIFACT_DIR / f"review-{theme}-facilitator.png",
                        full_page=True)

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
    print("\nAll theme surface and toggle checks passed.")


if __name__ == "__main__":
    main()
