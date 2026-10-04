"""Real dashboard + simfleet: Performance locks, convergence and restart.

BOPOS_PERFORMANCE_SCREENSHOT=<directory> saves on/off at 1440/900/420px.
"""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time

from playwright.sync_api import sync_playwright
from pythonosc.osc_message_builder import OscMessageBuilder
from project_fixture import project_path, data_root
from verify_patches_tab import REPO, free_port, stop, wait_http, write_patch

sys.dont_write_bytecode=True
SCREENSHOTS=os.environ.get("BOPOS_PERFORMANCE_SCREENSHOT")


def main():
    with tempfile.TemporaryDirectory(prefix="bopos-performance-") as temporary:
        root=Path(temporary); patches=root/"patches"; assets=root/"assets"
        patches.mkdir(); assets.mkdir()
        for name in ("demo-pd","live"):
            write_patch(str(patches),name,name.encode())
        project=project_path(root/"data")
        project.write_text(json.dumps({"schema":1,"patches":["live"],
            "fleet_patch":{"name":"live"},"seats":{}}))
        data=data_root(project)
        http=free_port(socket.SOCK_STREAM)
        report=free_port(socket.SOCK_DGRAM); command=free_port(socket.SOCK_DGRAM)
        base=f"http://127.0.0.1:{http}"
        server_args=[sys.executable,str(Path(REPO)/"dashboard/server.py"),
            "--host","127.0.0.1","--port",str(http),"--listen-port",str(report),
            "--send-port",str(command),"--osc-target","127.0.0.1","--data-dir",data,
            "--assets-dir",str(assets),"--patches-dir",str(patches),"--public-url",base,
            "--sim-no-engine","--sim-audio-backend","none"]
        fleet_args=[sys.executable,str(Path(REPO)/"tools/simfleet.py"),"--devices","2",
            "--target","127.0.0.1","--report-port",str(report),"--cmd-port",str(command),
            "--hb-interval","0.2","--patches-dir",str(patches),
            "--state-dir",str(root/"nodes"),"--manifest",str(patches/"live/bopos.patch.json")]
        server=fleet=None
        with (root/"server.log").open("w") as server_log, (root/"fleet.log").open("w") as fleet_log:
            try:
                server=subprocess.Popen(server_args,cwd=REPO,stdout=server_log,stderr=subprocess.STDOUT)
                wait_http(base,server)
                fleet=subprocess.Popen(fleet_args,cwd=REPO,stdout=fleet_log,stderr=subprocess.STDOUT)
                with sync_playwright() as playwright:
                    browser=playwright.chromium.launch(headless=True)
                    page=browser.new_page(viewport={"width":1440,"height":900})
                    page.set_default_timeout(12000)
                    errors=[]
                    page.on("pageerror",lambda error:errors.append(str(error)))
                    page.on("dialog",lambda dialog:dialog.accept())
                    page.goto(base+"#patches")
                    page.wait_for_function("Object.keys(installation.devices).length===2 && Object.values(installation.devices).every(d=>d.report?.performance===false)")
                    toggle=page.locator("#performance-toggle")
                    assert toggle.get_attribute("aria-checked")=="false"
                    assert page.locator("#patch-edit").is_enabled()
                    assert page.locator("#patch-deploy").is_enabled()
                    assert page.locator("#patch-new-version").is_enabled()
                    print("PASS development starts unlocked",flush=True)

                    def screenshots(active):
                        if not SCREENSHOTS:return
                        destination=Path(SCREENSHOTS); destination.mkdir(parents=True,exist_ok=True)
                        for width in (1440,900,420):
                            page.set_viewport_size({"width":width,"height":900})
                            page.evaluate("window.scrollTo(0,0)")
                            button=toggle.bounding_box()
                            assert button and button["x"]>=0 and button["x"]+button["width"]<=width
                            assert button["height"]>=30
                            page.screenshot(path=str(destination/f"performance-{'on' if active else 'off'}-{width}.png"))
                        page.set_viewport_size({"width":1440,"height":900})

                    screenshots(False)
                    toggle.click()
                    page.wait_for_function("installation.performance===true && Object.values(installation.devices).filter(d=>!d.virtual).every(d=>d.report?.performance===true)")
                    assert toggle.is_enabled()
                    assert page.locator('[data-execution-target="edit"]').is_disabled()
                    for selector in ("#patch-edit","#patch-deploy","#patch-new-version","#editor-new-patch","#manifest-save"):
                        assert page.locator(selector).is_disabled(),selector
                    assert page.locator("#editor-panel").is_hidden()
                    assert page.locator("#performance-warning").is_hidden()
                    assert page.locator("#wifi-add").is_disabled()
                    assert page.locator("#wifi-send").is_disabled()
                    assert page.locator("#wifi-country").is_disabled()
                    for form in ("[data-monitor-send-form]","[data-monitor-report-form]"):
                        assert page.locator(form+" input").first.is_disabled()
                        assert page.locator(form+" button").first.is_disabled()
                    print("PASS header, patch, Wi-Fi and Monitor locks; exit stays enabled",flush=True)
                    screenshots(True)

                    # A real contradictory node report triggers host convergence.
                    saved_modes={path:path.stat().st_mtime_ns for path in (root/"nodes").glob("*.performance")}
                    assert len(saved_modes)==2
                    message=OscMessageBuilder(address="/all/os/performance"); message.add_arg(0)
                    with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as sender:
                        sender.sendto(message.build().dgram,("127.0.0.1",command))
                    deadline=time.monotonic()+12
                    def repaired():
                        return all(path.stat().st_mtime_ns>previous and json.loads(path.read_text()) is True
                                   for path,previous in saved_modes.items())
                    while not repaired() and time.monotonic()<deadline:time.sleep(.05)
                    assert repaired(),"a contradictory assertion must be persisted, then restored by the host"
                    page.wait_for_function("Object.values(installation.devices).filter(d=>!d.virtual).every(d=>d.report?.performance===true)")
                    # Unknown/new node: no mode claim counts as disagreement.
                    page.evaluate("""() => {installation.devices.pending={uid:'pending',online:true,report:{performance:false}};renderHeader();}""")
                    assert page.locator("#performance-warning").is_visible()
                    assert "1 devices still in development" in page.locator("#performance-warning").inner_text()
                    page.evaluate("installation.devices.pending.online=false;renderHeader()")
                    assert page.locator("#performance-warning").is_visible(),"known disagreement remains visible while offline"
                    page.evaluate("delete installation.devices.pending;renderHeader()")
                    print("PASS mismatch warning and real node convergence",flush=True)

                    # Restart host mid-show while the nodes stay up.
                    stop(server)
                    server=subprocess.Popen(server_args,cwd=REPO,stdout=server_log,stderr=subprocess.STDOUT)
                    wait_http(base,server); page.reload()
                    page.wait_for_function("installation.performance===true && Object.keys(installation.devices).length===2 && Object.values(installation.devices).every(d=>d.report?.performance===true)")
                    assert toggle.get_attribute("aria-checked")=="true"
                    # A new simulator process restores each node's remembered mode.
                    stop(fleet)
                    fleet=subprocess.Popen(fleet_args,cwd=REPO,stdout=fleet_log,stderr=subprocess.STDOUT)
                    page.evaluate("Object.values(installation.devices).forEach(d=>{d.online=false;})")
                    page.wait_for_function("Object.values(installation.devices).every(d=>d.online&&d.report?.performance===true)")
                    print("PASS host and node restart retain Performance",flush=True)

                    toggle.click()
                    page.wait_for_function("installation.performance===false && Object.values(installation.devices).every(d=>d.report?.performance===false)")
                    assert page.locator("#patch-edit").is_enabled()
                    assert page.locator("#patch-deploy").is_enabled()
                    assert page.locator("#wifi-add").is_enabled()
                    assert page.locator("[data-monitor-send-form] input").is_enabled()
                    assert page.locator("[data-monitor-report-form] input").is_enabled()
                    # Entering Performance closes an existing edit session.
                    page.locator("#patch-edit").click()
                    page.wait_for_function("installation.supervisor.mode==='edit'")
                    toggle.click()
                    page.wait_for_function("installation.performance===true && installation.supervisor.mode==='off'")
                    assert page.locator("#editor-panel").is_hidden()
                    assert not errors,errors
                    browser.close()
                    print("PASS exit unlocks development; entering Performance stops Patch Edit; no browser errors",flush=True)
            except Exception:
                print((root/"server.log").read_text()[-6000:])
                print((root/"fleet.log").read_text()[-3000:])
                raise
            finally:
                stop(fleet); stop(server)


if __name__=="__main__":main()
