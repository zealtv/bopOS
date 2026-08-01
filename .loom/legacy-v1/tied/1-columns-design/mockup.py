#!/usr/bin/env python3
"""Mockup generator for the N-column Control tab (08/1).

Not a drawing. This boots the REAL dashboard + simfleet, renders the REAL
control surface once per column target, harvests the rendered markup, and
composes it into the proposed N-column shell with the shipping stylesheets
inlined. Every card, row, picker and preset row in the output is the component
that ships today; only the shell around them is new. That is the whole point —
a hand-drawn mockup of a design whose constraint is "the panel never reflows"
would beg the question it exists to answer.

Modelled on .loom/tied/02-token-promotion/shoot.py (fixture, ports, teardown).

Usage: mockup.py <output-dir>   (the stitch dir itself — a subdirectory would
       look like a child stitch to loom.sh)
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

# The four columns the mockup argues for: the aggregate, two group columns, and
# one seat. Column 4 doubles as the mixture case (a group plus a loose seat).
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
    page.goto(base + "/facilitator?embedded=1")
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


def clean(picker_html):
    """Two edits to the harvested picker markup, both design statements.

    - The disclosure is forced CLOSED. Its terse state is the column's title
      row; a column that opens its picker on load spends a third of its height
      on a roster nobody asked for.
    - The per-column `Capture as Show step` button is REMOVED. It is exactly
      what the consult ruled against (one per column, differing only in a
      filter that barely filters); the tab-level action replaces it.
    """
    # `open` survives an innerHTML round trip as `open=""`, not ` open` — a
    # boolean attribute set by the parser serializes with an empty value.
    return (picker_html
            .replace(' open=""', "").replace(" open>", ">")
            .split('<button type="button" class="capture-show-step"')[0])


def harvest(browser, base, theme):
    """Render the real surface once per column target and keep its markup."""
    harvested = []
    for column in COLUMNS:
        page = browser.new_page(viewport={"width": 520, "height": 1400})
        page.set_default_timeout(20000)
        page.on("dialog", lambda d: d.dismiss())
        page.goto(base + "/facilitator?embedded=1")
        page.evaluate(
            "([t, sel]) => { localStorage.setItem('bopos.theme', t);"
            " localStorage.setItem('bopos.target.control', JSON.stringify(sel));"
            " localStorage.setItem('bopos.target.control.open', 'false'); }",
            [theme, column["selection"]])
        page.goto(base + "/facilitator?embedded=1")
        page.wait_for_selector(".live-card, #cards .empty")
        page.wait_for_function(
            "n => Object.keys(installation.devices || {}).length === n",
            arg=SEATS)
        time.sleep(1.2)
        harvested.append(dict(column, picker=clean(page.eval_on_selector(
            "#target-picker-host", "el => el.innerHTML")),
            cards=page.eval_on_selector("#cards", "el => el.innerHTML")))
        page.close()
    return harvested


def stylesheet():
    sheets = ["style.css", "param-generator.css", "control-panel.css",
              "value-box.css", "target-picker.css"]
    parts = []
    for name in sheets:
        with open(os.path.join(STATIC, "css", name), encoding="utf-8") as t:
            parts.append(f"/* ==== {name} ==== */\n" + t.read())
    return "\n".join(parts)


SHELL = """<!doctype html>
<html lang="en" data-theme="__THEME__">
<head><meta charset="utf-8"><title>Control tab — N columns (08/1 mockup)</title>
<style>__CSS__</style>
<style>
/* ---- the only NEW css in this file: the column shell -------------------
   Everything inside a column is shipping markup and shipping css.

   Except — and this is a FINDING, see decisions.md D6 — the card chrome
   itself. `.live-card`, `.live-card-head`, `.name`, `.dot`, `.send-all`,
   `.promoted-controls` and `.empty` are all declared in `css/facilitator.css`
   (lines 26-52), which `index.html` does not load. Today that is invisible
   because the Control tab is an iframe of `facilitator.html`. The moment the
   iframe goes, the parent document has no card chrome at all. So the block
   below is not mockup scaffolding — it is a preview of the stylesheet
   `3-iframe-retirement` has to write, at desktop metrics rather than the
   tablet-first 44px/19px facilitator values. */
body{margin:0;background:var(--bg);color:var(--text);
  font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:12px}
.mock-chrome{display:flex;align-items:center;gap:4px;padding:4px 16px;
  border-bottom:1px solid var(--line);background:var(--surface-bar)}
.mock-chrome button{flex:none;border-color:transparent;background:transparent;
  color:var(--dim);font-weight:650}
.mock-chrome button.on{border-color:var(--accent);background:var(--control);color:var(--text)}
.mock-chrome .spacer{margin-left:auto}
.mock-chrome .view-link{margin-left:auto;color:var(--dim)}

