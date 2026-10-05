"""Real dashboard/browser and UDP doors; fake device and no audio engine.

Optional argument: main-tree stitch directory for four viewport/theme captures.
"""
import json
from pathlib import Path
import select
import socket
import subprocess
import sys
import tempfile
import threading
import time

from playwright.sync_api import sync_playwright
from pythonosc.osc_message import OscMessage
from pyOSC3 import OSCBundle, OSCMessage, decodeOSC
from verify_device_control_modes import physical_host, packet, drain_socket
from verify_patches_tab import REPO, UID_A, UID_B, free_port, stop, wait_http
from project_fixture import project_path, data_root

sys.dont_write_bytecode = True


class Peer:
    def __init__(self, command, report, stream, modules):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((physical_host(), command))
        self.sock.settimeout(.05)
        self.report_port, self.stream_port, self.modules = report, stream, modules
        self.running, self.active = True, False
        self.frames = []
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def send(self, address, *args):
        self.sock.sendto(packet(address, *args), ('127.0.0.1', self.report_port))

    def bundle(self, value):
        bundle = OSCBundle()
        for name, values in [('adc', [value, 1.25, 2., 3.]), ('oled', [])]:
            message = OSCMessage('/'+name)
            for atom in values:
                message.append(atom)
            bundle.append(message)
        return bundle.getBinary()

    def inject(self, bundle):
        self.sock.sendto(packet('/io/stream', UID_A, bundle), ('127.0.0.1', self.stream_port))

    def run(self):
        next_report = 0
        while self.running:
            if time.monotonic() >= next_report:
                for uid in (UID_A, UID_B):
                    self.send('/hb', uid, -1, 'io-test', 1)
                    self.send('/os/report', json.dumps(dict(uid=uid, hostname='ciro-toast',
                        engine='test', patch='alpha', performance=False, io=dict(
                            bus=1, scanned=True, addresses=[], modules=self.modules))))
                next_report = time.monotonic() + .3
            try:
                message = OscMessage(self.sock.recvfrom(65535)[0])
                args = message.params
                self.frames.append((message.address, args))
                if message.address == '/all/os/to' and len(args) >= 3 and args[1] == 'io-stream':
                    self.active = bool(args[2])
                    self.send('/os/io-stream', args[0], 'ok', json.dumps(dict(active=self.active, error=None)))
            except socket.timeout:
                pass

    def close(self):
        self.running = False
        self.thread.join(timeout=1)
        self.sock.close()


def polls(sock, duration=.45):
    rows = []
    end = time.monotonic()+duration
    while time.monotonic() < end:
        if select.select([sock], [], [], max(0, end-time.monotonic()))[0]:
            data = sock.recvfrom(65535)[0]
            if data.startswith(b'#bundle\0'):
                rows.append(decodeOSC(data)[2:])
    return rows


