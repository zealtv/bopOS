"""Refresh current Control guide images from an isolated two-Seat fixture."""
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
sys.dont_write_bytecode = True
ROOT = Path.cwd()
sys.path.insert(0, str(ROOT / 'tests'))
from verify_control_tab import make_fixture, free_port, wait_http, stop_process
from playwright.sync_api import sync_playwright

with tempfile.TemporaryDirectory(prefix='bopos-control-images-') as temporary:
    state = make_fixture(temporary)
    http, listen, send = [free_port(kind) for kind in (socket.SOCK_STREAM, socket.SOCK_DGRAM, socket.SOCK_DGRAM)]
    patches = str(Path(temporary) / 'patches')
    assets = str(Path(temporary) / 'assets')
    url = f'http://127.0.0.1:{http}'
    processes = []
    with open(Path(temporary) / 'server.log', 'w') as log:
        try:
            processes.append(subprocess.Popen([sys.executable, str(ROOT / 'dashboard/server.py'), '--host', '127.0.0.1', '--port', str(http), '--listen-port', str(listen), '--send-port', str(send), '--osc-target', '127.0.0.1', '--state-file', state, '--patches-dir', patches, '--assets-dir', assets, '--public-url', url], stdout=log, stderr=subprocess.STDOUT))
            wait_http(url, processes[0])
            processes.append(subprocess.Popen([sys.executable, str(ROOT / 'tools/simfleet.py'), '--devices', '2', '--target', '127.0.0.1', '--report-port', str(listen), '--cmd-port', str(send), '--hb-interval', '0.5', '--boot-secs', '0.2', '--patches-dir', patches, '--assets-dir', assets, '--manifest', str(Path(patches) / 'alpha/bopos.patch.json')], stdout=log, stderr=subprocess.STDOUT))
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page(viewport={'width': 1440, 'height': 960})
                errors = []
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.goto(url + '#control')
                page.wait_for_selector('#ws-status.online')
                page.wait_for_selector('.live-card[data-live-scope="all"] [data-live-param]')
                page.wait_for_function('() => Object.values(installation.devices || {}).filter(d => d.online).length === 2')
                page.screenshot(path=str(ROOT / 'docs/images/tab-dashboard.png'))
                picker = page.locator('#control-column-host .target-picker')
                picker.locator('summary').click()
                picker.locator('[data-target-toggle="1"]').click()
                picker.locator('summary').click()
                page.wait_for_selector('.live-card[data-live-scope="seat"] [data-live-param]')
                page.screenshot(path=str(ROOT / 'docs/images/tab-dashboard-seats.png'))
                assert not errors, errors
                browser.close()
        finally:
            for process in reversed(processes):
                stop_process(process)
