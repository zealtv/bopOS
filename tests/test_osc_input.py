"""Declared outside OSC input, runtime routing and deterministic fades."""
import asyncio
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'dashboard'))
from osc_input import translate, MasterRamp, OSCInput, InputProtocol
from osc_bridge import OSCBridge
from state import InstallationState
from pythonosc.osc_message_builder import OscMessageBuilder


MANIFEST = {'events': [
    {'name': 'hit', 'fields': [
        {'name': 'gain', 'kind': 'float', 'min': 0, 'max': 1},
        {'name': 'mode', 'kind': 'enum', 'min': 0, 'max': 2, 'optional': True, 'default': 1},
        {'name': 'file', 'kind': 'text', 'optional': True, 'default': 'folder/file'}]},
    {'name': 'same', 'fields': []},
    {'path': ['os'], 'name': 'play', 'fields': []}],
    'params': [{'name': 'gain', 'kind': 'float'}, {'name': 'same', 'kind': 'float'}]}
GROUPS = {'3': {'id': 3, 'name': 'spot1'}}


class TranslationTests(unittest.TestCase):
    def trans(self, address, args=(), lead=500):
        result, error = translate(address, args, MANIFEST, GROUPS, 123000000, lead)
        self.assertIsNone(error)
        return result

    def reject(self, address, args=()):
        result, reason = translate(address, args, MANIFEST, GROUPS, 0, 500)
        self.assertIsNone(result)
        self.assertTrue(reason)

    def test_targets_defaults_and_stamp(self):
        for target, selector in [('all', 'all'), ('12', '12'), ('g3', 'g3'), ('spot1', 'g3')]:
            result = self.trans('/' + target + '/hit', [.5])
            self.assertEqual(result.address, '/' + selector + '/e/hit')
            self.assertEqual(result.args, ['623000000', .5, 1, 'folder/file'])
        self.assertEqual(self.trans('/all/e/hit', [1], lead=0).args[0], '0')

    def test_clamps_and_numeric_coercion(self):
        result = self.trans('/all/hit', [4, 8.0, 'file'])
        self.assertEqual(result.args[1:], [1.0, 2, 'file'])
        self.assertIsInstance(result.args[1], float)
        self.assertIsInstance(result.args[2], int)
        self.assertEqual(len(result.clamps), 2)
        self.assertEqual(self.trans('/all/hit', [-4, -8]).args[1:3], [0., 0])

    def test_rejection_and_ambiguity(self):
        for address, args in [('/all/hit', []), ('/all/hit', [1, .5]),
                              ('/all/hit', ['1']), ('/all/hit', [1, 1, 4]),
                              ('/all/hit', [1, 1, 'has space']),
                              ('/all/hit', [float('nan')]), ('/all/hit', [1,1,'x',3]),
                              ('/all/same', []), ('/all/os/play', []),
                              ('/all/e/gain', []), ('/all/p/hit', []),
                              ('/all/e/unknown', []), ('/unknown/hit', [1]),
                              ('/g99/hit', [1]), ('/all//hit', [1])]:
            with self.subTest(address=address, args=args):
                self.reject(address, args)
        self.trans('/all/e/same')
        self.trans('/all/e/os/play')
        self.assertEqual(self.trans('/spot1/p/same', [1, '2s']).args, [1, '2s'])

    def test_commands_and_points(self):
        for address in ['/pt', '/point', '/pt/clear']:
            self.assertEqual(self.trans(address, [1, 2]).args, [1, 2])
        for duration, ms in [(50, 50), ('250ms', 250), ('10s', 10000), ('1.5m', 90000)]:
            self.assertEqual(self.trans('/bop/master', [.5, duration]).args, [.5, ms])
        for address, args in [('/bop/master', [2]), ('/bop/master', [.5, -1]),
                              ('/bop/mute', [2]), ('/bop/lead', [1.5]),
                              ('/bop/lead', [10001]), ('/bop/patch', ['x'])]:
            self.reject(address, args)


