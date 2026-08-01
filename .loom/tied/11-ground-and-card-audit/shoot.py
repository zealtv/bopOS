#!/usr/bin/env python3
"""Evidence generator for the §12 ground-and-card audit.

Descends from `.loom/tied/02-token-promotion/shoot.py`, with two corrections
that stitch's own decisions recorded as defects:

  * the theme key is `bopos-theme` (what `theme.js` reads), not `bopos.theme`,
    and it is planted with `add_init_script` so the very first paint is already
    in the theme being shot — the old harness set the key after `goto`, so every
    "dark" app shot carried a light Control panel;
  * the Remote view is shot at both a tablet width and the desktop widths, since
    §12 names it the reference implementation and the audit has to record it.

Usage: shoot.py <output-dir>
"""
import json, os, random, socket, subprocess, sys, tempfile, time, urllib.request
from playwright.sync_api import sync_playwright

sys.dont_write_bytecode = True
# Locate the repo by marker, never by hop count: tie MOVES this directory.
REPO = os.path.realpath(os.path.dirname(__file__))
while not os.path.isfile(os.path.join(REPO, "tools", "simfleet.py")):
    _parent = os.path.dirname(REPO)
    if _parent == REPO:
        raise SystemExit("cannot locate bopOS repository")
    REPO = _parent
OUT = None  # set in main(); probe.py imports this module for its fixture.
UIDS = ["02:53:49:4d:00:01", "02:53:49:4d:00:02"]
RESERVED = set()


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
    raise RuntimeError("no free port")


def wait_http(base, proc):
    for _ in range(200):
        if proc.poll() is not None:
            raise SystemExit("server died")
        try:
            urllib.request.urlopen(base, timeout=.5).read()
            return
        except Exception:
            time.sleep(.1)
    raise SystemExit("server never came up")


def make_fixture(root):
    patches = os.path.join(root, "patches")
    patch = os.path.join(patches, "bonks-pd")
    os.makedirs(patch)
    os.makedirs(os.path.join(root, "assets"))
    os.makedirs(os.path.join(root, "sim-state"))
    with open(os.path.join(patch, "main.bin"), "wb") as t:
        t.write(b"ground-and-card-shoot")
    manifest = {
        "engine": "test", "entrypoint": "main.bin",
        "params": [
            {"name": "gain", "kind": "float", "min": 0, "max": 1,
             "default": .82, "dashboard": True},
            {"name": "filter", "kind": "float", "min": 0, "max": 1,
             "default": .35, "dashboard": True},
            {"name": "enable-fx", "kind": "toggle", "default": 1,
             "dashboard": True},
            {"name": "steps", "kind": "int", "min": 0, "max": 127,
             "default": 64, "dashboard": True},
            {"name": "mode", "kind": "enum",
             "options": ["mode-1", "mode-2", "mode-3"], "default": 0,
             "dashboard": True},
            {"name": "size", "kind": "float", "min": 0, "max": 1,
             "default": .4, "path": ["reverb"], "dashboard": True},
            {"name": "time", "kind": "float", "min": 0, "max": 1,
             "default": .3, "path": ["delay"], "dashboard": True},
        ],
        "events": [{"name": "strike", "arity": 2, "defaults": [64, 127],
                    "dashboard": True}],
        "caps": [], "slots": [],
    }
    with open(os.path.join(patch, "bopos.patch.json"), "w", encoding="utf-8") as t:
        json.dump(manifest, t, indent=2)

    def seat(i, name, uid, params):
        return {"id": i, "name": name, "positions": [[i + 1, 1]], "groups": [0],
                "bound": uid, "patch": "bonks-pd", "params": params}

    base = {"gain": .82, "filter": .35, "enable-fx": 1, "steps": 64,
            "mode": 0, "reverb/size": .4}
    a = dict(base, **{"delay/time": .3})
    b = dict(base, **{"delay/time": .7})
    state = {
        "schema": 1, "name": "Ground audit", "params_patch": "bonks-pd",
        "fleet_patch": {"name": "bonks-pd", "fingerprint": "a" * 64,
                        "assets": []},
        "seats": {"0": seat(0, "Front", UIDS[0], a),
                  "1": seat(1, "Back", UIDS[1], b)},
        "groups": {"0": {"id": 0, "name": "all seats"}},
        "venue": {"width": 8, "depth": 6, "origin": [0, 0]},
    }
    path = os.path.join(root, "installation.json")
    with open(path, "w", encoding="utf-8") as t:
        json.dump(state, t, indent=2)
    return path


