#!/usr/bin/env python3
"""Generate the proposed CardsGrid from the real dashboard and simfleet.

The script does not draw controls. Shipping ControlColumn/ControlSurface code
renders one card per real target; this script recomposes those card nodes into
the proposed derived grid and adds only the proposed shell CSS.
"""

import json
import os
import random
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

from playwright.sync_api import sync_playwright

sys.dont_write_bytecode = True
REPO = os.path.realpath(os.path.dirname(__file__))
while not os.path.isfile(os.path.join(REPO, "tools", "simfleet.py")):
    parent = os.path.dirname(REPO)
    if parent == REPO:
        raise SystemExit("cannot locate bopOS repository")
    REPO = parent
OUT = os.path.realpath(sys.argv[1])
os.makedirs(OUT, exist_ok=True)
SEATS = 6
UIDS = [f"02:53:49:4d:00:{index + 1:02x}" for index in range(SEATS)]
RESERVED = set()
TARGETS = ["all", "g0", "g1", "g2", "0", "1", "2", "3", "4", "5"]


GRID_CSS = r"""
.control-tab-strip { display:none !important; }
#tab-control { padding-top:12px; }
#control-column-host, .cards-grid {
  display:grid !important;
  grid-template-columns:repeat(auto-fill,342px) !important;
  align-items:start !important;
  align-content:start !important;
  gap:12px !important;
  height:auto !important;
  max-height:none !important;
  overflow:visible !important;
}
#control-column-host > .control-column { display:contents !important; }
.control-column-head, .control-column-status { display:none !important; }
.control-column-cards { display:contents !important; }
.live-card {
  min-width:0 !important;
  display:grid !important;
  align-content:start !important;
  gap:var(--gap) !important;
  padding:var(--pad-panel) !important;
  border:1px solid var(--group-line) !important;
  border-radius:var(--radius-panel) !important;
  background:var(--panel) !important;
}
.live-card + .live-card { border-top:1px solid var(--group-line) !important; }
@media (max-width:374px) {
  #control-column-host, .cards-grid {
    grid-template-columns:minmax(0,1fr) !important;
  }
}
"""

REMOTE_CSS = GRID_CSS + r"""
#control-column-host.control-column {
  display:block !important;
  margin:12px !important;
  padding:0 !important;
  border:0 !important;
  background:transparent !important;
  max-height:none !important;
  overflow:visible !important;
}
body { height:auto !important; min-height:100%; overflow-y:auto !important; }
"""


