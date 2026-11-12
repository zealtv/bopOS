#!/usr/bin/env python3
"""Browser-tier socket journeys for bridge/node and dashboard/simfleet streams."""
import asyncio
import importlib.util
import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import time
from types import SimpleNamespace

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'python'), str(ROOT / 'python/io'), str(ROOT / 'dashboard')]
from pyOSC3 import OSCServer, OSCMessage, decodeOSC
from io_stream import NodeStream, BridgeReplyServer
from io_control import IOControl
from osc_bridge import OSCBridge
from state import InstallationState


def port():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def until(predicate, timeout=3):
    deadline = time.monotonic() + timeout
    while not predicate():
        if time.monotonic() > deadline:
            raise AssertionError('local socket journey timed out')
        time.sleep(.01)


def local_journey():
    spec = importlib.util.spec_from_file_location('stream_bridge', ROOT / 'python/io/main.py')
    bridge = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bridge)
    bridge.usable_bus = bridge.have_bus = lambda: True
    bridge.scan_inventory = lambda bus, skip: (True, [{'address': '0x48', 'claimed': False}])
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as engine, \
            socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as values, \
            socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as receipts, \
            socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sender:
        for sock in (engine, values, receipts):
            sock.bind(('127.0.0.1', 0))
            sock.settimeout(3)
        bridge.PD_PORT, bridge.CONTROL_PORT = engine.getsockname()[1], port()
        command_port = port()
        manager = bridge.IOManager()
        manager.peripherals = {'adc': SimpleNamespace(read_data=lambda: [1.25, 2], address=0x48)}
        def command(address, args):
            message = OSCMessage(address)
            for arg in args:
                message.append(arg)
            sender.sendto(message.getBinary(), ('127.0.0.1', command_port))
        def forward(packet, target):
            assert target == ('127.0.0.1', 5551)
            sender.sendto(packet, values.getsockname())
        class Reply:
            def sendto(self, packet, target):
                assert target == ('127.0.0.1', 5550)
                sender.sendto(packet, receipts.getsockname())
        now, allowed = [100.0], [True]
        stream = NodeStream('local-node', command, forward, lambda: allowed[0], clock=lambda: now[0])
        control = IOControl('local-node', command, lambda *args: None)
        node_server = BridgeReplyServer(('127.0.0.1', bridge.CONTROL_PORT), stream)
        node_server.addMsgHandler('default', lambda path, tags, args, source: control.handle(path, args))
        bridge_server = OSCServer(('127.0.0.1', command_port))
        bridge_server.addMsgHandler('default', manager.handle_command)
        threads = [threading.Thread(target=server.serve_forever, daemon=True)
                   for server in (node_server, bridge_server)]
        try:
            for thread in threads:
                thread.start()
            stream.request([1], Reply(), '127.0.0.1')
            receipt = decodeOSC(receipts.recvfrom(65535)[0])
            assert receipt[:4] == ['/os/io-stream', ',sss', 'local-node', 'ok']
            until(lambda: manager.stream_lease.active)
            manager.poll_and_send()
            original = engine.recvfrom(65535)[0]
            message = decodeOSC(values.recvfrom(65535)[0])
            assert message == ['/io/stream', ',sb', 'local-node', original]
            assert decodeOSC(original)[2] == ['/adc', ',fi', 1.25, 2]
            control.request('scan', None, Reply(), '127.0.0.1')
            assert decodeOSC(receipts.recvfrom(65535)[0])[0] == '/os/io-scan'
            now[0] += 10
            stream._expire()
            until(lambda: not manager.stream_lease.active)
            manager.poll_and_send()
            values.settimeout(.15)
            try:
                values.recvfrom(65535)
                raise AssertionError('value after expiry')
            except socket.timeout:
                pass
            stream.request([1], Reply(), '127.0.0.1')
            receipts.recvfrom(65535)
            until(lambda: manager.stream_lease.active)
            allowed[0] = False
            stream.close()
            until(lambda: not manager.stream_lease.active)
            stream.request([1], Reply(), '127.0.0.1')
            refusal = decodeOSC(receipts.recvfrom(65535)[0])
            assert json.loads(refusal[4]) == {'active': False, 'error': 'performance'}
            manager.poll_and_send()
            # Control still works with Performance active and the stream closed.
            control.request('scan', None, Reply(), '127.0.0.1')
            assert decodeOSC(receipts.recvfrom(65535)[0])[0] == '/os/io-scan'
            print('PASS: real bridge/node UDP preserves bundle bytes and types; expiry/Performance close copying; control scans continue (chip access faked)')
        finally:
            stream.close()
            control.close()
            for server in (node_server, bridge_server):
                server.close()
            for thread in threads:
                thread.join(timeout=2)


