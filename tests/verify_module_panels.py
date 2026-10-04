"""Real dashboard/simfleet journey for driver panels and ordinary windows.

BOPOS_MODULE_PANELS_SCREENSHOT=<directory> saves four viewport/theme captures.
No physical chip, Pi or audio engine is exercised.
"""
import json
import os
from pathlib import Path
import socket
import struct
import subprocess
import sys
import tempfile
import time

from playwright.sync_api import sync_playwright
from pythonosc.udp_client import SimpleUDPClient
from pythonosc.osc_bundle_builder import OscBundleBuilder, IMMEDIATELY
from pythonosc.osc_message_builder import OscMessageBuilder
from verify_patches_tab import REPO, UID_A, free_port, stop, wait_http

sys.dont_write_bytecode = True


def main():
    with tempfile.TemporaryDirectory(prefix='bopos-module-panels-') as temporary:
        root = Path(temporary)
        for name in ('data', 'patches', 'assets'):
            (root / name).mkdir()
        config = root / 'io.json'
        modules = {
            'adc': dict(type='ads1115', address='0x48', state='running', error=None),
            'oled': dict(type='ssd1306', address='0x3c', state='running', error=None),
            'touch': dict(type='mpr121', address='0x5a', state='running', error=None),
        }
        config.write_text(json.dumps(dict(bus=1, scanned=True, addresses=[], modules=modules)))
        http = free_port(socket.SOCK_STREAM)
        report, command, stream = [free_port(socket.SOCK_DGRAM) for _ in range(3)]
        base = 'http://127.0.0.1:%s' % http
        server = fleet = None
        with (root/'server.log').open('w') as server_log, (root/'fleet.log').open('w') as fleet_log:
            try:
                server = subprocess.Popen([sys.executable, str(Path(REPO)/'dashboard/server.py'),
                    '--host', '127.0.0.1', '--port', str(http), '--listen-port', str(report),
                    '--send-port', str(command), '--stream-port', str(stream), '--osc-target', '127.0.0.1',
                    '--data-dir', str(root/'data'), '--patches-dir', str(root/'patches'),
                    '--assets-dir', str(root/'assets'), '--sim-no-engine'], cwd=REPO,
                    stdout=server_log, stderr=subprocess.STDOUT)
                wait_http(base, server)
                fleet = subprocess.Popen([sys.executable, str(Path(REPO)/'tools/simfleet.py'),
                    '--devices', '2', '--unassigned', '2', '--boot-secs', '0', '--hb-interval', '.3',
                    '--target', '127.0.0.1', '--report-port', str(report), '--cmd-port', str(command),
                    '--stream-port', str(stream), '--io-config', str(config)], cwd=REPO,
                    stdout=fleet_log, stderr=subprocess.STDOUT)
                with sync_playwright() as pw:
                    browser = pw.chromium.launch(headless=True)
                    context = browser.new_context(viewport={'width':1440, 'height':1000})
                    errors = []
                    context.on('page', lambda tab: tab.on('pageerror', lambda error: errors.append(str(error))))
                    page = context.new_page()
                    page.goto(base+'#devices')
                    page.wait_for_function('uid => !!installation.devices[uid]?.report?.io?.modules?.adc', arg=UID_A)
                    page.wait_for_function('Object.keys(installation.devices).length === 2')
                    page.locator('#device-roster .device-row[data-uid="%s"] strong' % UID_A).click()
                    page.evaluate('''() => {
                        window.writes=[];
                        const send=ws.send.bind(ws);
                        ws.send=(type,data)=>{if(type==='io_write')writes.push(data);send(type,data)};
                    }''')
                    def check(name):
                        page.locator('#device-io [data-io-monitor="%s"]' % name).check()
                    check('adc')
                    adc = page.locator('.module-panel[data-module-name="adc"]')
                    page.wait_for_function('ws.acceptedCapture?.modules?.names.includes("adc")')
                    page.wait_for_function('document.querySelector("[data-module-patch]").textContent.startsWith("/adc ")')
                    assert '· live' in adc.locator('[data-module-source]').inner_text()
                    assert adc.locator('[data-module-value]').count() == 4
                    assert adc.locator('[data-module-value="0"]').inner_text().endswith(' V')
                    assert adc.locator('[data-module-close]').get_attribute('title') == 'Close panel'
                    # All three original polls in one broker tick reach the trace.
                    # Stop the fake device so only the deliberately injected bundle
                    # burst can contribute to this section (the source remains online).
                    stop(fleet)
                    fleet = None
                    before = len(adc.locator('[data-module-spark="0"]').get_attribute('d').split('L'))
                    udp = SimpleUDPClient('127.0.0.1', stream)
                    for value in (0., 3.3, 0.):
                        bundle = OscBundleBuilder(IMMEDIATELY)
                        msg = OscMessageBuilder(address='/adc')
                        for channel in [value, 1.25, 2., 3.]:
                            msg.add_arg(channel)
                        bundle.add_content(msg.build())
                        udp.send_message('/io/stream', [UID_A, bundle.build().dgram])
                    page.wait_for_function('before => document.querySelector("[data-module-spark] path, path[data-module-spark]").getAttribute("d").split("L").length >= before+3', arg=before)
                    trace = adc.locator('[data-module-spark="0"]').get_attribute('d')
                    assert '1.25' in adc.locator('[data-module-patch]').inner_text()
                    assert len(trace.split('L')) >= before + 3, trace
                    assert any(float(point.split(',')[1]) < 3 for point in trace.replace('M','L').split('L') if point.strip()), trace
                    bundle = OscBundleBuilder(IMMEDIATELY)
                    msg = OscMessageBuilder(address='/adc')
                    for channel in [1.1, 1.2345678, -0.000012345678, 2000001]:
                        msg.add_arg(channel)
                    bundle.add_content(msg.build())
                    udp.send_message('/io/stream', [UID_A, bundle.build().dgram])
                    page.wait_for_function('document.querySelector("[data-module-patch]").textContent === "/adc 1.1 1.23457 -1.23457e-5 2000001"')
                    assert adc.locator('[data-module-value="0"]').inner_text() == '1.1 V'
                    assert adc.locator('[data-module-value="1"]').inner_text() == '1.23457 V'
                    assert adc.locator('[data-module-value="3"]').inner_text() == '2000001 V'
                    assert '1.100000023841858' not in adc.inner_text()
                    exact = struct.unpack('!f', struct.pack('!f', 1.1))[0]
                    last_y = float(adc.locator('[data-module-spark="0"]').get_attribute('d').strip().split(',')[-1])
                    assert abs(last_y - (30 - exact / 3.3 * 28)) < 1e-12
                    # Hidden choices survive while the source consumer closes.
                    page.click('[data-monitor-tab="in"]')
                    page.wait_for_function('ws.acceptedCapture?.modules === null')
                    assert page.locator('#device-io [data-io-monitor="adc"]').is_checked()
                    page.click('[data-monitor-tab="modules"]')
                    page.wait_for_function('ws.acceptedCapture?.modules?.uid')
                    page.click('[data-monitor-collapse]')
                    page.wait_for_function('ws.acceptedCapture?.modules === null')
                    page.click('[data-monitor-tab="modules"]')
                    page.wait_for_function('ws.acceptedCapture?.modules?.uid')
                    # Resume the fake device for control receipts and continuous IO.
                    fleet = subprocess.Popen([sys.executable, str(Path(REPO)/'tools/simfleet.py'),
                        '--devices', '2', '--unassigned', '2', '--boot-secs', '0', '--hb-interval', '.3',
                        '--target', '127.0.0.1', '--report-port', str(report), '--cmd-port', str(command),
                        '--stream-port', str(stream), '--io-config', str(config)], cwd=REPO,
                        stdout=fleet_log, stderr=subprocess.STDOUT)
                    page.wait_for_timeout(600)
                    check('oled')
                    check('touch')
                    oled = page.locator('.module-panel[data-module-name="oled"]')
                    text = oled.locator('[data-module-command="text"]')
                    text.locator('input').fill('hello module')
                    text.locator('button').click()
                    page.wait_for_function('uid => installation.devices[uid].io_write?.status === "ok"', arg=UID_A)
                    assert page.evaluate('writes[0].config') == dict(name='oled', command='text', args=['hello module'])
                    text.locator('input').fill('invalid\x00text')
                    text.locator('button').click()
                    page.wait_for_function('document.querySelector("[data-module-command=text] [data-module-receipt]").textContent === "invalid-arguments"')
                    assert text.locator('button').is_enabled()
                    text.locator('input').fill('hello module')
                    threshold = page.locator('.module-panel[data-module-name="touch"] [data-module-command="threshold"]')
                    threshold.locator('input').nth(0).fill('12')
                    threshold.locator('input').nth(1).fill('6')
                    threshold.locator('button').click()
                    page.wait_for_function('uid => installation.devices[uid].io_write?.command === "threshold" && installation.devices[uid].io_write.status === "ok"', arg=UID_A)
                    assert page.evaluate('writes.at(-1).config.args') == [12, 6]
                    # Refusing a second UID leaves the first connection subscribed.
                    other = page.evaluate('uid => Object.keys(installation.devices).find(key=>key!==uid)', UID_A)
                    page.locator('#device-roster .device-row[data-uid="%s"] strong' % other).click()
                    page.locator('#device-io [data-io-monitor="adc"]').click()
                    assert not page.locator('#device-io [data-io-monitor="adc"]').is_checked()
                    assert page.evaluate('ws.capture.modules.uid') == UID_A
                    assert 'another device' in page.locator('.module-panels-feedback').inner_text()
                    page.locator('#device-roster .device-row[data-uid="%s"] strong' % UID_A).click()
                    observer = context.new_page()
                    from urllib.parse import urlencode
                    observer.goto(base+'?'+urlencode({'monitor':'panel','module':json.dumps([other,'adc'])}))
                    observer.wait_for_function('document.querySelector(".module-panels-feedback").textContent.includes("another device")')
                    assert page.evaluate('ws.capture.modules.uid') == UID_A
                    observer.close()
                    # Performance disables controls, drops subscriptions, and the
                    # server also rejects a direct browser command without OSC.
                    page.click('#performance-toggle')
                    page.wait_for_function('installation.performance && ws.acceptedCapture?.modules === null')
                    assert text.locator('button').is_disabled()
                    page.evaluate('''() => {window.refused=[];ws.on('error', data=>refused.push(data));ws.send('io_write',writes[0]);}''')
                    page.wait_for_function('refused.some(row=>row.message === "Performance" || row === "Performance")')
                    assert page.evaluate('uid => installation.devices[uid].io_write.command', UID_A) == 'threshold'
                    page.click('#performance-toggle')
                    page.wait_for_function('!installation.performance && ws.acceptedCapture?.modules?.names.length===3')
                    # Single-panel ordinary window uses the same generic component.
                    with page.expect_popup() as opened:
                        oled.locator('[data-module-popout]').click()
                    popup = opened.value
                    popup.wait_for_selector('.module-panel[data-module-name="oled"]')
                    popup.wait_for_function('ws.acceptedCapture?.modules?.names[0]==="oled"')
                    assert popup.locator('.module-panel').count() == 1
                    page.wait_for_function('!ws.capture.modules.names.includes("oled")')
                    popup.close()
                    page.wait_for_function('ws.acceptedCapture?.modules?.names.includes("oled")')
                    with page.expect_popup() as opened:
                        page.click('[data-monitor-popout]')
                    popup = opened.value
                    popup.wait_for_function('ws.acceptedCapture?.modules?.names.length===3')
                    page.wait_for_function('ws.acceptedCapture?.modules===null')
                    assert popup.locator('.module-panel').count() == 3
                    popup.close()
                    page.wait_for_function('ws.acceptedCapture?.modules?.names.length===3')
                    # Reconnect restores current interest; hidden document releases it.
                    generation = page.evaluate('ws.generation')
                    page.evaluate('ws.socket.close()')
                    page.wait_for_function('old => ws.generation>old && ws.acceptedCapture?.modules?.names.length===3', arg=generation)
                    page.evaluate('Object.defineProperty(document,"hidden",{configurable:true,value:true});document.dispatchEvent(new Event("visibilitychange"))')
                    page.wait_for_function('ws.acceptedCapture?.modules===null')
                    page.evaluate('Object.defineProperty(document,"hidden",{configurable:true,value:false});document.dispatchEvent(new Event("visibilitychange"))')
                    page.wait_for_function('ws.acceptedCapture?.modules?.names.length===3')
                    screenshots = sys.argv[1] if len(sys.argv) > 1 else os.environ.get('BOPOS_MODULE_PANELS_SCREENSHOT')
                    for width in (1440, 420):
                        page.set_viewport_size({'width':width, 'height':1000})
                        for _ in range(12):
                            page.locator('.monitor-resize').press('ArrowUp')
                        for theme in ('light','dark'):
                            page.select_option('#theme-select', theme)
                            page.wait_for_timeout(150)
                            assert page.evaluate('document.querySelector("#monitor-dock").scrollWidth <= innerWidth')
                            assert page.evaluate('''() => [...document.querySelectorAll('.module-panel')].every(panel=>panel.scrollWidth<=panel.clientWidth)''')
                            if screenshots:
                                page.screenshot(path=str(Path(screenshots)/('modules-%s-%s.png' % (width, theme))))
                    page.set_viewport_size({'width':1440, 'height':1000})
                    page.click('[data-monitor-collapse]')
                    page.locator('#device-io [data-io-monitor="adc"]').uncheck()
                    page.locator('#device-io [data-io-monitor="oled"]').uncheck()
                    page.locator('#device-io [data-io-monitor="touch"]').uncheck()
                    page.wait_for_function('ws.acceptedCapture?.modules === null')
                    assert page.locator('.module-panel').count() == 0
                    with page.expect_popup() as opened:
                        page.click('[data-monitor-popout]')
                    popup = opened.value
                    popup.wait_for_selector('body.monitor-window', state='attached')
                    assert page.locator('#monitor-dock').evaluate('dock=>dock.classList.contains("is-collapsed")')
                    popup.close()
                    page.wait_for_timeout(600)
                    assert page.locator('#monitor-dock').evaluate('dock=>dock.classList.contains("is-collapsed")')
                    page.reload()
                    assert page.locator('.module-panel').count() == 0
                    assert errors == [], errors
                    browser.close()
                    print('PASS driver metadata, live units/patch values, ordered burst/sparklines, checkbox lifecycle, writes/receipts, one device, Performance refusal, dock/panel windows, reconnect, visibility, viewport/theme and session reset')
            except Exception:
                print((root/'server.log').read_text()[-4000:])
                print((root/'fleet.log').read_text()[-2000:])
                raise
            finally:
                stop(fleet)
                stop(server)


if __name__ == '__main__':
    main()
