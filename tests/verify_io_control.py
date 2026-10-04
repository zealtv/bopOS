#!/usr/bin/env python3
"""Browser-tier IO integration: real bridge/node OSC and dashboard/simfleet."""
import asyncio
import json
import importlib.util
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from types import SimpleNamespace
from unittest.mock import patch

sys.dont_write_bytecode = True
ROOT = next(parent for parent in Path(__file__).resolve().parents
            if (parent / 'tools/simfleet.py').is_file())


def port(kind):
    with socket.socket(socket.AF_INET, kind) as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def stop(process):
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def local_journey():
    """Real OSC sockets and bridge/node helpers, with only chip access faked."""
    sys.path[:0] = [str(ROOT / 'python'), str(ROOT / 'python/io')]
    from pyOSC3 import OSCServer, OSCMessage, decodeOSC
    from io_control import IOControl
    spec = importlib.util.spec_from_file_location('bridge_fixture', ROOT / 'python/io/main.py')
    bridge = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bridge)
    bridge.usable_bus = lambda: True
    bridge.have_bus = lambda: True
    rows = [{'address': '0x1a', 'claimed': True}, {'address': '0x48', 'claimed': False}]
    bridge.scan_inventory = lambda bus, skip: (True, rows)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as engine, \
            socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as lan, \
            socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sender:
        engine.bind(('127.0.0.1', 0))
        lan.bind(('127.0.0.1', 0))
        engine.settimeout(5)
        lan.settimeout(5)
        bridge.PD_PORT = engine.getsockname()[1]
        bridge.CONTROL_PORT = port(socket.SOCK_DGRAM)
        command_port = port(socket.SOCK_DGRAM)
        manager = bridge.IOManager()
        writes = []
        manager.peripherals['adc'] = SimpleNamespace(address=0x48,
            write_data=lambda **kwargs: writes.append(kwargs), read_data=lambda: [1.0])
        manager.io['modules']['adc'] = {'type': 'ads1115', 'address': '0x48',
                                        'state': 'running', 'error': None}

        def send(address, values, target):
            message = OSCMessage(address)
            for value in values:
                message.append(value)
            sender.sendto(message.getBinary(), target)

        control = IOControl('local-node',
            lambda address, values: send(address, values, ('127.0.0.1', command_port)),
            lambda name, reason: send('/os/io-error', ['local-node', name, reason], lan.getsockname()))
        class LANReply:
            def sendto(self, data, target):
                assert target == ('127.0.0.1', 5550)
                sender.sendto(data, lan.getsockname())
        reply = LANReply()
        node_server = OSCServer(('127.0.0.1', bridge.CONTROL_PORT))
        node_server.addMsgHandler('default', lambda path, tags, args, source: control.handle(path, args))
        bridge_server = OSCServer(('127.0.0.1', command_port))
        bridge_server.addMsgHandler('default', manager.handle_command)
        threads = [threading.Thread(target=server.serve_forever, daemon=True)
                   for server in (node_server, bridge_server)]
        try:
            for thread in threads:
                thread.start()
            for _ in range(2):
                control.request('scan', None, reply, '127.0.0.1')
            for name in ('adc', 'unknown'):
                control.request('write', json.dumps({'name': name, 'command': 'clear', 'args': []}),
                                reply, '127.0.0.1')
            received = [decodeOSC(lan.recvfrom(65535)[0]) for _ in range(5)]
            scans = [message for message in received if message[0] == '/os/io-scan']
            receipts = [message for message in received if message[0] == '/os/io-write']
            assert len(scans) == 2 and all(json.loads(message[3])['addresses'] == rows for message in scans)
            assert [message[3] for message in receipts] == ['ok', 'err']
            assert any(message[0] == '/os/io-error' and message[2:] ==
                       ['local-node', 'unknown', 'unknown-command'] for message in received)
            assert writes == [{'command': 'clear', 'args': []}]
            engine_messages = []
            while not {'/io/scanned', '/io/written', '/io/error'} <= set(engine_messages):
                engine_messages.append(decodeOSC(engine.recvfrom(65535)[0])[0])
            assert not control.pending['scan'] and not control.pending['write']
            print('PASS: real localhost bridge/node OSC, FIFO scans/writes, dual replies and unsolicited error relay (chip access faked)')
            declaration = {'name': 'adc', 'type': 'ads1115', 'address': '0x48'}
            with patch.object(bridge.patch_manifest, 'load', return_value=({'io_modules': [declaration]}, None)):
                for kind, address in [('wrong-type', '0x48'), ('ads1115', '0x49')]:
                    send('/io/create', ['adc', kind, address], ('127.0.0.1', command_port))
                    error = decodeOSC(lan.recvfrom(65535)[0])
                    assert error == ['/os/io-error', ',sss', 'local-node', 'adc', 'create-failed'], error
                assert control.snapshot()['modules']['adc'] == {
                    'type': 'ads1115', 'address': '0x48', 'state': 'running', 'error': None}
                send('/io/create', ['bad', 'wrong-type', '0x48'], ('127.0.0.1', command_port))
                assert decodeOSC(lan.recvfrom(65535)[0])[2:] == ['local-node', 'bad', 'create-failed']
            print('PASS: wrong type/address create failures reach unsolicited LAN error replies; declared live chip stays healthy')
            def recreate(name, kind, address):
                manager.peripherals[name] = SimpleNamespace(address=address, cleanup=lambda: None,
                    read_data=lambda: [1.0], write_data=lambda **kwargs: writes.append(kwargs))
                return True
            manager.peripherals['adc'].cleanup = lambda: None
            with patch.object(bridge.patch_manifest, 'load', return_value=({'io_modules': [declaration]}, None)), \
                    patch.object(manager, '_create_peripheral', side_effect=recreate):
                control.write_allowed = lambda: False
                control.request('reinit', 'adc', reply, '127.0.0.1')
                receipt = decodeOSC(lan.recvfrom(65535)[0])
                assert receipt[:4] == ['/os/io-reinit', ',sss', 'local-node', 'ok'], receipt
                assert json.loads(receipt[4]) == {'name': 'adc', 'error': None}
                assert control.snapshot()['modules']['adc']['state'] == 'running'
            print('PASS: real node/bridge Re-init receipt and registry refresh while Performance forbids writes (chip setup faked)')
        finally:
            control.close()
            node_server.close()
            bridge_server.close()
            for thread in threads:
                thread.join(timeout=2)


