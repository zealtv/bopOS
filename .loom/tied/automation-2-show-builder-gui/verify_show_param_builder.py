#!/usr/bin/env python3
"""Real Dashboard + simfleet verification for the Show param automation builder."""

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


def wait_for(predicate, timeout=6):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(.1)
    return False


def make_fixture(root):
    root = Path(root)
    patches = root / "patches"
    assets = root / "assets"
    state_dir = root / "fleet-state"
    shows = root / "shows"
    patch = patches / "automation"
    patch.mkdir(parents=True)
    assets.mkdir()
    state_dir.mkdir()
    shows.mkdir()
    (patch / "main.bin").write_bytes(b"show-param-builder")
    manifest = {
        "engine": "test", "entrypoint": "main.bin", "caps": [], "slots": [],
        "params": [
            {"name": "gain", "type": "f", "min": 0, "max": 1,
             "default": .25, "facilitator": True},
            {"name": "voices", "type": "i", "min": 0, "max": 8,
             "default": 2, "facilitator": True},
            # The manifest validator only allows numeric defaults, so the
            # string declaration carries none.
            {"name": "label", "type": "s", "facilitator": True},
        ],
        "cues": [],
    }
    manifest_path = patch / "bopos.patch.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    state = {
        "schema": 1, "name": "Param builder verifier",
        "current_show": "automation", "params_patch": "automation",
        "fleet_patch": {"name": "automation", "fingerprint": "a" * 64,
                        "staged_at": time.time(), "previous": None},
        "seats": {"0": {"id": 0, "name": "Zero", "positions": [[1, 1]],
                          "groups": [], "bound": None, "patch": "automation",
                          "params": {}}},
        "groups": {}, "next_group_id": 0,
    }
    messages = []
    for uid, alias in [
            ("aaaa0001", "value"), ("aaaa0002", "single fade"),
            ("aaaa0003", "multi fade"), ("aaaa0004", "loop"),
            ("aaaa0005", "lfo"), ("aaaa0006", "stop"),
            ("aaaa0007", "string"), ("aaaa0008", "invalid")]:
        messages.append({"uid": uid, "alias": alias, "address": "/p/gain",
                         "args": [{"type": "f", "value": .25}],
                         "target": ["all"]})
    show = {
        "schema": 1, "name": "automation", "items": [{
            "kind": "step", "uid": "11111111", "alias": "generators",
            "messages": messages, "duration_s": .4, "play_count": 1,
            "then_actions": [{"type": "stop"}],
        }],
    }
    state_path = root / "installation.json"
    show_path = shows / "automation.json"
    state_path.write_text(json.dumps(state), encoding="utf-8")
    show_path.write_text(json.dumps(show, indent=2) + "\n", encoding="utf-8")
    return patches, assets, state_dir, manifest_path, state_path, show_path


