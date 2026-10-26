"""Outside UDP -> real dashboard -> simfleet stamped event smoke check, isolated ports."""
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


def fire(input_port):
    from pythonosc.udp_client import SimpleUDPClient
    SimpleUDPClient('127.0.0.1', input_port).send_message('/all/typed/check', ['folder/file', 2])


def main():
    http = port(socket.SOCK_STREAM)
    report, command, stream, input_port = (port(socket.SOCK_DGRAM) for _ in range(4))
    processes = []
    with tempfile.TemporaryDirectory(prefix='bopos-typed-live-') as temporary:
        temporary = Path(temporary)
        sys.path.insert(0, str(ROOT / 'dashboard'))
        sys.path.insert(0, str(ROOT))
        from state import InstallationState
        state = InstallationState(str(temporary / 'data'), None)
        state.data['fleet_patch'] = {'name': 'input-test', 'fingerprint': 'unknown'}
        state.data['event_lead_ms'] = 150
        state.save()
        patch = temporary / 'patches' / 'input-test'
        patch.mkdir(parents=True)
        (patch / 'main.scd').touch()
        (patch / 'bopos.patch.json').write_text(json.dumps({
            'engine': 'sc', 'entrypoint': 'main.scd', 'events': [{
                'path': ['typed'], 'name': 'check', 'fields': [
                    {'name': 'file', 'kind': 'text'},
                    {'name': 'gain', 'kind': 'float', 'min': 0, 'max': 1},
                    {'name': 'mode', 'kind': 'toggle', 'optional': True, 'default': 1}]}]}))
        try:
            with (temporary / 'dashboard.log').open('w') as dashlog, (temporary / 'simfleet.log').open('w') as simlog:
                processes.append(subprocess.Popen([
                    sys.executable, '-u', str(ROOT / 'dashboard/server.py'),
                    '--host', '127.0.0.1', '--port', str(http),
                    '--listen-port', str(report), '--send-port', str(command),
                    '--stream-port', str(stream), '--input-port', str(input_port),
                    '--patches-dir', str(temporary / 'patches'), '--osc-target', '127.0.0.1',
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
                    '--devices', '2', '--target', '127.0.0.1',
                    '--cmd-port', str(command), '--report-port', str(report),
                    '--stream-port', str(stream), '--boot-secs', '0',
                    '--hb-interval', '.2'], cwd=ROOT,
                    stdout=simlog, stderr=subprocess.STDOUT))
                time.sleep(1)
                fire(input_port)
                for _ in range(50):
                    output = (temporary / 'simfleet.log').read_text()
                    lines = [line for line in output.splitlines() if 'event typed/check fired' in line]
                    if len(lines) >= 2:
                        assert any('sim1 ' in line for line in lines), lines
                        assert any('sim2 ' in line for line in lines), lines
                        for line in lines:
                            assert 'elements=folder/file 1 1' in line, line
                            assert 'dev_deadline=0 ' not in line, line
                            assert ' LATE' not in line, line
                            print(line)
                        print('PASS: outside UDP -> dashboard stamp, clamp and default -> simfleet on two nodes; isolated ephemeral ports')
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