async def journey(http_port):
    import websockets
    async with websockets.connect(f'ws://127.0.0.1:{http_port}/ws') as ws:
        pending = []
        async def until(predicate):
            async def receive():
                while True:
                    if pending:
                        event = pending.pop(0)
                    else:
                        event = json.loads(await ws.recv())
                        if event['type'] == 'telemetry':
                            pending.extend(event['data']['entries'])
                            continue
                    if predicate(event):
                        return event
            return await asyncio.wait_for(receive(), timeout=15)

        discovered = set()
        def discovery(event):
            if event['type'] == 'state':
                discovered.update(event['data']['devices'])
            elif event['type'] == 'device_update':
                discovered.add(event['data']['uid'])
            return len(discovered) >= 2
        await until(discovery)
        first, second = sorted(discovered)
        for uid in (first, second):
            await ws.send(json.dumps({'type': 'io_scan', 'data': {'uid': uid}}))
            event = await until(lambda event: event['type'] == 'report'
                                and event['data']['uid'] == uid
                                and (event['data'].get('report', {}).get('io') or {}).get('scanned'))
            io = event['data']['report']['io']
            assert io['bus'] == 1
            assert io['addresses'] == [{'address': '0x1a', 'claimed': True},
                                       {'address': '0x48', 'claimed': False}]
            assert io['modules']['adc']['state'] == 'running'
        payload = {'name': 'adc', 'command': 'threshold', 'args': [15, 8]}
        await ws.send(json.dumps({'type': 'io_write', 'data': {'uid': first, 'config': payload}}))
        event = await until(lambda event: event['type'] == 'report'
                            and event['data']['uid'] == first
                            and (event['data'].get('io_write') or {}).get('status') == 'ok')
        assert event['data']['io_write'] == {'name': 'adc', 'command': 'threshold',
                                           'error': None, 'status': 'ok'}
        payload['name'] = 'unknown'
        await ws.send(json.dumps({'type': 'io_write', 'data': {'uid': second, 'config': payload}}))
        event = await until(lambda event: event['type'] == 'report'
                            and event['data']['uid'] == second
                            and (event['data'].get('io_error') or {}).get('error') == 'unknown-command')
        assert event['data']['io_write']['status'] == 'err'

        async def set_performance(active):
            await ws.send(json.dumps({'type': 'set_performance', 'data': {'active': active}}))
            confirmed = set()
            def converged(event):
                if (event['type'] == 'report' and event['data']['uid'] in (first, second)
                        and event['data'].get('report', {}).get('performance') is active):
                    confirmed.add(event['data']['uid'])
                return len(confirmed) == 2
            await until(converged)

        await set_performance(True)
        payload['name'] = 'adc'
        await ws.send(json.dumps({'type': 'io_write', 'data': {'uid': first, 'config': payload}}))
        event = await until(lambda event: event['type'] == 'report'
                            and event['data']['uid'] == first
                            and (event['data'].get('io_write') or {}).get('error') == 'performance')
        assert event['data']['io_write'] == {'name': 'adc', 'command': 'threshold',
                                           'error': 'performance', 'status': 'err'}
        module = event['data']['report']['io']['modules']['adc']
        assert module['state'] == 'running' and module['error'] is None
        assert not event['data'].get('io_error')
        await ws.send(json.dumps({'type': 'io_scan', 'data': {'uid': first}}))
        await until(lambda event: event['type'] == 'device_update'
                    and event['data']['uid'] == first and event['data'].get('io_scan_pending'))
        event = await until(lambda event: event['type'] == 'report'
                            and event['data']['uid'] == first
                            and event['data'].get('io_scan_pending') is False)
        assert event['data']['report']['performance'] is True
        assert event['data']['io_scan']['status'] == 'ok'
        await set_performance(False)
        await ws.send(json.dumps({'type': 'io_write', 'data': {'uid': first, 'config': payload}}))
        event = await until(lambda event: event['type'] == 'report'
                            and event['data']['uid'] == first
                            and (event['data'].get('io_write') or {}).get('status') == 'ok')
        assert event['data']['io_write']['error'] is None
        print('PASS: real dashboard/simfleet Performance refusal receipt, healthy module, allowed scan and unlocked write')
        # A fresh client sees the observed IO facts in its initial snapshot.
    async with websockets.connect(f'ws://127.0.0.1:{http_port}/ws') as ws:
        snapshot = json.loads(await asyncio.wait_for(ws.recv(), 10))
        assert snapshot['type'] == 'state'
        for uid in (first, second):
            assert snapshot['data']['devices'][uid]['report']['io']['scanned']
    print('PASS: two exact-UID scans, sorted/claimed inventory, write success/error, unsolicited error and reconnect snapshot')


