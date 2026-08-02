#!/usr/bin/env python3
"""Throwaway repro for Bob's two Control-tab column reports (2026-08-02):

  A. a column with several targets renders N cards and cannot be scrolled
     to reach cards 2..N;
  B. selecting a preset in one column appears to affect every column.

Launches the real dashboard + simfleet on free ports, builds three groups and
six seats, and MEASURES rather than asserts.  Not a guard; scratch only.
"""

import json
import os
import random
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

from playwright.sync_api import sync_playwright

sys.dont_write_bytecode = True

# Locate the repository by MARKER, never by a fixed number of `..` hops: a
# stitch's depth changes when its goal is archived (CLAUDE.md, Records).
HERE = os.path.realpath(os.path.dirname(__file__))
REPO = HERE
while not os.path.isfile(os.path.join(REPO, "tools", "simfleet.py")):
    parent = os.path.dirname(REPO)
    if parent == REPO:
        raise SystemExit("cannot locate bopOS repository")
    REPO = parent

RESERVED = set()
SHOT_DIR = HERE


def free_port(kind):
    for _ in range(256):
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
    raise RuntimeError("no port")


def wait_http(url, process):
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("dashboard exited")
        try:
            urllib.request.urlopen(url, timeout=.5).close()
            return
        except OSError:
            time.sleep(.1)
    raise RuntimeError("no HTTP")


def make_fixture(root):
    patches = os.path.join(root, "patches")
    assets = os.path.join(root, "assets")
    patch = os.path.join(patches, "alpha")
    os.makedirs(patch)
    os.makedirs(assets)
    with open(os.path.join(patch, "main.bin"), "wb") as target:
        target.write(b"column-repro")
    params = [
        {"name": f"p{n}", "kind": "float", "min": 0, "max": 1,
         "default": .2, "dashboard": True} for n in range(8)
    ]
    with open(os.path.join(patch, "bopos.patch.json"), "w",
              encoding="utf-8") as target:
        json.dump({"engine": "test", "entrypoint": "main.bin",
                   "params": params,
                   "events": [{"name": "go", "arity": 0, "dashboard": True}],
                   "caps": [], "slots": []}, target)

    uids = [f"02:53:49:4d:00:0{n}" for n in range(1, 7)]

    def seat(seat_id, name, uid, groups):
        return {"id": seat_id, "name": name, "positions": [[seat_id, 1]],
                "groups": groups, "bound": uid, "patch": "alpha",
                "params": {f"p{n}": .2 for n in range(8)}}

    state = {
        "schema": 1, "name": "Column repro",
        "fleet_patch": {"name": "alpha", "fingerprint": "a" * 64,
                        "staged_at": time.time(), "previous": None},
        "params_patch": "alpha",
        "facilitator_commands": ["restart-engine", "reboot"],
        "groups": {"0": {"id": 0, "name": "Front"},
                   "1": {"id": 1, "name": "Back"},
                   "2": {"id": 2, "name": "Wide"}},
        "seats": {str(n): seat(n, f"Seat {n}", uids[n - 1],
                               [0] if n <= 2 else [1] if n <= 4 else [2])
                  for n in range(1, 7)},
    }
    path = os.path.join(root, "installation.json")
    with open(path, "w", encoding="utf-8") as target:
        json.dump(state, target)
    return path, patches, assets