def static_component_cards(full):
    """Render current component markup in Node when macOS blocks Chromium.

    This fallback still calls the shipping ControlSurface renderer; only the
    app shell is static. `mockup.py` prefers the live server/browser path.
    """
    params = [
        {"name": "density", "identity": "density", "kind": "float",
         "min": 0, "max": 1, "default": .2, "dashboard": True, "path": []},
        {"name": "depth", "identity": "depth", "kind": "float",
         "min": 0, "max": 1, "default": .4, "dashboard": True, "path": []},
        {"name": "movement", "identity": "movement", "kind": "float",
         "min": -1, "max": 1, "default": 0, "dashboard": True, "path": []},
        {"name": "texture", "identity": "texture", "kind": "float",
         "min": 0, "max": 1, "default": .65, "dashboard": False, "path": []},
        {"name": "space", "identity": "reverb/space", "kind": "float",
         "min": 0, "max": 1, "default": .3, "dashboard": False,
         "path": ["reverb"]},
        {"name": "strike", "identity": "strike", "kind": "event",
         "arity": 2, "defaults": [64, 100], "dashboard": True, "path": []},
    ]
    groups_for = {0: [0], 1: [0], 2: [1], 3: [1], 4: [2], 5: [2]}
    names = ["Front L", "Front R", "Side L", "Side R", "Balc L", "Balc R"]
    seats = []
    for index in range(SEATS):
        seats.append({
            "id": index, "name": names[index], "groups": groups_for[index],
            "params": {"density": .47 if index < 2 else .2, "depth": .4,
                       "movement": 0, "texture": .65, "reverb/space": .3},
            "applied_preset": {"patch": "alpha", "name": "Dawn"},
            "preset_dirty": "deviated" if index < 2 else None,
        })
    payload = {
        "full": full, "params": params, "seats": seats,
        "groups": [{"id": 0, "name": "Front"},
                   {"id": 1, "name": "Sides"},
                   {"id": 2, "name": "Balcony"}],
    }
    script = r"""
global.window=global; global.document={};
global.localStorage={getItem:()=>null,setItem:()=>{}};
global.OscMessage={typedArg:(type,value)=>({type,value})};
const fs=require('fs'), data=JSON.parse(process.argv[3]);
eval(fs.readFileSync(process.argv[1],'utf8'));
eval(fs.readFileSync(process.argv[2],'utf8'));
const state={automation:{}};
const surface=ControlSurface.create({
  getState:()=>state,
  deviceForSeat:()=>({online:true,engine_alive:1}),
  presetCatalog:()=>[{name:'Dawn',slug:'Dawn',valid:true,drift:false}],
});
const declarations=data.params.filter(item=>data.full || item.dashboard);
const esc=value=>String(value).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function card(scope,item,members){
  const id=scope==='all'?null:item.id;
  const name=scope==='all'?'All Seats':item.name;
  const meta=scope==='all'?`${members.length} Seats`:scope==='group'?`g${id} · ${members.length} Seats`:`Seat ${id} · online`;
  const presets=data.full?surface.presetRow(scope,id,members,'alpha',{key:`${scope}:${id??'all'}`}):'';
  const controls=surface.tree(scope,id,members,declarations,false);
  return `<article class="live-card ${scope}-card" role="region" aria-label="${esc(name)}" data-live-scope="${scope}"${id==null?'':` data-live-id="${id}"`}><div class="live-card-head">${scope==='seat'?'<i class="dot ok" aria-hidden="true"></i>':''}<span class="name"><strong>${esc(name)}</strong><small>${esc(meta)}</small></span></div>${presets}<div class="promoted-controls">${controls}</div></article>`;
}
const cards=[card('all',{},data.seats)];
for(const group of data.groups) cards.push(card('group',group,data.seats.filter(seat=>seat.groups.includes(group.id))));
for(const seat of data.seats) cards.push(card('seat',seat,[seat]));
process.stdout.write(JSON.stringify(cards));
"""
    result = subprocess.run([
        "node", "-e", script,
        os.path.join(REPO, "dashboard", "static", "js", "paramspec.js"),
        os.path.join(REPO, "dashboard", "static", "js", "control-surface.js"),
        json.dumps(payload),
    ], check=True, capture_output=True, text=True)
    return json.loads(result.stdout)


def static_styles():
    names = ["style.css", "param-generator.css", "control-panel.css",
             "value-box.css", "target-picker.css", "preset-menu.css",
             "control-column.css"]
    parts = []
    for name in names:
        with open(os.path.join(REPO, "dashboard", "static", "css", name),
                  encoding="utf-8") as source:
            parts.append(source.read())
    return "\n".join(parts)


