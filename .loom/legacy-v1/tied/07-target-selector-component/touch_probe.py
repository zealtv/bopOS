#!/usr/bin/env python3
"""What the target picker's collapse costs the Remote (facilitator) touch surface.

`49-remote-ipad-restyle` asks each component collapse to MEASURE its own tap
targets rather than inherit either the alarm ("44px becomes 34px") or the
reassurance (`05e` measured no change at all). This is `07`'s measurement.

`05c`'s `cascade_probe.py` does not apply here: it diffs computed properties on
the SAME elements before and after a re-anchor, and the elements this stitch
retires (`.target-filter button`, `.target-filter-seat select`) no longer exist.
So this measures the replacement directly, under coarse-pointer emulation, and
compares against the deleted rules' declared values.

Usage: touch_probe.py   (boots its own dashboard + simfleet)
"""
import json, os, random, socket, subprocess, sys, tempfile, time, urllib.request
from playwright.sync_api import sync_playwright

sys.dont_write_bytecode = True
REPO = os.path.realpath(os.path.dirname(__file__))
while not os.path.isfile(os.path.join(REPO, "tools", "simfleet.py")):
    _parent = os.path.dirname(REPO)
    if _parent == REPO:
        raise SystemExit("cannot locate bopOS repository")
    REPO = _parent
UIDS = ["02:53:49:4d:00:01", "02:53:49:4d:00:02"]
RESERVED = set()

# The rules this stitch deleted from facilitator.css, with their touch metrics.
RETIRED = {
    ".target-filter button": {"min-height": "44px", "font-size": "14px"},
    ".target-filter-seat select": {"min-height": "44px", "min-width": "140px"},
}


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
    patch = os.path.join(patches, "probe")
    os.makedirs(patch)
    os.makedirs(os.path.join(root, "assets"))
    with open(os.path.join(patch, "main.bin"), "wb") as target:
        target.write(b"touch-probe")
    with open(os.path.join(patch, "bopos.patch.json"), "w",
              encoding="utf-8") as target:
        json.dump({"engine": "test", "entrypoint": "main.bin", "caps": [],
                   "slots": [],
                   "params": [{"name": "gain", "kind": "float", "min": 0,
                               "max": 1, "default": .5, "dashboard": True}]},
                  target)
    state = {
        "schema": 1, "name": "Touch probe",
        "fleet_patch": {"name": "probe", "fingerprint": "a" * 64,
                        "staged_at": time.time(), "previous": None},
        "params_patch": "probe",
        "groups": {"0": {"id": 0, "name": "Front"}},
        "seats": {str(index): {"id": index, "name": f"Seat {index}",
                               "positions": [[index, 1]], "groups": [0],
                               "bound": uid, "patch": "probe",
                               "params": {"gain": .5}}
                  for index, uid in enumerate(UIDS)},
    }
    path = os.path.join(root, "installation.json")
    with open(path, "w", encoding="utf-8") as target:
        json.dump(state, target)
    return path


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-touch-probe-") as temp:
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
                "--patches-dir", os.path.join(temp, "patches"),
                "--assets-dir", os.path.join(temp, "assets"),
                "--manifest", os.path.join(temp, "patches", "probe",
                                           "bopos.patch.json"),
            ], cwd=REPO, stdout=log, stderr=subprocess.STDOUT)
            with sync_playwright() as pw:
                browser = pw.chromium.launch(headless=True)
                # iPad portrait, coarse pointer — the closest emulation there is
                # to the real device this stitch cannot test on.
                context = browser.new_context(
                    viewport={"width": 820, "height": 1180},
                    has_touch=True, is_mobile=False)
                page = context.new_page()
                page.set_default_timeout(15000)
                page.goto(base + "/facilitator")
                page.wait_for_selector("#target-picker-host .target-picker")
                page.wait_for_function(
                    "() => document.querySelectorAll("
                    "'#target-picker-host [data-target-toggle]').length >= 3")
                measured = page.evaluate("""() => {
                  const rows = [...document.querySelectorAll(
                    '#target-picker-host [data-target-toggle]')];
                  const style = getComputedStyle(rows[0]);
                  return {
                    chips: rows.length,
                    coarse: matchMedia('(pointer:coarse)').matches,
                    rowToken: getComputedStyle(document.documentElement)
                      .getPropertyValue('--row-h').trim(),
                    height: Math.round(
                      rows[0].getBoundingClientRect().height),
                    // The invisible ::after pad widens the real hit area.
                    hit: Math.round(
                      rows[0].getBoundingClientRect().height) + 8,
                    fontSize: style.fontSize,
                    width: Math.round(rows[0].getBoundingClientRect().width),
                  };
                }""")
                print("retired rules (facilitator.css):")
                for selector, metrics in RETIRED.items():
                    print(f"  {selector}: {metrics}")
                print("replacement (.target-chip, iPad-portrait emulation):")
                print(f"  {measured}")
                context.close()
                browser.close()
        finally:
            for process in (fleet, server):
                if process and process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except Exception:
                        process.kill()
            log.close()


if __name__ == "__main__":
    main()
