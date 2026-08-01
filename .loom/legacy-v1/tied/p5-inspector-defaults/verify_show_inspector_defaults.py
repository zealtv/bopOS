#!/usr/bin/env python3
"""Focused model + Playwright verification for Show inspector defaults."""

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
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from dashboard import show_model  # noqa: E402

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


def model_checks():
    legacy = {
        "schema": 1, "name": "legacy",
        "items": [{"kind": "step", "uid": "11111111", "alias": None,
                   "messages": [], "duration_s": 1, "play_count": 1,
                   "then_actions": []}],
    }
    cleaned = show_model.clean_show(legacy)
    check("legacy empty then-actions normalize to stop",
          cleaned["items"][0]["then_actions"] == [{"type": "stop"}])
    created, step, error = show_model.add_step(show_model.empty_show("new"))
    check("new model step starts with stop",
          error is None and step["then_actions"] == [{"type": "stop"}])
    updated, result, error = show_model.update_step(
        created, step["uid"], {"then_actions": []})
    check("empty step update preserves the invariant",
          error is None and result["then_actions"] == [{"type": "stop"}]
          and updated["items"][0]["then_actions"] == [{"type": "stop"}])


def make_fixture(root):
    root = Path(root)
    patches = root / "patches"
    assets = root / "assets"
    patch = patches / "alpha"
    shows = root / "shows"
    patch.mkdir(parents=True)
    assets.mkdir()
    shows.mkdir()
    (patch / "main.bin").write_bytes(b"show-inspector-defaults")
    (patch / "bopos.patch.json").write_text(json.dumps({
        "engine": "test", "entrypoint": "main.bin",
        "params": [{"name": "gain", "type": "f", "min": 0, "max": 1,
                    "default": .4, "facilitator": True}],
        "cues": [{"id": "snap", "label": "Snap"}],
        "caps": [], "slots": [],
    }), encoding="utf-8")
    state = {
        "schema": 1, "name": "Inspector defaults verifier",
        "current_show": "opening-set", "params_patch": "alpha",
        "fleet_patch": {"name": "alpha", "fingerprint": "a" * 64,
                        "staged_at": time.time(), "previous": None},
        "seats": {
            "3": {"id": 3, "name": "Three", "positions": [[1, 1]],
                  "groups": [1], "bound": None, "patch": "alpha", "params": {}},
            "7": {"id": 7, "name": "Seven", "positions": [[2, 1]],
                  "groups": [], "bound": None, "patch": "alpha", "params": {}},
        },
        "groups": {"1": {"id": 1, "name": "Main"}}, "next_group_id": 2,
    }
    show = {
        "schema": 1, "name": "opening-set", "items": [{
            "kind": "step", "uid": "11111111", "alias": "legacy",
            "messages": [
                {"uid": "aaaa0001", "alias": "multi", "address": "/p/gain",
                 "args": [{"type": "f", "value": .6}],
                 "target": ["3", "7", "g1"]},
                {"uid": "aaaa0002", "alias": "cue", "address": "/cue",
                 "args": [{"type": "s", "value": "snap"}], "target": ["all"]},
                {"uid": "aaaa0003", "alias": "point", "address": "/pt",
                 "args": [{"type": "i", "value": 0}, {"type": "f", "value": 0},
                          {"type": "f", "value": 0}, {"type": "f", "value": 1},
                          {"type": "i", "value": 1}], "target": ["all"]},
            ],
            "duration_s": 5, "play_count": 1, "then_actions": [],
        }],
    }
    state_path = root / "installation.json"
    show_path = shows / "opening-set.json"
    state_path.write_text(json.dumps(state), encoding="utf-8")
    show_path.write_text(json.dumps(show, indent=2) + "\n", encoding="utf-8")
    return patches, assets, state_path, show_path


def saved_step(show_path, uid):
    doc = json.loads(show_path.read_text(encoding="utf-8"))
    return next(item for item in doc["items"] if item.get("uid") == uid)


