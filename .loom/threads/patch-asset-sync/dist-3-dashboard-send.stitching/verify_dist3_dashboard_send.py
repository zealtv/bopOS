#!/usr/bin/env python3
"""Playwright verification for the dashboard patch/asset Send + Sync surface."""

import asyncio
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

sys.dont_write_bytecode = True

from playwright.sync_api import sync_playwright


HERE = os.path.realpath(os.path.dirname(__file__))
REPO = HERE
while not os.path.isfile(os.path.join(REPO, "tools", "simfleet.py")):
    parent = os.path.dirname(REPO)
    if parent == REPO:
        raise SystemExit("cannot locate the bopOS repo root")
    REPO = parent
sys.path.insert(0, os.path.join(REPO, "dashboard"))
from osc_bridge import OSCBridge

HTTP_PORT, OSC_LISTEN, OSC_COMMAND = 18107, 15577, 16687
BASE_URL = f"http://127.0.0.1:{HTTP_PORT}"
FAILURES = []


def check(label, condition, detail=""):
    print("[{}] {}{}".format("PASS" if condition else "FAIL", label,
                             " -- " + detail if detail and not condition else ""))
    if not condition:
        FAILURES.append(label)


def write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    mode = "wb" if isinstance(data, bytes) else "w"
    kwargs = {} if mode == "wb" else {"encoding": "utf-8"}
    with open(path, mode, **kwargs) as target:
        target.write(data)


def read_url(path):
    with urllib.request.urlopen(BASE_URL + path, timeout=5) as response:
        return response.status, response.read(), response.headers


def wait_log(page, path, text, timeout=8000):
    deadline = time.monotonic() + timeout / 1000
    while time.monotonic() < deadline:
        try:
            with open(path, encoding="utf-8") as source:
                value = source.read()
            if text in value:
                return value
        except OSError:
            pass
        page.wait_for_timeout(100)
    return ""


def row(page, kind, name):
    return page.locator(
        f'.distribution-item[data-kind="{kind}"][data-name="{name}"]')


def wait_status(page, kind, name, status, timeout=8000):
    page.wait_for_function(
        """([kind, name, status]) => {
          const item = [...document.querySelectorAll('.distribution-item')]
            .find(el => el.dataset.kind === kind && el.dataset.name === name);
          return item?.querySelector('.sync-status')?.innerText.trim() === status;
        }""", arg=[kind, name, status], timeout=timeout)


def request_retry_check():
    class State:
        devices = {"node": {"uid": "node", "id": 1, "ip": "10.0.0.1"}}

    class Sender:
        def __init__(self):
            self.packets = []

        def sendto(self, packet, destination):
            self.packets.append((packet, destination))

        def close(self):
            pass

    async def exercise():
        bridge = OSCBridge(State(), lambda *_args: None, 15579, 16689, "127.0.0.1")
        bridge.sender = Sender()
        bridge.request("node", "patches")
        bridge._expire_request("patches", "node")
        bridge.request("node", "patches")
        result = len(bridge.sender.packets) == 2 and list(bridge.pending["patches"]) == ["node"]
        bridge.close()
        return result

    return asyncio.run(exercise())


