"""Declared repair lifecycle, shared mutation FIFO and host/simulator parity."""
import asyncio
import copy
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'python'), str(ROOT / 'dashboard'), str(ROOT / 'tools')]
from io_control import IOControl
from test_io_bridge import bridge
from pythonosc.osc_message import OscMessage
from server import Dashboard
import simfleet

ROW = {'name': 'adc', 'type': 'ads1115', 'address': '0x48'}


class Reply:
    def __init__(self):
        self.calls = []
    def sendto(self, packet, target):
        message = OscMessage(packet)
        self.calls.append((message.address, message.params, target))


class QueueTests(unittest.TestCase):
    def setUp(self):
        self.send, self.error, self.reply = Mock(), Mock(), Reply()
        self.allowed = True
        self.timers = []
        class Timer:
            def __init__(timer, delay, callback, args):
                timer.callback, timer.args = callback, args
                timer.cancel = Mock()
                self.timers.append(timer)
            def start(timer):
                pass
        self.control = IOControl('node', self.send, self.error, Timer,
                                 write_allowed=lambda: self.allowed)
        self.addCleanup(self.control.close)

    def repair(self, name='adc'):
        self.control.request('reinit', name, self.reply, '192.0.2.1')

    def write(self):
        self.control.request('write', json.dumps({'name': 'adc', 'command': 'clear', 'args': []}),
                             self.reply, '192.0.2.1')

    def test_write_and_repair_share_fifo_and_one_error_has_one_owner(self):
        self.write()
        self.repair()
        self.assertEqual(self.send.call_count, 1)
        self.control.handle('/io/error', ['adc', 'write-failed'])
        self.assertEqual(self.reply.calls[0][0], '/os/io-write')
        self.send.assert_called_with('/io/reinit', ['adc'])
        self.control.handle('/io/written', ['adc', 'clear'])
        self.assertEqual(len(self.reply.calls), 1)
        self.control.handle('/io/reinitialized', ['other'])
        self.assertEqual(len(self.reply.calls), 1)
        self.control.handle('/io/reinitialized', ['adc'])
        address, args, target = self.reply.calls[-1]
        self.assertEqual((address, args[:2], target), ('/os/io-reinit', ['node', 'ok'], ('192.0.2.1', 5550)))
        self.assertEqual(json.loads(args[2]), {'name': 'adc', 'error': None})

    def test_performance_drops_waiting_writes_but_retains_and_runs_repairs(self):
        self.write()
        self.write()
        self.repair()
        self.write()
        self.allowed = False
        self.control.recheck_writes()
        self.assertEqual(len(self.reply.calls), 2)
        self.assertTrue(all(json.loads(call[1][2])['error'] == 'performance' for call in self.reply.calls))
        self.control.handle('/io/written', ['adc', 'clear'])
        self.send.assert_called_with('/io/reinit', ['adc'])
        self.control.handle('/io/reinitialized', ['adc'])
        self.repair()
        self.send.assert_called_with('/io/reinit', ['adc'])

    def test_repair_timeout_is_silent_and_serves_next_mutation(self):
        self.repair()
        self.write()
        self.timers[0].callback(*self.timers[0].args)
        self.assertFalse(self.reply.calls)
        self.send.assert_called_with('/io/adc', ['clear'])
        self.control.handle('/io/reinitialized', ['adc'])
        self.assertFalse(self.reply.calls)

    def test_invalid_name_returns_receipt_without_bridge_send(self):
        for name in (None, '', 'reinit', 'a/b', 1):
            self.repair(name)
            self.assertEqual(json.loads(self.reply.calls[-1][1][2])['error'], 'invalid-arguments')
        self.send.assert_not_called()

    def test_unrelated_driver_write_failure_does_not_complete_repair(self):
        self.repair()
        self.control.handle('/io/error', ['adc', 'write-failed'])
        self.error.assert_called_once_with('adc', 'write-failed')
        self.assertFalse(self.reply.calls)
        self.control.handle('/io/reinitialized', ['adc'])
        self.assertEqual(self.reply.calls[-1][0], '/os/io-reinit')