def browser_checks():
    with tempfile.TemporaryDirectory(prefix="bopos-inspector-defaults-") as root:
        patches, assets, state_path, show_path = make_fixture(root)
        http_port = free_port(socket.SOCK_STREAM)
        listen_port = free_port(socket.SOCK_DGRAM)
        send_port = free_port(socket.SOCK_DGRAM)
        base_url = f"http://127.0.0.1:{http_port}"
        log_path = Path(root, "server.log")
        log = log_path.open("w", encoding="utf-8")
        server = None
        try:
            server = subprocess.Popen([
                sys.executable, str(ROOT / "dashboard" / "server.py"),
                "--host", "127.0.0.1", "--port", str(http_port),
                "--listen-port", str(listen_port), "--send-port", str(send_port),
                "--osc-target", "127.0.0.1", "--state-file", str(state_path),
                "--assets-dir", str(assets), "--patches-dir", str(patches),
                "--public-url", base_url,
            ], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
            wait_http(base_url, server)
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page(viewport={"width": 900, "height": 900})
                page_errors = []
                page.on("pageerror", lambda error: page_errors.append(str(error)))
                page.goto(base_url)
                page.wait_for_selector("#ws-status.online")
                page.click("#tab-button-show")
                page.wait_for_selector('[data-show-step-row="11111111"]')

                page.locator('[data-show-step-row="11111111"] .show-step-alias').click()
                rows = page.locator(".show-then-row")
                check("legacy step renders exactly one then row", rows.count() == 1)
                check("legacy first row is stop and non-removable",
                      rows.locator('[data-then-type="0"]').input_value() == "stop"
                      and rows.locator("[data-remove-then]").count() == 0)
                page.click("[data-add-then-action]")
                page.wait_for_function(
                    "() => document.querySelectorAll('.show-then-row').length === 2")
                check("only the appended then row is removable",
                      page.locator('.show-then-row [data-remove-then="1"]').count() == 1
                      and page.locator('.show-then-row [data-remove-then="0"]').count() == 0)
                page.click('[data-remove-then="1"]')
                page.wait_for_function(
                    "() => document.querySelectorAll('.show-then-row').length === 1")
                check("removing row two returns to the fixed stop row",
                      page.locator('.show-then-row [data-then-type="0"]').input_value() == "stop"
                      and page.locator("[data-remove-then]").count() == 0)
                check("legacy normalization persists on the next edit",
                      wait_for(lambda: saved_step(show_path, "11111111")["then_actions"]
                               == [{"type": "stop"}]))

                page.locator('[data-show-message-focus="aaaa0001"]').click()
                target = page.locator(".show-target-picker")
                check("existing target defaults collapsed", not target.evaluate("node => node.open"))
                check("closed target summary matches wire preview",
                      "target" in target.locator("summary").inner_text().lower()
                      and "3+7+g1" in target.locator("summary").inner_text()
                      and "-> 3+7+g1" in page.locator("#show-wire-preview").inner_text())
                target.locator("summary").click()
                check("target disclosure expands", target.evaluate("node => node.open"))
                page.screenshot(path=str(HERE / "inspector-defaults.png"), full_page=False)
                page.click('[data-target-toggle="7"]')
                page.wait_for_function(
                    "() => document.querySelector('.show-target-terse')?.innerText === '3+g1'")
                check("target edit lands and open state survives broadcast render",
                      page.locator(".show-target-picker").evaluate("node => node.open")
                      and "-> 3+g1" in page.locator("#show-wire-preview").inner_text())
                page.locator(".show-target-picker summary").click()
                page.locator("#show-message-alias").fill("multi renamed")
                page.locator("#show-message-alias").press("Tab")
                page.wait_for_function(
                    "() => document.querySelector('#show-message-alias')?.value === 'multi renamed'")
                check("closed state survives an ordinary broadcast render",
                      not page.locator(".show-target-picker").evaluate("node => node.open"))

                page.locator('[data-item-add-end="step"]').click()
                page.wait_for_function(
                    "() => document.querySelectorAll('[data-show-step-row]').length === 2")
                new_uid = page.locator("[data-show-step-row].focused").get_attribute(
                    "data-show-step-row")
                check("new UI step begins with one fixed stop row",
                      page.locator(".show-then-row").count() == 1
                      and page.locator('[data-then-type="0"]').input_value() == "stop"
                      and page.locator("[data-remove-then]").count() == 0)
                page.click("#show-add-message")
                page.wait_for_selector(f'[data-show-step-row="{new_uid}"] .show-message-pill')
                check("fresh message target defaults expanded",
                      page.locator(".show-target-picker").evaluate("node => node.open"))

                page.locator(
                    f'[data-show-step-row="{new_uid}"] .show-message-pill').focus()
                page.keyboard.press("Control+c")
                page.locator(f'[data-show-step-row="{new_uid}"]').focus()
                page.keyboard.press("Control+v")
                page.wait_for_function(
                    "() => document.querySelectorAll('.show-message-pill').length === 5")
                check("pasted message target defaults collapsed",
                      not page.locator(".show-target-picker").evaluate("node => node.open"))

                for uid, mode in (("aaaa0002", "cue"), ("aaaa0003", "point")):
                    page.locator(f'[data-show-message-focus="{uid}"]').click()
                    picker = page.locator(".show-target-picker")
                    picker.locator("summary").click()
                    check(f"{mode} target picker remains greyed and disabled",
                          "show-disabled-field" in (picker.get_attribute("class") or "")
                          and picker.locator("[data-target-toggle]").evaluate_all(
                              "nodes => nodes.length > 0 && nodes.every(node => node.disabled)"))

                check("browser emitted no page errors", not page_errors, repr(page_errors))
                browser.close()
        finally:
            stop(server)
            log.close()
        if FAILURES:
            print("\nserver log tail:\n", log_path.read_text(encoding="utf-8")[-4000:])


def main():
    model_checks()
    browser_checks()
    print(f"\n{len(FAILURES)} failure(s)")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(main())