def saved_messages(show_path):
    document = json.loads(show_path.read_text(encoding="utf-8"))
    return {message["uid"]: message for message in document["items"][0]["messages"]}


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-show-param-builder-") as root:
        patches, assets, state_dir, manifest_path, state_path, show_path = make_fixture(root)
        http_port = free_port(socket.SOCK_STREAM)
        listen_port = free_port(socket.SOCK_DGRAM)
        send_port = free_port(socket.SOCK_DGRAM)
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
                page = browser.new_page(viewport={"width": 1180, "height": 1000})
                browser_errors = []
                page.on("pageerror", lambda error: browser_errors.append(str(error)))
                page.on("console", lambda message: browser_errors.append(message.text)
                        if message.type == "error" else None)
                page.goto(base_url)
                page.wait_for_selector("#ws-status.online")
                page.click("#tab-button-show")
                page.wait_for_selector('[data-show-step-row="11111111"]')

                def focus(uid):
                    page.locator(f'[data-show-message-focus="{uid}"]').click()
                    page.wait_for_selector(f'[data-show-message-editor="{uid}"]')

                def blur(selector):
                    page.locator(selector).press("Tab")

                def expect_args(uid, expected, label):
                    ok = wait_for(lambda: saved_messages(show_path)[uid]["args"] == expected)
                    actual = saved_messages(show_path)[uid]["args"]
                    check(label, ok, repr(actual))
                    return actual

                # Value.
                focus("aaaa0001")
                page.fill("#show-param-value", "0.375")
                blur("#show-param-value")
                expect_args("aaaa0001", [{"type": "f", "value": .375}],
                            "value emits one declaration-typed arg")

                # Single fade with explicit start.
                focus("aaaa0002")
                page.select_option("#show-param-generator", "fade")
                page.fill("[data-param-segment-value]", "0.8")
                blur("[data-param-segment-value]")
                page.fill("[data-param-segment-duration]", "1.5")
                blur("[data-param-segment-duration]")
                page.select_option("[data-param-segment-unit]", "m")
                page.fill("[data-param-from]", "0.1")
                blur("[data-param-from]")
                expect_args("aaaa0002", [
                    {"type": "f", "value": .1}, {"type": "f", "value": .8},
                    {"type": "s", "value": "1.5m"}],
                    "single fade emits explicit start and suffixed duration")

                # Multi-segment fade clears the explicit-start form.
                focus("aaaa0003")
                page.select_option("#show-param-generator", "fade")
                page.locator("[data-add-param-segment]").click()
                rows = page.locator("[data-param-segment]")
                rows.nth(0).locator("[data-param-segment-value]").fill("0.7")
                rows.nth(0).locator("[data-param-segment-duration]").fill("2")
                rows.nth(0).locator("[data-param-segment-unit]").select_option("s")
                rows.nth(1).locator("[data-param-segment-value]").fill("0.2")
                rows.nth(1).locator("[data-param-segment-duration]").fill("500")
                rows.nth(1).locator("[data-param-segment-unit]").select_option("ms")
                expect_args("aaaa0003", [
                    {"type": "f", "value": .7}, {"type": "s", "value": "2s"},
                    {"type": "f", "value": .2}, {"type": "s", "value": "500ms"}],
                    "multi fade emits destination/duration pairs without from")
                check("multi fade hides explicit start", page.locator("[data-param-from]").count() == 0)

                # Loop and canonical short curve.
                focus("aaaa0004")
                page.select_option("#show-param-generator", "loop")
                rows = page.locator("[data-param-segment]")
                rows.nth(0).locator("[data-param-segment-value]").fill("0.2")
                rows.nth(0).locator("[data-param-segment-duration]").fill("2")
                rows.nth(0).locator("[data-param-segment-unit]").select_option("s")
                rows.nth(1).locator("[data-param-segment-value]").fill("0.8")
                rows.nth(1).locator("[data-param-segment-duration]").fill("500")
                rows.nth(1).locator("[data-param-segment-unit]").select_option("ms")
                page.fill("[data-param-curve]", "1.5")
                blur("[data-param-curve]")
                loop_args = [
                    {"type": "s", "value": "loop"},
                    {"type": "f", "value": .2}, {"type": "s", "value": "2s"},
                    {"type": "f", "value": .8}, {"type": "s", "value": "500ms"},
                    {"type": "s", "value": "c:1.5"},
                ]
                expect_args("aaaa0004", loop_args, "loop emits canonical keyword and c: option")

                # Integer LFO and canonical p:/f/c: ordering.
                focus("aaaa0005")
                page.select_option("#show-param-picker", "voices")
                page.wait_for_function(
                    "() => document.querySelector('#show-param-picker')?.value === 'voices'")
                page.select_option("#show-param-generator", "lfo")
                page.select_option('[data-param-lfo="shape"]', "tri")
                page.fill('[data-param-lfo="min"]', "1.9")
                blur('[data-param-lfo="min"]')
                page.fill('[data-param-lfo="max"]', "7.8")
                blur('[data-param-lfo="max"]')
                page.fill('[data-param-lfo="period"]', "4.5")
                blur('[data-param-lfo="period"]')
                page.select_option('[data-param-lfo="period-unit"]', "s")
                page.fill('[data-param-lfo="phase"]', "0.25")
                blur('[data-param-lfo="phase"]')
                page.check('[data-param-lfo="free"]')
                page.fill('[data-param-lfo="curve"]', "-1.5")
                blur('[data-param-lfo="curve"]')
                lfo_args = [
                    {"type": "s", "value": "lfo"}, {"type": "s", "value": "tri"},
                    {"type": "i", "value": 1}, {"type": "i", "value": 7},
                    {"type": "s", "value": "4.5s"},
                    {"type": "s", "value": "p:0.25"},
                    {"type": "s", "value": "f"},
                    {"type": "s", "value": "c:-1.5"},
                ]
                expect_args("aaaa0005", lfo_args,
                            "integer LFO emits typed bounds and ordered short options")

                # Stop.
                focus("aaaa0006")
                page.select_option("#show-param-generator", "stop")
                expect_args("aaaa0006", [{"type": "s", "value": "stop"}],
                            "stop emits one strict string arg")

                # String declarations remain constant-only.
                focus("aaaa0007")
                page.select_option("#show-param-picker", "label")
                page.wait_for_function(
                    "() => document.querySelector('#show-param-picker')?.value === 'label'"
                    " && !document.querySelector('#show-param-generator')")
                check("string param has no generator select",
                      page.locator("#show-param-generator").count() == 0)
                page.fill("#show-param-value", "hello")
                blur("#show-param-value")
                expect_args("aaaa0007", [{"type": "s", "value": "hello"}],
                            "string param stays constant-only")

                # Playing sends the canonical message args unchanged.
                page.locator('[data-console="out"] summary').click()
                page.locator('[data-console="out"] [data-console-clear]').click()
                page.locator('[data-show-step-row="11111111"] [data-show-action="step_start"]').click()
                outgoing_forms = [
                    "/all/p/gain  0.375", "/all/p/gain  0.1 0.8 1.5m",
                    "/all/p/gain  0.7 2s 0.2 500ms",
                    "/all/p/gain  loop 0.2 2s 0.8 500ms c:1.5",
                    "/all/p/voices  lfo tri 1 7 4.5s p:0.25 f c:-1.5",
                    "/all/p/gain  stop", "/all/p/label  hello",
                ]
                for form in outgoing_forms:
                    page.wait_for_function(
                        "needle => document.querySelector('[data-console=\"out\"] [data-console-log]')?.innerText.includes(needle)",
                        arg=form)
                check("step playback forwards every canonical form to outgoing OSC", True)

                # Reload/refocus must infer fields without rewriting any args.
                before_reload = {uid: message["args"] for uid, message in saved_messages(show_path).items()}
                page.reload()
                page.wait_for_selector("#ws-status.online")
                page.click("#tab-button-show")
                page.wait_for_selector('[data-show-step-row="11111111"]')
                for uid, mode in [("aaaa0001", "value"), ("aaaa0002", "fade"),
                                  ("aaaa0003", "fade"), ("aaaa0004", "loop"),
                                  ("aaaa0005", "lfo"), ("aaaa0006", "stop")]:
                    focus(uid)
                    check(f"{mode} repopulates after reload",
                          page.locator("#show-param-generator").input_value() == mode)
                check("round-trip keeps the exact persisted args",
                      all(saved_messages(show_path)[uid]["args"] == args
                          for uid, args in before_reload.items()))
                focus("aaaa0001")
                check("value field repopulates",
                      page.locator("#show-param-value").input_value() == "0.375")
                focus("aaaa0002")
                check("explicit fade fields repopulate",
                      page.locator("[data-param-from]").input_value() == "0.1"
                      and page.locator("[data-param-segment-value]").input_value() == "0.8"
                      and page.locator("[data-param-segment-duration]").input_value() == "1.5"
                      and page.locator("[data-param-segment-unit]").input_value() == "m")
                focus("aaaa0003")
                check("multi-fade rows repopulate without from",
                      page.locator("[data-param-segment]").count() == 2
                      and page.locator("[data-param-from]").count() == 0)
                focus("aaaa0004")
                check("loop curve repopulates",
                      page.locator("[data-param-curve]").input_value() == "1.5")
                focus("aaaa0005")
                check("LFO fields repopulate",
                      page.locator('[data-param-lfo="shape"]').input_value() == "tri"
                      and page.locator('[data-param-lfo="period"]').input_value() == "4.5"
                      and page.locator('[data-param-lfo="period-unit"]').input_value() == "s"
                      and page.locator('[data-param-lfo="free"]').is_checked())

                # Invalid direct-model injection produces raw fallback untouched.
                invalid_args = [
                    {"type": "s", "value": "lfo"},
                    {"type": "s", "value": "sine"},
                    {"type": "f", "value": 0},
                ]
                page.evaluate(
                    "payload => ws.send('update_message', payload)",
                    arg={"uid": "aaaa0008", "address": "/p/gain", "args": invalid_args})
                focus("aaaa0008")
                page.wait_for_selector("[data-param-raw-fallback]")
                check("invalid automation shows labelled raw fallback",
                      "unrecognised automation form" in
                      page.locator("[data-param-raw-fallback]").inner_text().lower())
                check("invalid args survive fallback focus unchanged",
                      saved_messages(show_path)["aaaa0008"]["args"] == invalid_args)

                # One-row loop is an invalid editor draft and must not emit.
                focus("aaaa0004")
                loop_before = saved_messages(show_path)["aaaa0004"]["args"]
                page.locator("[data-param-segment]").nth(1).locator(
                    "[data-remove-param-segment]").click()
                check("one-row loop shows its inline hint",
                      page.locator(".show-param-loop-hint").is_visible()
                      and "at least two" in page.locator(".show-param-loop-hint").inner_text())
                time.sleep(.3)
                check("one-row loop refuses to update args",
                      saved_messages(show_path)["aaaa0004"]["args"] == loop_before)

                check("browser emitted no console errors", not browser_errors,
                      repr(browser_errors))
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
    print("\nAll Show param builder checks passed.")


if __name__ == "__main__":
    main()
