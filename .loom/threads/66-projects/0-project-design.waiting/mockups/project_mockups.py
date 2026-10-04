#!/usr/bin/env python3
"""Mockups for 66-projects/0-project-design, drawn into the running dashboard.

Runs the real dashboard + simfleet in a temp dir (loopback only), deploys a
patch through the real UI, then injects the proposed header, Patches tab,
project menu and dialogs, and screenshots each. Round 2 (Bob, 2026-10-04):
patch list as a sidebar, "Set Live", Remote commands on the Patches tab,
"Live" mode label and placement, New Site dialog.
"""
import json, os, random, shutil, socket, subprocess, sys, tempfile, time, urllib.request
from playwright.sync_api import sync_playwright

REPO = "/Users/bob/repos/bopOS"
OUT = os.path.dirname(os.path.abspath(__file__))
UIDS = ["02:53:49:4d:00:01", "02:53:49:4d:00:02", "02:53:49:4d:00:03"]
PATCHES = ["kite-v1", "kite-v2", "kite-v3", "kite-sketch", "kite-rehearsal",
           "kite-broadwalk", "kite-quiet", "kite-v2-loud"]


def free_port(kind):
    while True:
        port = random.randrange(20000, 60000)
        s = socket.socket(socket.AF_INET, kind)
        try:
            s.bind(("127.0.0.1", port)); return port
        except OSError:
            pass
        finally:
            s.close()


def wait_http(url):
    for _ in range(100):
        try:
            urllib.request.urlopen(url, timeout=0.5); return
        except Exception:
            time.sleep(0.1)
    raise SystemExit("dashboard did not start")


CSS = r"""
header{grid-template-columns:auto minmax(24px,1fr) auto auto!important}
header .app-header-spacer{display:flex!important;justify-content:center;align-items:center;gap:10px}
.mk-project{display:inline-flex;align-items:center;gap:8px;height:30px;min-height:30px;padding:0 12px;
  border:1px solid var(--control-line);border-radius:999px;background:var(--control);color:var(--text);
  font-size:13px;text-transform:none;white-space:nowrap}
.mk-project b{font-weight:700}.mk-project .mk-sep{color:var(--dim)}
.mk-project .mk-k{color:var(--dim);font-size:10px;letter-spacing:.1em;text-transform:uppercase;margin-right:4px}
/* mode switch: same 30px height as the project pill, 5px clear of the header edges */
header #execution-target.execution-options{min-height:30px;height:30px;padding:2px;border-radius:999px}
header #execution-target.execution-options button{min-height:24px;height:24px;padding:0 12px;border-radius:999px;font-size:12px}
.mk-menu{position:fixed;top:calc(var(--header-h) - 4px);left:50%;transform:translateX(-50%);z-index:50;width:400px;
  background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px;box-shadow:0 12px 40px #0008}
.mk-menu h3{margin:14px 0 6px}.mk-menu h3:first-child{margin-top:0}
.mk-row{display:flex;align-items:center;justify-content:space-between;gap:8px;padding:7px 9px;border-radius:6px}
.mk-row.cur{background:var(--hover)}.mk-row small{color:var(--dim)}
.mk-actions{display:flex;gap:8px;flex-wrap:wrap;margin-top:6px}
.mk-tag{font-size:10px;font-weight:800;letter-spacing:.08em;text-transform:uppercase;padding:2px 7px;border-radius:999px;
  border:1px solid var(--status-ok-border);background:var(--status-ok-bg);color:var(--status-ok-text)}
.mk-patches{display:grid;grid-template-columns:320px minmax(0,1fr);gap:20px;align-items:start}
.mk-side{padding:20px;border:1px solid var(--line);border-radius:9px;background:var(--panel)}
.mk-side h2{margin:0}.mk-side .section-head{margin-bottom:12px}
.mk-filter{width:100%;border:1px solid var(--line);border-radius:6px;background:var(--input-alt);color:var(--text);padding:9px;font:inherit}
.mk-list{margin:8px 0 0;display:grid;gap:2px}
.mk-item{display:flex;align-items:center;gap:10px;padding:9px 10px;border-radius:6px;cursor:pointer}
.mk-item:hover{background:var(--hover)}.mk-item.sel{background:var(--hover);box-shadow:inset 3px 0 0 var(--accent-cyan,#5cc8e0)}
.mk-item span{flex:1;min-width:0}.mk-item .mk-tag{flex:none}.mk-item strong,.mk-item small{display:block}.mk-item small{color:var(--dim);font-size:11px;margin-top:2px}
.mk-side fieldset{border:1px solid var(--line);border-radius:7px;display:grid;gap:6px;font-size:13px;margin:8px 0 0}
.mk-side .mk-setting{margin-top:22px;padding-top:16px;border-top:1px solid var(--line)}
.mk-side .mk-setting p{margin:2px 0 0;font-size:12px}
.mk-detail-head{display:flex;align-items:center;justify-content:space-between;gap:16px}
.mk-detail-head h2{margin:0;display:flex;align-items:center;gap:10px}
.mk-detail dl{margin-top:14px}
.mk-dialog-back{position:fixed;inset:0;background:#0009;z-index:60;display:grid;place-items:center}
.mk-dialog{width:440px;background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:18px}
.mk-dialog h2{margin:0 0 6px}.mk-dialog label.mk-field{display:grid;gap:6px;margin:14px 0;color:var(--dim);font-size:12px}
.mk-dialog input[type=text],.mk-dialog select{background:var(--input);border:1px solid var(--line);color:var(--text);border-radius:6px;padding:8px;font:inherit}
.mk-radio{display:flex;align-items:center;gap:8px;margin:8px 0;font-size:14px}
.mk-note{position:fixed;right:12px;bottom:12px;z-index:70;background:#d9a43a;color:#171008;font:700 11px system-ui;
  padding:5px 9px;border-radius:5px;letter-spacing:.06em}
"""

