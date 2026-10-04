"""Production WS/OSC journey for capture lifecycle, batching and bounded replay."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time

from playwright.sync_api import sync_playwright
from pythonosc.udp_client import SimpleUDPClient
from project_fixture import project_path, data_root
from verify_ws_snapshot_replay import free_port, wait_http, stop_process, REPO

sys.dont_write_bytecode = True
UID = '02:53:49:4d:00:01'


def main():
    with tempfile.TemporaryDirectory(prefix='bopos-monitor-transport-') as temp:
        state_path = project_path(temp)
        state_path.write_text(json.dumps({'schema': 1, 'seats': {
            '1': {'id': 1, 'name': 'Monitor node', 'bound': UID, 'positions': [[1, 1]]}}}))
        assets, patches = Path(temp)/'assets', Path(temp)/'patches'
        assets.mkdir()
        patches.mkdir()
        http, listen, send = free_port(socket.SOCK_STREAM), free_port(socket.SOCK_DGRAM), free_port(socket.SOCK_DGRAM)
        base = 'http://127.0.0.1:%s' % http
        process = None
        with (Path(temp)/'dashboard.log').open('w') as log:
            try:
                process = subprocess.Popen([sys.executable, str(Path(REPO)/'dashboard/server.py'),
                    '--host', '127.0.0.1', '--port', str(http), '--listen-port', str(listen),
                    '--send-port', str(send), '--osc-target', '127.0.0.1',
                    '--data-dir', data_root(state_path), '--assets-dir', str(assets),
                    '--patches-dir', str(patches)], cwd=REPO, stdout=log, stderr=subprocess.STDOUT)
                wait_http(base, process)
                udp = SimpleUDPClient('127.0.0.1', listen)
                with sync_playwright() as pw:
                    browser = pw.chromium.launch(headless=True)
                    page = browser.new_page(viewport={'width': 1440, 'height': 1000})
                    errors = []
                    page.on('pageerror', lambda error: errors.append(str(error)))
                    page.goto(base)
                    page.wait_for_selector('#ws-status.online')
                    udp.send_message('/hb', [UID, 1, 'monitor-test', 1, -50])
                    page.wait_for_function('(uid) => !!installation.devices[uid]', arg=UID)
                    assert page.evaluate('ws.capture.directions') == []
                    page.click('[data-monitor-tab="in"]')
                    page.wait_for_function('ws.capture.directions.includes("in")')
                    incoming = page.locator('[data-console="in"]')
                    output = incoming.locator('[data-console-log]')
                    page.wait_for_timeout(150)
                    udp.send_message('/os/receipt-test', [UID, 'alpha'])
                    page.wait_for_function('document.querySelector("[data-console=in] [data-console-log]").textContent.includes("alpha")')
                    udp.send_message('/sync/pong', [1, '0', UID, '0'])
                    page.wait_for_timeout(250)
                    assert '/sync/pong' not in output.inner_text()
                    incoming.locator('summary').click()
                    incoming.locator('[data-capture-class="sync"]').check()
                    page.wait_for_timeout(150)
                    udp.send_message('/sync/pong', [1, '0', UID, '0'])
                    page.wait_for_function('document.querySelector("[data-console=in] [data-console-log]").textContent.includes("/sync/pong")')
                    incoming.locator('[data-capture-field="include"]').fill('/os/')
                    incoming.locator('[data-capture-field="include"]').press('Tab')
                    page.wait_for_timeout(150)
                    udp.send_message('/sync/pong', [1, '0', UID, 'filtered-marker'])
                    udp.send_message('/os/receipt-test', [UID, 'beta'])
                    page.wait_for_function('document.querySelector("[data-console=in] [data-console-log]").textContent.includes("beta")')
                    assert 'filtered-marker' not in output.inner_text()
                    incoming.locator('[data-console-filter]').fill('ALP* !beta')
                    assert 'alpha' in output.inner_text() and 'beta' not in output.inner_text()
                    incoming.locator('[data-console-filter]').fill('')
                    incoming.locator('[data-console-pause]').click()
                    assert page.evaluate('ws.capture.directions') == []
                    udp.send_message('/os/receipt-test', [UID, 'paused-marker'])
                    page.wait_for_timeout(200)
                    incoming.locator('[data-console-pause]').click()
                    page.wait_for_timeout(150)
                    assert 'paused-marker' not in output.inner_text()
                    page.click('[data-monitor-collapse]')
                    assert page.evaluate('ws.capture.directions') == []
                    udp.send_message('/os/receipt-test', [UID, 'hidden-marker'])
                    page.wait_for_timeout(150)
                    page.click('[data-monitor-tab="in"]')
                    page.wait_for_timeout(150)
                    assert 'hidden-marker' not in output.inner_text()
                    # Both visible split panes contribute to one selection.
                    page.locator('[data-monitor-pane="left"] .monitor-tab-menu > summary').click()
                    page.locator('[data-monitor-pane="left"] [data-monitor-move="right"]').click()
                    page.click('[data-monitor-tab="out"]')
                    assert set(page.evaluate('ws.capture.directions')) == {'in', 'out'}
                    # Document visibility suspends both and restores remembered panes.
                    page.evaluate('Object.defineProperty(document,"hidden",{configurable:true,value:true});document.dispatchEvent(new Event("visibilitychange"))')
                    assert page.evaluate('ws.capture.directions') == []
                    page.evaluate('Object.defineProperty(document,"hidden",{configurable:true,value:false});document.dispatchEvent(new Event("visibilitychange"))')
                    assert set(page.evaluate('ws.capture.directions')) == {'in', 'out'}
                    # Invalid server replacement leaves the acknowledged selection live.
                    page.evaluate('ws.requestCapture({include:["bad"]})')
                    page.wait_for_function('ws.capture.include[0] === "/os/"')
                    udp.send_message('/os/receipt-test', [UID, 'after-refusal'])
                    page.wait_for_function('document.querySelector("[data-console=in] [data-console-log]").textContent.includes("after-refusal")')
                    incoming.locator('[data-capture-field="include"]').fill('/os/ /ordinary/')
                    incoming.locator('[data-capture-field="include"]').press('Tab')
                    page.wait_for_timeout(150)
                    # A real matching burst reaches admission/byte limits, with a gap.
                    for chunk in range(8):
                        for n in range(180):
                            udp.send_message('/os/receipt-test', [UID, 'flood-%s-%s' % (chunk, n), 'x'*600])
                        time.sleep(.01)
                    page.wait_for_function('!document.querySelector("[data-console=in] [data-capture-loss]").hidden')
                    page.wait_for_function('document.querySelector("[data-console=in] [data-console-log]").textContent.includes("matching messages dropped")')
                    page.wait_for_timeout(1500)
                    incoming.locator('[data-console-clear]').click()
                    page.wait_for_timeout(200)
                    assert output.inner_text() == ''
                    assert incoming.locator('[data-capture-loss]').is_hidden()
                    old_generation = page.evaluate('ws.generation')
                    page.evaluate('ws.socket.close()')
                    page.wait_for_function('(old) => ws.generation > old && ws.socket.readyState === WebSocket.OPEN', arg=old_generation)
                    page.evaluate('(old) => ws.emit("telemetry", {generation:old,status:{},entries:[{type:"osc_in",data:{ts:1,address:"/stale-generation"}}]})', old_generation)
                    assert '/stale-generation' not in output.inner_text()
                    assert 'new history period' in output.inner_text()
                    # Map receives at most ten paints/s, while OSC remains 25 Hz.
                    page.evaluate('window.mapPaints=0;const original=Spatial.frame;Spatial.frame=(data)=>{mapPaints++;original(data)};ws.send("set_point",{point:{id:0,x:1,y:1,motion:{type:"orbit",center:[1,1],radius:.5,period:8}}})')
                    page.wait_for_timeout(200)
                    page.evaluate('mapPaints=0')
                    page.wait_for_timeout(1100)
                    assert 5 <= page.evaluate('mapPaints') <= 11
                    # Backend clock facts arrive through the consumed summary.
                    page.click('[data-monitor-tab="system"]')
                    for n in range(4):
                        stamp = time.monotonic_ns()
                        udp.send_message('/sync/pong', [n, str(stamp), UID, str(stamp)])
                        time.sleep(.005)
                    page.wait_for_function('document.querySelector("[data-monitor-system=clock]").textContent === "1 / 1 with 3+ samples"')
                    remote = browser.new_page()
                    remote.goto(base+'/facilitator')
                    remote.wait_for_function('typeof ws !== "undefined" && ws.socket.readyState === WebSocket.OPEN')
                    assert remote.evaluate('ws.capture.map') is False
                    result = remote.evaluate('''() => {
                      for(let n=0;n<10000;n++) for(const type of ["sync","heartbeat","osc_in","point_frame","io_samples"]) ws.emit(type,{n});
                      for(let n=0;n<1000;n++) ws.emit("late_event",{n,text:"x".repeat(2000)});
                      return [ws.pendingOrder.length,ws.pendingBytes,ws.pendingDropped,!!ws.pending.sync];
                    }''')
                    assert result[0] <= 50 and result[1] <= 65536 and result[2] > 0 and not result[3]
                    remote.wait_for_timeout(5100)
                    assert remote.evaluate('ws.pendingOrder.length') == 0
                    # Latest snapshot still replays to a late handler.
                    assert remote.evaluate('''() => {let seen;ws.on("state",data=>seen=data);return !!seen?.devices;}''')
                    prefix = os.environ.get('BOPOS_MONITOR_TRANSPORT_SCREENSHOT')
                    if prefix:
                        page.click('[data-monitor-tab="in"]')
                        page.locator('[data-monitor-pane="right"] .monitor-tab-menu > summary').click()
                        page.locator('[data-monitor-pane="right"] [data-monitor-move="single"]').click()
                        # Keep the reviewed loss/rate fixture stable while
                        # screenshot encoding runs. Real delivery was checked above.
                        page.evaluate('ws.socket.onmessage=()=>{}')
                        for width in (1440, 420):
                            page.set_viewport_size({'width': width, 'height': 1000})
                            # Resize with the public keyboard control, for legible filters.
                            for _ in range(12):
                                page.locator('.monitor-resize').press('ArrowUp')
                            if incoming.locator('.monitor-capture-filters').get_attribute('open') is None:
                                incoming.locator('.monitor-capture-filters summary').click()
                            incoming.locator('[data-capture-class="sync"]').check()
                            incoming.locator('[data-capture-class="sync"]').uncheck()
                            incoming.locator('[data-console-clear]').click()
                            page.evaluate('ws.emit("capture_counters",{in:{dropped_since_subscribe:12,dropped_interval:12,truncated:2},out:{},rates:{in:{sync:100,heartbeat:5,points:25},out:{}}});ws.emit("osc_in",{ts:1,address:"/os/receipt-test",args:["preview"]})')
                            for theme in ('light', 'dark'):
                                page.select_option('#theme-select', theme)
                                page.wait_for_timeout(150)
                                page.screenshot(path='%s-%s-%s.png' % (prefix, width, theme), full_page=True)
                        page.click('[data-monitor-tab="system"]')
                        page.screenshot(path=prefix+'-system.png', full_page=True)
                    assert errors == [], errors
                    browser.close()
                    print('PASS: real OSC capture/filter/rate/Pause/hidden/split/visibility/refusal/drop/Clear/reconnect, map cadence, consumed clock, Remote bounds/expiry and snapshots')
            except Exception:
                log.flush()
                print((Path(temp)/'dashboard.log').read_text()[-5000:])
                raise
            finally:
                stop_process(process)


if __name__ == '__main__':
    main()