/* The tab strip: the tab's own chrome, carrying its two tab-scoped actions at
   the two furthest-apart points. `+ column` is quieter than `capture` on
   purpose (judgment §7: attention allows about three columns). */
.control-tab-strip{display:flex;align-items:center;gap:var(--gap);
  padding:5px 16px;border-bottom:1px solid var(--line);
  background:var(--surface-bar)}
.control-tab-strip button{min-height:var(--row-h);padding:var(--pad-control);
  border:1px solid var(--control-line);border-radius:var(--radius-momentary);
  background:var(--control);color:var(--text);font:inherit;text-transform:none;
  cursor:pointer}
.control-tab-strip .add-column{border-style:dashed;color:var(--dim);
  background:transparent}
.control-tab-strip .capture{margin-left:auto}
.control-tab-strip .capture b{font-weight:400;color:var(--dim);
  font-variant-numeric:tabular-nums}
.control-tab-strip .capture[disabled]{opacity:.55;cursor:default}

/* §12: the ground shows ONLY as the gutter between columns. The tab itself
   paints nothing and the 1400px cap is lifted — see decisions.md D1. */
.control-columns{display:flex;align-items:flex-start;gap:12px;
  padding:12px 16px;overflow-x:auto}
/* 342px = the 320px drawer face + 2×--pad-panel + 2×1px border. The column
   IS the card, so the panel's own padding is the column's (D1). */
.control-column{flex:0 0 342px;width:342px;
  display:grid;gap:var(--gap);align-content:start;
  background:var(--panel);border:1px solid var(--group-line);
  border-radius:var(--radius-panel);padding:var(--pad-panel)}
.control-column-head{display:flex;align-items:center;gap:4px;
  min-height:var(--row-h)}
.control-column-head .grip{color:var(--dim);cursor:grab;font-size:10px}
.control-column-head .target-picker-host{min-width:0;flex:1}
.control-column-head .close{width:var(--row-h);height:var(--row-h);flex:none;
  display:grid;place-items:center;padding:0;border:1px solid var(--control-line);
  border-radius:var(--radius-momentary);background:var(--control);color:var(--dim);
  font:inherit;cursor:pointer}
.control-column .cards{display:grid;gap:var(--gap)}

/* ---- card chrome (see the note above: this is 3-iframe-retirement's) ---- */
.control-column .live-card{min-width:0;display:grid;align-content:start;
  gap:var(--gap);background:transparent;border:0;padding:0;border-radius:0}
.control-column .cards > .live-card + .live-card{padding-top:var(--gap);
  border-top:1px solid var(--group-line)}
.control-column .live-card-head{min-height:var(--row-h);display:flex;
  align-items:center;gap:var(--gap)}
.control-column .live-card .name{min-width:0;flex:1;font-size:12px;
  font-weight:700;display:flex;align-items:baseline;gap:6px;overflow:hidden}
.control-column .live-card .name strong{overflow:hidden;text-overflow:ellipsis;
  white-space:nowrap}
.control-column .live-card .name small{color:var(--dim);font-weight:400;
  white-space:nowrap}
.control-column .dot{width:7px;height:7px;border-radius:50%;flex:none;
  background:var(--offline-mark)}
.control-column .dot.ok{background:var(--green)}
.control-column .send-all{min-width:0;min-height:var(--row-h);flex:none;
  padding:var(--pad-control);font-size:11px;text-transform:none}
.control-column .promoted-controls{display:grid;gap:var(--gap)}
.control-column .empty{margin:0;padding:var(--gap) 0;color:var(--dim)}
/* An empty target is a real, chosen state — dimmed, never hidden (D2). */
.control-column .live-card.empty-group{opacity:.72}

/* The capture preview: arm-then-fire, never a modal (judgment §5). It is a
   card on the ground like the columns, not an overlay. */
.capture-preview{margin:12px 16px 0;max-width:620px;padding:var(--pad-panel);
  display:grid;gap:var(--gap);background:var(--panel);
  border:1px solid var(--accent);border-radius:var(--radius-panel)}
.capture-preview h2{margin:0;font-size:12px;font-weight:700}
.capture-preview table{border-collapse:collapse;width:100%}
.capture-preview td{padding:2px 6px 2px 0;vertical-align:top}
.capture-preview .pill{display:inline-block;padding:0 4px;
  border:1px solid var(--mod);border-radius:var(--radius-toggle);
  color:var(--mod);font-size:10px}
.capture-preview .note{color:var(--dim)}
.capture-preview .warn{color:var(--mod)}
.capture-preview .omitted td{color:var(--dim)}
.capture-preview footer{display:flex;gap:var(--gap);justify-content:flex-end}
.capture-preview footer button{min-height:var(--row-h);
  padding:var(--pad-control);border:1px solid var(--control-line);
  border-radius:var(--radius-momentary);background:var(--control);
  color:var(--text);font:inherit;cursor:pointer}