async def sim_journey():
    async def wait(predicate, timeout=5):
        deadline = asyncio.get_running_loop().time() + timeout
        while not predicate():
            if asyncio.get_running_loop().time() > deadline:
                raise AssertionError('dashboard/simfleet journey timed out')
            await asyncio.sleep(.02)
    with tempfile.TemporaryDirectory() as directory:
        config = Path(directory) / 'io.json'
        config.write_text(json.dumps({'bus': 1, 'scanned': False,
            'addresses': [{'address': '0x48', 'claimed': False}],
            'modules': {'adc': {'type': 'ads1115', 'address': '0x48', 'state': 'running', 'error': None}}}))
        state = InstallationState(directory, None)
        command_port = port()
        events, samples, raw = [], [], []
        bridge = OSCBridge(state, lambda *args: events.append(args), 0, command_port,
                           '127.0.0.1', stream_port=0)
        await bridge.start()
        receive = bridge.io_streams.datagram_received
        def tap(data, addr):
            raw.append(time.monotonic())
            receive(data, addr)
        bridge.io_streams.datagram_received = tap
        log = open(Path(directory) / 'sim.log', 'w+')
        process = subprocess.Popen([sys.executable, str(ROOT / 'tools/simfleet.py'),
            '--devices', '2', '--unassigned', '2', '--boot-secs', '0', '--target', '127.0.0.1',
            '--cmd-port', str(command_port), '--report-port', str(bridge.transport.get_extra_info('sockname')[1]),
            '--stream-port', str(bridge.stream_transport.get_extra_info('sockname')[1]),
            '--io-config', str(config)], stdout=log, stderr=log)
        try:
            await wait(lambda: len(state.devices) == 2)
            first, second = sorted(state.devices)
            bridge.subscribe_io(first, 'panel', lambda data, values: samples.append((data, values)))
            bridge.subscribe_io(first, 'editor', lambda *args: None)
            try:
                bridge.subscribe_io(second, 'second', lambda *args: None)
                raise AssertionError('two devices accepted')
            except ValueError:
                pass
            await wait(lambda: len(samples) >= 3 and state.devices[first].get('io_stream', {}).get('active'))
            assert len(samples[0][1]['adc']) == 4
            assert all(decodeOSC(data)[0] == '#bundle' for data, _values in samples)
            before_hb = state.devices[first]['last_seen']
            bridge.io_scan(first)
            await wait(lambda: state.devices[first].get('report', {}).get('io', {}).get('scanned'))
            await wait(lambda: state.devices[first]['last_seen'] > before_hb, timeout=4)
            # Span a real renew interval, then release each consumer independently.
            await asyncio.sleep(3.1)
            bridge.unsubscribe_io(first, 'panel')
            count = len(samples)
            assert bridge.io_streams.uid == first
            bridge.unsubscribe_io(first, 'editor')
            await wait(lambda: state.devices[first]['io_stream']['active'] is False)
            await asyncio.sleep(.2)
            assert len(samples) == count and bridge.io_streams.renewal is None
            bridge.subscribe_io(second, 'panel', lambda data, values: samples.append((data, values)))
            await wait(lambda: len(samples) > count)
            state.performance = True
            bridge.set_performance(True)
            await wait(lambda: all(device.get('report', {}).get('performance') is True for device in state.devices.values()))
            count = len(samples)
            bridge.uid_command(second, 'io-stream', [1])
            await wait(lambda: state.devices[second].get('io_stream', {}).get('error') == 'performance')
            bridge.io_scan(second)
            await wait(lambda: state.devices[second].get('report', {}).get('io', {}).get('scanned'))
            await asyncio.sleep(.2)
            assert len(samples) == count and not bridge.io_streams.consumers
            assert state.devices[second]['report']['io']['modules']['adc']['state'] == 'running'
            state.performance = False
            bridge.set_performance(False)
            await wait(lambda: all(device.get('report', {}).get('performance') is False for device in state.devices.values()))
            # An unconsumed lease gets no dashboard renewal and expires at 10s.
            raw.clear()
            bridge.uid_command(first, 'io-stream', [1])
            await wait(lambda: len(raw) >= 3)
            opened = raw[0]
            await asyncio.sleep(max(0, opened + 10.3 - time.monotonic()))
            last = len(raw)
            await asyncio.sleep(.3)
            assert len(raw) == last and raw[-1] - opened < 10.1
            assert last <= 101, last
            print('PASS: real dashboard 5551 receiver and simfleet UDP; shared consumers/renewal, one-device rule, fake values, 10s expiry, Performance refusal, scans and heartbeats')
        except Exception:
            log.flush()
            log.seek(0)
            print(log.read()[-5000:])
            print('stream diagnostics:', len(raw), len(samples),
                  {uid: (device.get('ip'), device.get('io_stream'),
                         device.get('report', {}).get('io')) for uid, device in state.devices.items()})
            raise
        finally:
            bridge.close()
            await state.close()
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
            log.close()


if __name__ == '__main__':
    local_journey()
    asyncio.run(sim_journey())
