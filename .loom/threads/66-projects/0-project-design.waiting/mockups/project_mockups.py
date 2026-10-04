#!/usr/bin/env python3
"""Mockups for 66-projects/0-project-design, drawn into the running dashboard.

Runs the real dashboard + simfleet in a temp dir (loopback only), deploys a
patch through the real UI, then injects the proposed project bar, project menu,
Patches-tab versions panel and New Version dialog, and screenshots each.
"""
import json, os, random, shutil, socket, subprocess, sys, tempfile, time, urllib.request
from playwright.sync_api import sync_playwright

REPO = "/Users/bob/repos/bopOS"
OUT = os.path.dirname(os.path.abspath(__file__))
UIDS = ["02:53:49:4d:00:01", "02:53:49:4d:00:02", "02:53:49:4d:00:03"]


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


CSS = """
.mk-project{justify-self:center;display:inline-flex;align-items:center;gap:8px;min-height:30px;
  padding:4px 12px;border:1px solid var(--control-line);border-radius:999px;background:var(--control);
  color:var(--text);font-size:13px;text-transform:none;white-space:nowrap}
.mk-project b{font-weight:700}.mk-project .mk-sep{color:var(--dim)}.mk-project .mk-k{color:var(--dim);font-size:10px;
  letter-spacing:.1em;text-transform:uppercase;margin-right:4px}
.mk-menu{position:fixed;top:calc(var(--header-h) - 4px);left:50%;transform:translateX(-50%);z-index:50;width:420px;
  background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px;box-shadow:0 12px 40px #0008}
.mk-menu h3{margin:14px 0 6px}.mk-menu h3:first-child{margin-top:0}
.mk-row{display:flex;align-items:center;justify-content:space-between;gap:8px;padding:7px 9px;border-radius:6px}
.mk-row.cur{background:var(--hover)}.mk-row small{color:var(--dim)}
.mk-actions{display:flex;gap:8px;flex-wrap:wrap;margin-top:6px}
.mk-menu fieldset{border:1px solid var(--line);border-radius:7px;display:grid;grid-template-columns:1fr 1fr;gap:6px;font-size:13px}
.mk-versions{display:grid;gap:8px;margin:12px 0}
.mk-version{display:grid;grid-template-columns:minmax(180px,1fr) auto auto auto;align-items:center;gap:10px;padding:10px;
  border:1px solid var(--line);border-radius:7px;background:var(--surface-bar)}
.mk-version.is-patch{box-shadow:inset 3px 0 0 var(--green)}
.mk-version strong,.mk-version small{display:block}.mk-version small{color:var(--dim);margin-top:3px}
.mk-tag{font-size:10px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;padding:3px 7px;border-radius:999px;
  border:1px solid var(--status-ok-border);background:var(--status-ok-bg);color:var(--status-ok-text)}
.mk-dialog-back{position:fixed;inset:0;background:#0009;z-index:60;display:grid;place-items:center}
.mk-dialog{width:440px;background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:18px}
.mk-dialog h2{margin:0 0 6px}.mk-dialog label{display:grid;gap:6px;margin:14px 0;color:var(--dim);font-size:12px}
.mk-dialog input{background:var(--input);border:1px solid var(--line);color:var(--text);border-radius:6px;padding:9px;font:inherit}
.mk-note{position:fixed;right:12px;bottom:12px;z-index:70;background:#d9a43a;color:#171008;font:700 11px system-ui;
  padding:5px 9px;border-radius:5px;letter-spacing:.06em}
"""

BAR = """
(() => {
  const st = document.createElement('style'); st.textContent = CSS; document.head.append(st);
  const spacer = document.querySelector('header .app-header-spacer');
  const bar = document.createElement('button'); bar.className = 'mk-project'; bar.id = 'mk-project';
  bar.innerHTML = '<span><span class="mk-k">Project</span><b>Kite Choir</b></span><span class="mk-sep">·</span>'
    + '<span><span class="mk-k">Site</span>Northern Broadwalk</span><span class="mk-sep">·</span>'
    + '<span><span class="mk-k">Patch</span>kite-v2</span><span class="mk-sep">▾</span>';
  spacer.removeAttribute('aria-hidden'); spacer.style.display = 'grid'; spacer.append(bar);
  const note = document.createElement('div'); note.className = 'mk-note'; note.textContent = 'MOCKUP';
  document.body.append(note);
  // Venue bar and show picker go; Remote commands leave the Patches tab.
  document.getElementById('venue-bar').style.display = 'none';
  document.getElementById('remote-command-editor')?.setAttribute('hidden', '');
})()
"""