def populate_show(page):
    if page.query_selector("#show-create-form"):
        page.fill("#show-create-name", "audit")
        page.click("#show-create-form button[type=submit]")
        page.wait_for_selector(".show-edit-bar")
    elif page.query_selector("#show-load-button"):
        page.click("#show-load-button")
        page.wait_for_selector(".show-edit-bar")
    for _ in range(2):
        page.click('[data-edit-bar-action="add-step"]')
        time.sleep(.4)
    row = page.query_selector(".show-step-row")
    if row:
        row.click()
    time.sleep(.8)


def new_page(browser, width, height, theme):
    page = browser.new_page(viewport={"width": width, "height": height})
    page.set_default_timeout(20000)
    page.on("dialog", lambda d: d.dismiss())
    # theme.js reads `bopos-theme` and applies it on first evaluation, so the
    # key has to exist BEFORE the document's scripts run.
    page.add_init_script(
        "try { localStorage.setItem('bopos-theme', %r); } catch (e) {}"
        % theme)
    return page


def main():
    global OUT
    OUT = os.path.realpath(sys.argv[1])
    os.makedirs(OUT, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="bopos-ground-") as temp:
        state_path = make_fixture(temp)
        http_port = free_port(socket.SOCK_STREAM)
        listen_port = free_port(socket.SOCK_DGRAM)
        send_port = free_port(socket.SOCK_DGRAM)
        base = f"http://127.0.0.1:{http_port}"
        log = open(os.path.join(temp, "log.txt"), "w", encoding="utf-8")
        server = fleet = None
        try:
            server = subprocess.Popen([
                sys.executable, os.path.join(REPO, "dashboard", "server.py"),
                "--host", "127.0.0.1", "--port", str(http_port),
                "--listen-port", str(listen_port), "--send-port", str(send_port),
                "--osc-target", "127.0.0.1", "--state-file", state_path,
                "--assets-dir", os.path.join(temp, "assets"),
                "--patches-dir", os.path.join(temp, "patches"),
                "--public-url", base,
            ], cwd=REPO, stdout=log, stderr=subprocess.STDOUT)
            wait_http(base, server)
            fleet = subprocess.Popen([
                sys.executable, os.path.join(REPO, "tools", "simfleet.py"),
                "--devices", "2", "--target", "127.0.0.1",
                "--report-port", str(listen_port), "--cmd-port", str(send_port),
                "--hb-interval", "0.5", "--boot-secs", "0.2",
                "--state-dir", os.path.join(temp, "sim-state"),
                "--manifest", os.path.join(temp, "patches", "bonks-pd",
                                           "bopos.patch.json"),
                "--patches-dir", os.path.join(temp, "patches"),
                "--assets-dir", os.path.join(temp, "assets"),
            ], cwd=REPO, stdout=log, stderr=subprocess.STDOUT)

            with sync_playwright() as pw:
                browser = pw.chromium.launch(headless=True)
                for theme in ("light", "dark"):
                    # Remote — §12's reference implementation.
                    page = new_page(browser, 900, 1250, theme)
                    page.goto(base + "/facilitator")
                    page.wait_for_selector('.live-card[data-live-scope="all"]')
                    page.wait_for_function(
                        "() => Object.keys(installation.devices||{}).length"
                        " === 2")
                    time.sleep(1.5)
                    page.screenshot(path=os.path.join(
                        OUT, f"remote-{theme}.png"), full_page=True)
                    page.close()

                    for width in (1280, 1680):
                        page = new_page(browser, width, 950, theme)
                        page.goto(base)
                        for tab in ("control", "show", "seats", "devices",
                                    "patches", "assets"):
                            page.click(f"#tab-button-{tab}")
                            time.sleep(2.5 if tab == "control" else 1.2)
                            if tab == "show":
                                populate_show(page)
                            if tab == "seats":
                                # Open a seat so the inspector is on screen.
                                row = page.query_selector(
                                    "#seat-roster .device-row small")
                                if row:
                                    row.click()
                                    time.sleep(.8)
                            page.screenshot(path=os.path.join(
                                OUT, f"app-{tab}-{width}-{theme}.png"))
                        page.click("[data-monitor-collapse]")
                        page.click('[data-monitor-tab="globals"]')
                        time.sleep(1.0)
                        page.screenshot(path=os.path.join(
                            OUT, f"app-monitor-{width}-{theme}.png"))
                        page.close()
                browser.close()
        finally:
            for p in (fleet, server):
                if p and p.poll() is None:
                    p.terminate()
                    try:
                        p.wait(timeout=5)
                    except Exception:
                        p.kill()
            log.close()
    print("shots in", OUT)
    for f in sorted(os.listdir(OUT)):
        print("  ", f)


if __name__ == "__main__":
    main()