class RuntimeTests(unittest.TestCase):
    def app(self):
        app = Mock()
        app.supervisor_mode = 'live'
        app.state.data = {'master': 1., 'groups': GROUPS, 'editor': {'params': {}}}
        app.live_control_manifest.return_value = MANIFEST
        app.osc._selector_seats.return_value = [{'id': 0, 'params': {}}]
        return app

    def test_ring_and_forwarding(self):
        app = self.app()
        receiver = OSCInput(app)
        for _ in range(60):
            receiver.handle('/all/missing', [], '1.2.3.4')
        self.assertEqual(len(receiver.snapshot()['recent']), 50)
        receiver.handle('/spot1/hit', [3], '1.2.3.4')
        self.assertEqual(receiver.recent[-1]['kind'], 'clamp')
        sent = app.osc.send.call_args.args
        self.assertEqual(sent[0], '/g3/e/hit')
        self.assertGreater(int(sent[1][0]), 0)
        receiver.handle('/all/gain', [.75], 'ip')
        app.osc._store_fade_destination.assert_called_with(
            app.osc._selector_seats.return_value, 'gain', .75)
        receiver.handle('/pt', [0], 'ip')
        self.assertGreater(app.osc.outside_points_until, 0)
        receiver.handle('/bop/mute', [1], 'ip')
        self.assertTrue(app.state.data['muted'])
        receiver.handle('/bop/lead', [123], 'ip')
        self.assertEqual(app.state.data['event_lead_ms'], 123)

    def test_editor_manifest_and_mirror(self):
        app = self.app()
        app.supervisor_mode = 'edit'
        app.state.data['editor']['patch'] = 'edited'
        app.editor_target.return_value = {'params': {}}
        receiver = OSCInput(app)
        receiver.handle('/all/gain', [.5], 'ip')
        app.live_control_manifest.assert_called_with('edited')
        app.osc._store_fade_destination.assert_called_with(
            [app.editor_target.return_value], 'gain', .5)

    def test_real_bridge_records_scalar_and_automation(self):
        app = self.app()
        seats = {'0': {'id': 0, 'groups': [3], 'params': {}, 'bound': 'node'}}
        devices = {'node': {'uid': 'node', 'params': {}}}
        app.state = SimpleNamespace(data={'groups': GROUPS}, seats=seats,
                                    devices=devices, save_debounced=Mock(),
                                    clean_group_id=InstallationState.clean_group_id)
        app.osc = OSCBridge(app.state, Mock(), 0, 0, '127.0.0.1')
        app.osc.send = Mock()
        receiver = OSCInput(app)
        receiver.handle('/spot1/gain', [.75], 'ip')
        self.assertEqual(seats['0']['params']['gain'], .75)
        self.assertEqual(devices['node']['params']['gain'], .75)
        app.osc.send.assert_called_with('/g3/p/gain', [.75])
        receiver.handle('/all/p/gain', [.2, '2s'], 'ip')
        self.assertEqual(app.osc.automation['0']['gain']['kind'], 'fade')
        self.assertEqual(seats['0']['params']['gain'], .2)
        app.osc.send.assert_called_with('/all/p/gain', [.2, '2s'])
        # Parameter arguments still pass through without storing invalid scalars.
        receiver.handle('/all/p/gain', [b'blob'], 'ip')
        app.osc.send.assert_called_with('/all/p/gain', [b'blob'])
        self.assertEqual(seats['0']['params']['gain'], .2)

    def test_packet_and_invalid_datagram(self):
        receiver = Mock()
        protocol = InputProtocol(receiver)
        protocol.datagram_received(b'broken', ('ip', 12))
        receiver.note.assert_called_once()
        message = OscMessageBuilder(address='/bop/lead')
        message.add_arg(12)
        protocol.datagram_received(message.build().dgram, ('ip', 12))
        receiver.handle.assert_called_once_with('/bop/lead', [12], 'ip')

    def test_points_guard_includes_catchup_and_expires(self):
        bridge = OSCBridge.__new__(OSCBridge)
        bridge.outside_points_until = 3
        bridge.send = Mock()
        bridge.state = SimpleNamespace(data={'points': {}})
        bridge._points_elapsed = lambda: 0
        with patch('osc_bridge.time.monotonic', return_value=2):
            bridge.send_points_frame()
        bridge.send.assert_not_called()
        with patch('osc_bridge.time.monotonic', return_value=4):
            bridge.send_points_frame()
        bridge.send.assert_called_once()

    def test_ramp_steps_cancellation_and_persistence(self):
        now, queue, values = [0.], [], []
        def schedule(delay, callback):
            handle = Mock()
            queue.append((callback, handle))
            return handle
        ramp = MasterRamp(values.append, lambda: now[0], schedule)
        ramp.start(1, 0, 1000)
        self.assertEqual(values, [1])
        now[0] = .5
        callback, _ = queue.pop()
        callback()
        self.assertEqual(values[-1], .5)
        pending = queue[-1][1]
        ramp.start(.5, .8, 0)
        pending.cancel.assert_called_once()
        self.assertAlmostEqual(values[-1], .8)
        with tempfile.TemporaryDirectory() as directory:
            state = InstallationState(directory, None)
            app = self.app()
            app.state = state
            receiver = OSCInput(app)
            receiver.ramp = MasterRamp(receiver.emit_master, lambda: now[0], schedule)
            receiver.set_master(.2, 1000)
            self.assertEqual(state.data['master'], 1.)
            self.assertEqual(state.durable()['master'], .2)
            # Another save mid-fade must keep the destination.
            state.save()
            self.assertEqual(InstallationState(directory, None).data['master'], .2)
            async def immediate():
                receiver.set_master(.7)
                await state.close()
            asyncio.run(immediate())
            self.assertAlmostEqual(state.data['master'], .7)
            self.assertEqual(state.durable()['master'], .7)


if __name__ == '__main__':
    unittest.main()