HEADER = """
(CSS) => {
  const st = document.createElement('style'); st.textContent = CSS; document.head.append(st);
  const spacer = document.querySelector('header .app-header-spacer');
  spacer.removeAttribute('aria-hidden');
  const bar = document.createElement('button'); bar.className = 'mk-project'; bar.id = 'mk-project';
  bar.innerHTML = '<span><span class="mk-k">Project</span><b>Kite Choir</b></span><span class="mk-sep">·</span>'
    + '<span><span class="mk-k">Site</span>Northern Broadwalk</span><span class="mk-sep">·</span>'
    + '<span><span class="mk-k">Patch</span>kite-v2</span><span class="mk-sep">▾</span>';
  const exec = document.getElementById('execution-target');
  for (const b of exec.querySelectorAll('button')) if (/live/i.test(b.textContent)) b.textContent = 'Live';
  spacer.append(bar, exec);
  const note = document.createElement('div'); note.className = 'mk-note'; note.textContent = 'MOCKUP';
  document.body.append(note);
  document.getElementById('venue-bar').style.display = 'none';
}
"""

PATCHES_TAB = """
(names) => {
  const tab = document.getElementById('tab-patches');
  const fleet = document.getElementById('fleet-patch-panel');
  const editor = document.getElementById('editor-panel');
  const remote = document.getElementById('remote-command-editor');
  const meta = {'kite-v2': '3 of 3 devices current', 'kite-v3': 'new · edited today',
                'kite-v1': 'last live 28 Sep'};
  const items = names.slice().sort().map(n => `
    <div class="mk-item${n === 'kite-v2' ? ' sel' : ''}"><span><strong>${n}</strong>
      <small>${meta[n] || 'pd'}</small></span>${n === 'kite-v2' ? '<span class="mk-tag">Live</span>' : ''}</div>`).join('');
  const grid = document.createElement('div'); grid.className = 'mk-patches';
  grid.innerHTML = `
    <aside class="mk-side">
      <div class="section-head"><h2>Patches</h2><button>New Version</button></div>
      <input class="mk-filter" placeholder="Filter patches…">
      <div class="mk-list">${items}</div>
      <div class="mk-actions"><button>Add Existing…</button></div>
      <div class="mk-setting"><h3>Remote device commands</h3>
        <p class="dim">Project setting · buttons shown on Remote</p>
        <fieldset><label><input type="checkbox"> Restart engine</label><label><input type="checkbox"> Update bopOS</label>
        <label><input type="checkbox" checked> Reboot</label><label><input type="checkbox" checked> Shutdown</label></fieldset></div>
    </aside>
    <div class="mk-main">
      <section class="mk-detail">
        <div class="mk-detail-head"><h2>kite-v2 <span class="mk-tag">Live</span></h2>
          <div class="mk-actions" style="margin:0"><button>Edit</button><button>Push</button></div></div>
        <p class="dim" style="margin:6px 0 0">The live fleet runs this patch. Edit and push it in place, or make a New Version.</p>
        <dl><dt>Devices</dt><dd><span class="patch-badge patch-badge-current">current</span> 3 of 3</dd>
          <dt>Last pushed</dt><dd>4 Oct 14:02</dd><dt>Engine</dt><dd>pd · main.pd</dd></dl>
      </section>
    </div>`;
  fleet.style.display = 'none';
  remote.style.display = 'none';
  // The selected patch's manifest editor lives under its detail; the separate
  // "host patch" picker goes, because the list is the picker.
  editor.querySelector('.editor-launch').style.display = 'none';
  editor.querySelector('.section-head h2').textContent = 'Manifest & editor';
  grid.querySelector('.mk-main').append(editor);
  tab.prepend(grid);
}
"""