def main():
    check("lost patch query expires and can be retried", request_retry_check())
    with tempfile.TemporaryDirectory() as temp:
        assets = os.path.join(temp, "assets")
        patches = os.path.join(temp, "patches")
        nodes = os.path.join(temp, "nodes")
        os.makedirs(nodes)

        write(os.path.join(assets, "pack-a", "one.raw"), b"one")
        write(os.path.join(assets, "pack-a", "nested", "two.raw"), b"twice")
        patch_manifest = json.dumps({
            "engine": "test", "entrypoint": "main.bin",
            "params": [], "caps": [], "slots": [],
        }, separators=(",", ":"))
        for name, payload in (("default", b"active"), ("mirror-a", b"mirror")):
            write(os.path.join(patches, name, "main.bin"), payload)
            write(os.path.join(patches, name, "bopos.patch.json"), patch_manifest)

        state_file = os.path.join(temp, "installation.json")
        fleet_path = os.path.join(temp, "fleet.log")
        server_path = os.path.join(temp, "server.log")
        fleet_log = open(fleet_path, "w", encoding="utf-8")
        server_log = open(server_path, "w", encoding="utf-8")
        server = subprocess.Popen([
            sys.executable, os.path.join(REPO, "dashboard/server.py"),
            "--port", str(HTTP_PORT), "--listen-port", str(OSC_LISTEN),
            "--send-port", str(OSC_COMMAND), "--osc-target", "127.0.0.1",
            "--state-file", state_file, "--assets-dir", assets,
            "--patches-dir", patches, "--public-url", BASE_URL,
        ], cwd=REPO, stdout=server_log, stderr=subprocess.STDOUT)
        fleet = subprocess.Popen([
            sys.executable, os.path.join(REPO, "tools/simfleet.py"),
            "--devices", "2", "--state-dir", nodes, "--target", "127.0.0.1",
            "--report-port", str(OSC_LISTEN), "--cmd-port", str(OSC_COMMAND),
            "--hb-interval", "0.5", "--boot-secs", "1",
        ], cwd=REPO, stdout=fleet_log, stderr=subprocess.STDOUT)

        try:
            time.sleep(2)

            # Exercise the real FastAPI routes before driving the browser.
            status, body, _ = read_url("/patches/mirror-a/.manifest.json")
            manifest = json.loads(body)
            files = {item["path"]: item for item in manifest["files"]}
            expected_manifest = patch_manifest.encode()
            check("patch transfer manifest route", status == 200
                  and set(files) == {"bopos.patch.json", "main.bin"})
            check("patch manifest contains exact size and sha256",
                  files["main.bin"]["size"] == len(b"mirror")
                  and files["main.bin"]["sha256"] == hashlib.sha256(b"mirror").hexdigest()
                  and files["bopos.patch.json"]["sha256"]
                  == hashlib.sha256(expected_manifest).hexdigest(), repr(files))
            status, body, _ = read_url("/patches/mirror-a/main.bin")
            check("patch static bytes served", status == 200 and body == b"mirror")
            write(os.path.join(patches, "mirror-a", ".git", "config"), "secret")
            os.symlink(os.path.join(patches, "mirror-a", ".git", "config"),
                       os.path.join(patches, "mirror-a", "public-config"))
            try:
                read_url("/patches/mirror-a/.git/config")
                hidden_status = 200
            except urllib.error.HTTPError as error:
                hidden_status = error.code
            check("patch source-control internals are not served", hidden_status == 404,
                  str(hidden_status))
            try:
                read_url("/patches/mirror-a/public-config")
                symlink_status = 200
            except urllib.error.HTTPError as error:
                symlink_status = error.code
            check("patch symlink aliases are not served", symlink_status == 404,
                  str(symlink_status))
            status, body, _ = read_url("/assets/pack-a/.manifest.json")
            asset_manifest = json.loads(body)
            check("asset manifest retains nested forward paths", status == 200
                  and [item["path"] for item in asset_manifest["files"]]
                  == ["nested/two.raw", "one.raw"], repr(asset_manifest))
            try:
                read_url("/patches/missing/.manifest.json")
                missing_status = 200
            except urllib.error.HTTPError as error:
                missing_status = error.code
            check("missing patch manifest is 404", missing_status == 404,
                  str(missing_status))

            with sync_playwright() as playwright:
                browser = playwright.chromium.launch()
                page = browser.new_page(viewport={"width": 1400, "height": 1100})
                dialogs = []

                def handle_dialog(dialog):
                    dialogs.append({"type": dialog.type, "message": dialog.message})
                    dialog.accept("dist3-verify" if dialog.type == "prompt" else None)

                page.on("dialog", handle_dialog)
                page.goto(BASE_URL + "/")
                device_row = page.locator("#assigned .device-row").first
                device_row.wait_for(timeout=10000)
                device_row.click()
                page.wait_for_selector("#distribution", timeout=5000)
                page.wait_for_function(
                    "() => [...document.querySelectorAll('#patch-select option')]"
                    ".some(option => option.value === 'default')", timeout=5000)

                # Keep a history across detail re-renders so both progress phases
                # are proved rather than merely checking the terminal state.
                page.evaluate("""() => {
                  window.__dist3Statuses = [];
                  new MutationObserver(() => {
                    document.querySelectorAll('.distribution-item').forEach(item => {
                      const status = item.querySelector('.sync-status')?.innerText.trim();
                      const value = `${item.dataset.kind}:${item.dataset.name}:${status}`;
                      if (status && window.__dist3Statuses.at(-1) !== value)
                        window.__dist3Statuses.push(value);
                    });
                  }).observe(document.body, {subtree:true, childList:true, characterData:true});
                }""")

                options = page.locator("#patch-select option").all_inner_texts()
                check("patch dropdown populated from /os/patches",
                      any("default" in option for option in options), repr(options))
                check("typed patch input removed", page.locator("#patch-name").count() == 0)

                asset = row(page, "asset", "pack-a")
                patch = row(page, "patch", "mirror-a")
                check("asset catalog metadata renders",
                      "2 files · 8 B" in asset.inner_text()
                      and asset.locator("time[datetime]").count() == 1,
                      asset.inner_text())
                check("patch catalog metadata renders",
                      "2 files" in patch.inner_text()
                      and patch.locator("time[datetime]").count() == 1,
                      patch.inner_text())

                patch.locator("[data-send]").click()
                wait_status(page, "patch", "mirror-a", "in sync", timeout=8000)
                history = page.evaluate("window.__dist3Statuses")
                check("patch send shows queued then fetching then in sync",
                      "patch:mirror-a:queued" in history
                      and "patch:mirror-a:fetching" in history
                      and "patch:mirror-a:in sync" in history, repr(history))
                fetch_line = (f"fetch {BASE_URL}/patches/mirror-a/.manifest.json "
                              "patch:mirror-a")
                check("patch Send uses dashboard manifest URL and patch slot",
                      bool(wait_log(page, fleet_path, fetch_line)), fetch_line)

                # A changed host fingerprint makes the prior successful receipt stale.
                write(os.path.join(patches, "mirror-a", "main.bin"), b"mirror changed")
                page.click("#refresh-distribution")
                wait_status(page, "patch", "mirror-a", "stale", timeout=5000)
                check("changed host hash marks sent patch stale", True)
                row(page, "patch", "mirror-a").locator("[data-send]").click()
                wait_status(page, "patch", "mirror-a", "in sync", timeout=8000)

                asset.locator("[data-send]").click()
                wait_status(page, "asset", "pack-a", "in sync", timeout=8000)
                history = page.evaluate("window.__dist3Statuses")
                check("asset send consumes progress and terminal reply",
                      "asset:pack-a:queued" in history
                      and "asset:pack-a:fetching" in history
                      and "asset:pack-a:in sync" in history, repr(history))

                before_dialogs = len(dialogs)
                active = row(page, "patch", "default")
                active.locator("[data-send]").click()
                wait_status(page, "patch", "default", "in sync", timeout=8000)
                active_dialogs = dialogs[before_dialogs:]
                check("active patch Send is confirm-gated",
                      len(active_dialogs) == 1
                      and active_dialogs[0]["type"] == "confirm"
                      and "stop and restart" in active_dialogs[0]["message"].lower(),
                      repr(active_dialogs))

                # Sync all must iterate every current host directory. Compare log
                # deltas so earlier individual sends cannot satisfy the assertion.
                with open(fleet_path, encoding="utf-8") as source:
                    before_sync = source.read()
                page.click("#sync-all")
                expected_sync = {
                    f"fetch {BASE_URL}/patches/default/.manifest.json patch:default",
                    f"fetch {BASE_URL}/patches/mirror-a/.manifest.json patch:mirror-a",
                    f"fetch {BASE_URL}/assets/pack-a/.manifest.json pack-a",
                }
                deadline = time.monotonic() + 12
                sync_delta = ""
                while time.monotonic() < deadline:
                    with open(fleet_path, encoding="utf-8") as source:
                        sync_delta = source.read()[len(before_sync):]
                    if all(line in sync_delta for line in expected_sync):
                        break
                    page.wait_for_timeout(100)
                check("Sync all iterates every patch and asset exactly once",
                      all(sync_delta.count(line) == 1 for line in expected_sync),
                      sync_delta[-1600:])
                for kind, name in (("patch", "default"), ("patch", "mirror-a"),
                                   ("asset", "pack-a")):
                    wait_status(page, kind, name, "in sync", timeout=12000)

                # Add a Git patch whose name also exists on the host. The node list
                # drives both the dropdown glyph and the host-card Git guard.
                write(os.path.join(patches, "git-piece", "main.bin"), b"git")
                write(os.path.join(patches, "git-piece", "bopos.patch.json"), patch_manifest)
                page.click("#refresh-distribution")
                page.fill("#patch-user", "bopos")
                page.fill("#patch-repo", "git-piece")
                page.click("#patch-add")
                page.wait_for_function(
                    "() => [...document.querySelectorAll('#patch-select option')]"
                    ".some(option => option.value === 'git-piece' && option.innerText.includes('◆'))",
                    timeout=6000)
                git_row = row(page, "patch", "git-piece")
                check("Git patch is legible in dropdown and host catalog",
                      git_row.locator(".git-badge").count() == 1
                      and git_row.locator("[data-send]").is_disabled())
                check("Pull latest hidden for non-Git active patch",
                      page.locator("#patch-pull").count() == 0)

                # All-target mode must show both nodes and enforce Git-XOR per
                # target: selected node is Git-managed, the other remains eligible.
                page.check("#distribution-all")
                git_row = row(page, "patch", "git-piece")
                check("all-target status names each device",
                      git_row.locator(".device-sync").count() == 1
                      and "Git-managed" in git_row.locator(".device-sync").inner_text()
                      and "unknown" in git_row.locator(".device-sync").inner_text()
                      and " · " in git_row.locator(".device-sync").inner_text(),
                      git_row.inner_text())
                with open(fleet_path, encoding="utf-8") as source:
                    before_git_all = source.read()
                git_row.locator("[data-send]").click()
                page.wait_for_function(
                    """() => document.querySelector(
                      '.distribution-item[data-kind="patch"][data-name="git-piece"] .sync-status'
                    )?.innerText.trim() === '1/1 in sync'""", timeout=8000)
                with open(fleet_path, encoding="utf-8") as source:
                    git_all_delta = source.read()[len(before_git_all):]
                git_fetch = f"fetch {BASE_URL}/patches/git-piece/.manifest.json patch:git-piece"
                check("all-target Send skips Git-managed device",
                      git_all_delta.count(git_fetch) == 1, git_all_delta[-1000:])
                page.uncheck("#distribution-all")

                # Patch and asset deletion are both confirm-gated and hit v1.3 verbs.
                page.select_option("#patch-select", "mirror-a")
                before_dialogs = len(dialogs)
                page.click("#patch-drop")
                page.wait_for_function(
                    "() => ![...document.querySelectorAll('#patch-select option')]"
                    ".some(option => option.value === 'mirror-a')", timeout=5000)
                check("patch delete confirms and fires droppatch",
                      len(dialogs) == before_dialogs + 1
                      and "os/droppatch mirror-a" in wait_log(
                          page, fleet_path, "os/droppatch mirror-a"), repr(dialogs[-1:]))

                before_dialogs = len(dialogs)
                row(page, "asset", "pack-a").locator("[data-drop-asset]").click()
                check("asset delete confirms and fires dropassets",
                      len(dialogs) == before_dialogs + 1
                      and "os/dropassets pack-a" in wait_log(
                          page, fleet_path, "os/dropassets pack-a"), repr(dialogs[-1:]))

                before_dialogs = len(dialogs)
                page.click('[data-action="updatebopos"]')
                update_log = wait_log(page, fleet_path, "os/updatebopos", timeout=5000)
                check("Update bopOS is labelled and sends updatebopos",
                      page.locator('[data-action="updatebopos"]').text_content() == "Update bopOS"
                      and len(dialogs) == before_dialogs + 1
                      and "os/updatebopos" in update_log)

                body = page.locator("body").inner_text().lower()
                sources = ""
                for root, _dirs, names in os.walk(os.path.join(REPO, "dashboard")):
                    for name in names:
                        if name.endswith((".py", ".js", ".html")):
                            with open(os.path.join(root, name), encoding="utf-8") as source:
                                sources += source.read().lower()
                check("getsamples removed from dashboard UI and source",
                      "get samples" not in body and "getsamples" not in sources
                      and "get_samples" not in sources)

                page.screenshot(path=os.path.join(HERE, "dist3-dashboard-send.png"),
                                full_page=True)
                browser.close()
        finally:
            fleet.terminate()
            server.terminate()
            fleet.wait(timeout=5)
            server.wait(timeout=5)
            fleet_log.close()
            server_log.close()

    print()
    if FAILURES:
        print("FAILED:", ", ".join(FAILURES))
        return 1
    print("dist-3 dashboard Send + Sync checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
