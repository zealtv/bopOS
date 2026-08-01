#!/usr/bin/env python3
"""Browser journey for Show preset authoring, playback and capture-as-step."""

import datetime as dt
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
for source in (ROOT, ROOT / "python", ROOT / "dashboard"):
    sys.path.insert(0, str(source))

import identity  # noqa: E402
import preset_store  # noqa: E402

FAILURES = []
RESERVED = set()


def check(label, condition, detail=""):
    print(f"[{'PASS' if condition else 'FAIL'}] {label}"
          + (f" -- {detail}" if detail and not condition else ""), flush=True)
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
    root = Path(root)
    patch = root / "patches" / "alpha"
    assets = root / "assets"
    shows = root / "shows"
    patch.mkdir(parents=True)
    assets.mkdir()
    shows.mkdir()
    (patch / "main.bin").write_bytes(b"show-preset-message-verifier")
    manifest = {
        "engine": "test", "entrypoint": "main.bin",
        "params": [
            {"name": "gain", "kind": "float", "min": 0, "max": 1,
             "default": .2, "dashboard": True},
            {"name": "gate", "kind": "toggle", "default": 0,
             "dashboard": True},
        ],
        "events": [], "caps": [], "slots": [],
    }
    (patch / "bopos.patch.json").write_text(json.dumps(manifest))
    store = preset_store.PresetStore(root / "patches")
    now = dt.datetime(2026, 7, 29, tzinfo=dt.timezone.utc)
    store.save("alpha", "Dawn", {"gain": [.8], "gate": [1]}, now=now)
    store.save("alpha", "Dusk", {"gain": [.1], "gate": [0]}, now=now)

    def seat(seat_id, groups):
        return {
            "id": seat_id, "name": f"Seat {seat_id}", "positions": [],
            "groups": groups, "bound": None,
            "params": {"gain": .2, "gate": 0},
        }

    state = {
        "schema": 1, "name": "Show preset rig",
        "current_show": "opening",
        "fleet_patch": {
            "name": "alpha", "fingerprint": identity.fingerprint(patch),
            "staged_at": time.time(), "previous": None,
        },
        "params_patch": "alpha",
        "groups": {"1": {"id": 1, "name": "Front"}},
        "next_group_id": 2,
        "seats": {
            "1": seat(1, [1]), "2": seat(2, [1]), "3": seat(3, []),
        },
    }
    show = {
        "schema": 1, "name": "opening",
        "items": [{
            "kind": "step", "uid": "11111111", "alias": "Preset step",
            "messages": [], "duration_s": 5, "play_count": 1,
            "then_actions": [{"type": "stop"}],
        }],
    }
    state_path = root / "installation.json"
    show_path = shows / "opening.json"
    state_path.write_text(json.dumps(state))
    show_path.write_text(json.dumps(show))
    return state_path, show_path, root / "patches", assets


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-show-presets-") as temporary:
        state_path, show_path, patches, assets = make_fixture(temporary)
        http_port = free_port(socket.SOCK_STREAM)
        listen_port = free_port(socket.SOCK_DGRAM)
        send_port = free_port(socket.SOCK_DGRAM)
        base_url = f"http://127.0.0.1:{http_port}"
        log_path = Path(temporary) / "server.log"
        log = log_path.open("w", encoding="utf-8")
        server = None
        try:
            server = subprocess.Popen([
                sys.executable, str(ROOT / "dashboard" / "server.py"),
                "--host", "127.0.0.1", "--port", str(http_port),
                "--listen-port", str(listen_port), "--send-port", str(send_port),
                "--osc-target", "127.0.0.1",
                "--state-file", str(state_path),
                "--assets-dir", str(assets), "--patches-dir", str(patches),
                "--public-url", base_url,
            ], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
            wait_http(base_url, server)

            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page(viewport={"width": 1440, "height": 1100})
                page.set_default_timeout(15000)
                errors = []
                dialogs = []
                page.on("pageerror", lambda error: errors.append(str(error)))

                def accept_dialog(dialog):
                    dialogs.append(dialog.message)
                    dialog.accept()

                page.on("dialog", accept_dialog)
                page.goto(base_url + "#show")
                page.wait_for_selector("#ws-status.online")
                page.wait_for_selector('[data-show-step-row="11111111"]')

                # Author a reference through the real Show inspector.
                page.locator('[data-show-step-row="11111111"]').click()
                page.click("#show-add-message")
                page.wait_for_selector("#show-message-mode")
                page.select_option("#show-message-mode", "preset")
                page.wait_for_selector("#show-preset-picker")
                page.fill("#show-preset-duration", "250")
                page.locator("#show-preset-duration").press("Tab")
                page.wait_for_function(
                    "() => document.querySelector('.show-message-pill')"
                    "?.classList.contains('show-pill-driven')")
                authored = json.loads(show_path.read_text())["items"][0]["messages"][0]
                check("the editor authors a preset reference with both fingerprints",
                      authored["kind"] == "reference"
                      and authored["address"] == "/preset/alpha/Dawn"
                      and authored["reference"]["content"]["name"] == "alpha"
                      and len(authored["reference"]["content"]["fingerprint"]) == 64
                      and authored["reference"]["schema"].startswith("sha256:")
                      and authored["args"][0]["value"] == 250,
                      repr(authored))
                pill = page.locator(".show-message-pill")
                pill_class = pill.get_attribute("class") or ""
                check("the timed preset pill is PRE with modulation ink",
                      "PRE" in pill.inner_text()
                      and "show-pill-driven" in pill_class, pill_class)

                # Playback must show only expanded parameter sends in Monitor.
                page.locator('[data-show-step-row="11111111"] '
                             '[data-show-action="step_start"]').click()
                page.click('[data-monitor-tab="out"]')
                page.wait_for_function(
                    "() => document.querySelector('[data-console=\"out\"] "
                    "[data-console-log]')?.textContent.includes('/all/p/gain')")
                outgoing = page.locator(
                    '[data-console="out"] [data-console-log]').inner_text()
                check("Monitor shows expanded sends and never the pseudo-address",
                      "/all/p/gain" in outgoing and "/all/p/gate" in outgoing
                      and "/preset/" not in outgoing, repr(outgoing))

                # Leave one target without provenance, then capture from the
                # Control iframe. The confirmation states the omission first.
                page.evaluate(
                    "() => ws.send('apply_preset',"
                    " {scope:'seat', id:3, patch:'alpha', name:null})")
                page.wait_for_function(
                    "() => !installation.seats['3'].applied_preset")
                page.click("#tab-button-control")
                frame = page.frame_locator("#dashboard-live-view")
                frame.locator("[data-capture-show-step]").wait_for()
                frame.locator("[data-capture-show-step]").click()
                page.wait_for_function(
                    "() => document.querySelector('#tab-button-control')"
                    "?.getAttribute('aria-selected') === 'true'")
                deadline = time.monotonic() + 8
                while len(dialogs) < 1 and time.monotonic() < deadline:
                    page.wait_for_timeout(50)
                check("capture states applied and omitted target counts before commit",
                      any("2 of 3 targets have a preset applied"
                          in message and "other 1 will not be captured"
                          in message for message in dialogs),
                      repr(dialogs))
                page.wait_for_function(
                    "() => installation.current_show === 'opening'")
                deadline = time.monotonic() + 8
                captured = None
                while time.monotonic() < deadline:
                    document = json.loads(show_path.read_text())
                    if len(document["items"]) == 2:
                        captured = document["items"][1]
                        break
                    time.sleep(.1)
                check("capture appends one portable preset step",
                      captured is not None
                      and len(captured["messages"]) == 1
                      and captured["messages"][0]["target"] == ["group:Front"]
                      and captured["messages"][0]["address"]
                      == "/preset/alpha/Dawn",
                      repr(captured))
                check("browser emitted no page errors", not errors, repr(errors))
                browser.close()
        finally:
            stop(server)
            log.close()

        if FAILURES:
            print("\nserver log tail:\n"
                  + log_path.read_text(encoding="utf-8")[-5000:])
        print(f"\n{len(FAILURES)} failure(s)")
        return 1 if FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(main())
