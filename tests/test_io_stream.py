"""Leases, byte fidelity, consumer lifecycle and Performance boundaries."""
import asyncio
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
from pyOSC3 import OSCBundle, OSCMessage, decodeOSC
from pythonosc.osc_message import OscMessage
import io_stream
from io_streams import IOStreams
from osc_bridge import OSCBridge
from test_io_bridge import bridge
from test_log_config import bopos, ReplySocket
from test_performance_mode import node
import simfleet


def bundle():
    result = OSCBundle()
    for name, values in [('adc', [1.25, 2]), ('switch', [1, 0, 0]), ('oled', [])]:
        message = OSCMessage('/' + name)
        for value in values:
            message.append(value)
        result.append(message)
    return result.getBinary()


class Timer:
    def __init__(self, delay, callback):
        self.delay, self.callback = delay, callback
        self.cancel = Mock()
    def start(self):
        pass


class NodeStreamTests(unittest.TestCase):
    def setUp(self):
        self.now = 100.0
        self.allowed = True
        self.commands, self.values = [], []
        self.stream = io_stream.NodeStream('node-a',
            lambda *args: self.commands.append(args), lambda *args: self.values.append(args),
            lambda: self.allowed, clock=lambda: self.now, timer=Timer)
        self.reply = ReplySocket()
        self.addCleanup(self.stream.close)

    def request(self, args, host='192.0.2.1'):
        self.stream.request(args, self.reply, host)
        packet, target = self.reply.calls[-1]
        self.assertEqual(packet[:3], ['/os/io-stream', ',sss', 'node-a'])
        self.assertEqual(target, (host, 5550))
        return packet[3], json.loads(packet[4])

    def test_renew_takeover_and_old_timer_cannot_close_new_lease(self):
        self.assertEqual(self.request([1]), ('ok', {'active': True, 'error': None}))
        old = self.stream.timer
        self.now += 9
        self.request([1], '192.0.2.2')
        self.now += 2
        old.callback()
        self.stream.forward(bundle())
        packet, target = self.values[-1]
        self.assertEqual(target, ('192.0.2.2', 5551))
        self.assertEqual(decodeOSC(packet), ['/io/stream', ',sb', 'node-a', bundle()])
        self.assertEqual(self.stream.timer.delay, 10.0)
        self.now += 8
        self.stream.timer.callback()
        self.assertFalse(self.stream.lease.active)
        self.assertEqual(self.commands[-1], ('/io/stream', [0]))
        self.stream.forward(bundle())
        self.assertEqual(len(self.values), 1)

    def test_invalid_preserves_lease_close_is_idempotent_and_any_host_can_close(self):
        self.request([1])
        deadline = self.stream.lease.until
        for bad in ([], [2], [1.0], ['1'], [True], [0, 1]):
            self.assertEqual(self.request(bad),
                ('err', {'active': True, 'error': 'invalid-arguments'}))
            self.assertEqual(self.stream.lease.until, deadline)
        for _ in range(2):
            self.assertEqual(self.request([0], '192.0.2.2'),
                ('ok', {'active': False, 'error': None}))

    def test_performance_refuses_both_values_and_never_sends_values(self):
        self.request([1])
        self.allowed = False
        for arg in (0, 1):
            self.assertEqual(self.request([arg]),
                ('err', {'active': False, 'error': 'performance'}))
        self.stream.forward(bundle())
        self.assertEqual(self.values, [])

    def test_bad_bundles_are_dropped_and_original_types_survive(self):
        self.request([1])
        for packet in (b'#bundle\x00', b'junk', OSCMessage('/io/error').getBinary()):
            self.stream.forward(packet)
        self.assertFalse(self.values)
        self.stream.forward(bundle())
        self.assertEqual(OscMessage(self.values[0][0]).params, ['node-a', bundle()])

    def test_node_dispatch_and_entering_performance_close_immediately(self):
        with tempfile.TemporaryDirectory() as root:
            state = node(root)
            state.io_stream = self.stream
            self.stream.allowed = lambda: bopos.development_allowed('io-stream', state)
            with patch.object(bopos, 'report_reply', return_value=True):
                self.assertTrue(bopos.dispatch_uid_admin('io-stream', [1], state, self.reply, '192.0.2.1'))
                self.assertTrue(self.stream.lease.active)
                self.assertTrue(bopos.set_performance(1, self.reply, '192.0.2.1', state))
                self.assertFalse(self.stream.lease.active)
                self.stream.forward(bundle())
                self.assertEqual(self.values, [])
                bopos.set_performance(0, self.reply, '192.0.2.1', state)
                self.assertFalse(self.stream.lease.active)
            state.io_control.close()