def main():
    screenshots = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    with tempfile.TemporaryDirectory(prefix='bopos-editor-input-') as temporary:
        root = Path(temporary)
        for name in ('assets', 'patches'):
            (root/name).mkdir()
        patch = root/'patches'/'alpha'
        patch.mkdir()
        (patch/'main.bin').write_bytes(b'test engine')
        declarations = [dict(name='adc', type='ads1115', address='0x48'),
                        dict(name='oled', type='ssd1306', address='0x3c')]
        (patch/'bopos.patch.json').write_text(json.dumps(dict(engine='test', entrypoint='main.bin',
            params=[], caps=[], slots=[], io_modules=declarations)))
        project = project_path(root/'data')
        project.write_text(json.dumps(dict(schema=1, patches=['alpha'], seats={})))
        http = free_port(socket.SOCK_STREAM)
        command, report, stream = [free_port(socket.SOCK_DGRAM) for _ in range(3)]
        base = 'http://127.0.0.1:%s' % http
        server = peer = None
        engine = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        engine.bind(('127.0.0.1', 6662))
        with (root/'server.log').open('w') as log:
            try:
                server = subprocess.Popen([sys.executable, str(Path(REPO)/'dashboard/server.py'),
                    '--host', '127.0.0.1', '--port', str(http), '--listen-port', str(report),
                    '--send-port', str(command), '--stream-port', str(stream),
                    '--osc-target', physical_host(), '--data-dir', data_root(project),
                    '--patches-dir', str(root/'patches'), '--assets-dir', str(root/'assets'),
                    '--sim-no-engine'], cwd=REPO, stdout=log, stderr=subprocess.STDOUT)
                wait_http(base, server)
                modules = {row['name']: dict(type=row['type'], address=row['address'], state='running', error=None)
                           for row in declarations}
                peer = Peer(command, report, stream, modules)
                with sync_playwright() as pw:
                    browser = pw.chromium.launch(headless=True)
                    context = browser.new_context(viewport=dict(width=1440, height=1000))
                    errors = []
                    context.on('page', lambda tab: tab.on('pageerror', lambda error: errors.append(str(error))))
                    page = context.new_page()
                    page.on('dialog', lambda dialog: dialog.accept())
                    page.set_default_timeout(10000)
                    page.goto(base+'#patches')
                    page.evaluate('window.serverErrors=[];ws.on("error", data=>serverErrors.push(data))')
                    page.wait_for_function('uid => !!installation.devices[uid]?.report?.io?.modules?.adc', arg=UID_A)
                    page.evaluate("ws.send('set_edit',{active:true,patch:'alpha',confirmed:true})")
                    page.wait_for_function('installation.supervisor?.mode === "edit" && installation.editor?.active')
                    picker = page.locator('#editor-input-source')
                    assert picker.is_visible()
                    # A device chosen before its inventory gets panels when modules arrive,
                    # and loses them when they go.
                    live = '.module-panel[data-module-uid="%s"]' % UID_A
                    peer.modules = {}
                    page.wait_for_function('uid => !Object.keys(installation.devices[uid].report.io.modules).length', arg=UID_A)
                    picker.select_option(UID_A)
                    page.wait_for_function('uid => installation.editor.input.source === uid', arg=UID_A)
                    assert page.locator(live).count() == 0
                    peer.modules = {'adc': modules['adc']}
                    page.wait_for_function('selector => document.querySelectorAll(selector).length === 1', arg=live)
                    peer.modules = modules
                    page.wait_for_function('selector => document.querySelectorAll(selector).length === 2', arg=live)
                    peer.modules = {'oled': modules['oled']}
                    page.wait_for_function('selector => document.querySelectorAll(selector).length === 1', arg=live)
                    assert page.locator(live).get_attribute('data-module-name') == 'oled'
                    peer.modules = modules
                    page.wait_for_function('selector => document.querySelectorAll(selector).length === 2', arg=live)
                    page.wait_for_function('uid => ws.acceptedCapture?.modules?.uid === uid', arg=UID_A)
                    assert '· live' in page.locator('[data-module-source]').first.inner_text()
                    original = peer.bundle(1.2345678)
                    peer.inject(original)
                    assert select.select([engine], [], [], 2)[0]
                    assert engine.recvfrom(65535)[0] == original
                    page.wait_for_function('document.querySelector("[data-module-patch]").textContent.includes("1.23457")')
                    # Hiding visual interest keeps the independent editor feed.
                    page.click('[data-monitor-collapse]')
                    page.wait_for_function('ws.acceptedCapture?.modules === null')
                    peer.inject(original)
                    assert select.select([engine], [], [], 2)[0]
                    assert engine.recvfrom(65535)[0] == original
                    picker.select_option(UID_B)
                    page.wait_for_function('uid => installation.editor.input.source === uid && ws.acceptedCapture?.modules?.uid === uid', arg=UID_B)
                    picker.select_option(UID_A)
                    page.wait_for_function('uid => installation.editor.input.source === uid && ws.acceptedCapture?.modules?.uid === uid', arg=UID_A)
                    picker.select_option('')
                    page.wait_for_function('installation.editor.input.source === null')
                    deadline = time.monotonic()+2
                    while peer.active and time.monotonic() < deadline:
                        time.sleep(.02)
                    assert not peer.active
                    peer.inject(original)
                    assert not polls(engine, .25)
                    # A panel consumer still owns the sole real-device stream.
                    page.evaluate('uid => ModulesMonitor.toggle(uid,"adc",true)', UID_A)
                    page.wait_for_function('uid => ws.acceptedCapture?.modules?.uid === uid', arg=UID_A)
                    picker.select_option(UID_B)
                    page.wait_for_function('document.querySelector(".module-panels-feedback").textContent.includes("another device")', timeout=1500)
                    assert page.evaluate('installation.editor.input.source') is None
                    page.evaluate('uid => ModulesMonitor.toggle(uid,"adc",false)', UID_A)
                    page.wait_for_function('ws.acceptedCapture?.modules === null')
                    picker.select_option('simulated')
                    page.wait_for_function('installation.editor.input.source === "simulated"')
                    adc = page.locator('.module-panel[data-module-name="adc"][data-module-uid="simulated"]')
                    pad = adc.locator('[data-module-pad="0"]')
                    page.wait_for_function('document.querySelector("[data-module-pad]") && !document.querySelector("[data-module-pad]").disabled')
                    drain_socket(engine)
                    baseline = polls(engine)
                    assert len(baseline) >= 3, baseline
                    assert all(row[0][2:] == [0.,0.,0.,0.] for row in baseline)
                    # Reconnect callbacks before a fresh sample leave drive/release inert.
                    stale = page.evaluate('''() => {
                        const panel=document.querySelector('.module-panel[data-module-uid="simulated"][data-module-name="adc"]');
                        const slider=panel.querySelector('[data-module-slider="0"]'), pad=panel.querySelector('[data-module-pad="1"]');
                        const key={key:' ', preventDefault(){}}, thrown=[];
                        pad.onkeydown(key);
                        ws.emit('connection',false); ws.emit('connection',true);
                        const enabled=!slider.disabled || !pad.disabled;
                        try {slider.value=2; slider.oninput();} catch(error) {thrown.push(String(error));}
                        try {pad.onkeyup(key);} catch(error) {thrown.push(String(error));}
                        return {enabled, thrown};
                    }''')
                    assert stale == dict(enabled=False, thrown=[]), stale
                    page.wait_for_function('!document.querySelector("[data-module-slider]").disabled')
                    slider = adc.locator('[data-module-slider="1"]')
                    slider.evaluate('(slider)=>{slider.value=3.3;slider.dispatchEvent(new Event("input"))}')
                    page.wait_for_function('document.querySelectorAll("[data-module-value]")[1].textContent.startsWith("3.3")')
                    drain_socket(engine)
                    pad.focus()
                    page.keyboard.down('Space')
                    held = polls(engine, .3)
                    page.keyboard.up('Space')
                    released = polls(engine, .3)
                    assert any(row[0][2] > 3.29 for row in held), held
                    assert any(row[0][2] == 0 for row in released), released
                    high_pad = adc.locator('[data-module-pad="1"]')
                    high_pad.focus()
                    page.keyboard.down('Space')
                    held = polls(engine, .3)
                    page.keyboard.up('Space')
                    released = polls(engine, .3)
                    assert any(row[0][3] == 0 for row in held), held
                    assert any(row[0][3] > 3.29 for row in released), released
                    # Real patch-to-bridge commands drive the same component backwards.
                    engine.sendto(packet('/io/oled', 'text', 'hello patch'), ('127.0.0.1', 8880))
                    engine.sendto(packet('/io/oled', 'line', 2, 'second row'), ('127.0.0.1', 8880))
                    page.wait_for_function('document.querySelector("[data-module-oled]").textContent.includes("second row")')
                    assert 'hello patch' in page.locator('[data-module-oled]').inner_text()
                    with page.expect_popup() as opened:
                        adc.locator('[data-module-popout]').click()
                    popup = opened.value
                    popup.wait_for_function('document.querySelector("[data-module-pad]") && !document.querySelector("[data-module-pad]").disabled')
                    assert popup.locator('[data-module-source]').inner_text() == 'simulated'
                    popup.locator('[data-module-slider="2"]').evaluate('(slider)=>{slider.value=1.234567;slider.dispatchEvent(new Event("input"))}')
                    popup.wait_for_function('document.querySelectorAll("[data-module-value]")[2].textContent === "1.23457 V"')
                    popup.close()
                    page.wait_for_function('!document.querySelector(".module-panel[data-module-name=adc]").hidden')
                    page.click('[data-monitor-collapse]')
                    drain_socket(engine)
                    assert len(polls(engine)) >= 3
                    page.click('[data-monitor-tab="modules"]')
                    for width in (1440, 420):
                        page.set_viewport_size(dict(width=width, height=1000))
                        for _ in range(12):
                            page.locator('.monitor-resize').press('ArrowUp')
                        for theme in ('light', 'dark'):
                            page.select_option('#theme-select', theme)
                            page.wait_for_timeout(150)
                            if width == 420:
                                page.locator('#editor-input-control').scroll_into_view_if_needed()
                            assert page.evaluate('document.querySelector("#monitor-dock").scrollWidth <= innerWidth')
                            assert page.evaluate('[...document.querySelectorAll(".module-panel")].every(panel=>panel.scrollWidth<=panel.clientWidth)')
                            if screenshots:
                                page.screenshot(path=str(screenshots/('editor-input-%s-%s.png' % (width, theme))))
                    # Owner loss releases feed; a new connection does not resurrect it.
                    page.set_viewport_size(dict(width=1440, height=1000))
                    old = page.evaluate('ws.generation')
                    page.evaluate('ws.socket.close()')
                    page.wait_for_function('old => ws.generation > old && installation.editor.input.source === null', arg=old)
                    drain_socket(engine)
                    assert polls(engine, .25) == []
                    picker.select_option('simulated')
                    page.wait_for_function('document.querySelector("[data-module-pad]") && !document.querySelector("[data-module-pad]").disabled')
                    drain_socket(engine)
                    assert all(row[0][2:] == [0.,0.,0.,0.] for row in polls(engine))
                    assert page.locator('[data-module-oled]').inner_text() == ''
                    generation = page.evaluate('installation.editor.generation')
                    page.evaluate("ws.send('set_edit',{active:false,confirmed:true})")
                    page.wait_for_function('!installation.editor.active && installation.editor.input.source === null')
                    drain_socket(engine)
                    assert polls(engine, .25) == []
                    page.evaluate("ws.send('set_edit',{active:true,patch:'alpha',confirmed:true})")
                    page.wait_for_function('old => installation.editor.active && installation.editor.generation > old', arg=generation)
                    picker.select_option('simulated')
                    page.wait_for_function('document.querySelector("[data-module-pad]") && !document.querySelector("[data-module-pad]").disabled')
                    page.click('#performance-toggle')
                    page.wait_for_function('installation.performance && !installation.editor.active && installation.editor.input.source === null')
                    drain_socket(engine)
                    assert polls(engine, .25) == []
                    page.evaluate("ws.send('set_editor_input',{source:'simulated'})")
                    page.wait_for_timeout(200)
                    assert page.evaluate('installation.editor.input.source') is None
                    assert errors == [], errors
                    browser.close()
                print('PASS late and removed live modules, inert drive before a fresh sample after reconnect, original-bundle forwarding, shared stream/refusal, hidden visual feed, unpick, continuous simulated rest, per-channel opposite rails, OLED commands, pop-out control, six-digit display, four screenshots, disconnect/session reset and Performance')
            except Exception:
                print((root/'server.log').read_text()[-5000:])
                try:
                    print(page.evaluate('({editor:installation.editor,supervisor:installation.supervisor,errors:serverErrors})'))
                except Exception:
                    pass
                raise
            finally:
                if peer:
                    peer.close()
                stop(server)
                engine.close()


if __name__ == '__main__':
    main()