SELECT_OTHER = """
() => {
  document.querySelectorAll('.mk-item').forEach(i => i.classList.toggle('sel', i.textContent.includes('kite-v3')));
  const d = document.querySelector('.mk-detail');
  d.innerHTML = `<div class="mk-detail-head"><h2>kite-v3</h2>
      <div class="mk-actions" style="margin:0"><button>Edit</button><button>Set Live</button></div></div>
    <p class="dim" style="margin:6px 0 0">Not live. Set Live pushes it to the fleet and switches every device to it.</p>
    <dl><dt>Devices</dt><dd class="dim">on kite-v2 (live)</dd><dt>Created</dt><dd>4 Oct 15:10 from kite-v2</dd>
      <dt>Engine</dt><dd>pd · main.pd</dd></dl>`;
}
"""

MENU = """
() => {
  document.getElementById('mk-dialog')?.remove();
  const m = document.createElement('div'); m.className = 'mk-menu'; m.id = 'mk-menu';
  m.innerHTML = `
    <h3>Project</h3>
    <div class="mk-row cur"><span><b>Kite Choir</b><br><small>3 Seats · 3 devices</small></span><button>Rename</button></div>
    <div class="mk-row"><span>The Plants<br><small>8 Seats · 8 devices</small></span><button>Open</button></div>
    <div class="mk-actions"><button>New Project</button></div>
    <h3>Site</h3>
    <div class="mk-row cur"><span><b>Northern Broadwalk</b><br><small>40 × 12 m</small></span><span class="dim">current</span></div>
    <div class="mk-row"><span>Workshop<br><small>10 × 8 m</small></span><button>Use</button></div>
    <div class="mk-actions"><button>New Site</button></div>`;
  document.body.append(m);
}
"""

NEW_SITE = """
() => {
  document.getElementById('mk-menu')?.remove();
  const d = document.createElement('div'); d.className = 'mk-dialog-back'; d.id = 'mk-dialog';
  d.innerHTML = `<div class="mk-dialog"><h2>New Site</h2>
    <label class="mk-field">Name<input type="text" placeholder="e.g. Town Hall"></label>
    <div class="dim" style="font-size:12px">Start from</div>
    <label class="mk-radio"><input type="radio" name="start"> An empty room</label>
    <label class="mk-radio"><input type="radio" name="start" checked> An existing site
      <select><option>Northern Broadwalk</option><option>Workshop</option></select></label>
    <p class="dim" style="font-size:12px;margin:4px 0 0">Copies its room size, listener and Seat positions.</p>
    <div class="mk-actions" style="justify-content:flex-end;margin-top:14px"><button>Cancel</button><button>Create Site</button></div></div>`;
  document.body.append(d);
}
"""

NEW_VERSION = """
() => {
  document.getElementById('mk-dialog')?.remove();
  const d = document.createElement('div'); d.className = 'mk-dialog-back'; d.id = 'mk-dialog';
  d.innerHTML = `<div class="mk-dialog"><h2>New Version</h2>
    <p class="dim" style="margin:0">Copies <b>kite-v2</b> into a new patch in this project. The fleet keeps
    running kite-v2 until you Set Live the new one.</p>
    <label class="mk-field">Name<input type="text" value="kite-v3"></label>
    <div class="mk-actions" style="justify-content:flex-end"><button>Cancel</button><button>Create Version</button></div></div>`;
  document.body.append(d);
}
"""


