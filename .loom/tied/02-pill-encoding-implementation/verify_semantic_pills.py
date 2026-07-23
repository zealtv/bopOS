#!/usr/bin/env python3
"""Playwright verification for semantic Show message pills."""

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
FAILURES = []
RESERVED = set()


def check(label, condition, detail=""):
    print(f"[{'PASS' if condition else 'FAIL'}] {label}"
          + (f" -- {detail}" if detail and not condition else ""))
    if not condition:
        FAILURES.append(label)


def free_port(kind):
    while True:
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


def arg(kind, value):
    return {"type": kind, "value": value}


def fixture(root):
    root = Path(root)
    patch = root / "patches" / "alpha"
    assets = root / "assets"
    state_dir = root / "sim-state"
    shows = root / "shows"
    for directory in (patch, assets, state_dir, shows):
        directory.mkdir(parents=True, exist_ok=True)
    (patch / "main.bin").write_bytes(b"semantic-pills")
    manifest_path = patch / "bopos.patch.json"
    manifest_path.write_text(json.dumps({
        "engine": "test", "entrypoint": "main.bin",
        "params": [{"name": "gain", "type": "f", "min": 0, "max": 1,
                    "default": .5, "dashboard": True}],
        "cues": [{"id": "snap", "label": "Snap"}],
        "caps": [], "slots": [],
    }), encoding="utf-8")
    state_path = root / "installation.json"
    state_path.write_text(json.dumps({
        "schema": 1, "name": "Semantic pills", "current_show": "pills",
        "fleet_patch": {"name": "alpha", "fingerprint": "a" * 64,
                        "staged_at": time.time(), "previous": None},
        "params_patch": "alpha",
        "seats": {}, "groups": {}, "next_group_id": 0,
    }), encoding="utf-8")
    messages = [
        {"uid": "aaaa0001", "alias": "Blackout", "address": "/cue",
         "args": [arg("s", "snap")], "target": ["all"]},
        {"uid": "aaaa0002", "alias": "Listener point", "address": "/pt",
         "args": [arg("i", 0), arg("f", .5), arg("f", .5), arg("f", 1),
                  arg("i", 1)], "target": ["all"]},
        {"uid": "aaaa0003", "alias": "Identify", "address": "/notify",
         "args": [arg("s", "identify")], "target": ["all"]},
        {"uid": "aaaa0004", "alias": "Gain set", "address": "/p/gain",
         "args": [arg("f", .8)], "target": ["all"]},
        {"uid": "aaaa0005", "alias": "Gain fade", "address": "/p/gain",
         "args": [arg("f", .2), arg("s", "4s")], "target": ["all"]},
        {"uid": "aaaa0006", "alias": "Gain loop", "address": "/p/gain",
         "args": [arg("s", "loop"), arg("f", 0), arg("s", "1s"),
                  arg("f", 1), arg("s", "1s")], "target": ["all"]},
        {"uid": "aaaa0007", "alias": "Gain LFO", "address": "/p/gain",
         "args": [arg("s", "lfo"), arg("s", "sine"), arg("f", 0),
                  arg("f", 1), arg("s", "4s")], "target": ["all"]},
        {"uid": "aaaa0008", "alias": "Stop gain", "address": "/p/gain",
         "args": [arg("s", "stop")], "target": ["all"]},
    ]
    (shows / "pills.json").write_text(json.dumps({
        "schema": 1, "name": "pills",
        "items": [{"kind": "step", "uid": "11111111", "alias": "All categories",
                   "messages": messages, "duration_s": 8, "play_count": 1,
                   "then_actions": [], "forward_sync": False}],
    }), encoding="utf-8")
    return patch.parent, assets, state_dir, manifest_path, state_path


