"""IO control attribution, payloads, inventory and dashboard/simfleet parity."""
import asyncio
import copy
import errno
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'python'), str(ROOT / 'dashboard'),
               str(ROOT / 'tools')]
from io_control import IOControl, BRIDGE_REPLY_TIMEOUT_SECONDS
import io_protocol
from pythonosc.osc_message import OscMessage
from server import Dashboard
import osc_bridge
import simfleet
import test_io_bridge


def facts(scanned=False):
    return {'bus': 1, 'scanned': scanned,
            'addresses': [{'address': '0x48', 'claimed': False},
                          {'address': '0x1a', 'claimed': True}] if scanned else [],
            'modules': {'adc': {'type': 'ads1115', 'address': '0x48',
                                'state': 'running', 'error': None}}}


def write(name='adc', command='threshold'):
    return {'name': name, 'command': command, 'args': [1, 2]}


class ReplySocket:
    def __init__(self):
        self.calls = []

    def sendto(self, data, target):
        message = OscMessage(data)
        self.calls.append((message.address, list(message.params), target))


class PayloadTests(unittest.TestCase):
    def test_rejects_entire_malformed_write_before_osc_encoding(self):
        bad = [None, [], {}, dict(write(), extra=1), dict(write(), name='bridge'),
               dict(write(), name='adc/clear'), dict(write(), command=''),
               dict(write(), args=None)]
        bad.extend(dict(write(), args=[value]) for value in (
            None, {}, [], True, 2**31, float('nan'), float('inf'), 1e100, '\ud800'))
        for value in bad:
            with self.subTest(value=value), self.assertRaises(ValueError):
                io_protocol.validate_write(value)
        self.assertEqual(io_protocol.validate_write(write()), write())

    def test_inventory_copies_and_orders_addresses(self):
        source = facts(True)
        observed = io_protocol.validate_io(source)
        self.assertEqual([r['address'] for r in observed['addresses']], ['0x1a', '0x48'])
        observed['modules']['adc']['state'] = 'errored'
        self.assertEqual(source['modules']['adc']['state'], 'running')
        for source in (dict(facts(), bus=True), dict(facts(), scanned=1),
                       dict(facts(), addresses=[{'address': '0xAA', 'claimed': False}])):
            with self.assertRaises(ValueError):
                io_protocol.validate_io(source)


