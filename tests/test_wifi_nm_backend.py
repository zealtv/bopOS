"""NetworkManager helper without radios, root privileges or a running daemon."""
import configparser
import contextlib
import importlib.machinery
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock
import uuid

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'python'))
loader = importlib.machinery.SourceFileLoader('wifi_nm_helper', str(REPO / 'systemd/bopos-set-wifi'))
spec = importlib.util.spec_from_loader(loader.name, loader)
helper = importlib.util.module_from_spec(spec)
loader.exec_module(helper)
MISSING_USER_DATA = "Error: 'connection show': invalid field 'user.data'; no fields\n"


def row(ssid, secret='fixture-passphrase', enabled=True, hidden=False):
    return dict(ssid=ssid, psk=secret, enabled=enabled, hidden=hidden)


def config(*rows, country='GB'):
    return dict(country=country, networks=list(rows))


def escaped(value):
    return value.replace('\\', '\\\\').replace(':', '\\:')


class FakeNM:
    """Return nmcli's terse output; record argv separately from private stdin."""
    def __init__(self, profile_dir):
        self.profile_dir = Path(profile_dir)
        self.calls = []
        self.inputs = []
        self.profiles = {}
        self.country = 'GB'
        self.devices = 'wl-test0:wifi:connected\n'
        self.fail = None

    def add(self, ssid, owned=False, secret='fixture-existing', active=False, priority=0):
        ident = str(uuid.uuid4())
        self.profiles[ident] = dict(ssid=ssid, secret=secret, active=active,
                                   priority=priority, hidden=False, enabled=True,
                                   data=None,
                                   name='netplan-wlan0-' + ssid)
        if owned:
            path = self.profile_dir / ('bopos-' + ident + '.nmconnection')
            path.write_text(
                '[connection]\nuuid=' + ident + '\n\n[user]\nbopos.wifi=1\n')
            path.chmod(0o600)
        return ident

    def __call__(self, argv, **kwargs):
        self.calls.append(list(argv))
        if self.fail is not None:
            if isinstance(self.fail, BaseException):
                raise self.fail
            return SimpleNamespace(returncode=self.fail, stdout='', stderr='private failure')
        if argv[0] == helper.IW:
            if argv[1:] == ['reg', 'get']:
                output = 'global\ncountry ' + self.country + ': DFS-ETSI\n'
            else:
                assert argv[1:3] == ['reg', 'set']
                self.country = argv[3]
                output = ''
            return SimpleNamespace(returncode=0, stdout=output)
        assert argv[:3] == [helper.NMCLI, '--wait', '5'], argv
        args = argv[3:]
        if args == ['-t', '-f', 'DEVICE,TYPE,STATE', 'device', 'status']:
            output = self.devices
        elif args == ['-t', '-f', 'UUID,TYPE,ACTIVE', 'connection', 'show']:
            output = ''.join(ident + ':802-11-wireless:' + ('yes' if p['active'] else 'no') + '\n'
                             for ident, p in self.profiles.items())
        elif args[:6] == ['-t', '-g', 'user.data', 'connection', 'show', 'uuid']:
            data = self.profiles[args[-1]]['data']
            if data is None:
                return SimpleNamespace(returncode=2, stdout='', stderr=MISSING_USER_DATA)
            output = escaped(data) + '\n'
        elif args[:3] == ['--show-secrets', '-t', '-g']:
            output = escaped(self.profiles[args[-1]]['secret']) + '\n'
        elif args[:3] == ['--show-secrets', '-t', '-f']:
            p = self.profiles[args[-1]]
            fields = args[3].split(',')
            if 'user.data' in fields and p['data'] is None:
                return SimpleNamespace(returncode=2, stdout='', stderr=MISSING_USER_DATA)
            values = {'connection.id': p['name'], '802-11-wireless.ssid': p['ssid'],
                      '802-11-wireless.hidden': 'yes' if p['hidden'] else 'no',
                      'connection.autoconnect': 'yes' if p['enabled'] else 'no',
                      'connection.autoconnect-priority': str(p['priority']),
                      '802-11-wireless-security.psk': p['secret'], 'user.data': p['data']}
            output = ''.join(key + ':' + escaped(values[key]) + '\n' for key in fields)
        elif args[:3] == ['--offline', 'connection', 'modify']:
            self.inputs.append(kwargs['input'])
            output = kwargs['input']
        elif args[:2] == ['connection', 'load']:
            parser = configparser.ConfigParser(interpolation=None)
            parser.read(args[2])
            ident = parser['connection']['uuid']
            # Test the exact GLib escaping the generator writes.
            def unescape(value):
                return (value.replace('\\s', ' ').replace('\\n', '\n')
                        .replace('\\r', '\r').replace('\\t', '\t').replace('\\\\', '\\'))
            was_active = self.profiles.get(ident, {}).get('active', False)
            ssid = bytes(int(n) for n in parser['wifi']['ssid'].rstrip(';').split(';')).decode('utf-8')
            # Do not synthesize a usable CLI ownership dictionary from the
            # file. Production must read its actual canonical keyfile itself.
            self.profiles[ident] = dict(ssid=ssid, data=None,
                name=parser['connection']['id'], active=was_active,
                secret=unescape(parser['wifi-security']['psk']),
                hidden=parser['wifi'].getboolean('hidden'),
                enabled=parser['connection'].getboolean('autoconnect'),
                priority=int(parser['connection']['autoconnect-priority']))
            output = ''
        elif args[:2] == ['connection', 'delete']:
            self.profiles.pop(args[3])
            (self.profile_dir / ('bopos-' + args[3] + '.nmconnection')).unlink(missing_ok=True)
            output = ''
        elif args[:2] == ['connection', 'down']:
            self.profiles[args[3]]['active'] = False
            output = ''
        else:
            raise AssertionError(argv)
        return SimpleNamespace(returncode=0, stdout=output)


class BackendTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.nm = FakeNM(self.directory)
        self.backend = helper.NetworkManager(self.nm, self.directory,
                                            self.directory / 'country.conf')

    def apply(self, value):
        code, state = helper.backend_apply(helper.wifi_config.validate(value), self.backend)
        self.assertEqual(code, 0)
        # Disk writes/normalization are permitted before receipt; live changes aren't.
        self.assertFalse(any('load' in call or 'delete' in call or 'down' in call
                             for call in self.nm.calls))
        self.backend.activate()
        return state

    def test_nm_152_missing_user_setting_is_unmanaged_and_read_only(self):
        ident = self.nm.add('fixture-imager', active=True)
        argv = [helper.NMCLI, '--wait', '5', '--show-secrets', '-t', '-f',
                'connection.id,user.data', 'connection', 'show', 'uuid', ident]
        result = self.nm(argv)
        self.assertEqual((result.returncode, result.stdout, result.stderr),
                         (2, '', MISSING_USER_DATA))
        output, errors = io.StringIO(), io.StringIO()
        with mock.patch.object(helper, 'NetworkManager', return_value=self.backend), \
             mock.patch.object(sys, 'argv', ['bopos-set-wifi', '--status']), \
             contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            self.assertEqual(helper.main(), 0)
        self.assertEqual(json.loads(output.getvalue()), dict(managed=True, country='GB',
                         active='fixture-imager', networks=[], unmanaged=['fixture-imager']))
        self.assertEqual(errors.getvalue(), '')
        self.assertEqual(list(self.directory.iterdir()), [])
        self.assertFalse(any('modify' in call or 'load' in call or 'delete' in call
                             or 'down' in call for call in self.nm.calls))

    def test_unrelated_user_data_is_not_owned(self):
        ident = self.nm.add('fixture-unmanaged')
        self.nm.profiles[ident]['data'] = 'fixture.owner = 1'
        self.assertEqual(self.backend.status()['unmanaged'], ['fixture-unmanaged'])
        self.assertEqual(self.backend.status()['networks'], [])
        self.assertEqual(list(self.directory.iterdir()), [])

    def test_helper_written_files_round_trip_without_cli_user_data(self):
        state = self.apply(config(row('fixture-Ta', hidden=True), row('fixture-Tb'),
                                  row('fixture-Tc', enabled=False)))
        for ident in self.nm.profiles:
            result = self.nm([helper.NMCLI, '--wait', '5', '-t', '-g', 'user.data',
                              'connection', 'show', 'uuid', ident])
            self.assertEqual((result.returncode, result.stderr), (2, MISSING_USER_DATA))
            path = self.directory / ('bopos-' + ident + '.nmconnection')
            self.assertTrue(path.is_file())
            self.assertIn('[user]\nbopos.wifi=1', path.read_text())
        self.assertEqual(self.backend.status(), state)
        self.assertEqual(len(state['networks']), 3)
        self.assertTrue(all(p['owned'] for p in self.backend.snapshot()[1]))

    def test_ownership_requires_canonical_filename_matching_uuid_and_direct_user_key(self):
        ident = self.nm.add('fixture-marker')
        content = '[connection]\nuuid=' + ident + '\n\n[user]\nbopos.wifi=1\n'
        wrong_path = self.directory / (ident + '.nmconnection')
        wrong_path.write_text(content)
        self.assertFalse(self.backend.snapshot()[1][0]['owned'])
        path = self.directory / ('bopos-' + ident + '.nmconnection')
        wrong_path.rename(path)
        self.assertTrue(self.backend.snapshot()[1][0]['owned'])
        for bad in (content.replace(ident, str(uuid.uuid4())),
                    content.replace('bopos.wifi=1', 'data=bopos.wifi=1'),
                    content.replace('[user]', '[unrelated]')):
            path.write_text(bad)
            self.assertFalse(self.backend.snapshot()[1][0]['owned'])

    def test_malformed_owned_keyfile_diagnostic_never_quotes_secret_lines(self):
        ident = self.nm.add('fixture-malformed', owned=True)
        path = self.directory / ('bopos-' + ident + '.nmconnection')
        path.write_text('[connection]\nuuid=' + ident + '\n[wifi-security]\n'
                        'psk=fixture-private-secret\npsk=fixture-private-secret\n')
        errors = io.StringIO()
        with contextlib.redirect_stderr(errors):
            self.assertEqual(helper.backend_status(self.backend), {'managed': False})
        self.assertEqual(errors.getvalue(), 'bopos-set-wifi status: ValueError\n')

    def test_pi_check_expected_observed_output_redacts_non_test_names_and_secrets(self):
        # This guards a development-only verification script that lives in a
        # work-tracking dot-directory of the development repository. Its
        # directory name changes with work lifecycle, so find it by name. A
        # release export carries no such directory; the check then has
        # nothing to guard and is skipped.
        matches = sorted(
            found
            for work in REPO.glob('.*')
            if work.is_dir() and work.name.lstrip('.') not in {'git', 'github', 'claude', 'worktrees'}
            for found in work.glob('*/**/2-network-config-implementation*/pi-safe-check.py'))
        if not matches:
            self.skipTest('development-only verification script absent (release export)')
        self.assertEqual(len(matches), 1, matches)
        path = matches[0]
        loader = importlib.machinery.SourceFileLoader('pi_check_test', str(path))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        check = importlib.util.module_from_spec(spec)
        loader.exec_module(check)
        expected = [dict(ssid='fixture-Ta', hidden=True, enabled=True, secret=True)]
        output = io.StringIO()
        observed = [dict(ssid='fixture-private-ssid', hidden=True, enabled=False,
                         secret='fixture-private-secret', psk='fixture-private-secret')]
        with contextlib.redirect_stdout(output), self.assertRaises(AssertionError):
            check.expect_networks(expected, observed, ['fixture-Ta'])
        text = output.getvalue()
        self.assertIn('"expected":', text)
        self.assertIn('"observed":', text)
        self.assertIn('"ssid": "Ta"', text)
        self.assertIn('<non-test>', text)
        self.assertNotIn('fixture-private', text)

    def test_metadata_errors_fail_with_class_only_status_diagnostic(self):
        self.nm.add('fixture-private-ssid', secret='fixture-private-secret')
        original = self.nm.__call__
        for code, stderr in ((1, MISSING_USER_DATA),
                             (2, "Error: 'connection show': invalid field 'other.data'; no fields\n"),
                             (2, 'fixture-private-ssid fixture-private-secret')):
            def refuse_metadata(argv, **kwargs):
                if '--show-secrets' in argv:
                    return SimpleNamespace(returncode=code, stdout='', stderr=stderr)
                return original(argv, **kwargs)
            self.backend.runner = refuse_metadata
            output, errors = io.StringIO(), io.StringIO()
            with self.subTest(code=code, stderr=stderr), \
                 mock.patch.object(helper, 'NetworkManager', return_value=self.backend), \
                 mock.patch.object(sys, 'argv', ['bopos-set-wifi', '--status']), \
                 contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
                self.assertEqual(helper.main(), 0)
            self.assertEqual(json.loads(output.getvalue()), {'managed': False})
            self.assertEqual(errors.getvalue(), 'bopos-set-wifi status: RuntimeError\n')
            self.assertEqual(helper.backend_apply(config(row('fixture-new')), self.backend)[0], 1)
            self.assertEqual(list(self.directory.iterdir()), [])

    def test_adopt_by_ssid_and_leave_unrelated_unmanaged_untouched(self):
        adopted = self.nm.add('fixture-adopt')
        untouched = self.nm.add('fixture-unmanaged', active=True)
        state = self.apply(config(row('fixture-adopt', None)))
        self.assertNotIn(adopted, self.nm.profiles)
        self.assertIn(untouched, self.nm.profiles)
        deletes = [call[-1] for call in self.nm.calls if 'delete' in call]
        self.assertEqual(deletes, [adopted])
        self.assertEqual(state['unmanaged'], ['fixture-unmanaged'])
        self.assertEqual(state['active'], 'fixture-unmanaged')
        self.assertEqual(self.backend.status(), state)
        owned = next(p for p in self.backend.snapshot()[1] if p['owned'])
        self.assertTrue(owned['secret'])
        self.assertIn('[user]\nbopos.wifi=1',
                      (self.directory / ('bopos-' + owned['uuid'] + '.nmconnection')).read_text())

    def test_create_hidden_disabled_root_only_and_no_secret_in_argv(self):
        secret = ' leading : \\ $(); trailing '
        state = self.apply(config(row('fixture-hidden', secret, hidden=True),
                                  row('fixture-disabled', enabled=False)))
        self.assertEqual(state['networks'], [dict(ssid='fixture-hidden', hidden=True, enabled=True, secret=True),
                                            dict(ssid='fixture-disabled', hidden=False, enabled=False, secret=True)])
        self.assertNotIn(secret, repr(self.nm.calls) + json.dumps(state))
        self.assertIn(helper.key_string(secret), ''.join(self.nm.inputs))
        self.assertEqual(self.backend.status(), state)
        for path in self.directory.glob('*.nmconnection'):
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertIn('psk-flags=0', path.read_text())
            self.assertIn('[user]\nbopos.wifi=1', path.read_text())
        disabled = next(p for p in self.nm.profiles.values() if p['ssid'] == 'fixture-disabled')
        self.assertFalse(disabled['enabled'])

    def test_reorder_priorities_keep_uuid_and_keep_secret(self):
        first = self.nm.add('fixture-first', owned=True, priority=2)
        second = self.nm.add('fixture-second', owned=True, priority=1)
        state = self.apply(config(row('fixture-second', None), row('fixture-first', None)))
        self.assertEqual([p['ssid'] for p in state['networks']], ['fixture-second', 'fixture-first'])
        self.assertGreater(self.nm.profiles[second]['priority'], self.nm.profiles[first]['priority'])
        self.assertEqual(self.nm.profiles[first]['secret'], 'fixture-existing')
        self.assertEqual(self.backend.status(), state)

    def test_missing_secret_rejects_whole_list_before_writes(self):
        self.nm.add('fixture-empty', secret='')
        for value in (config(row('fixture-new', None)),
                      config(row('fixture-first'), row('fixture-empty', None))):
            code, _ = helper.backend_apply(value, self.backend)
            self.assertEqual(code, 2)
            self.assertEqual(list(self.directory.iterdir()), [])
            self.assertFalse(any('load' in call or 'delete' in call for call in self.nm.calls))

    def test_remove_owned_and_active_disable_only_after_receipt(self):
        old = self.nm.add('fixture-old', owned=True)
        active = self.nm.add('fixture-active', owned=True, active=True)
        self.apply(config(row('fixture-active', None, enabled=False), row('fixture-fallback')))
        self.assertNotIn(old, self.nm.profiles)
        self.assertFalse(self.nm.profiles[active]['enabled'])
        self.assertFalse(self.nm.profiles[active]['active'])
        self.assertIn([helper.NMCLI, '--wait', '5', 'connection', 'down', 'uuid', active], self.nm.calls)

    def test_status_read_only_and_terse_ssid_escaping(self):
        self.nm.add('fixture:a\\b', owned=True, active=True)
        before = {p.name: p.read_bytes() for p in self.directory.iterdir()}
        state = self.backend.status()
        self.assertEqual(state['active'], 'fixture:a\\b')
        self.assertEqual({p.name: p.read_bytes() for p in self.directory.iterdir()}, before)
        self.assertFalse(any('modify' in call or 'load' in call or 'delete' in call for call in self.nm.calls))
        self.assertEqual(helper.terse('a\\:b:c\\\\d'), ['a:b', 'c\\d'])

    def test_missing_nmcli_daemon_failure_and_no_wifi(self):
        for failure, expected in ((FileNotFoundError(), 3), (8, 3), (1, 1),
                                  (subprocess.TimeoutExpired('nmcli', 5), 1)):
            self.nm.fail = failure
            self.assertEqual(helper.backend_apply(config(row('fixture-new')), self.backend)[0], expected)
            self.assertEqual(helper.backend_status(self.backend), {'managed': False})
        self.nm.fail = None
        self.nm.devices = 'eth-test:ethernet:connected\n'
        self.assertEqual(helper.backend_apply(config(row('fixture-new')), self.backend)[0], 3)

    def test_failed_validation_has_no_writes_and_failed_activation_is_redacted(self):
        original = self.nm.__call__
        def refuse_offline(argv, **kwargs):
            if '--offline' in argv:
                return SimpleNamespace(returncode=1, stdout='', stderr='fixture-passphrase')
            return original(argv, **kwargs)
        self.backend.runner = refuse_offline
        self.assertEqual(helper.backend_apply(config(row('fixture-new')), self.backend)[0], 1)
        self.assertEqual(list(self.directory.iterdir()), [])
        self.backend.runner = self.nm
        self.backend.prepare(config(row('fixture-new')))
        self.nm.fail = 1
        with self.assertRaisesRegex(RuntimeError, '^nmcli failed$'):
            self.backend.activate()

    def test_country_change_is_deferred_and_persistent(self):
        code, state = helper.backend_apply(config(row('fixture-new'), country='AU'), self.backend)
        self.assertEqual(code, 0)
        self.assertEqual(state['country'], 'AU')
        self.assertFalse((self.directory / 'country.conf').exists())
        self.assertEqual(self.nm.country, 'GB')
        self.backend.activate()
        self.assertEqual(self.nm.country, 'AU')
        self.assertEqual((self.directory / 'country.conf').read_text(),
                         'options cfg80211 ieee80211_regdom=AU\n')

    def test_helper_output_precedes_activation_and_stdin_release(self):
        output = io.StringIO()
        events = []
        class Input(io.StringIO):
            def read(self, size=-1):
                events.append(('release', json.loads(output.getvalue())))
                return super().read(size)
        original = self.backend.activate
        def activate():
            events.append(('activate', json.loads(output.getvalue())))
            original()
        payload = json.dumps(config(row('fixture-new'))) + '\n'
        with mock.patch.object(helper, 'NetworkManager', return_value=self.backend), \
             mock.patch.object(self.backend, 'activate', side_effect=activate), \
             mock.patch.object(sys, 'argv', ['bopos-set-wifi']), \
             mock.patch.object(sys, 'stdin', Input(payload)), contextlib.redirect_stdout(output):
            self.assertEqual(helper.main(), 0)
        self.assertEqual([e[0] for e in events], ['release', 'activate'])
        self.assertTrue(all(e[1]['managed'] for e in events))
        self.assertNotIn('fixture-passphrase', output.getvalue())


if __name__ == '__main__':
    unittest.main()
