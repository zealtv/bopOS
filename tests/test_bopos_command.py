"""Human command/update fixtures with local Git and intercepted privilege calls."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import fixture_git

sys.dont_write_bytecode = True
REPO = Path(__file__).resolve().parents[1]


class BoposCommandTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='bopos-command-')
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)
        self.source = self.base / 'source'
        self.root = self.base / 'node'
        self.source.mkdir()
        self.git(self.source, 'init', '-b', 'main')
        self.git(self.source, 'config', 'user.name', 'Fixture')
        self.git(self.source, 'config', 'user.email', 'fixture@example.invalid')
        for directory in ('bash', 'systemd', 'patches'):
            (self.source / directory).mkdir()
        self.marker = self.base / 'level'
        self.marker.write_text('1\n')
        update = (REPO / 'bash/update.sh').read_text().replace('/etc/bopos/provision-level', str(self.marker))
        (self.source / 'bash/update.sh').write_text(update)
        (self.source / 'bash/provision.sh').write_text('#!/bin/bash\necho provisioned >> "$CALLS"\n')
        (self.source / 'bash/provision.sh').chmod(0o755)
        (self.source / 'systemd/provision-level').write_text('1\n')
        (self.source / 'patches/active_patch.txt').write_text('default\n')
        (self.source / 'payload').write_text('old')
        self.commit('Initial fixture')
        subprocess.run(['git', 'clone', str(self.source), str(self.root)], cwd=self.base,
                       env=fixture_git.environment(), check=True, capture_output=True)
        (self.root / 'patches/active_patch.txt').write_text('selected\n')
        self.bin = self.base / 'bin'
        self.bin.mkdir()
        self.calls = self.base / 'calls'
        for name, body in {
            'sudo': 'echo "$*" >> "$CALLS"\ncase "$1" in */provision.sh) exec "$1" ;; esac\n',
            'systemctl': 'echo "systemctl $*" >> "$CALLS"\n',
            'journalctl': 'echo "journalctl $*" >> "$CALLS"\n',
        }.items():
            path = self.bin / name
            path.write_text('#!/bin/bash\n' + body)
            path.chmod(0o755)
        self.command = self.bin / 'bopos'
        self.command.write_text((REPO / 'bash/bopos').read_text().replace('/home/pi/bopOS', str(self.root)))
        self.env = dict(fixture_git.environment(), CALLS=str(self.calls), PATH=str(self.bin) + os.pathsep + os.environ['PATH'])

    def git(self, root, *args):
        return subprocess.check_output(['git', '-C', str(root), *args], cwd=root,
                                       env=fixture_git.environment(), text=True, stderr=subprocess.DEVNULL).strip()

    def commit(self, message):
        self.git(self.source, 'add', '.')
        self.git(self.source, 'commit', '-m', message)

    def run_command(self, *args):
        return subprocess.run(['bash', str(self.command), *args], text=True, capture_output=True, env=self.env, cwd=self.root, timeout=15)

    def test_plain_case_lists_and_routes_commands(self):
        self.assertIn('bopos update', self.run_command().stdout)
        for action in ('start', 'stop', 'restart'):
            self.assertEqual(self.run_command(action).returncode, 0)
        self.assertEqual(self.run_command('logs').returncode, 0)
        self.assertEqual(self.calls.read_text().splitlines(), [
            '/usr/bin/systemctl start bopos.target', '/usr/bin/systemctl stop bopos.target',
            '/usr/bin/systemctl restart bopos.target', 'journalctl -u bopos* -b -f'])
        self.assertEqual(self.run_command('unknown').returncode, 2)

    def test_update_preserves_selection_and_provisions_changed_root_files(self):
        (self.source / 'systemd/fixture.service').write_text('changed root-owned unit')
        self.commit('Change privileged pieces')
        result = self.run_command('update')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.root / 'patches/active_patch.txt').read_text(), 'selected\n')
        self.assertIn('provisioned', self.calls.read_text())
        self.assertTrue(self.calls.read_text().endswith('/usr/bin/systemctl restart bopos.target\n'))

    def test_update_without_privileged_change_only_restarts(self):
        (self.source / 'payload').write_text('new')
        self.commit('Framework-only change')
        result = self.run_command('update')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.calls.read_text(), '/usr/bin/systemctl restart bopos.target\n')

    def test_old_marker_requires_provision_even_without_new_commit(self):
        self.marker.write_text('0\n')
        result = self.run_command('update')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('provisioned', self.calls.read_text())

    def test_failed_pull_preserves_selection_and_does_not_restart(self):
        (self.root / 'payload').write_text('local modification')
        (self.source / 'payload').write_text('new')
        self.commit('Conflicting update')
        result = self.run_command('update')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual((self.root / 'patches/active_patch.txt').read_text(), 'selected\n')
        self.assertFalse(self.calls.exists())

    def test_status_uses_the_real_read_only_helper(self):
        (self.root / 'python').mkdir()
        for path in (REPO / 'python').glob('*.py'):
            shutil.copy(path, self.root / 'python' / path.name)
        home = self.base / 'home/venv/bin'
        home.mkdir(parents=True)
        (home / 'python').symlink_to(sys.executable)
        self.env['HOME'] = str(self.base / 'home')
        result = self.run_command('status')
        self.assertEqual(result.returncode, 0, result.stderr)
        for expected in ('Engine alive: 0', 'Active patch: selected', 'Framework version: unknown',
                         'Framework revision:', 'Last bopos log lines:', 'Last io log lines:'):
            self.assertIn(expected, result.stdout)

    def test_version_prints_the_release_version_of_the_checkout(self):
        (self.root / 'python').mkdir()
        shutil.copy(REPO / 'python/version_identity.py', self.root / 'python')
        home = self.base / 'home/venv/bin'
        home.mkdir(parents=True)
        (home / 'python').symlink_to(sys.executable)
        self.env['HOME'] = str(self.base / 'home')
        (self.root / 'VERSION').write_text('1.0.0\n')
        self.git(self.root, 'tag', 'v1.0.0')
        result = self.run_command('version')
        self.assertEqual((result.returncode, result.stdout), (0, 'bopOS 1.0.0\n'), result.stderr)
        self.git(self.root, '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                 'commit', '--allow-empty', '-m', 'Ahead of the release')
        self.assertRegex(self.run_command('version').stdout, r'^bopOS 1\.0\.0\+dev\.1\.g[0-9a-f]{7}\n$')

    def test_dashboard_maps_machine_token_to_draft_wording(self):
        source = (REPO / 'dashboard/static/js/dashboard-devices.js').read_text()
        function = source[source.index('function frameworkReceiptText'):source.index('function deviceFactsMarkup')]
        script = function + '\nconsole.log(JSON.stringify([frameworkReceiptText({status:"err",phase:"provision"}), frameworkReceiptText({status:"err",phase:"pull"})]));'
        result = subprocess.run(['node', '-e', script], text=True, capture_output=True, check=True)
        self.assertEqual(json.loads(result.stdout), ['Update bopOS needs device setup. Run bopos update on this device, then try again.', 'err pull'])


if __name__ == '__main__':
    unittest.main()