def write_static_image(name, width, height, theme, cards, remote=False):
    chrome = (f'<header><h1>{"Cards grid review" if remote else "bopOS"}</h1>'
              f'<span class="dim">{"Remote" if remote else "0 / 6 online"}</span></header>')
    tabs = "" if remote else ('<div class="primary-tabs"><nav class="primary-tab-list">'
        '<button>Show</button><button aria-selected="true">Control</button>'
        '<button>Seats</button><button>Devices</button><button>Patches</button>'
        '<button>Assets</button></nav><a class="view-link">Remote</a></div>')
    footer = ('<footer class="mock-remote-footer"><span>Master</span>'
              '<input type="range" value="100"><button class="danger">SILENCE ALL</button></footer>') if remote else ""
    extra = REMOTE_CSS if remote else GRID_CSS
    font_source = ("/opt/homebrew/Library/Homebrew/vendor/portable-ruby/4.0.5_1/"
                   "lib/ruby/gems/4.0.0/gems/rdoc-7.0.4/lib/rdoc/generator/"
                   "template/darkfish/fonts/Lato-Regular.ttf")
    font_path = os.path.join(OUT, "mockup-font.ttf")
    if not os.path.exists(font_path):
        shutil.copyfile(font_source, font_path)
    font = "file://" + font_path
    columns = 2 if remote else 4
    html = f"""<!doctype html><html data-theme="{theme}"><head><meta charset="utf-8">
<style>@font-face{{font-family:MockLato;src:url('{font}');font-weight:400}}
@font-face{{font-family:MockLato;src:url('{font}');font-weight:700}}
@page{{size:{width}px {height}px;margin:0}}{static_styles()}\n{extra}
*{{font-family:MockLato!important}} body{{min-height:{height}px}}
details>summary::before{{content:'>'!important}} details[open]>summary::before{{content:'v'!important}}
.preset-menu:not([open]) .preset-menu-body{{display:none!important}}
.cards-grid{{display:grid!important;grid-template-columns:repeat({columns},342px)!important;gap:12px!important;align-items:start!important}}
.mock-grid-shell{{padding:12px 16px}}
.mock-remote-footer{{display:flex;gap:12px;align-items:center;padding:12px;border-top:1px solid var(--line)}}
</style></head><body>{chrome}{tabs}<main class="mock-grid-shell"><div class="cards-grid">{''.join(cards)}</div></main>{footer}</body></html>"""
    html = "\n".join(line.rstrip() for line in html.splitlines()) + "\n"
    html_path = os.path.join(OUT, name + ".html")
    pdf_path = os.path.join(OUT, name + ".pdf")
    with open(html_path, "w", encoding="utf-8") as target:
        target.write(html)
    try:
        subprocess.run(["weasyprint", html_path, pdf_path], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["pdftoppm", "-png", "-singlefile", "-r", "96",
                        pdf_path, os.path.join(OUT, name)], check=True)
        os.unlink(pdf_path)
    except subprocess.CalledProcessError:
        if os.path.exists(pdf_path):
            os.unlink(pdf_path)
        print(f"rasterizer unavailable; retained {os.path.basename(html_path)}",
              file=sys.stderr)


def static_fallback():
    control = static_component_cards(True)
    remote = static_component_cards(False)
    # WeasyPrint in the managed sandbox has no system-font fallback. These
    # glyphs live only in the closed menu's hidden body in this static preview;
    # replace them there so rasterization does not crash. The preferred live
    # Chromium path above renders the shipping glyphs unchanged.
    replacements = {"↥": "^", "⌫": "x", "▾": "v", "↗": "!", "⚠": "!"}
    control = ["".join(replacements.get(char, char) for char in card)
               for card in control]
    for theme in ("dark", "light"):
        write_static_image(f"cards-control-1440-{theme}", 1440, 2200,
                           theme, control)
        write_static_image(f"cards-remote-820-{theme}", 820, 2600,
                           theme, remote, remote=True)
    os.unlink(os.path.join(OUT, "mockup-font.ttf"))


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
    raise RuntimeError("could not reserve a port")


def wait_http(base, process):
    for _ in range(150):
        if process.poll() is not None:
            raise RuntimeError("dashboard exited before serving")
        try:
            urllib.request.urlopen(base, timeout=.5).read()
            return
        except OSError:
            time.sleep(.1)
    raise RuntimeError("dashboard did not serve")