def shot(page, name, **kw):
    page.screenshot(path=os.path.join(OUT, name), **kw)


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-mockups-") as temp:
        state_path = os.path.join(temp, "installation.json")
        assets, patches = os.path.join(temp, "assets"), os.path.join(temp, "patches")
        os.makedirs(assets)
        for name in ("kite-v1", "kite-v2", "kite-v3"):
            shutil.copytree(os.path.join(REPO, "patches", "demo-pd"), os.path.join(patches, name))
        seats = {str(i): {"id": i, "name": f"Seat {i}", "positions": [[2 + 3 * i, 4]], "params": {},
                          "bound": uid, "groups": []} for i, uid in enumerate(UIDS)}
        json.dump({"schema": 1, "name": "Kite Choir",
                   "room": {"width": 40.0, "depth": 12.0, "origin": [0, 0], "units": "m"},
                   "seats": seats}, open(state_path, "w"))
        http, listen, send = (free_port(socket.SOCK_STREAM), free_port(socket.SOCK_DGRAM),
                              free_port(socket.SOCK_DGRAM))
        base = f"http://127.0.0.1:{http}"
        log = open(os.path.join(temp, "server.log"), "w")
        server = subprocess.Popen([sys.executable, os.path.join(REPO, "dashboard", "server.py"),
            "--host", "127.0.0.1", "--port", str(http), "--listen-port", str(listen),
            "--send-port", str(send), "--osc-target", "127.0.0.1", "--state-file", state_path,
            "--assets-dir", assets, "--patches-dir", patches, "--public-url", base],
            cwd=REPO, stdout=log, stderr=subprocess.STDOUT)
        fleet = None
        try:
            wait_http(base)
            fleet = subprocess.Popen([sys.executable, os.path.join(REPO, "tools", "simfleet.py"),
                "--devices", "3", "--target", "127.0.0.1", "--report-port", str(listen),
                "--cmd-port", str(send), "--hb-interval", "0.2", "--fetch-seconds", "0.3",
                "--patches-dir", patches,
                "--manifest", os.path.join(patches, "kite-v2", "bopos.patch.json")],
                cwd=REPO, stdout=log, stderr=subprocess.STDOUT)
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page(viewport={"width": 1440, "height": 900}, color_scheme="dark")
                page.on("dialog", lambda d: d.accept())
                page.goto(base)
                page.wait_for_selector("#ws-status.online")
                page.wait_for_function("() => Object.keys(installation.devices||{}).length === 3")
                page.click("#tab-button-patches")
                page.wait_for_function("() => [...document.querySelectorAll('#patch-select option')]"
                                       ".some(o => o.value === 'kite-v2')")
                page.select_option("#patch-target", "all")
                page.select_option("#patch-select", "kite-v2")
                page.click("#patch-switch")
                time.sleep(4)
                page.select_option("#editor-patch", "kite-v2")
                page.evaluate(HEADER, CSS)
                page.evaluate(PATCHES_TAB, PATCHES)
                time.sleep(0.3)
                shot(page, "mockup-1-patches-live.png")
                shot(page, "mockup-0-header.png", clip={"x": 0, "y": 0, "width": 1440, "height": 76})
                page.evaluate(SELECT_OTHER)
                shot(page, "mockup-2-patches-other.png")
                page.evaluate(NEW_VERSION)
                shot(page, "mockup-3-new-version.png")
                page.evaluate(MENU)
                shot(page, "mockup-4-project-menu.png")
                page.evaluate(NEW_SITE)
                shot(page, "mockup-5-new-site.png")
                page.evaluate("document.getElementById('mk-dialog').remove()")
                page.click("#tab-button-seats")
                time.sleep(0.5)
                shot(page, "mockup-6-seats-tab.png")
                # measure the header after the change
                print(page.evaluate("""() => { const r = s => { const b = document.querySelector(s).getBoundingClientRect();
                    return [Math.round(b.top), Math.round(b.height)] };
                    return {header: r('header'), exec: r('#execution-target'), pill: r('#mk-project')} }"""))
                browser.close()
        finally:
            for proc in (fleet, server):
                if proc and proc.poll() is None:
                    proc.terminate(); proc.wait(timeout=5)


if __name__ == "__main__":
    main()