def main():
    local_journey()
    http_port, report_port, command_port = (port(socket.SOCK_STREAM),
                                            port(socket.SOCK_DGRAM), port(socket.SOCK_DGRAM))
    with tempfile.TemporaryDirectory(prefix='bopos-io-control-') as temporary:
        work = Path(temporary)
        for name in ('patches', 'assets', 'data'):
            (work / name).mkdir()
        manifest = work / 'fixture.json'
        manifest.write_text(json.dumps({'name': 'IO fixture', 'engine': 'pd',
                                        'entrypoint': 'main.pd', 'params': []}))
        config = work / 'io.json'
        config.write_text(json.dumps({'bus': 1, 'scanned': False,
                                      'addresses': [{'address': '0x48', 'claimed': False},
                                                    {'address': '0x1a', 'claimed': True}],
                                      'modules': {'adc': {'type': 'ads1115', 'address': '0x48',
                                                          'state': 'running', 'error': None}}}))
        with (work / 'dashboard.log').open('w+') as dashboard_log, \
                (work / 'simfleet.log').open('w+') as fleet_log:
            dashboard = subprocess.Popen([sys.executable, str(ROOT / 'dashboard/server.py'),
                '--host', '127.0.0.1', '--port', str(http_port), '--listen-port', str(report_port),
                '--send-port', str(command_port), '--osc-target', '127.0.0.1',
                '--data-dir', str(work / 'data'), '--patches-dir', str(work / 'patches'),
                '--assets-dir', str(work / 'assets'), '--sim-no-engine'],
                cwd=ROOT, stdout=dashboard_log, stderr=subprocess.STDOUT)
            fleet = None
            try:
                deadline = time.monotonic() + 10
                while True:
                    try:
                        urllib.request.urlopen(f'http://127.0.0.1:{http_port}/', timeout=.2).close()
                        break
                    except OSError:
                        if dashboard.poll() is not None or time.monotonic() > deadline:
                            raise RuntimeError('dashboard startup failed')
                        time.sleep(.1)
                fleet = subprocess.Popen([sys.executable, str(ROOT / 'tools/simfleet.py'),
                    '--devices', '2', '--unassigned', '2', '--target', '127.0.0.1',
                    '--cmd-port', str(command_port), '--report-port', str(report_port),
                    '--hb-interval', '.2', '--boot-secs', '0', '--io-config', str(config),
                    '--manifest', str(manifest), '--patches-dir', str(work / 'patches'),
                    '--assets-dir', str(work / 'assets')],
                    cwd=ROOT, stdout=fleet_log, stderr=subprocess.STDOUT)
                asyncio.run(journey(http_port))
            except Exception:
                for name, log in (('dashboard', dashboard_log), ('simfleet', fleet_log)):
                    log.seek(0)
                    print(name, log.read()[-6000:])
                raise
            finally:
                if fleet is not None:
                    stop(fleet)
                stop(dashboard)


if __name__ == '__main__':
    main()
