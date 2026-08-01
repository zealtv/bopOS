#!/usr/bin/env python3
"""Shoot the REAL Control tab and COUNT its chrome, for D8's before/after.

D8's case is arithmetic — "six chrome controls per card, three cards per
mixture, three columns, fifty-four before a parameter" — and the stitch asks
for that to be visible rather than asserted. So this does two things at once:

  * screenshots the real tab (no composed shell, unlike `1-columns-design`'s
    `mockup.py`, which needed one because the N-column tab did not exist yet);
  * counts, per card, the chrome controls an operator can actually reach
    without opening anything: `Send all`, the preset `<select>`, `new`, `save`,
    `del`, `Device setup`. A control behind a closed disclosure is NOT counted,
    which is the whole point of a demotion.

Run it on the pre-change tree and again after, into different output labels:

    git stash push -- dashboard/static
    shoot.py <stitch-dir> before
    git stash pop
    shoot.py <stitch-dir> after

Modelled on `.loom/tied/1-columns-design/mockup.py` (fixture, ports, teardown).
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
LABEL = sys.argv[2] if len(sys.argv) > 2 else "after"
os.makedirs(OUT, exist_ok=True)
SEATS = 6
UIDS = [f"02:53:49:4d:00:0{i + 1}" for i in range(SEATS)]
RESERVED = set()

# The same three columns D8 costs: the aggregate, a group, and a mixture that
# renders three cards on its own.
COLUMNS = [
    {"id": "c0", "target": ["all"], "open": False},
    {"id": "c1", "target": ["g0"], "open": False},
    {"id": "c2", "target": ["g1", "4", "5"], "open": False},
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
    patch = os.path.join(root, "patches", "bonks-pd")
    os.makedirs(os.path.join(patch, "presets"))
    os.makedirs(os.path.join(root, "assets"))
    os.makedirs(os.path.join(root, "sim-state"))
    with open(os.path.join(patch, "main.bin"), "wb") as t:
        t.write(b"chrome-demotions")
    manifest = {
        "engine": "test", "entrypoint": "main.bin",
        "params": [
            {"name": "gain", "kind": "float", "min": 0, "max": 1,
             "default": .82, "dashboard": True},
            {"name": "filter", "kind": "float", "min": 0, "max": 1,
             "default": .35, "dashboard": True},
            {"name": "steps", "kind": "int", "min": 0, "max": 127,
             "default": 64, "dashboard": True},
            {"name": "size", "kind": "float", "min": 0, "max": 1,
             "default": .4, "path": ["reverb"], "dashboard": True},
        ],
        "events": [{"name": "strike", "arity": 2, "defaults": [64, 127],
                    "dashboard": True}],
        "caps": [], "slots": [],
    }
    with open(os.path.join(patch, "bopos.patch.json"), "w",
              encoding="utf-8") as t:
        json.dump(manifest, t, indent=2)

    groups_for = {0: [0], 1: [0], 2: [1], 3: [1], 4: [2], 5: [2]}
    names = ["Front L", "Front R", "Side L", "Side R", "Balc L", "Balc R"]
    seats = {}
    for i in range(SEATS):
        seats[str(i)] = {
            "id": i, "name": names[i], "positions": [[1 + i, 1 + i % 3]],
            "groups": groups_for[i], "bound": UIDS[i], "patch": "bonks-pd",
            "params": {"gain": .82, "filter": .35, "steps": 64,
                       "reverb/size": .4},
        }
    state = {
        "schema": 1, "name": "Chrome demotions", "params_patch": "bonks-pd",
        "fleet_patch": {"name": "bonks-pd", "fingerprint": "a" * 64,
                        "assets": []},
        # The per-device commands are what D8 takes off the column, so the
        # fixture has to declare them or "before" understates its own case.
        "facilitator_commands": ["restart-engine", "updatebopos", "reboot",
                                 "shutdown"],
        "seats": seats,
        "groups": {"0": {"id": 0, "name": "Left"},
                   "1": {"id": 1, "name": "Right"},
                   "2": {"id": 2, "name": "Balcony"}},
        "venue": {"width": 10, "depth": 8, "origin": [0, 0]},
    }
    path = os.path.join(root, "installation.json")
    with open(path, "w", encoding="utf-8") as t:
        json.dump(state, t, indent=2)
    return path


# What an operator can reach on a card without opening anything — the
# distinction a demotion makes and a plain `querySelectorAll` count would miss.
#
# `offsetParent` alone is NOT enough: Chromium suppresses a closed `<details>`'s
# contents with `content-visibility`, not `display:none`, so every demoted
# button still reports an offset parent and the first run of this script
# counted the demotion as having changed nothing. Ask the structural question
# instead, and keep the offset check for anything hidden some other way.
COUNT = """() => {
  const visible = element => !!element.offsetParent &&
    !element.closest('details:not([open]) > :not(summary),'
      + ' details:not([open]) > :not(summary) *');
  return [...document.querySelectorAll('#control-column-host .live-card')]
    .map(card => {
      const controls = [...card.querySelectorAll(
        '.send-all, .live-preset-select, .live-preset-action,'
        + ' .device-commands > summary, .live-card-overflow > summary,'
        + ' .live-preset-authoring > summary')];
      return {
        target: (card.dataset.liveScope || '?')
          + ':' + (card.dataset.liveId ?? 'all'),
        chrome: controls.filter(visible).length,
        hidden: controls.filter(control => !visible(control)).length,
      };
    });
}"""


def shoot(browser, base, theme, width):
    page = browser.new_page(viewport={"width": width, "height": 1000})
    page.set_default_timeout(20000)
    page.on("dialog", lambda dialog: dialog.dismiss())
    page.goto(base + "/#control")
    # Retried, because on the PRE-CHANGE tree this loses: a `device_update`
    # heartbeat that beats the initial `state` renders a restored column against
    # an empty venue, D5 prunes its target, and the prune PERSISTS — so the
    # stored layout is erased and the next load is unresolved too. That is what
    # this script found, and the fix is in `js/control-host.js`. Re-seeding the
    # layout each attempt is what clears the erased record.
    for attempt in range(6):
        page.evaluate(
            "([theme, columns]) => {"
            " localStorage.setItem('bopos-theme', theme);"
            " localStorage.setItem('bopos.control.columns',"
            "   JSON.stringify(columns)); }",
            [theme, COLUMNS])
        page.reload()
        page.wait_for_selector("#ws-status.online")
        page.wait_for_function(
            "n => Object.keys(installation.devices || {}).length === n",
            arg=SEATS)
        page.wait_for_selector("#control-column-host .live-card")
        time.sleep(1.5)
        if page.locator("#control-column-host .live-unresolved").count() == 0:
            break
        print(f"  (attempt {attempt + 1}: a column lost its target on restore)")
    cards = page.evaluate(COUNT)
    path = os.path.join(OUT, f"control-{LABEL}-{width}-{theme}.png")
    page.screenshot(path=path, full_page=False)
    page.close()
    return path, cards


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-demotions-") as temp:
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
                "--listen-port", str(listen_port),
                "--send-port", str(send_port),
                "--osc-target", "127.0.0.1", "--state-file", state_path,
                "--assets-dir", os.path.join(temp, "assets"),
                "--patches-dir", os.path.join(temp, "patches"),
                "--public-url", base,
            ], cwd=REPO, stdout=log, stderr=subprocess.STDOUT)
            wait_http(base, server)
            fleet = subprocess.Popen([
                sys.executable, os.path.join(REPO, "tools", "simfleet.py"),
                "--devices", str(SEATS), "--target", "127.0.0.1",
                "--report-port", str(listen_port), "--cmd-port",
                str(send_port), "--hb-interval", "0.5", "--boot-secs", "0.2",
                "--state-dir", os.path.join(temp, "sim-state"),
                "--manifest", os.path.join(temp, "patches", "bonks-pd",
                                           "bopos.patch.json"),
                "--patches-dir", os.path.join(temp, "patches"),
                "--assets-dir", os.path.join(temp, "assets"),
            ], cwd=REPO, stdout=log, stderr=subprocess.STDOUT)

            tally = {}
            with sync_playwright() as pw:
                browser = pw.chromium.launch(headless=True)
                for theme in ("dark", "light"):
                    path, cards = shoot(browser, base, theme, 1280)
                    print(os.path.basename(path))
                    if theme == "dark":
                        tally = cards
                browser.close()
            total = sum(card["chrome"] for card in tally)
            report = {"label": LABEL, "cards": tally, "total_chrome": total}
            with open(os.path.join(OUT, f"chrome-count-{LABEL}.json"), "w",
                      encoding="utf-8") as t:
                json.dump(report, t, indent=2)
            for card in tally:
                print(f"  {card['target']:>12}  reachable={card['chrome']}"
                      f"  behind a disclosure={card['hidden']}")
            print(f"  TOTAL reachable chrome across 3 columns: {total}")
        finally:
            for proc in (fleet, server):
                if proc and proc.poll() is None:
                    proc.terminate()
                    try:
                        proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        proc.kill()
            log.close()


if __name__ == "__main__":
    main()