class BridgeStreamTests(unittest.TestCase):
    def test_copy_and_independent_timeout_leave_engine_delivery_unchanged(self):
        with patch.object(bridge, 'OSCClient', side_effect=lambda: Mock()):
            manager = bridge.IOManager()
        now = [100.0]
        manager.stream_lease = io_stream.Lease(lambda: now[0])
        manager.peripherals = {'adc': SimpleNamespace(read_data=lambda: [1.0, 2])}
        manager.poll_and_send()
        self.assertEqual(manager.osc_client.send.call_count, 1)
        manager.control_client.send.assert_not_called()
        manager.handle_io(['stream'], [1])
        manager.poll_and_send()
        self.assertIs(manager.osc_client.send.call_args.args[0],
                      manager.control_client.send.call_args.args[0])
        now[0] += 9
        manager.handle_io(['stream'], [1])
        now[0] += 2
        manager.poll_and_send()
        self.assertEqual(manager.control_client.send.call_count, 2)
        now[0] += 8
        manager.poll_and_send()
        self.assertEqual(manager.control_client.send.call_count, 2)
        self.assertEqual(manager.osc_client.send.call_count, 4)
        manager.handle_io(['stream'], [1])
        manager.osc_client.send.side_effect = OSError('engine offline')
        manager.poll_and_send()
        self.assertEqual(manager.control_client.send.call_count, 3)
        manager.handle_io(['stream'], [0])
        self.assertFalse(manager.stream_lease.active)


class ConsumerTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.state = SimpleNamespace(performance=False, data={}, devices={
            uid: {'uid': uid, 'ip': '192.0.2.1'} for uid in ('one', 'two')})
        self.command = Mock()
        self.streams = IOStreams(self.state, self.command)
        self.addCleanup(self.streams.close)

    async def test_shared_consumers_renew_and_last_release_stops(self):
        first, second = Mock(), Mock()
        with patch('io_streams.RENEW_SECONDS', .01):
            self.streams.subscribe('one', 'panel', first)
            self.streams.subscribe('one', 'editor', second)
            with self.assertRaises(ValueError):
                self.streams.subscribe('two', 'other', Mock())
            await asyncio.sleep(.025)
            self.assertGreaterEqual(self.command.call_count, 2)
            self.streams.datagram_received(io_stream.stream_packet('one', bundle()), ('192.0.2.1', 123))
            for callback in (first, second):
                callback.assert_called_once_with(bundle(), {'adc': [1.25, 2], 'switch': [1, 0, 0], 'oled': []})
            self.streams.unsubscribe('one', 'panel')
            self.assertEqual(len(self.streams.consumers), 1)
            self.streams.unsubscribe('one', 'editor')
            self.assertEqual(self.command.call_args.args, ('one', 'io-stream', [0]))
            count = self.command.call_count
            await asyncio.sleep(.025)
            self.assertEqual(self.command.call_count, count)
            self.streams.subscribe('two', 'panel', first)
            self.assertEqual(self.streams.uid, 'two')

    async def test_wrong_source_uid_and_malformed_packets_do_not_reach_consumer(self):
        callback = Mock()
        self.streams.subscribe('one', 'panel', callback)
        for packet, host in [(io_stream.stream_packet('two', bundle()), '192.0.2.1'),
                             (io_stream.stream_packet('one', bundle()), '192.0.2.2'),
                             (b'bad', '192.0.2.1'),
                             (io_stream.stream_packet('one', b'bad'), '192.0.2.1')]:
            self.streams.datagram_received(packet, (host, 123))
        callback.assert_not_called()

    async def test_performance_stops_renewal_and_clears_consumers(self):
        bridge = OSCBridge(self.state, Mock(), 5550, 6660, '192.0.2.255')
        bridge.send_for_uid = Mock()
        bridge.send_physical = Mock()
        callback = Mock()
        bridge.subscribe_io('one', 'panel', callback)
        self.state.performance = True
        bridge.set_performance(True)
        self.assertFalse(bridge.io_streams.consumers)
        self.assertIsNone(bridge.io_streams.renewal)
        with self.assertRaises(ValueError):
            bridge.subscribe_io('one', 'panel', callback)
        bridge.io_streams.datagram_received(io_stream.stream_packet('one', bundle()), ('192.0.2.1', 123))
        callback.assert_not_called()
        self.state.performance = False
        self.assertIsNone(bridge.io_streams.uid)
        bridge.close()

    async def test_receipt_validation_and_refusal_stop_consumers_without_module_faults(self):
        self.state.devices['one']['report'] = {'io': {'modules': {}}}
        bridge = OSCBridge(self.state, Mock(), 5550, 6660, '192.0.2.255')
        bridge.send_for_uid = Mock()
        bridge.subscribe_io('one', 'panel', Mock())
        bridge.handle('/os/io-stream', ['one', 'err', json.dumps({'active': True, 'error': 'performance'})], '192.0.2.1')
        self.assertNotIn('io_stream', self.state.devices['one'])
        bridge.handle('/os/io-stream', ['one', 'err', json.dumps({'active': False, 'error': 'performance'})], '192.0.2.1')
        self.assertEqual(self.state.devices['one']['io_stream'],
                         {'active': False, 'error': 'performance', 'status': 'err'})
        self.assertFalse(bridge.io_streams.consumers)
        self.assertNotIn('io_error', self.state.devices['one'])
        bridge.close()


class SimStreamTests(unittest.TestCase):
    def test_single_destination_generation_and_performance_refusal(self):
        fleet = simfleet.SimFleet.__new__(simfleet.SimFleet)
        fleet.args = SimpleNamespace(report_port=5550, stream_port=5551)
        fleet.sock, fleet.schedule = Mock(), Mock()
        device = simfleet.Device('one', 'sim', -1, 'test')
        device.io['modules'] = {'adc': {'type': 'ads1115', 'state': 'running'}}
        fleet.uid_admin(device, 'io-stream', [1], ('192.0.2.1', 123))
        old = device.io_stream_generation
        fleet.uid_admin(device, 'io-stream', [1], ('192.0.2.2', 123))
        fleet.sock.reset_mock()
        fleet.stream_io(device, old)
        fleet.sock.sendto.assert_not_called()
        fleet.stream_io(device, device.io_stream_generation)
        packet, target = fleet.sock.sendto.call_args.args
        self.assertEqual(target, ('192.0.2.2', 5551))
        self.assertEqual(len(io_stream.decode_bundle(OscMessage(packet).params[1])[0][2:]), 4)
        self.assertEqual(fleet.schedule.call_args.args[0], .1)
        device.performance = True
        fleet.uid_admin(device, 'io-stream', [1], ('192.0.2.2', 123))
        packet = OscMessage(fleet.sock.sendto.call_args.args[0])
        self.assertEqual(packet.address, '/os/io-stream')
        self.assertEqual(json.loads(packet.params[2]), {'active': False, 'error': 'performance'})
        fleet.sock.reset_mock()
        fleet.stream_io(device, device.io_stream_generation)
        fleet.sock.sendto.assert_not_called()


if __name__ == '__main__':
    unittest.main()
