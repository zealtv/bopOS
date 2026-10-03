"""IO dispatch and lifecycle checks without sockets, browsers or hardware."""
import contextlib
import importlib.util
import io
from pathlib import Path
import sys
import threading
import types
import unittest
from unittest.mock import Mock, patch

sys.dont_write_bytecode = True
IO_DIR = Path(__file__).resolve().parents[1] / 'python' / 'io'


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


with patch.object(sys, 'path', [str(IO_DIR), *sys.path]):
    bridge = load_module('io_bridge_under_test', IO_DIR / 'main.py')


class BridgeTests(unittest.TestCase):
    def setUp(self):
        with patch.object(bridge, 'OSCClient'):
            self.manager = bridge.IOManager()
        self.manager._send = Mock()
        self.bus = patch.object(bridge, 'have_bus', return_value=True)
        self.bus.start()
        self.addCleanup(self.bus.stop)

    def command(self, parts, args=()):
        with contextlib.redirect_stdout(io.StringIO()) as output:
            self.manager.handle_io(parts, args)
        return output.getvalue()

    def test_invalid_create_arguments_are_contained_without_new_wire_behavior(self):
        for address in ('bad', float('nan'), float('inf'), None, 4.5, -1, 128):
            with self.subTest(address=address):
                self.command(['create'], ['tilt', 'lis3dh', address])
                self.manager._send.assert_not_called()
        with patch.object(bridge, 'have_bus', return_value=False):
            self.command(['create'], ['tilt', 'lis3dh', '0x19'])
        self.manager._send.assert_called_with('/io/error', 'tilt', 'no-bus')

    def test_poll_bad_arguments_preserve_rate_and_log_without_unratified_reply(self):
        for args in ([], ['bad'], [None], [float('inf')], [float('nan')]):
            with self.subTest(args=args):
                self.assertIn('Invalid /io/poll', self.command(['poll'], args))
                self.assertEqual(self.manager.poll_rate, bridge.DEFAULT_POLL_RATE)
        self.manager._send.assert_not_called()
        self.command(['poll'], [20])
        self.assertEqual(self.manager.poll_rate, 20)
        self.command(['poll'], [-1])
        self.assertEqual(self.manager.poll_rate, 0.1)

    def test_verbs_precede_peripherals_and_reserved_names_cannot_be_created(self):
        for verb in bridge.RESERVED_NAMES:
            fake = Mock()
            self.manager.peripherals[verb] = fake
            args = {'create': [], 'poll': [10], 'report': [], 'scan': []}[verb]
            with patch.object(bridge, 'scan_bus', return_value=[]):
                self.command([verb], args)
            fake.write_data.assert_not_called()
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertFalse(self.manager.create_peripheral(verb, 'lis3dh', 0x19))

    def test_peripheral_dispatch_requires_one_segment_and_a_command(self):
        fake = Mock()
        self.manager.peripherals['light'] = fake
        self.command(['light'], ['fill', 1, 2, 3])
        fake.write_data.assert_called_once_with(command='fill', args=[1, 2, 3])
        fake.reset_mock()
        for parts, args in ((['light', 'fill'], [1, 2, 3]), (['light'], []),
                            (['unknown'], []), ([], [])):
            self.assertIn('Unknown /io verb', self.command(parts, args))
        fake.write_data.assert_not_called()
        self.manager._send.assert_not_called()

    def test_other_error_branches_are_diagnostic_without_new_wire_tokens(self):
        self.assertIn('Invalid /io/create', self.command(['create']))
        for value in ('bad', None, float('nan'), -1, 1.5):
            self.assertIn('Invalid /io/scan', self.command(['scan'], [value]))
        fake = Mock()
        fake.write_data.side_effect = OSError('chip unavailable')
        self.manager.peripherals['light'] = fake
        self.assertIn('Error writing to light', self.command(['light'], ['clear']))
        self.manager._send.assert_not_called()

    def test_scan_skips_registered_addresses(self):
        self.manager.peripherals['tilt'] = types.SimpleNamespace(address=0x18)
        with patch.object(bridge, 'scan_bus', return_value=[0x18]) as scan:
            self.command(['scan'])
        scan.assert_called_once_with(1, skip=[0x18])
        self.manager._send.assert_called_once_with('/io/scan', 0x18)

    def test_recreate_cleans_old_before_setup_and_failed_candidate(self):
        events = []
        old = Mock()
        old.cleanup.side_effect = lambda: events.append('old cleanup')
        candidate = Mock()
        candidate.setup.side_effect = lambda: events.append('new setup')
        module = types.SimpleNamespace(Fake=Mock(return_value=candidate))
        self.manager.peripherals['tilt'] = old
        with patch.dict(bridge.PERIPHERAL_TYPES, fake=('io_fake', 'Fake')), \
                patch.dict(sys.modules, io_fake=module):
            self.command(['create'], ['tilt', 'fake', '0x18'])
            self.assertEqual(events, ['old cleanup', 'new setup'])
            self.assertIs(self.manager.peripherals['tilt'], candidate)
            failed = Mock()
            failed.setup.side_effect = OSError('missing chip')
            module.Fake.return_value = failed
            self.command(['create'], ['tilt', 'fake', 0x19])
            candidate.cleanup.assert_called_once()
            failed.cleanup.assert_called_once()
            self.assertNotIn('tilt', self.manager.peripherals)
            self.manager._send.assert_called_with('/io/error', 'tilt', 'create-failed')

    def test_invalid_type_keeps_existing_instance(self):
        old = Mock()
        self.manager.peripherals['tilt'] = old
        self.command(['create'], ['tilt', 'missing_type', 0x19])
        old.cleanup.assert_not_called()
        self.assertIs(self.manager.peripherals['tilt'], old)

    def test_poll_serializes_write_scan_and_replacement(self):
        for operation in ('write', 'scan', 'replace'):
            with self.subTest(operation=operation):
                reading, release, attempting, finished = (threading.Event() for _ in range(4))
                fake = Mock()
                fake.address = 0x19
                def read():
                    reading.set()
                    if not release.wait(2):
                        raise RuntimeError('test timed out')
                    return [1]
                fake.read_data.side_effect = read
                self.manager.peripherals = {'tilt': fake}
                self.manager.osc_client = Mock()
                candidate = Mock()
                module = types.SimpleNamespace(Fake=Mock(return_value=candidate))
                calls = {'write': (['tilt'], ['clear']), 'scan': (['scan'], []),
                         'replace': (['create'], ['tilt', 'fake', 0x19])}
                def command():
                    attempting.set()
                    self.manager.handle_io(*calls[operation])
                    finished.set()
                with patch.dict(bridge.PERIPHERAL_TYPES, fake=('io_fake', 'Fake')), \
                        patch.dict(sys.modules, io_fake=module), \
                        patch.object(bridge, 'scan_bus', return_value=[]) as scan:
                    reader = threading.Thread(target=self.manager.poll_and_send)
                    writer = threading.Thread(target=command)
                    reader.start()
                    try:
                        self.assertTrue(reading.wait(1))
                        writer.start()
                        self.assertTrue(attempting.wait(1))
                        self.assertFalse(finished.wait(0.05))
                        fake.write_data.assert_not_called()
                        fake.cleanup.assert_not_called()
                        scan.assert_not_called()
                    finally:
                        release.set()
                        reader.join(2)
                        if writer.ident is not None:
                            writer.join(2)
                    self.assertFalse(reader.is_alive())
                    self.assertFalse(writer.is_alive())
                    self.assertTrue(finished.is_set())
                    if operation == 'write':
                        fake.write_data.assert_called_once()
                    elif operation == 'scan':
                        scan.assert_called_once()
                    else:
                        fake.cleanup.assert_called_once()
                        candidate.setup.assert_called_once()


class LIS3DHTests(unittest.TestCase):
    def test_explicit_address_and_default_are_passed_to_driver(self):
        driver = Mock()
        with patch.dict(sys.modules, PiicoDev_LIS3DH=types.SimpleNamespace(PiicoDev_LIS3DH=driver)):
            lis = load_module('lis3dh_under_test', IO_DIR / 'io_lis3dh.py')
        for address, expected in ((None, 0x19), (0x18, 0x18), (0x4B, 0x4B)):
            sensor = lis.IO_LIS3DH(address=address)
            self.assertEqual(sensor.address, expected)
            sensor.setup()
            driver.assert_called_with(address=expected)
        driver.side_effect = OSError('no chip at requested address')
        with self.assertRaises(OSError):
            lis.IO_LIS3DH(address=0x4B).setup()


if __name__ == '__main__':
    unittest.main()
