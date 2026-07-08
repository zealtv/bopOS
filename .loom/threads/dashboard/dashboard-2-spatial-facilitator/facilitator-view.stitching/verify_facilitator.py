#!/usr/bin/env python3
"""Browser pass for facilitator-view.

Real dashboard + real simfleet, headless Chromium. Phase 1 (default manifest,
gain has role:volume): volume cards, VCA master scaling on the wire, Silence
All / RESUME via /os/mute, Sound check (aloha), preset save on the tech page ->
load from the facilitator page, PWA surface. Phase 2 (--manifest without a
volume-usable param): cards degrade to status-only with a "no volume param"
badge. Plus manifest.py role-validation unit checks.
"""
import json
import os
import subprocess
import sys
import tempfile
import time

from playwright.sync_api import sync_playwright

HERE = os.path.realpath(os.path.dirname(__file__))
REPO = HERE
while not os.path.isfile(os.path.join(REPO, "tools", "simfleet.py")):
    parent = os.path.dirname(REPO)
    if parent == REPO:
        raise SystemExit("cannot locate the bopOS repo root")
    REPO = parent
sys.path.insert(0, os.path.join(REPO, "python"))

FAILURES = []


def check(label, condition, detail=""):
    print("[{}] {}{}".format("PASS" if condition else "FAIL", label,
                             " -- " + detail if detail and not condition else ""))
    if not condition:
        FAILURES.append(label)


def set_slider(page, selector, value):
    page.eval_on_selector(selector, """(el, v) => {
        el.value = v;
        el.dispatchEvent(new Event('input', {bubbles: true}));
        el.dispatchEvent(new Event('change', {bubbles: true}));
    }""", value)