.capture-preview footer .commit{border-color:var(--accent)}
.mock-caption{margin:0;padding:8px 16px 0;color:var(--dim)}
</style></head>
<body>
<div class="mock-chrome">
  <button>Show</button><button class="on">Control</button><button>Seats</button>
  <button>Devices</button><button>Patches</button><button>Assets</button>
  <a class="view-link">Remote</a>
</div>
<div class="control-tab-strip">__TABACTION__</div>
__CAPTION__
__PREVIEW__
<div class="control-columns">__COLUMNS__</div>
</body></html>
"""


def compose(harvested, theme, caption, keep=None, preview=""):
    columns = []
    for column in (harvested if keep is None else harvested[:keep]):
        columns.append(
            '<section class="control-column">'
            '<div class="control-column-head">'
            '<span class="grip" aria-hidden="true">⋮⋮</span>'
            f'<div class="target-picker-host">{column["picker"]}</div>'
            '<button class="close" title="Remove column" '
            'aria-label="Remove column">✕</button>'
            '</div>'
            f'<div class="cards">{column["cards"]}</div>'
            '</section>')
    return (SHELL
            .replace("__CSS__", stylesheet())
            .replace("__THEME__", theme)
            .replace("__CAPTION__",
                     f'<p class="mock-caption">{caption}</p>' if caption else "")
            .replace("__TABACTION__", TAB_STRIP)
            .replace("__PREVIEW__", preview)
            .replace("__COLUMNS__", "".join(columns)))


# The tab strip: exactly two tab-scoped actions, at the two furthest-apart
# points (judgment §2, §5). The capture count is ambient and client-derived —
# 4 of the 6 seats carry provenance in this fixture. Markup only; inert here.
TAB_STRIP = ('<button class="add-column">+ column</button>'
             '<button class="capture">capture step <b>· 4/6</b></button>')

# The armed state: a non-modal preview of the messages the server would mint,
# on the ground beside the columns. Never a dialog (judgment §5, §7).
CAPTURE_PREVIEW = """
<div class="capture-preview">
  <h2>Capture arrangement — 2 messages, 2 seats omitted</h2>
  <table>
    <tr><td><span class="pill">PRE</span></td><td>dusk</td>
        <td>→ group “Left”</td><td class="note">portable</td></tr>
    <tr><td><span class="pill">PRE</span></td><td>bloom</td>
        <td>→ group “Balcony”</td>
        <td class="warn">edited since applied — captures the preset,
            not the edits</td></tr>
    <tr class="omitted"><td>—</td><td>(none)</td><td>→ 2 seats</td>
        <td>no preset applied · not captured</td></tr>
  </table>
  <footer><button>Cancel</button>
    <button class="commit">Capture</button></footer>
</div>
"""


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
                    harvested = harvest(browser, base, theme)
                    plans = [
                        ("1280", 1280, 3,
                         "1280 — three 342px columns and the add slot. Old "
                         "1400px cap would have allowed these three and no "
                         "more at any width."),
                        ("1680", 1680, 4,
                         "1680 — four columns, cap lifted (D1). Column 4 is a "
                         "mixture: one card per selected entry."),
                        ("2560", 2560, 5,
                         "2560 — five columns, the fifth an empty group (D2). "
                         "Width buys more columns, never wider ones."),
                    ]
                    for label, width, keep, caption in plans:
                        html = compose(harvested, theme, caption, keep=keep)
                        path = os.path.join(OUT, f"mockup-{label}-{theme}.html")
                        with open(path, "w", encoding="utf-8") as t:
                            t.write(html)
                        page = browser.new_page(
                            viewport={"width": width, "height": 1000})
                        page.goto("file://" + path)
                        time.sleep(.6)
                        page.screenshot(path=os.path.join(
                            OUT, f"mockup-{label}-{theme}.png"),
                            full_page=True)
                        page.close()
                    # Two more states, both at 1280.
                    extras = [
                        ("760", 760, 4, "",
                         "760 — below two columns the row scrolls "
                         "horizontally; the panel never reflows (06/06b)."),
                        ("armed", 1280, 3, CAPTURE_PREVIEW,
                         "The armed capture: a non-modal preview of the "
                         "messages the server would mint (judgment §5). No "
                         "alert, no confirm."),
                    ]
                    for label, width, keep, preview, caption in extras:
                        html = compose(harvested, theme, caption, keep=keep,
                                       preview=preview)
                        path = os.path.join(OUT, f"mockup-{label}-{theme}.html")
                        with open(path, "w", encoding="utf-8") as t:
                            t.write(html)
                        page = browser.new_page(
                            viewport={"width": width, "height": 1000})
                        page.goto("file://" + path)
                        time.sleep(.6)
                        page.screenshot(path=os.path.join(
                            OUT, f"mockup-{label}-{theme}.png"))
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
    print("mockups in", OUT)
    for f in sorted(os.listdir(OUT)):
        print("  ", f)


main()