class NodeControlTests(unittest.TestCase):
    def setUp(self):
        self.send = Mock()
        self.errors = Mock()
        self.timers = []
        class Timer:
            def __init__(timer, interval, callback, args):
                timer.interval, timer.callback, timer.args = interval, callback, args
                timer.cancelled = False
                timer.started = False
                self.timers.append(timer)
            def start(timer):
                timer.started = True
            def cancel(timer):
                timer.cancelled = True
            def fire(timer):
                timer.callback(*timer.args)
        self.control = IOControl('node-a', self.send, self.errors, timer_factory=Timer)
        self.addCleanup(self.control.close)
        self.reply = ReplySocket()

    def test_missing_scan_and_write_receipts_expire_silently_and_serve_next(self):
        for kind in ('scan', 'write'):
            with self.subTest(kind=kind):
                raw = json.dumps(write()) if kind == 'write' else None
                for host in ('192.0.2.1', '192.0.2.2'):
                    self.control.request(kind, raw, self.reply, host)
                expired = self.timers[-1]
                self.assertEqual(expired.interval, 3.0)
                self.assertEqual(expired.interval, BRIDGE_REPLY_TIMEOUT_SECONDS)
                self.assertTrue(expired.started and expired.daemon)
                before = self.send.call_count
                expired.fire()
                self.assertEqual(self.send.call_count, before + 1)
                self.assertEqual(len(self.control.pending[kind]), 1)
                self.assertFalse(self.reply.calls)
                self.errors.assert_not_called()
                expired.fire()  # a late cancelled callback cannot expire the next job
                self.assertEqual(len(self.control.pending[kind]), 1)
                self.timers[-1].fire()
                self.assertFalse(self.control.pending[kind])
                self.assertNotIn(kind, self.control.timeouts)

    def test_receipt_and_shutdown_cancel_timers(self):
        self.control.request('scan', None, self.reply, '192.0.2.1')
        finished = self.timers[-1]
        self.control.handle('/io/scanned', [json.dumps(facts(True))])
        self.assertTrue(finished.cancelled)
        self.control.request('scan', None, self.reply, '192.0.2.2')
        finished.fire()
        self.assertEqual(len(self.control.pending['scan']), 1)
        active = self.timers[-1]
        self.control.close()
        self.assertTrue(active.cancelled)
        active.fire()
        self.assertFalse(self.control.pending['scan'])
        self.assertFalse(self.control.timeouts)

    def test_scan_fifo_does_not_confuse_registry_with_terminal_scan(self):
        for host in ('192.0.2.1', '192.0.2.2'):
            self.control.request('scan', None, self.reply, host)
        self.send.assert_called_once_with('/io/scan', [])
        self.control.handle('/io/registry', [json.dumps(facts())])
        self.assertFalse(self.reply.calls)
        self.control.handle('/io/scanned', [json.dumps(facts(True))])
        self.assertEqual(self.send.call_count, 2)
        self.control.handle('/io/scanned', [json.dumps(io_protocol.empty_io())])
        self.assertEqual([call[2] for call in self.reply.calls],
                         [('192.0.2.1', 5550), ('192.0.2.2', 5550)])
        self.assertTrue(json.loads(self.reply.calls[0][1][1])['scanned'])
        self.assertIsNone(json.loads(self.reply.calls[1][1][1])['bus'])
        self.assertFalse(self.control.pending['scan'])

    def test_write_waits_for_matching_success_or_error_and_queues_fifo(self):
        for payload in (write(), write('lights', 'fill')):
            self.control.request('write', json.dumps(payload), self.reply, '192.0.2.1')
        self.send.assert_called_once_with('/io/adc', ['threshold', 1, 2])
        self.control.handle('/io/written', ['adc', 'other-command'])
        self.control.handle('/io/error', ['other-module', 'write-failed'])
        self.assertFalse(self.reply.calls)
        self.control.handle('/io/written', ['adc', 'threshold'])
        self.send.assert_called_with('/io/lights', ['fill', 1, 2])
        self.control.handle('/io/error', ['lights', 'write-failed'])
        self.assertEqual([call[1][1] for call in self.reply.calls], ['ok', 'err'])
        self.assertEqual(json.loads(self.reply.calls[1][1][2]),
                         {'name': 'lights', 'command': 'fill', 'error': 'write-failed'})
        self.errors.assert_any_call('lights', 'write-failed')
        self.assertFalse(self.control.pending['write'])

    def test_invalid_write_and_invalid_registry_do_not_mutate_or_send(self):
        self.control.request('write', '{', self.reply, '192.0.2.1')
        self.send.assert_not_called()
        self.assertEqual(json.loads(self.reply.calls[0][1][2])['error'], 'invalid-arguments')
        self.control.handle('/io/registry', ['{}'])
        self.assertEqual(self.control.snapshot(), io_protocol.empty_io())

    def test_error_updates_cache_and_broadcast_failure_does_not_block_receipt(self):
        self.control.handle('/io/registry', [json.dumps(facts())])
        self.control.request('write', json.dumps(write()), self.reply, '192.0.2.1')
        self.errors.side_effect = OSError('unavailable route')
        self.control.handle('/io/error', ['adc', 'write-failed'])
        self.assertEqual(self.control.snapshot()['modules']['adc']['state'], 'errored')
        self.assertEqual(self.reply.calls[0][1][1], 'err')

    def test_exact_uid_dispatch_and_report_use_same_io_object(self):
        import test_log_config as fixture
        node = fixture.bopos
        state = SimpleNamespace(uid='node-a', id=-1, groups=(), io_control=self.control)
        from pyOSC3 import OSCMessage
        message = OSCMessage('/all/os/to')
        for value in ('node-b', 'io-scan'):
            message.append(value)
        node.handle_lan_datagram(message.getBinary(), ('192.0.2.1', 1000), self.reply, state)
        self.send.assert_not_called()
        self.assertTrue(node.dispatch_uid_admin('io-scan', [], state, self.reply, '192.0.2.1'))
        self.assertFalse(node.dispatch_uid_admin('io-modules', [], state, self.reply, '192.0.2.1'))
        self.control.handle('/io/scanned', [json.dumps(facts(True))])
        with tempfile.TemporaryDirectory() as root:
            full_state = fixture.Node(root)
            full_state.io_control = self.control
            self.reply.calls.clear()
            with patch.object(node, 'audio_report', return_value={}), \
                    patch.object(node.wifi_config, 'helper_status', return_value={'managed': False}):
                node.report_reply(self.reply, '192.0.2.1', full_state)
            self.assertEqual(json.loads(self.reply.calls[0][1][0])['io'], self.control.snapshot())