def launch(temp, http_port, osc_listen, osc_cmd, manifest=None):
    state_file = os.path.join(temp, "installation.json")
    fleet_log = open(os.path.join(temp, "fleet.log"), "w")
    server = subprocess.Popen([
        sys.executable, os.path.join(REPO, "dashboard/server.py"), "--port", str(http_port),
        "--listen-port", str(osc_listen), "--send-port", str(osc_cmd),
        "--osc-target", "127.0.0.1", "--state-file", state_file,
    ], cwd=REPO, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    fleet_cmd = [
        sys.executable, os.path.join(REPO, "tools/simfleet.py"), "--devices", "3",
        "--target", "127.0.0.1", "--report-port", str(osc_listen),
        "--cmd-port", str(osc_cmd), "--hb-interval", "1.0", "--boot-secs", "2.0",
    ]
    if manifest:
        fleet_cmd += ["--manifest", manifest]
    fleet = subprocess.Popen(fleet_cmd, cwd=REPO, stdout=fleet_log, stderr=subprocess.STDOUT)
    return server, fleet, fleet_log, state_file


def manifest_unit_checks():
    import manifest as manifest_module
    with tempfile.TemporaryDirectory() as temp:
        open(os.path.join(temp, "main.pd"), "w").close()

        def write(params):
            with open(os.path.join(temp, "bopos.patch.json"), "w") as target:
                json.dump({"engine": "pd", "entrypoint": "main.pd", "params": params}, target)

        write([{"name": "gain", "type": "f", "role": "volume"},
               {"name": "level", "type": "f", "role": "volume"}])
        _, error = manifest_module.load(temp)
        check("validator rejects two role:volume params", error is not None, str(error))

        write([{"name": "gain", "type": "f", "role": 3}])
        _, error = manifest_module.load(temp)
        check("validator rejects non-string role", error is not None, str(error))

        write([{"name": "pan", "type": "f"}])
        loaded, error = manifest_module.load(temp)
        check("no-volume manifest loads with a warning",
              error is None and any("volume" in note for note in manifest_module.warnings(loaded)))

        write([{"name": "level", "type": "f", "role": "volume"}])
        loaded, error = manifest_module.load(temp)
        check("role:volume manifest loads clean",
              error is None and not manifest_module.warnings(loaded))


def phase_one():
    with tempfile.TemporaryDirectory() as temp:
        server, fleet, fleet_log, state_file = launch(temp, 18089, 15559, 16669)
        try:
            time.sleep(3)
            with sync_playwright() as p:
                browser = p.chromium.launch()
                context = browser.new_context(viewport={"width": 900, "height": 1200})
                fac = context.new_page()
                fac.goto("http://127.0.0.1:18089/facilitator")
                fac.wait_for_selector(".card input[type=range]", timeout=10000)
                check("volume cards render with sliders",
                      fac.locator(".card input[type=range]").count() == 3)

                # PWA surface
                for path, label in (("/manifest.webmanifest", "webmanifest served"),
                                    ("/icon-180.png", "icon served")):
                    response = fac.request.get(f"http://127.0.0.1:18089{path}")
                    check(label, response.ok)

                # master scaling: master 0.5 x mix 0.8 -> 0.4 on the wire
                set_slider(fac, "#master", "0.5")
                fac.wait_for_timeout(300)
                set_slider(fac, ".card input[type=range]", "0.8")
                fac.wait_for_timeout(500)

                # silence all -> RESUME, /os/mute on the wire
                fac.click("#silence")
                fac.wait_for_function(
                    "() => document.querySelector('#silence').innerText.includes('RESUME')",
                    timeout=5000)
                check("silence flips to RESUME", True)
                fac.click("#silence")
                fac.wait_for_function(
                    "() => !document.querySelector('#silence').innerText.includes('RESUME')",
                    timeout=5000)

                # sound check = aloha to all
                fac.click("#soundcheck")
                fac.wait_for_timeout(400)
                fac.screenshot(path=os.path.join(HERE, "01-facilitator.png"))

                # preset: save on the tech page, appears + loads on facilitator
                tech = context.new_page()
                tech.on("dialog", lambda d: d.accept("morning-quiet")
                        if d.type == "prompt" else d.accept())
                tech.goto("http://127.0.0.1:18089/")
                tech.wait_for_selector("#preset-save", timeout=10000)
                tech.click("#preset-save")
                fac.wait_for_selector(".chip", timeout=5000)
                check("preset chip appears on facilitator", True)

                set_slider(fac, ".card input[type=range]", "0.2")
                fac.wait_for_timeout(300)
                fac.click(".chip")
                fac.wait_for_function(
                    "() => Number(document.querySelector('.card input[type=range]').value) === 0.8",
                    timeout=5000)
                check("preset load restores the mix", True)

                # facilitator scope guard: no admin verbs, no patch panel
                body = fac.locator("body").inner_text().lower()
                check("no admin controls in facilitator view",
                      all(word not in body for word in ("reboot", "shutdown", "update", "patch")))
                fac.screenshot(path=os.path.join(HERE, "02-facilitator-preset.png"))

                time.sleep(1.5)  # let the debounced save land
                saved = json.load(open(state_file))
                check("master persisted", saved.get("master") == 0.5, repr(saved.get("master")))
                preset = saved.get("presets", {}).get("morning-quiet", {})
                check("preset persisted with master + devices",
                      preset.get("master") == 0.5 and len(preset.get("devices", {})) == 3,
                      json.dumps(preset)[:200])
                browser.close()
        finally:
            fleet.terminate()
            server.terminate()
            fleet.wait(timeout=5)
            server.wait(timeout=5)
            fleet_log.close()
            log_text = open(fleet_log.name).read()
            check("wire: master-scaled volume (0.8 x 0.5 = 0.4)",
                  "command=gain 0.4" in log_text, log_text[-400:])
            check("wire: mute on", "muted=1" in log_text, log_text[-400:])
            check("wire: mute off", "muted=0" in log_text, log_text[-400:])
            check("wire: sound check aloha", "command=aloha 1" in log_text, log_text[-400:])
            check("wire: preset reload re-sent scaled volume",
                  log_text.count("command=gain 0.4") >= 2, log_text[-400:])


def phase_two():
    novol = os.path.join(tempfile.gettempdir(), "novol.bopos.patch.json")
    with open(novol, "w") as target:
        json.dump({"engine": "pd", "entrypoint": "main.pd",
                   "params": [{"name": "pan", "type": "f", "min": 0, "max": 1,
                               "default": 0.5, "group": "mix"}]}, target)
    with tempfile.TemporaryDirectory() as temp:
        server, fleet, fleet_log, _ = launch(temp, 18090, 15560, 16670, manifest=novol)
        try:
            time.sleep(3)
            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page(viewport={"width": 900, "height": 1200})
                page.goto("http://127.0.0.1:18090/facilitator")
                page.wait_for_selector(".card .badge", timeout=10000)
                page.wait_for_function(
                    "() => [...document.querySelectorAll('.card .badge')]"
                    ".filter(b => b.innerText.includes('no volume param')).length === 3",
                    timeout=10000)
                check("no-volume manifest degrades to status-only cards",
                      page.locator(".card input[type=range]").count() == 0)
                page.screenshot(path=os.path.join(HERE, "03-no-volume-param.png"))
                browser.close()
        finally:
            fleet.terminate()
            server.terminate()
            fleet.wait(timeout=5)
            server.wait(timeout=5)
            fleet_log.close()
    os.unlink(novol)


def main():
    manifest_unit_checks()
    phase_one()
    phase_two()
    print()
    if FAILURES:
        print("FAILED:", ", ".join(FAILURES))
        return 1
    print("facilitator checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