VERSIONS = """
(() => {
  const panel = document.getElementById('fleet-patch-panel');
  panel.innerHTML = `
    <div class="section-head"><h2>Patch</h2>
      <div class="mk-actions"><button>New Version</button><button>Add existing…</button></div></div>
    <p class="dim" style="margin:6px 0 0">The fleet runs the Patch. Edit and push it in place, or make a New Version.</p>
    <div class="mk-versions">
      <div class="mk-version is-patch"><span><strong>kite-v2 <span class="mk-tag">Patch</span></strong>
        <small>pd · pushed 4 Oct 14:02 · 3 of 3 devices current</small></span>
        <span class="patch-badge patch-badge-current">current</span><button>Edit</button><button>Push</button></div>
      <div class="mk-version"><span><strong>kite-v1</strong><small>pd · last the Patch 28 Sep</small></span>
        <span></span><button>Edit</button><button>Make it the Patch</button></div>
      <div class="mk-version"><span><strong>kite-sketch</strong><small>pd · never the Patch</small></span>
        <span></span><button>Edit</button><button>Make it the Patch</button></div>
    </div>`;
})()
"""

MENU = """
(() => {
  const m = document.createElement('div'); m.className = 'mk-menu'; m.id = 'mk-menu';
  m.innerHTML = `
    <h3>Project</h3>
    <div class="mk-row cur"><span><b>Kite Choir</b><br><small>3 Seats · 3 devices</small></span><button>Rename</button></div>
    <div class="mk-row"><span>The Plants<br><small>8 Seats · 8 devices</small></span><button>Open</button></div>
    <div class="mk-actions"><button>New project</button></div>
    <h3>Site</h3>
    <div class="mk-row cur"><span><b>Northern Broadwalk</b><br><small>40 × 12 m</small></span><span class="dim">current</span></div>
    <div class="mk-row"><span>Workshop<br><small>10 × 8 m</small></span><button>Use</button></div>
    <div class="mk-actions"><button>New site (copy current)</button></div>
    <h3>Remote device commands</h3>
    <fieldset><label><input type="checkbox"> Restart engine</label><label><input type="checkbox"> Update bopOS</label>
      <label><input type="checkbox" checked> Reboot</label><label><input type="checkbox" checked> Shutdown</label></fieldset>`;
  document.body.append(m);
})()
"""

DIALOG = """
(() => {
  document.getElementById('mk-menu')?.remove();
  const d = document.createElement('div'); d.className = 'mk-dialog-back'; d.id = 'mk-dialog';
  d.innerHTML = `<div class="mk-dialog"><h2>New Version</h2>
    <p class="dim" style="margin:0">Copies <b>kite-v2</b> into a new patch folder in this project. The fleet keeps
    running kite-v2 until you make the new version the Patch.</p>
    <label>Folder name<input value="kite-v3"></label>
    <div class="mk-actions" style="justify-content:flex-end"><button>Cancel</button><button>Create version</button></div></div>`;
  document.body.append(d);
})()
"""


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-mockups-") as temp:
        state_path = os.path.join(temp, "installation.json")
        assets, patches = os.path.join(temp, "assets"), os.path.join(temp, "patches")
        os.makedirs(assets)
        for name in ("kite-v1", "kite-v2", "kite-sketch"):
            shutil.copytree(os.path.join(REPO, "patches", "demo-pd"), os.path.join(patches, name))
        with open(os.path.join(patches, "kite-v1", "mockup-v1.txt"), "w") as f:
            f.write("v1")
        seats = {str(i): {"id": i, "name": f"Seat {i}", "positions": [[2 + 3 * i, 4]], "params": {},
                          "bound": uid, "groups": []} for i, uid in enumerate(UIDS)}
        json.dump({"schema": 1, "name": "Kite Choir",
                   "room": {"width": 40.0, "depth": 12.0, "origin": [0, 0], "units": "m"},
                   "seats": seats}, open(state_path, "w"))
        http, listen, send = (free_port(socket.SOCK_STREAM), free_port(socket.SOCK_DGRAM),
                              free_port(socket.SOCK_DGRAM))
        base = f"http://127.0.0.1:{http}"
        log = open(os.path.join(OUT, "mockup-server.log"), "w")
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
                page = browser.new_page(viewport={"width": 1440, "height": 900},
                                        color_scheme="dark")
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
                page.evaluate("CSS => {window.CSS_MK = CSS}", CSS)
                page.evaluate(BAR.replace("CSS;", "window.CSS_MK;"))
                page.evaluate(VERSIONS)
                page.screenshot(path=os.path.join(OUT, "mockup-1-patches-tab.png"))
                page.evaluate(MENU)
                page.screenshot(path=os.path.join(OUT, "mockup-2-project-menu.png"))
                page.evaluate(DIALOG)
                page.screenshot(path=os.path.join(OUT, "mockup-3-new-version.png"))
                page.evaluate("document.getElementById('mk-dialog').remove()")
                page.click("#tab-button-seats")
                time.sleep(0.5)
                page.screenshot(path=os.path.join(OUT, "mockup-4-seats-tab.png"))
                browser.close()
        finally:
            for proc in (fleet, server):
                if proc and proc.poll() is None:
                    proc.terminate(); proc.wait(timeout=5)


if __name__ == "__main__":
    main()