class BusInventoryTests(unittest.TestCase):
    def test_kernel_claims_and_skip_are_preserved_without_probing_live_chip(self):
        bus_module = sys.modules['sys_i2c']
        probes = []
        class Bus:
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
            def probe(self, address):
                probes.append(address)
                if address == 0x1a:
                    raise OSError(errno.EBUSY, 'kernel-owned')
                raise OSError(errno.ENXIO, 'empty')
            def read_byte(self, address):
                self.probe(address)
            def i2c_rdwr(self, address):
                self.probe(address)
        with patch.object(bus_module, 'HAVE_SMBUS', True), \
                patch.object(bus_module, 'SMBus', return_value=Bus(), create=True), \
                patch.object(bus_module, 'i2c_msg', SimpleNamespace(write=lambda addr, data: addr), create=True):
            usable, rows = bus_module.scan_inventory(skip=[0x48])
            self.assertTrue(usable)
            self.assertEqual(rows, [{'address': '0x1a', 'claimed': True},
                                    {'address': '0x48', 'claimed': False}])
            self.assertNotIn(0x48, probes)
        with patch.object(bus_module, 'HAVE_SMBUS', True), \
                patch.object(bus_module, 'SMBus', side_effect=PermissionError('denied'), create=True):
            self.assertFalse(bus_module.usable_bus())
            self.assertEqual(bus_module.scan_inventory(), (False, []))


class DashboardIOTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        args = SimpleNamespace(data_dir=self.temp.name, devices_file=None,
                               listen_port=15559, send_port=16669, osc_target='192.0.2.255',
                               assets_dir=self.temp.name, patches_dir=self.temp.name)
        self.dashboard = Dashboard(args)
        self.events, self.frames = [], []
        # Async handle_ws awaits Dashboard.broadcast; OSCBridge uses a sync callback.
        async def broadcast(kind, data):
            self.events.append((kind, copy.deepcopy(data)))
        self.dashboard.broadcast = broadcast
        self.dashboard.osc.broadcast = lambda kind, data: self.events.append((kind, copy.deepcopy(data)))
        self.dashboard.osc.send_for_uid = lambda uid, address, args: self.frames.append((uid, address, args))
        self.dashboard.osc.request = Mock()
        self.device = {'uid': 'node-a', 'id': -1, 'online': True, 'ip': '192.0.2.1',
                       'report': {}, 'virtual': False}
        self.dashboard.state.devices['node-a'] = self.device

    async def asyncTearDown(self):
        self.dashboard.osc.close()
        await self.dashboard.state.close()
        self.temp.cleanup()

    async def test_ws_routes_physical_requests_and_replies_broadcast_io(self):
        dash = self.dashboard
        await dash.handle_ws({'type': 'io_scan', 'data': {'uid': 'node-a'}})
        self.assertEqual(self.frames[-1], ('node-a', '/all/os/to', ['node-a', 'io-scan']))
        dash.osc.handle('/os/io-scan', ['node-a', json.dumps(facts(True))], '192.0.2.1')
        self.assertNotIn(('node-a', 'scan'), dash.osc._io_timeouts)
        self.assertFalse(self.device['io_scan_pending'])
        self.assertTrue(self.events[-1][1]['report']['io']['scanned'])
        await dash.handle_ws({'type': 'io_write', 'data': {'uid': 'node-a', 'config': write()}})
        self.assertEqual(json.loads(self.frames[-1][2][2]), write())
        result = {'name': 'adc', 'command': 'threshold', 'error': None}
        dash.osc.handle('/os/io-write', ['node-a', 'ok', json.dumps(result)], '192.0.2.1')
        self.assertNotIn(('node-a', 'write'), dash.osc._io_timeouts)
        self.assertEqual(self.device['io_write']['status'], 'ok')
        dash.osc.handle('/os/io-error', ['node-a', 'adc', 'write-failed'], '192.0.2.1')
        self.assertEqual(self.device['report']['io']['modules']['adc']['error'], 'write-failed')
        self.assertEqual(self.events[-1][0], 'report')

    async def test_missing_receipts_expire_dashboard_pending_state_without_wire_tokens(self):
        dash = self.dashboard
        self.assertGreater(osc_bridge.IO_REQUEST_TIMEOUT_SECONDS, BRIDGE_REPLY_TIMEOUT_SECONDS)
        timed_out = asyncio.Event()
        broadcast = dash.osc.broadcast
        def observe(kind, data):
            broadcast(kind, data)
            if all((data.get('io_' + name) or {}).get('phase') == 'timeout'
                   for name in ('scan', 'write')):
                timed_out.set()
        dash.osc.broadcast = observe
        with patch.object(osc_bridge, 'IO_REQUEST_TIMEOUT_SECONDS', .02):
            await dash.handle_ws({'type': 'io_scan', 'data': {'uid': 'node-a'}})
            await dash.handle_ws({'type': 'io_write', 'data': {'uid': 'node-a', 'config': write()}})
            self.assertTrue(self.device['io_scan_pending'])
            self.assertEqual(self.device['io_write']['status'], 'pending')
            await asyncio.wait_for(timed_out.wait(), 1)
        self.assertFalse(self.device['io_scan_pending'])
        for kind in ('scan', 'write'):
            self.assertEqual(self.device['io_' + kind]['status'], 'err')
            self.assertEqual(self.device['io_' + kind]['phase'], 'timeout')
        self.assertIsNone(self.device['io_write']['error'])
        self.assertEqual(len(self.frames), 2)  # only the original requests
        self.assertFalse(dash.osc._io_timeouts)
        dash.osc.request.assert_called_with('node-a', 'report')

    async def test_replaced_and_closed_dashboard_timers_are_cancelled(self):
        dash = self.dashboard
        await dash.handle_ws({'type': 'io_scan', 'data': {'uid': 'node-a'}})
        old = dash.osc._io_timeouts[('node-a', 'scan')]
        await dash.handle_ws({'type': 'io_scan', 'data': {'uid': 'node-a'}})
        self.assertTrue(old.cancelled())
        active = dash.osc._io_timeouts[('node-a', 'scan')]
        dash.osc.close()
        self.assertTrue(active.cancelled())
        self.assertFalse(dash.osc._io_timeouts)

    async def test_malformed_unknown_or_virtual_receipts_do_not_replace_facts(self):
        dash = self.dashboard
        self.device['report']['io'] = facts(True)
        for uid, payload in (('node-b', facts()), ('node-a', {}), ('node-a', [])):
            dash.osc.handle('/os/io-scan', [uid, json.dumps(payload)], '192.0.2.1')
        self.assertEqual(self.device['report']['io'], facts(True))
        self.assertFalse([event for event in self.events if event[0] == 'report'])
        self.device['virtual'] = True
        dash.osc.handle('/os/io-error', ['node-a', 'adc', 'write-failed'], '192.0.2.1')
        self.assertFalse([event for event in self.events if event[0] == 'report'])


