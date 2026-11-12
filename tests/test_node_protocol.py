"""Canonical expectations as well as cross-adapter datagram parity."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from node_protocol_fixture import load_node, probe


class NodeProtocolParityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with contextlib.redirect_stdout(io.StringIO()):
            cls.node = load_node()

    @classmethod
    def tearDownClass(cls):
        cls.node.param_generator.close()

    def send(self, address, values, **kwargs):
        with contextlib.redirect_stdout(io.StringIO()):
            result = probe(self.node, 'fixture', address, values, **kwargs)
        self.assertEqual(result['errors'], {})
        return result

    def test_enabled_requires_exact_numeric_switch(self):
        for value in (.5, -1, 2, '0', float('nan'), float('inf')):
            with self.subTest(value=value):
                result = self.send('/all/os/to', ['probe-node', 'enabled', value])
                self.assertEqual(result['replies'], {name: [] for name in result['replies']})
        for value in (0, 0.0, 1, 1.0):
            with self.subTest(value=value):
                result = self.send('/all/os/to', ['probe-node', 'enabled', value])
                self.assertTrue(result['replies_equal'])
                self.assertEqual(result['replies']['node'], [dict(address='/os/enabled',
                    tags=',sii', params=['probe-node', int(value), int(value)],
                    target=['127.0.0.1', 5550])])

    def test_assignment_rejects_whole_malformed_state(self):
        for tail in ([3.5, 'seat'], ['3', 'seat'], [3, 'seat', 1.0],
                     [3, 'seat', '1', 2.0], [-1, 'seat'],
                     [float('inf'), 'seat'], [float('nan'), 'seat'],
                     [3, 'seat', float('nan'), 2.0]):
            with self.subTest(tail=tail):
                result = self.send('/all/os/assign', ['probe-node', *tail])
                for state in result['assignment_after'].values():
                    self.assertEqual(state, dict(id=0, elements=[]))
        result = self.send('/all/os/assign', ['probe-node', 3, 'seat', 1.0, 2.0])
        for state in result['assignment_after'].values():
            self.assertEqual(state, dict(id=3, elements=[[1.0, 2.0]]))

    def test_silent_uid_and_arity_rejections(self):
        for values in (['other', 'report'], ['probe-node', 'unknown'],
                       ['probe-node', 'report', 1], ['probe-node', 'enabled'],
                       ['probe-node', 'hostname', 'bad/name']):
            with self.subTest(values=values):
                result = self.send('/all/os/to', values)
                self.assertTrue(result['replies_equal'])
                self.assertEqual(result['replies']['node'], [])

    def test_ping_preserves_token_tag(self):
        # Audition's missing ping binding is completed after extraction.
        for tag, value in [('s', 'nonce'), ('i', 7), ('f', .5), ('d', .5)]:
            result = self.send('/all/os/ping', [value], types=[tag])
            expected = [dict(address='/os/pong', tags=',' + tag + 's',
                            params=[value, 'probe-node'], target=['127.0.0.1', 5550])]
            self.assertEqual(result['replies']['node'], expected)
            self.assertEqual(result['replies']['simfleet'], expected)

    def test_malformed_datagrams_are_silent(self):
        for datagram in (b'', b'garbage', b'/all/os/to\0',
                         b'/all/os/to\0\0,ss\0probe-node\0'):
            with self.subTest(datagram=datagram):
                result = self.send('/unused', [], datagram=datagram)
                self.assertTrue(result['replies_equal'])
                self.assertEqual(result['replies']['node'], [])

    def test_sync_types_arity_and_reply(self):
        for args in ([], [1], [1.0, '123'], ['1', '123'], [1, 123], [1, '123', 2]):
            with self.subTest(args=args):
                result = self.send('/sync/ping', args)
                self.assertEqual(result['replies']['node'], [])
                self.assertEqual(result['replies']['simfleet'], [])
        result = self.send('/sync/ping', [1, '123'])
        expected = [dict(address='/sync/pong', tags=',isss',
                        params=[1, '123', 'probe-node', '123456'], target=['127.0.0.1', 5550])]
        self.assertEqual(result['replies']['node'], expected)
        self.assertEqual(result['replies']['simfleet'], expected)

    def test_malformed_sync_does_not_escape(self):
        result = self.send('/sync/ping', ['bad', '123'])
        self.assertEqual(result['replies']['node'], [])
        self.assertEqual(result['replies']['simfleet'], [])

    def test_reinit_extra_arguments_keep_real_receipt_convention(self):
        result = self.send('/all/os/to', ['probe-node', 'io-reinit', 'adc', 'extra'])
        expected = [dict(address='/os/io-reinit', tags=',sss',
                        params=['probe-node', 'err', {'name': 'bridge', 'error': 'invalid-arguments'}],
                        target=['127.0.0.1', 5550])]
        self.assertEqual(result['replies']['node'], expected)
        self.assertEqual(result['replies']['simfleet'], expected)

    def test_installed_patch_rows_include_invalid_manifests(self):
        import audition
        import identity
        import simfleet
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            patches = root / 'patches'
            for name in ('valid', 'invalid'):
                (patches / name).mkdir(parents=True)
            (patches / 'valid' / 'main.scd').write_text('// inert\n')
            loaded = dict(engine='sc', entrypoint='main.scd', params=[])
            (patches / 'valid' / 'bopos.patch.json').write_text(json.dumps(loaded))
            rig = object.__new__(audition.AuditionRig)
            rig.args = SimpleNamespace(patches_dir=str(patches))
            rig._load_patch = lambda: (str(patches / 'valid'), loaded)
            with patch.object(self.node, 'BOPOS_DIR', str(root)), patch.object(
                    self.node, 'active_patch_path', return_value=str(patches / 'valid')):
                expected = self.node.installed_patches()
            self.assertEqual([row['manifest'] for row in expected], [False, True])
            self.assertEqual(rig.patch_listing(), expected)
            from node_protocol_fixture import Capture
            fleet = object.__new__(simfleet.SimFleet)
            fleet.sock = Capture()
            fleet.args = SimpleNamespace(report_port=5550)
            device = SimpleNamespace(active_patch='valid', patches={
                row['name']: {'manifest': row['manifest'],
                              'fingerprint': identity.fingerprint(patches / row['name'])}
                for row in expected})
            fleet.send_patch_list(device, ('127.0.0.1', 4000))
            self.assertEqual(fleet.sock.calls[0]['params'], [expected])

    def test_report_schema_is_complete_and_host_facts_remain_honest(self):
        import node_protocol
        result = self.send('/all/os/to', ['probe-node', 'report'])
        for name, replies in result['replies'].items():
            with self.subTest(adapter=name):
                self.assertEqual(len(replies), 1)
                self.assertEqual(replies[0]['tags'], ',s')
                report = replies[0]['params'][0]
                self.assertEqual(set(report) - {'release'},
                                 node_protocol.REPORT_FIELDS | {'contract_version'})
                # Contract 1.26: node and simfleet report release; audition omits it.
                self.assertEqual(report.get('release'),
                                 None if name == 'audition' else '1.0.0')
                self.assertEqual(report['uid'], 'probe-node')
                self.assertFalse(report['performance'])
                self.assertEqual(report['wifi'], {'managed': False})
        self.assertEqual(result['replies']['audition'][0]['params'][0]['update_model'], 'ephemeral')
        with self.assertRaises(ValueError):
            node_protocol.report(uid='incomplete')

    def test_release_is_an_optional_additive_report_fact(self):
        import node_protocol
        facts = {name: None for name in node_protocol.REPORT_FIELDS}
        absent = json.loads(node_protocol.report(**facts)[1][0])
        self.assertNotIn('release', absent)
        self.assertNotIn('release', node_protocol.report(release=None, **facts)[1][0])
        sent = json.loads(node_protocol.report(release='1.0.0+dev.12.gabc1234', **facts)[1][0])
        self.assertEqual(sent['release'], '1.0.0+dev.12.gabc1234')
        self.assertEqual(sent['git_rev'], None)
        with self.assertRaises(ValueError):
            node_protocol.report(release='1.0.0', uid='incomplete')

    def test_simfleet_release_option_hands_values_out_in_turn(self):
        import simfleet
        with patch('sys.argv', ['simfleet', '--release', '1.0.0, 1.0.0+dev.3.gabc1234,-']):
            args = simfleet.parse_args()
        self.assertEqual(args.release, ['1.0.0', '1.0.0+dev.3.gabc1234', None])
        with patch('sys.argv', ['simfleet']):
            self.assertIsNone(simfleet.parse_args().release)

    def test_shared_receipts_match_existing_adapters(self):
        # Audition's missing operation bindings remain a separately ruled step.
        for member, args in [('io-write', ['{}']), ('io-reinit', ['a/b']),
                             ('log-config', ['{}']), ('wifi-config', ['{}'])]:
            with self.subTest(member=member):
                result = self.send('/all/os/to', ['probe-node', member, *args])
                self.assertEqual(result['replies']['node'], result['replies']['simfleet'])
                self.assertEqual(result['replies']['node'][0]['params'][1], 'err')

    def test_uid_envelope_requires_strings(self):
        for values in ([123, 'report'], ['probe-node', 123]):
            result = self.send('/all/os/to', values)
            self.assertTrue(result['replies_equal'])
            self.assertEqual(result['replies']['node'], [])

    def test_invalid_manifest_keeps_simfleet_online_without_declarations(self):
        import simfleet
        from node_protocol_fixture import Capture
        fleet = object.__new__(simfleet.SimFleet)
        fleet.args = SimpleNamespace(patches_dir='/missing', report_port=5550, target='127.0.0.1')
        fleet.manifest_text = None
        fleet.sock = Capture()
        device = simfleet.Device('probe-node', 'probe-node', 0, 'probe', ephemeral=True)
        device.declared_io_names = {'old'}
        device.io['modules']['old'] = dict(type='ads1115', address='0x48', state='missing', error=None)
        fleet.create_manifest_modules(device)
        self.assertEqual(device.declared_io_names, set())
        self.assertEqual(device.io['modules'], {})
        fleet.uid_admin(device, 'io-reinit', ['adc'], ('127.0.0.1', 4000))
        self.assertEqual(fleet.sock.calls[0]['params'], [
            'probe-node', 'err', {'name': 'adc', 'error': 'unknown-command'}])

    def test_simfleet_validates_entire_manifest_and_keeps_raw_text(self):
        import manifest
        import simfleet
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'main.scd').write_text('// inert\n')
            path = root / manifest.MANIFEST_NAME
            candidate = dict(engine='sc', entrypoint='main.scd',
                             params=[dict(name='gain', kind='not-a-kind')])
            path.write_text(json.dumps(candidate))
            self.assertIsNone(simfleet.load_manifest(str(path))[0])
            candidate['params'][0]['kind'] = 'float'
            text = json.dumps(candidate, indent=4) + '\n'
            path.write_text(text)
            self.assertEqual(simfleet.load_manifest(str(path)), (text, {'gain'}))
            # Never validate the canonical sibling and serve another file's bytes.
            alternate = root / 'other.json'
            alternate.write_text('{"params": "invalid"}')
            self.assertIsNone(simfleet.load_manifest(str(alternate))[0])


if __name__ == '__main__':
    unittest.main()