def open_picker(column):
    if column.locator(".target-picker[open]").count() == 0:
        column.locator(".target-picker > summary").click()
    column.locator(".target-picker[open]").wait_for()


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-col-repro-") as temp:
        state_path, patches, assets = make_fixture(temp)
        http_port = free_port(socket.SOCK_STREAM)
        listen_port = free_port(socket.SOCK_DGRAM)
        send_port = free_port(socket.SOCK_DGRAM)
        base = f"http://127.0.0.1:{http_port}"
        logs = open(os.path.join(temp, "server.log"), "w", encoding="utf-8")
        flog = open(os.path.join(temp, "fleet.log"), "w", encoding="utf-8")
        server = subprocess.Popen([
            sys.executable, os.path.join(REPO, "dashboard", "server.py"),
            "--host", "127.0.0.1", "--port", str(http_port),
            "--listen-port", str(listen_port), "--send-port", str(send_port),
            "--osc-target", "127.0.0.1", "--state-file", state_path,
            "--assets-dir", assets, "--patches-dir", patches,
            "--public-url", base,
        ], cwd=REPO, stdout=logs, stderr=subprocess.STDOUT)
        fleet = None
        try:
            wait_http(base, server)
            fleet = subprocess.Popen([
                sys.executable, os.path.join(REPO, "tools", "simfleet.py"),
                "--devices", "6", "--target", "127.0.0.1",
                "--report-port", str(listen_port), "--cmd-port", str(send_port),
                "--hb-interval", "0.5", "--boot-secs", "0.2",
                "--patches-dir", patches, "--assets-dir", assets,
                "--manifest", os.path.join(patches, "alpha",
                                           "bopos.patch.json"),
            ], cwd=REPO, stdout=flog, stderr=subprocess.STDOUT)

            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page(viewport={"width": 1440, "height": 900})
                page.set_default_timeout(15000)
                page.on("dialog", lambda d: d.accept("repro-preset"))
                page.goto(base + "#control")
                page.wait_for_selector("#ws-status.online")
                page.wait_for_selector("#control-column-host .control-column")
                time.sleep(2)

                host = page.locator("#control-column-host")
                col = host.locator(".control-column").first

                # ---- A. one column, three targets -------------------------
                open_picker(col)
                print("chips:", col.locator(
                    ".target-picker [data-target-toggle]").evaluate_all(
                    "els => els.map(e => [e.dataset.targetToggle, e.textContent.trim()])"))
                for value in ("g0", "g1", "g2"):
                    chip = col.locator(
                        f".target-picker [data-target-toggle='{value}']")
                    if chip.count():
                        chip.first.click()
                        time.sleep(.3)
                time.sleep(1)
                col.locator(".target-picker > summary").click()
                time.sleep(1)

                print("== A: multi-target column geometry ==")
                print(json.dumps(page.evaluate("""() => {
                  const host = document.querySelector('#control-column-host');
                  const col = host.querySelector('.control-column');
                  const cards = col.querySelector('.control-column-cards');
                  const r = el => { const b = el.getBoundingClientRect();
                    return {top: Math.round(b.top), h: Math.round(b.height)}; };
                  return {
                    hostHeight: Math.round(host.getBoundingClientRect().height),
                    hostOverflowY: getComputedStyle(host).overflowY,
                    column: r(col),
                    columnMaxHeight: getComputedStyle(col).maxHeight,
                    columnScrollHeight: col.scrollHeight,
                    cards: r(cards),
                    cardsOverflowY: getComputedStyle(cards).overflowY,
                    cardsScrollHeight: cards.scrollHeight,
                    cardsClientHeight: cards.clientHeight,
                    cardsScrollable: cards.scrollHeight > cards.clientHeight + 1,
                    cardCount: cards.querySelectorAll('.live-card').length,
                    cardTops: [...cards.querySelectorAll('.live-card')].map(
                      el => Math.round(el.getBoundingClientRect().top)),
                    viewport: window.innerHeight,
                  };
                }"""), indent=2))

                page.screenshot(path=SHOT_DIR + "/A-multi-target.png")

                # back to a single group for part B
                open_picker(col)
                for value in ("g1", "g2"):
                    chip = col.locator(
                        f".target-picker [data-target-toggle='{value}']")
                    if chip.count():
                        chip.first.click()
                        time.sleep(.3)
                time.sleep(.5)
                col.locator(".target-picker > summary").click()

                # ---- B. two columns, two group targets, one preset --------
                page.locator(".control-tab-strip .add-column").click()
                time.sleep(1)
                col2 = host.locator(".control-column").nth(1)
                open_picker(col2)
                chip = col2.locator(".target-picker [data-target-toggle='g1']")
                if chip.count():
                    chip.first.click()
                time.sleep(.5)
                col2.locator(".target-picker > summary").click()
                time.sleep(1)

                def snapshot(tag):
                    print(f"-- {tag}")
                    print(json.dumps(page.evaluate("""() => {
                      return [...document.querySelectorAll(
                          '#control-column-host .control-column')].map(col => ({
                        target: col.getAttribute('aria-label'),
                        cards: [...col.querySelectorAll('.live-card')].map(card => ({
                          scope: card.dataset.liveScope,
                          id: card.dataset.liveId ?? null,
                          preset: card.querySelector('[data-preset-select]')
                            ?.selectedOptions?.[0]?.textContent ?? null,
                        })),
                      }));
                    }"""), indent=2))

                snapshot("before any preset")

                # author a preset from column 1 via new
                c1 = host.locator(".control-column").first
                auth = c1.locator(".live-preset-authoring > summary").first
                auth.click()
                time.sleep(.3)
                c1.locator("[data-preset-action='new']").first.click()
                time.sleep(.5)
                name_field = c1.locator(".live-preset-save-name, "
                                        "[data-preset-name]").first
                if name_field.count():
                    name_field.fill("Repro One")
                    time.sleep(.2)
                    commit = c1.locator("[data-preset-commit]").first
                    if commit.count():
                        commit.click()
                time.sleep(1.5)
                snapshot("after saving 'Repro One' from column 1")

                selects = page.locator(
                    "#control-column-host [data-preset-select]")
                print("preset selects on the tab:", selects.count())
                if selects.count():
                    first = selects.first
                    options = first.evaluate(
                        "el => [...el.options].map(o => o.value)")
                    print("column 1 options:", options)
                    pick = next((v for v in options if v), None)
                    if pick:
                        first.select_option(pick)
                        time.sleep(1.5)
                        snapshot(f"after applying '{pick}' in column 1")

                page.screenshot(path=SHOT_DIR + "/B-two-columns.png")
                browser.close()
        finally:
            for proc in (fleet, server):
                if proc and proc.poll() is None:
                    proc.terminate()
                    try:
                        proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        proc.kill()
            logs.close()
            flog.close()
            print("--- server log tail ---")
            with open(os.path.join(temp, "server.log"), encoding="utf-8") as f:
                print(f.read()[-2000:])


if __name__ == "__main__":
    main()