def make_fixture(root):
    patches = os.path.join(root, "patches")
    patch = os.path.join(patches, "alpha")
    os.makedirs(os.path.join(patch, "presets"))
    os.makedirs(os.path.join(root, "assets"))
    os.makedirs(os.path.join(root, "sim-state"))
    with open(os.path.join(patch, "main.bin"), "wb") as target:
        target.write(b"cards-grid-mockup")
    manifest = {
        "engine": "test", "entrypoint": "main.bin",
        "params": [
            {"name": "density", "kind": "float", "min": 0, "max": 1,
             "default": .2, "dashboard": True},
            {"name": "depth", "kind": "float", "min": 0, "max": 1,
             "default": .4, "dashboard": True},
            {"name": "movement", "kind": "float", "min": -1, "max": 1,
             "default": 0, "dashboard": True},
            {"name": "texture", "kind": "float", "min": 0, "max": 1,
             "default": .65, "dashboard": False},
            {"name": "space", "kind": "float", "min": 0, "max": 1,
             "default": .3, "path": ["reverb"], "dashboard": False},
        ],
        "events": [
            {"name": "strike", "arity": 2, "defaults": [64, 100],
             "dashboard": True},
        ],
        "caps": [], "slots": [],
    }
    with open(os.path.join(patch, "bopos.patch.json"), "w",
              encoding="utf-8") as target:
        json.dump(manifest, target)
    groups_for = {0: [0], 1: [0], 2: [1], 3: [1], 4: [2], 5: [2]}
    names = ["Front L", "Front R", "Side L", "Side R", "Balc L", "Balc R"]
    seats = {}
    for index in range(SEATS):
        seats[str(index)] = {
            "id": index, "name": names[index],
            "positions": [[index + 1, index % 3 + 1]],
            "groups": groups_for[index], "bound": UIDS[index],
            "patch": "alpha",
            "params": {"density": .2, "depth": .4, "movement": 0,
                       "texture": .65, "reverb/space": .3},
        }
    state = {
        "schema": 1, "name": "Cards grid review", "params_patch": "alpha",
        "fleet_patch": {"name": "alpha", "fingerprint": "a" * 64,
                        "assets": []},
        "seats": seats,
        "groups": {
            "0": {"id": 0, "name": "Front"},
            "1": {"id": 1, "name": "Sides"},
            "2": {"id": 2, "name": "Balcony"},
        },
        "venue": {"width": 10, "depth": 8, "origin": [0, 0]},
    }
    state_path = os.path.join(root, "installation.json")
    with open(state_path, "w", encoding="utf-8") as target:
        json.dump(state, target)
    return state_path


def set_theme(page, theme):
    page.evaluate("theme => localStorage.setItem('bopos-theme', theme)", theme)


def seed_preset(page):
    page.evaluate(
        "() => ws.send('save_patch_preset',"
        " {scope:'all', patch:'alpha', name:'Dawn'})")
    page.wait_for_function(
        "() => installation.preset_catalog?.alpha?.some(p => p.name === 'Dawn')")
    page.evaluate(
        "() => ws.send('apply_preset',"
        " {scope:'all', patch:'alpha', name:'Dawn'})")
    page.wait_for_function(
        "() => installation.seats['0'].applied_preset?.name === 'Dawn'")
    page.evaluate(
        "() => ws.send('set_live_param',"
        " {scope:'group', id:0, name:'density', value:0.47})")
    page.wait_for_function(
        "() => installation.seats['0'].preset_dirty === 'deviated'")


def control_shot(browser, base, theme):
    page = browser.new_page(viewport={"width": 1440, "height": 1000})
    page.set_default_timeout(20000)
    page.goto(base + "#control")
    records = [{"id": f"m{index}", "target": [selector], "open": False}
               for index, selector in enumerate(TARGETS)]
    set_theme(page, theme)
    page.evaluate(
        "records => localStorage.setItem('bopos.control.columns',"
        " JSON.stringify(records))", records)
    page.reload()
    page.wait_for_selector("#ws-status.online")
    page.wait_for_function(
        "n => document.querySelectorAll('#control-column-host .live-card').length"
        " === n", arg=len(TARGETS))
    seed_preset(page)
    page.add_style_tag(content=GRID_CSS)
    page.screenshot(path=os.path.join(OUT, f"cards-control-1440-{theme}.png"),
                    full_page=True)
    page.close()