class SimFleetIOTests(unittest.TestCase):
    def test_scan_write_error_report_and_configurable_fake_inventory(self):
        device = simfleet.Device('node-a', 'sim1', -1, 'abc1234')
        device.io = facts()
        device.io_addresses = facts(True)['addresses']
        fleet = simfleet.SimFleet.__new__(simfleet.SimFleet)
        fleet.args = SimpleNamespace(report_port=15559, target='127.0.0.1')
        fleet.start_monotonic = 0
        fleet.sock = ReplySocket()
        source = ('127.0.0.1', 9999)
        fleet.uid_admin(device, 'io-scan', [], source)
        self.assertEqual(fleet.sock.calls[-1][0], '/os/io-scan')
        self.assertTrue(json.loads(fleet.sock.calls[-1][1][1])['scanned'])
        fleet.uid_admin(device, 'io-write', [json.dumps(write())], source)
        self.assertEqual(fleet.sock.calls[-1][1][1], 'ok')
        self.assertEqual(device.io_writes, [write()])
        device.io['bus'] = None
        fleet.uid_admin(device, 'io-write', [json.dumps(write())], source)
        self.assertEqual(fleet.sock.calls[-1][:2], ('/os/io-error', ['node-a', 'adc', 'no-bus']))
        fleet.send_report(device, source)
        report = json.loads(fleet.sock.calls[-1][1][0])
        self.assertFalse(report['has_i2c'])
        self.assertEqual(report['io'], device.io)
        with tempfile.TemporaryDirectory() as root:
            config = Path(root) / 'io.json'
            config.write_text(json.dumps(dict(facts(), addresses=facts(True)['addresses'])))
            args = SimpleNamespace(devices=2, devices_file=None, unresponsive=0,
                                   unassigned=0, wired=0, engine_dead=0, ephemeral=0,
                                   version='abc1234', protocol='v1', state_dir=None,
                                   io_config=str(config))
            devices = simfleet.load_devices(args)
            self.assertEqual(devices[0].io['addresses'], [])
            self.assertEqual(devices[0].io_addresses, io_protocol.validate_io(facts(True))['addresses'])
            devices[0].io['modules']['adc']['error'] = 'write-failed'
            self.assertIsNone(devices[1].io['modules']['adc']['error'])


if __name__ == '__main__':
    unittest.main()
