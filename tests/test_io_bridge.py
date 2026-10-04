"""IO dispatch and lifecycle checks without sockets, browsers or hardware."""
import contextlib
import importlib.util
import io
import json
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
    def test_declared_create_is_idempotent_and_conflict_preserves_live_chip(self):
        declaration = {'name': 'tilt', 'type': 'lis3dh', 'address': '0x19'}
        peripheral = Mock(address=0x19)
        with patch.object(bridge.patch_manifest, 'load', return_value=({'io_modules': [declaration]}, None)), \
                patch.object(bridge, 'scan_inventory', return_value=(True, [{'address': '0x19', 'claimed': False}])), \
                patch.object(self.manager, 'create_peripheral', side_effect=lambda *args: self.manager.peripherals.update(tilt=peripheral) or True) as create:
            self.command(['create'], ['tilt', 'lis3dh', '0x19'])
            self.command(['create'], ['tilt', 'lis3dh', 25])
            self.assertEqual(create.call_count, 1)
            for kind, address in [('wrong', '0x19'), ('lis3dh', '0x18')]:
                self.command(['create'], ['tilt', kind, address])
                self.manager._send.assert_called_with('/io/error', 'tilt', 'create-failed')
                self.assertIs(self.manager.peripherals['tilt'], peripheral)
                self.assertEqual(self.manager.io['modules']['tilt']['state'], 'running')
            peripheral.cleanup.assert_not_called()

    def test_missing_optional_and_required_modules_and_present_setup_failure(self):
        for optional in (True, False):
            declaration = {'name': 'tilt', 'type': 'lis3dh', 'address': '0x19', 'optional': optional}
            for usable in (True, False):
                with patch.object(bridge.patch_manifest, 'load', return_value=({'io_modules': [declaration]}, None)), \
                        patch.object(bridge, 'scan_inventory', return_value=(usable, [])):
                    self.manager._send.reset_mock()
                    self.command(['create'], ['tilt', 'lis3dh', '0x19'])
                self.assertEqual(self.manager.io['modules']['tilt']['state'], 'missing')
                errors = [call for call in self.manager._send.call_args_list if call.args[0] == '/io/error']
                self.assertEqual(len(errors), 0 if optional else 1)
        with patch.object(bridge.patch_manifest, 'load', return_value=({'io_modules': [declaration]}, None)), \
                patch.object(bridge, 'scan_inventory', return_value=(True, [{'address': '0x19', 'claimed': False}])), \
                patch.object(self.manager, 'create_peripheral', return_value=False):
            self.command(['create'], ['tilt', 'lis3dh', '0x19'])
        self.assertEqual(self.manager.io['modules']['tilt']['state'], 'errored')
        self.manager._send.assert_called_with('/io/error', 'tilt', 'create-failed')

    def test_patch_change_retires_declared_modules(self):
        self.manager.declared = {'tilt': {'name': 'tilt', 'type': 'lis3dh', 'address': '0x19'}}
        peripheral = Mock(address=0x19)
        self.manager.peripherals['tilt'] = peripheral
        with patch.object(bridge.patch_manifest, 'load', return_value=({'io_modules': []}, None)):
            self.command(['report'])
        peripheral.cleanup.assert_called_once()
        self.assertNotIn('tilt', self.manager.peripherals)
        self.assertNotIn('tilt', self.manager.io['modules'])

    def test_manifest_ownership_replaces_conflicting_legacy_instance(self):
        peripheral = Mock(address=0x18)
        self.manager.peripherals['tilt'] = peripheral
        self.manager.io['modules']['tilt'] = dict(type='lis3dh', address='0x18', state='running', error=None)
        row = {'name': 'tilt', 'type': 'lis3dh', 'address': '0x19', 'optional': True}
        with patch.object(bridge.patch_manifest, 'load', return_value=({'io_modules': [row]}, None)), \
                patch.object(bridge, 'scan_inventory', return_value=(True, [])):
            self.command(['create'], ['tilt', 'lis3dh', '0x19'])
        peripheral.cleanup.assert_called_once()
        self.assertEqual(self.manager.io['modules']['tilt']['address'], '0x19')
        self.assertEqual(self.manager.io['modules']['tilt']['state'], 'missing')

    def test_vendor_read_diagnostics_do_not_swallow_other_threads_logs(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            with contextlib.redirect_stdout(bridge._ReadOutput(sys.stdout)):
                print('vendor diagnostic')
                thread = threading.Thread(target=lambda: print('other thread'))
                thread.start()
                thread.join(timeout=2)
        self.assertEqual(output.getvalue(), 'other thread\n')

    def test_read_failures_have_one_line_no_invalid_values_and_recover(self):
        def failed_read():
            print('Error reading from LIS3DH at address 0x19')
            raise TypeError("a bytes-like object is required, not 'float'")
        peripheral = Mock(address=0x19)
        peripheral.read_data.side_effect = failed_read
        self.manager.peripherals['tilt'] = peripheral
        self.manager.io['modules']['tilt'] = dict(type='lis3dh', address='0x19', state='running', error=None)
        for failure in (failed_read, lambda: [float('nan')], lambda: [None]):
            peripheral.read_data.side_effect = failure
            with contextlib.redirect_stdout(io.StringIO()) as output:
                self.manager.poll_and_send()
            self.assertEqual(output.getvalue(), "Error reading tilt at 0x19: the bus didn't answer\n")
            self.assertEqual(self.manager.io['modules']['tilt']['state'], 'errored')
        peripheral.read_data.side_effect = lambda: [1, 2, 3]
        self.manager.poll_and_send()
        self.assertEqual(self.manager.io['modules']['tilt']['state'], 'running')

    def test_driver_descriptions_do_not_import_hardware_and_cover_all_types(self):
        from io_catalog import descriptions, PERIPHERAL_TYPES
        with patch('builtins.__import__', side_effect=AssertionError('hardware import')):
            # Clear the cache so this exercises parsing, not a cached result.
            descriptions.cache_clear()
            catalog = descriptions()
        self.assertEqual(set(catalog), set(PERIPHERAL_TYPES))
        self.assertEqual(catalog['lis3dh']['inputs'][0]['unit'], 'degrees')
        self.assertEqual(len(catalog['ads1115']['inputs']), 4)
        self.assertEqual([row['command'] for row in catalog['rgb']['outputs']],
                         ['pixel', 'fill', 'all', 'hsv', 'clear', 'bright', 'power'])

    def setUp(self):
        with patch.object(bridge, 'OSCClient'):
            self.manager = bridge.IOManager()
        self.manager._send = Mock()
        self.bus = patch.object(bridge, 'usable_bus', return_value=True)
        self.bus.start()
        self.addCleanup(self.bus.stop)
        present = patch.object(bridge, 'have_bus', return_value=True)
        present.start()
        self.addCleanup(present.stop)

    def command(self, parts, args=()):
        with contextlib.redirect_stdout(io.StringIO()) as output:
            self.manager.handle_io(parts, args)
        return output.getvalue()

    def test_invalid_create_arguments_use_ratified_error(self):
        for address in ('bad', float('nan'), float('inf'), None, 4.5, -1, 128):
            with self.subTest(address=address):
                self.command(['create'], ['tilt', 'lis3dh', address])
                self.manager._send.assert_called_with('/io/error', 'tilt', 'invalid-arguments')
        with patch.object(bridge, 'have_bus', return_value=False):
            self.command(['create'], ['tilt', 'lis3dh', '0x19'])
        self.manager._send.assert_called_with('/io/error', 'tilt', 'no-bus')

    def test_poll_bad_arguments_preserve_rate_and_reply(self):
        for args in ([], ['bad'], [None], [float('inf')], [float('nan')]):
            with self.subTest(args=args):
                self.assertIn('Invalid /io/poll', self.command(['poll'], args))
                self.assertEqual(self.manager.poll_rate, bridge.DEFAULT_POLL_RATE)
                self.manager._send.assert_called_with('/io/error', 'bridge', 'invalid-arguments')
        self.command(['poll'], [20])
        self.assertEqual(self.manager.poll_rate, 20)
        self.command(['poll'], [-1])
        self.assertEqual(self.manager.poll_rate, 0.1)

    def test_verbs_precede_peripherals_and_reserved_names_cannot_be_created(self):
        for verb in bridge.RESERVED_NAMES:
            fake = Mock()
            self.manager.peripherals[verb] = fake
            args = {'create': [], 'poll': [10], 'report': [], 'scan': []}.get(verb, [])
            with patch.object(bridge, 'scan_inventory', return_value=(True, [])):
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
        self.manager._send.assert_called_with('/io/error', 'bridge', 'invalid-arguments')

    def test_other_error_branches_reply_with_ratified_tokens(self):
        self.assertIn('Invalid /io/create', self.command(['create']))
        self.manager._send.assert_called_with('/io/error', 'bridge', 'invalid-arguments')
        for value in ('bad', None, float('nan'), -1, 1.5):
            self.assertIn('Invalid /io/scan', self.command(['scan'], [value]))
            self.manager._send.assert_called_with('/io/error', 'bridge', 'invalid-arguments')
        fake = Mock()
        fake.write_data.side_effect = OSError('chip unavailable')
        self.manager.peripherals['light'] = fake
        self.assertIn('Error writing to light', self.command(['light'], ['clear']))
        self.manager._send.assert_called_with('/io/error', 'light', 'write-failed')

    def test_scan_skips_registered_addresses(self):
        self.manager.peripherals['tilt'] = types.SimpleNamespace(address=0x18)
        addresses = [{'address': '0x18', 'claimed': False}]
        with patch.object(bridge, 'scan_inventory', return_value=(True, addresses)) as scan:
            self.command(['scan'])
        scan.assert_called_once_with(1, skip=[0x18])
        self.manager._send.assert_any_call('/io/scan', 0x18)
        self.assertEqual(json.loads(self.manager._send.call_args.args[1]),
                         dict(bus=1, scanned=True, addresses=addresses, modules={}))

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
        self.manager.io['modules']['tilt'] = {
            'type': 'lis3dh', 'address': '0x18', 'state': 'running', 'error': None}
        self.command(['create'], ['tilt', 'missing_type', 0x19])
        old.cleanup.assert_not_called()
        self.assertIs(self.manager.peripherals['tilt'], old)
        self.assertEqual(self.manager.io['modules']['tilt'], {
            'type': 'lis3dh', 'address': '0x18', 'state': 'errored', 'error': 'create-failed'})

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
                        patch.object(bridge, 'scan_inventory', return_value=(True, [])) as scan:
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

    def test_replies_attempt_both_consumers_even_if_engine_is_absent(self):
        del self.manager._send
        self.manager.osc_client = Mock()
        self.manager.control_client = Mock()
        self.manager.osc_client.send.side_effect = OSError('no engine')
        with contextlib.redirect_stdout(io.StringIO()):
            self.manager._send('/io/error', 'bridge', 'invalid-arguments')
        self.manager.control_client.send.assert_called_once()

    def test_values_do_not_go_to_control_consumer(self):
        self.manager.peripherals['adc'] = Mock(read_data=Mock(return_value=[1, 2]))
        self.manager.osc_client = Mock()
        self.manager.control_client = Mock()
        self.manager.poll_and_send()
        self.manager.osc_client.send.assert_called_once()
        self.manager.control_client.send.assert_not_called()

    def test_scan_distinguishes_unavailable_empty_and_not_scanned(self):
        self.assertFalse(self.manager.io['scanned'])
        for usable in (False, True):
            with patch.object(bridge, 'scan_inventory', return_value=(usable, [])):
                self.command(['scan'])
            self.assertEqual(self.manager.io['bus'], 1 if usable else None)
            self.assertTrue(self.manager.io['scanned'])
            self.assertEqual(self.manager.io['addresses'], [])


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