def remote_cards(browser, base, theme):
    cards = []
    for selector in TARGETS:
        page = browser.new_page(viewport={"width": 500, "height": 900})
        page.set_default_timeout(20000)
        page.goto(base + "/facilitator")
        set_theme(page, theme)
        page.evaluate(
            "selector => {"
            " localStorage.setItem('bopos.target.remote', JSON.stringify([selector]));"
            " localStorage.setItem('bopos.target.remote.open', 'false');"
            " }", selector)
        page.reload()
        page.wait_for_selector("#ws-status.online")
        page.wait_for_selector(".live-card")
        cards.append(page.locator(".live-card").first.evaluate(
            "node => node.outerHTML"))
        page.close()
    return cards


def remote_shot(browser, base, theme):
    cards = remote_cards(browser, base, theme)
    page = browser.new_page(viewport={"width": 820, "height": 1000})
    page.set_default_timeout(20000)
    page.goto(base + "/facilitator")
    set_theme(page, theme)
    page.reload()
    page.wait_for_selector("#ws-status.online")
    page.add_style_tag(content=REMOTE_CSS)
    page.evaluate(
        "cards => { document.querySelector('#control-column-host').innerHTML ="
        " '<div class=\"cards-grid\">' + cards.join('') + '</div>'; }", cards)
    page.screenshot(path=os.path.join(OUT, f"cards-remote-820-{theme}.png"),
                    full_page=True)
    page.close()


def stop(process):
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-cards-grid-") as temp:
        state_path = make_fixture(temp)
        http_port = free_port(socket.SOCK_STREAM)
        listen_port = free_port(socket.SOCK_DGRAM)
        send_port = free_port(socket.SOCK_DGRAM)
        base = f"http://127.0.0.1:{http_port}"
        log = open(os.path.join(temp, "run.log"), "w", encoding="utf-8")
        server = fleet = None
        try:
            server = subprocess.Popen([
                sys.executable, os.path.join(REPO, "dashboard", "server.py"),
                "--host", "127.0.0.1", "--port", str(http_port),
                "--listen-port", str(listen_port), "--send-port", str(send_port),
                "--osc-target", "127.0.0.1", "--state-file", state_path,
                "--patches-dir", os.path.join(temp, "patches"),
                "--assets-dir", os.path.join(temp, "assets"),
            ], cwd=REPO, stdout=log, stderr=subprocess.STDOUT)
            wait_http(base, server)
            fleet = subprocess.Popen([
                sys.executable, os.path.join(REPO, "tools", "simfleet.py"),
                "--devices", str(SEATS), "--target", "127.0.0.1",
                "--report-port", str(listen_port), "--cmd-port", str(send_port),
                "--hb-interval", "0.5", "--boot-secs", "0.2",
                "--state-dir", os.path.join(temp, "sim-state"),
                "--manifest", os.path.join(temp, "patches", "alpha",
                                           "bopos.patch.json"),
                "--patches-dir", os.path.join(temp, "patches"),
                "--assets-dir", os.path.join(temp, "assets"),
            ], cwd=REPO, stdout=log, stderr=subprocess.STDOUT)
            with sync_playwright() as playwright:
                try:
                    browser = playwright.chromium.launch(headless=True)
                except Exception as error:
                    print("live browser unavailable; using component-render fallback:",
                          error, file=sys.stderr)
                    static_fallback()
                    return
                for theme in ("dark", "light"):
                    control_shot(browser, base, theme)
                    remote_shot(browser, base, theme)
                browser.close()
        finally:
            stop(fleet)
            stop(server)
            log.close()
    for name in sorted(os.listdir(OUT)):
        if name.endswith(".png"):
            print(name)


if __name__ == "__main__":
    main()