class BridgeTests(unittest.TestCase):
    def setUp(self):
        with patch.object(bridge, 'OSCClient'):
            self.manager = bridge.IOManager()
        self.manager._send = Mock()
        self.manager.peripherals = {'adc': Mock(address=0x48), 'other': Mock(address=0x19)}
        self.manager.io['modules'] = {'adc': dict(type='old', address='0x49', state='errored', error='create-failed'),
                                      'other': dict(type='lis3dh', address='0x19', state='running', error=None)}
        for name, value in [('usable_bus', True), ('have_bus', True)]:
            handle = patch.object(bridge, name, return_value=value)
            handle.start()
            self.addCleanup(handle.stop)
        handle = patch.object(bridge.patch_manifest, 'load', return_value=({'io_modules': [ROW]}, None))
        handle.start()
        self.addCleanup(handle.stop)
        handle = patch.object(bridge, 'scan_inventory', return_value=(True, [{'address': '0x48', 'claimed': False}]))
        handle.start()
        self.addCleanup(handle.stop)

    def test_retires_target_and_recreates_from_manifest_without_touching_other(self):
        old, other = self.manager.peripherals.values()
        unchanged = copy.deepcopy(self.manager.io['modules']['other'])
        def create(name, kind, address):
            old.cleanup.assert_called_once()
            self.assertEqual((name, kind, address), ('adc', 'ads1115', 0x48))
            self.manager.peripherals[name] = Mock(address=address)
            return True
        with patch.object(self.manager, '_create_peripheral', side_effect=create):
            self.manager.handle_io(['reinit'], ['adc'])
        self.assertIs(self.manager.peripherals['other'], other)
        other.cleanup.assert_not_called()
        self.assertEqual(self.manager.io['modules']['other'], unchanged)
        self.assertEqual(self.manager.io['modules']['adc'], dict(type='ads1115', address='0x48', state='running', error=None))
        self.manager._send.assert_called_with('/io/reinitialized', 'adc')

    def test_undeclared_target_is_rejected_without_changing_it(self):
        old = self.manager.peripherals['other']
        self.manager.handle_io(['reinit'], ['other'])
        old.cleanup.assert_not_called()
        self.manager._send.assert_called_with('/io/error', 'other', 'unknown-command')
        self.assertEqual(self.manager.io['modules']['other']['state'], 'running')

    def test_missing_bus_and_chip_stay_missing_but_setup_failure_is_errored(self):
        with patch.object(bridge, 'usable_bus', return_value=False):
            self.manager.handle_io(['reinit'], ['adc'])
        self.manager._send.assert_called_with('/io/error', 'adc', 'no-bus')
        self.assertEqual(self.manager.io['modules']['adc']['state'], 'missing')
        with patch.object(bridge, 'scan_inventory', return_value=(True, [])):
            self.manager.handle_io(['reinit'], ['adc'])
        self.manager._send.assert_called_with('/io/error', 'adc', 'create-failed')
        self.assertEqual(self.manager.io['modules']['adc']['state'], 'missing')
        with patch.object(self.manager, '_create_peripheral', return_value=False):
            self.manager.handle_io(['reinit'], ['adc'])
        self.assertEqual(self.manager.io['modules']['adc']['state'], 'errored')

    def test_cleanup_failure_returns_create_failed_and_other_module_is_untouched(self):
        self.manager.peripherals['adc'].cleanup.side_effect = OSError('chip offline')
        self.manager.handle_io(['reinit'], ['adc'])
        self.manager._send.assert_called_with('/io/error', 'adc', 'create-failed')
        self.manager.peripherals['other'].cleanup.assert_not_called()


class HostTests(unittest.IsolatedAsyncioTestCase):
    async def test_performance_routes_repairs_receipt_timeout_and_duplicate_suppression(self):
        with tempfile.TemporaryDirectory() as root:
            dashboard = Dashboard(SimpleNamespace(data_dir=root, devices_file=None, assets_dir=root,
                patches_dir=root, listen_port=5550, send_port=6660, osc_target='192.0.2.255'))
            dashboard.state.performance = True
            device = {'uid': 'node', 'online': True, 'report': {}}
            dashboard.state.devices['node'] = device
            dashboard.broadcast = Mock(side_effect=lambda *args: asyncio.sleep(0))
            dashboard.osc.broadcast = Mock()
            dashboard.osc.send_for_uid = Mock()
            dashboard.osc.request = Mock()
            try:
                for _ in range(2):
                    await dashboard.handle_ws({'type': 'io_reinit', 'data': {'uid': 'node', 'name': 'adc'}})
                dashboard.osc.send_for_uid.assert_called_once_with('node', '/all/os/to', ['node', 'io-reinit', 'adc'])
                dashboard.osc.handle('/os/io-reinit', ['node', 'ok', json.dumps({'name': 'adc', 'error': None})], '192.0.2.1')
                self.assertEqual(device['io_reinit']['adc']['status'], 'ok')
                self.assertNotIn(('node', 'reinit:adc'), dashboard.osc._io_timeouts)
                await dashboard.handle_ws({'type': 'io_reinit', 'data': {'uid': 'node', 'name': 'adc'}})
                dashboard.osc._expire_io('node', 'reinit:adc')
                self.assertEqual(device['io_reinit']['adc']['phase'], 'timeout')
            finally:
                dashboard.osc.close()
                await dashboard.state.close()


class SimulatorTests(unittest.TestCase):
    def test_repair_uses_active_manifest_and_is_allowed_in_performance(self):
        fleet = simfleet.SimFleet.__new__(simfleet.SimFleet)
        fleet.args = SimpleNamespace(report_port=5550, target='192.0.2.255', patches_dir='/fixture')
        fleet.sock = Reply()
        device = simfleet.Device('node', 'sim', -1, 'abc1234')
        device.performance = True
        device.io['bus'] = 1
        device.io_addresses = [{'address': '0x48', 'claimed': False}]
        device.io['modules'] = {'adc': dict(type='wrong', address='0x49', state='errored', error='create-failed')}
        with patch.object(simfleet.patch_manifest, 'load', return_value=({'io_modules': [ROW]}, None)):
            fleet.uid_admin(device, 'io-reinit', ['adc'], ('192.0.2.1', 123))
            self.assertEqual(json.loads(fleet.sock.calls[-1][1][2]), {'name': 'adc', 'error': None})
            self.assertEqual(device.io['modules']['adc']['address'], '0x48')
            self.assertEqual(device.io['modules']['adc']['state'], 'running')
            fleet.uid_admin(device, 'io-reinit', ['unknown'], ('192.0.2.1', 123))
            self.assertEqual(fleet.sock.calls[-1][0], '/os/io-error')
            self.assertEqual(json.loads(fleet.sock.calls[-2][1][2])['error'], 'unknown-command')


if __name__ == '__main__':
    unittest.main()
