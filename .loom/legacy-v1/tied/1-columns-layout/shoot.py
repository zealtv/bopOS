#!/usr/bin/env python3
"""Evidence shots of the REAL N-column Control tab (08/4/1-columns-layout).

Not a drawing. This boots the REAL dashboard + simfleet, renders the REAL
control surface once per column target, harvests the rendered markup, and
composes it into the proposed N-column shell with the shipping stylesheets
inlined. Every card, row, picker and preset row in the output is the component
that ships today; only the shell around them is new. That is the whole point —
a hand-drawn mockup of a design whose constraint is "the panel never reflows"
would beg the question it exists to answer.

Fixture, ports and provenance seeding are lifted verbatim from
`.loom/tied/1-columns-design/mockup.py`, so these shots are directly comparable
with the ratified `mockup-*.png` beside it. The difference is the whole point:
that script COMPOSED a proposed shell around harvested markup, and this one
drives the shipped tab.

Usage: shoot.py <output-dir>
"""
import json, os, random, socket, subprocess, sys, tempfile, time, urllib.request
from playwright.sync_api import sync_playwright

sys.dont_write_bytecode = True
# Repo by marker, never by hop count: tie MOVES this directory (CLAUDE.md).
REPO = os.path.realpath(os.path.dirname(__file__))
while not os.path.isfile(os.path.join(REPO, "tools", "simfleet.py")):
    _parent = os.path.dirname(REPO)
    if _parent == REPO:
        raise SystemExit("cannot locate bopOS repository")
    REPO = _parent
OUT = os.path.realpath(sys.argv[1])
os.makedirs(OUT, exist_ok=True)
STATIC = os.path.join(REPO, "dashboard", "static")
SEATS = 6
UIDS = [f"02:53:49:4d:00:0{i + 1}" for i in range(SEATS)]
RESERVED = set()

# The same five columns the mockup argued for, now a real stored layout:
# `bopos.control.columns` with MINTED ids (D9).
COLUMNS = [
    {"key": "all", "selection": ["all"], "title": "All Seats"},
    {"key": "left", "selection": ["g0"], "title": "Left"},
    {"key": "right", "selection": ["g1"], "title": "Right"},
    {"key": "mix", "selection": ["g2", "5"], "title": "Balcony + Seat 5"},
    {"key": "empty", "selection": ["g3"], "title": "Wings (no members)"},
]


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
    os.makedirs(os.path.join(patch, "presets"))
    os.makedirs(os.path.join(root, "assets"))
    os.makedirs(os.path.join(root, "sim-state"))
    with open(os.path.join(patch, "main.bin"), "wb") as t:
        t.write(b"columns-mockup")
    manifest = {
        "engine": "test", "entrypoint": "main.bin",
        "params": [
            {"name": "gain", "kind": "float", "min": 0, "max": 1,
             "default": .82, "dashboard": True},
            {"name": "filter", "kind": "float", "min": 0, "max": 1,
             "default": .35, "dashboard": True},
            {"name": "cutoff", "kind": "float", "min": 0, "max": 1,
             "default": .12, "dashboard": True},
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
            {"name": "wet", "kind": "float", "min": 0, "max": 1,
             "default": .25, "path": ["delay"], "dashboard": True},
        ],
        "events": [{"name": "strike", "arity": 2, "defaults": [64, 127],
                    "dashboard": True}],
        "caps": [], "slots": [],
    }
    with open(os.path.join(patch, "bopos.patch.json"), "w", encoding="utf-8") as t:
        json.dump(manifest, t, indent=2)

    # Presets are NOT hand-written here. `preset_store` accepts exactly
    # {bopos_preset, name, saved, schema, params} with a real schema
    # fingerprint (preset_store.py:123-146), so a fixture file is a forgery
    # waiting to be rejected. `seed_provenance` saves them through the store.

    # Three groups: Left (0,1), Right (2,3), Balcony (4,5). Seat 5 is also the
    # loose seat in the mixture column, which is what makes the overlap case
    # (the same seat visible in two columns at once) real in the shots.
    groups_for = {0: [0], 1: [0], 2: [1], 3: [1], 4: [2], 5: [2]}
    names = ["Front L", "Front R", "Side L", "Side R", "Balc L", "Balc R"]
    base = {"gain": .82, "filter": .35, "cutoff": .12, "enable-fx": 1,
            "steps": 64, "mode": 0, "reverb/size": .4}
    seats = {}
    for i in range(SEATS):
        params = dict(base)
        # Divergent delay values inside Right and Balcony so those group cards
        # render the ratified mixed hatch; Left stays unified for contrast.
        params["delay/time"] = .3 if i < 2 else (.3 + .12 * i)
        params["delay/wet"] = .25 if i < 2 else (.25 + .09 * i)
        seats[str(i)] = {"id": i, "name": names[i],
                         "positions": [[1 + i, 1 + i % 3]],
                         "groups": groups_for[i], "bound": UIDS[i],
                         "patch": "bonks-pd", "params": params}
    state = {
        "schema": 1, "name": "Columns mockup", "params_patch": "bonks-pd",
        "fleet_patch": {"name": "bonks-pd", "fingerprint": "a" * 64,
                        "assets": []},
        "seats": seats,
        # Wings has no members on purpose: it is the open question 2 case (a
        # column whose target resolves to no seats).
        "groups": {"0": {"id": 0, "name": "Left"},
                   "1": {"id": 1, "name": "Right"},
                   "2": {"id": 2, "name": "Balcony"},
                   "3": {"id": 3, "name": "Wings"}},
        "venue": {"width": 10, "depth": 8, "origin": [0, 0]},
    }
    path = os.path.join(root, "installation.json")
    with open(path, "w", encoding="utf-8") as t:
        json.dump(state, t, indent=2)
    return path


