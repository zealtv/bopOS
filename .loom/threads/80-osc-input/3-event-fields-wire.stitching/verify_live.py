"""Real dashboard -> UDP -> simfleet typed event smoke check, isolated ports."""
import asyncio
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
sys.dont_write_bytecode = True
ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'tools/simfleet.py').is_file())


def port(kind):
    with socket.socket(socket.AF_INET, kind) as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


async def fire(http):
    import websockets
    async with websockets.connect(f'ws://127.0.0.1:{http}/ws') as ws:
        await ws.send(json.dumps({'type': 'fire_event', 'data': {
            'selector': 'all', 'identity': 'typed/check',
            'elements': ['folder/file', 16777216, -.25, 1], 'lead_ms': 0}}))
        for _ in range(100):
            frame = json.loads(await asyncio.wait_for(ws.recv(), 5))
            if frame['type'] == 'error':
                raise AssertionError(frame)
            if frame['type'] == 'event_scheduled':
                assert frame['data']['elements'] == ['folder/file', 16777216, -.25, 1], frame
                return
        raise AssertionError('no event_scheduled frame')


def main():
    http = port(socket.SOCK_STREAM)
    report, command, stream = (port(socket.SOCK_DGRAM) for _ in range(3))
    processes = []
    with tempfile.TemporaryDirectory(prefix='bopos-typed-live-') as temporary:
        temporary = Path(temporary)
        try:
            with (temporary / 'dashboard.log').open('w') as dashlog, (temporary / 'simfleet.log').open('w') as simlog:
                processes.append(subprocess.Popen([
                    sys.executable, '-u', str(ROOT / 'dashboard/server.py'),
                    '--host', '127.0.0.1', '--port', str(http),
                    '--listen-port', str(report), '--send-port', str(command),
                    '--stream-port', str(stream), '--osc-target', '127.0.0.1',
                    '--data-dir', str(temporary / 'data')], cwd=ROOT,
                    stdout=dashlog, stderr=subprocess.STDOUT))
                for _ in range(100):
                    try:
                        urllib.request.urlopen(f'http://127.0.0.1:{http}/', timeout=.2).close()
                        break
                    except OSError:
                        time.sleep(.1)
                else:
                    raise AssertionError((temporary / 'dashboard.log').read_text())
                processes.append(subprocess.Popen([
                    sys.executable, '-u', str(ROOT / 'tools/simfleet.py'),
                    '--devices', '1', '--target', '127.0.0.1',
                    '--cmd-port', str(command), '--report-port', str(report),
                    '--stream-port', str(stream), '--boot-secs', '0',
                    '--hb-interval', '.2'], cwd=ROOT,
                    stdout=simlog, stderr=subprocess.STDOUT))
                time.sleep(1)
                asyncio.run(fire(http))
                for _ in range(50):
                    output = (temporary / 'simfleet.log').read_text()
                    if 'event typed/check fired' in output:
                        line = next(line for line in output.splitlines() if 'event typed/check fired' in line)
                        assert 'elements=folder/file 1.67772e+07 -0.25 1' in line, line
                        print(line)
                        print('PASS: real dashboard websocket -> typed UDP -> simfleet receipt; isolated ephemeral ports')
                        return
                    time.sleep(.1)
                raise AssertionError(output)
        finally:
            for process in reversed(processes):
                process.terminate()
            for process in reversed(processes):
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()


if __name__ == '__main__':
    main()