def main():
    expected = {
        "aaaa0001": ("show-pill-cue", "CUE", "cue:"),
        "aaaa0002": ("show-pill-point", "PT", "point:"),
        "aaaa0003": ("show-pill-raw", "RAW", "raw OSC:"),
        "aaaa0004": ("show-pill-param-value", "VAL", "parameter value:"),
        "aaaa0005": ("show-pill-param-fade", "FD", "parameter fade:"),
        "aaaa0006": ("show-pill-param-loop", "LP", "parameter loop:"),
        "aaaa0007": ("show-pill-param-lfo", "LFO", "parameter LFO:"),
        "aaaa0008": ("show-pill-param-stop", "STOP", "parameter stop:"),
    }
    with tempfile.TemporaryDirectory(prefix="bopos-semantic-pills-") as root:
        patches, assets, state_dir, manifest_path, state_path = fixture(root)
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
                "--devices", "1", "--target", "127.0.0.1",
                "--report-port", str(listen_port), "--cmd-port", str(send_port),
                "--hb-interval", "0.2", "--boot-secs", "0.2",
                "--state-dir", str(state_dir), "--manifest", str(manifest_path),
                "--patches-dir", str(patches), "--assets-dir", str(assets),
            ], cwd=ROOT, stdout=fleet_log, stderr=subprocess.STDOUT)

            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page(viewport={"width": 1280, "height": 850})
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.goto(base_url)
                page.wait_for_selector("#ws-status.online", state="attached")
                page.wait_for_selector(".show-message-pill")
                check("fixture renders all eight categories",
                      page.locator(".show-message-pill").count() == 8)

                for uid, (category, code, accessible_prefix) in expected.items():
                    pill = page.locator(f'[data-drag-message="{uid}"]')
                    check(f"{uid} has semantic class and visible code",
                          category in (pill.get_attribute("class") or "")
                          and pill.locator(".show-pill-kind").inner_text() == code)
                    check(f"{uid} accessible name expands the category",
                          (pill.get_attribute("aria-label") or "")
                              .startswith(accessible_prefix))

                theme_colours = {}
                for theme in ("dark", "light"):
                    page.locator("#theme-select").select_option(theme)
                    colours = page.locator(".show-message-pill").evaluate_all(
                        """pills => pills.map(pill => {
                          const style = getComputedStyle(pill);
                          return [style.backgroundColor, style.color];
                        })""")
                    theme_colours[theme] = colours
                    check(f"{theme} theme keeps eight distinct fills",
                          len({pair[0] for pair in colours}) == 8, str(colours))
                    page.locator(".show-step-row").screenshot(
                        path=HERE / f"semantic-pills-{theme}.png")

                check("theme token sets genuinely differ",
                      theme_colours["dark"] != theme_colours["light"])

                fade = page.locator('[data-drag-message="aaaa0005"]')
                fade.click()
                state = fade.evaluate("""pill => {
                  const before = getComputedStyle(pill);
                  const background = before.backgroundColor;
                  const focusedBorder = before.borderColor;
                  pill.classList.add('show-drop-before');
                  const dropped = getComputedStyle(pill);
                  return {background, focusedBorder,
                          dropShadow:dropped.boxShadow,
                          afterBackground:dropped.backgroundColor,
                          kind:pill.querySelector('.show-pill-kind').textContent};
                }""")
                check("focus and drop state preserve category paint and code",
                      state["background"] == state["afterBackground"]
                      and state["kind"] == "FD"
                      and state["dropShadow"] != "none"
                      and bool(state["focusedBorder"]), str(state))
                check("drag affordance remains first and visible",
                      fade.locator(":scope > .show-pill-drag").count() == 1
                      and fade.locator(":scope > .show-pill-drag").is_visible())
                check("legacy hash classes are absent",
                      page.locator('[class*="show-pill-0"],[class*="show-pill-1"],'
                                   '[class*="show-pill-2"],[class*="show-pill-3"],'
                                   '[class*="show-pill-4"],[class*="show-pill-5"],'
                                   '[class*="show-pill-6"],[class*="show-pill-7"]')
                          .count() == 0)
                check("no browser errors", not errors, "; ".join(errors))
                browser.close()
        finally:
            stop(fleet)
            stop(server)
            server_log.close()
            fleet_log.close()

        if FAILURES:
            print(f"\n{len(FAILURES)} failure(s): {', '.join(FAILURES)}")
            return 1
        print(f"\n{len(expected) * 2 + 8}/{len(expected) * 2 + 8} semantic pill checks passed")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