def seed_provenance(browser, base):
    """Apply two presets for real, so preset rows render real provenance.

    `applied_preset` is runtime state (41 F4: forgotten on restart), so it
    cannot be seeded from installation.json — it has to be applied through the
    same path an operator uses.
    """
    page = browser.new_page(viewport={"width": 520, "height": 900})
    page.set_default_timeout(20000)
    page.on("dialog", lambda d: d.dismiss())
    page.goto(base + "/facilitator")
    page.wait_for_selector(".live-card")
    page.wait_for_function(
        "n => Object.keys(installation.devices || {}).length === n", arg=SEATS)
    # `ws` is a top-level `const` in facilitator.js — a global lexical binding,
    # reachable by name from page.evaluate the same way `installation` is.
    # Save through the store (the only way to get a valid schema fingerprint),
    # then recall, which is what actually writes provenance.
    page.evaluate(
        "() => { ws.send('save_patch_preset',"
        " {scope:'group', id:0, patch:'bonks-pd', name:'dusk'});"
        " ws.send('save_patch_preset',"
        " {scope:'group', id:2, patch:'bonks-pd', name:'bloom'}); }")
    time.sleep(2.0)
    page.evaluate(
        "() => { ws.send('apply_preset',"
        " {scope:'group', id:0, patch:'bonks-pd', name:'dusk'});"
        " ws.send('apply_preset',"
        " {scope:'group', id:2, patch:'bonks-pd', name:'bloom'}); }")
    time.sleep(2.0)
    # Then move one Balcony parameter off its preset, so one column renders the
    # derived-dirty marker (41 F4) instead of every row reading clean.
    page.evaluate(
        "() => ws.send('set_live_param',"
        " {scope:'seat', id:4, name:'gain', value:0.41})")
    time.sleep(1.5)
    page.close()




def layout():
    """The stored layout, exactly as `control-host.js` writes it (D9)."""
    return [{"id": f"c{index}", "target": column["selection"], "open": False}
            for index, column in enumerate(COLUMNS)]


def shoot(browser, base, theme, width, keep, name):
    page = browser.new_page(viewport={"width": width, "height": 1000})
    page.set_default_timeout(20000)
    page.on("dialog", lambda dialog: dialog.dismiss())
    page.goto(base)
    page.evaluate(
        "([t, cols]) => { localStorage.setItem('bopos-theme', t);"
        " document.documentElement.dataset.theme = t;"
        " localStorage.setItem('bopos.control.columns', JSON.stringify(cols)); }",
        [theme, layout()[:keep]])
    page.goto(base)
    page.click("#tab-button-control")
    page.wait_for_selector("#control-column-host .control-column")
    page.wait_for_function(
        "n => Object.keys(installation.devices || {}).length === n", arg=SEATS)
    time.sleep(2.5)
    page.screenshot(path=os.path.join(OUT, f"{name}-{theme}.png"))
    page.close()


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-columns-") as temp:
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
                "--devices", str(SEATS), "--target", "127.0.0.1",
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
                seed_provenance(browser, base)
                for theme in ("dark", "light"):
                    shoot(browser, base, theme, 1280, 3, "control-1280")
                    shoot(browser, base, theme, 1680, 4, "control-1680")
                    shoot(browser, base, theme, 2560, 5, "control-2560")
                    shoot(browser, base, theme, 760, 4, "control-760")
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


main()
