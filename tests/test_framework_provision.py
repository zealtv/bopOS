"""Incoming provision checks use real local Git checkouts, never a Pi."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import fixture_git
from unittest import mock

sys.dont_write_bytecode = True
REPO = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(REPO / 'python'), str(REPO / 'tests')]
from test_admin_outcomes import bopos, ReplySocket
from types import SimpleNamespace
import provision_level


class FrameworkProvisionTests(unittest.TestCase):
    def git(self, root, *args):
        return subprocess.check_output(['git', '-C', str(root), *args], cwd=root,
                                       env=fixture_git.environment(), text=True, stderr=subprocess.DEVNULL).strip()

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='bopos-framework-provision-')
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)
        self.source = self.base / 'source'
        self.source.mkdir()
        self.git(self.source, 'init', '-b', 'main')
        self.git(self.source, 'config', 'user.name', 'Fixture')
        self.git(self.source, 'config', 'user.email', 'fixture@example.invalid')
        (self.source / 'patches').mkdir()
        (self.source / 'patches/active_patch.txt').write_text('default\n')
        (self.source / 'systemd').mkdir()
        (self.source / 'systemd/provision-level').write_text('0\n')
        (self.source / 'payload').write_text('old')
        self.commit('Initial fixture')
        self.root = self.base / 'node'
        subprocess.run(['git', 'clone', str(self.source), str(self.root)], cwd=self.base,
                       env=fixture_git.environment(), check=True, capture_output=True)
        (self.root / 'patches/active_patch.txt').write_text('selected\n')
        self.before = self.git(self.root, 'rev-parse', 'HEAD')
        self.marker = self.base / 'installed-level'
        (self.source / 'systemd/provision-level').write_text('1\n')
        (self.source / 'payload').write_text('new')
        self.commit('Require new privileged pieces')
        self.real_command = bopos._framework_command
        self.commands = []
        self.addCleanup(mock.patch.stopall)
        mock.patch.object(bopos, 'BOPOS_DIR', str(self.root)).start()
        mock.patch.object(bopos, '_framework_environment', side_effect=fixture_git.environment).start()
        mock.patch.object(provision_level, 'MARKER', str(self.marker)).start()
        mock.patch.object(bopos, '_framework_command', side_effect=self.command).start()

    def commit(self, message):
        self.git(self.source, 'add', '.')
        self.git(self.source, 'commit', '-m', message)

    def command(self, argv, phase, timeout=None):
        self.commands.append(argv)
        if phase == 'authorization':
            return None
        return self.real_command(argv, phase, timeout)

    def test_missing_or_older_level_refuses_before_any_checkout_change(self):
        for marker in (None, '0\n'):
            if marker is not None:
                self.marker.write_text(marker)
            (self.root / 'payload').write_text('local work')
            self.assertEqual(bopos.converge_framework(), {'status': 'err', 'phase': 'provision'})
            self.assertEqual(self.git(self.root, 'rev-parse', 'HEAD'), self.before)
            self.assertEqual((self.root / 'payload').read_text(), 'local work')
            self.assertEqual((self.root / 'patches/active_patch.txt').read_text(), 'selected\n')
            self.assertFalse(any('restore' in command or 'merge' in command for command in self.commands))

    def test_current_level_updates_pinned_revision_and_preserves_active_patch(self):
        self.marker.write_text('1\n')
        self.assertEqual(bopos.converge_framework(), {'status': 'ok', 'phase': 'converged', 'reboot': True})
        self.assertEqual((self.root / 'payload').read_text(), 'new')
        self.assertEqual((self.root / 'patches/active_patch.txt').read_text(), 'selected\n')
        merge = next(command for command in self.commands if 'merge' in command)
        self.assertEqual(merge[-1], self.git(self.source, 'rev-parse', 'HEAD'))
        self.assertFalse(any('pull' in command for command in self.commands))

    def test_checkout_is_also_guarded(self):
        self.assertEqual(bopos.converge_framework('main'), {'status': 'err', 'phase': 'provision'})
        self.assertEqual(self.git(self.root, 'rev-parse', 'HEAD'), self.before)

    def test_malformed_requirement_or_installed_marker_fails_closed(self):
        self.marker.write_text('broken')
        self.assertEqual(bopos.converge_framework()['phase'], 'provision')
        self.marker.write_text('999')
        (self.source / 'systemd/provision-level').write_text('broken')
        self.commit('Damaged requirement')
        self.assertEqual(bopos.converge_framework()['phase'], 'provision')
        self.assertEqual(self.git(self.root, 'rev-parse', 'HEAD'), self.before)

    def test_refusal_emits_existing_receipt_shape_without_reboot(self):
        reply = ReplySocket()
        state = SimpleNamespace(uid='node-a', update_model='persistent', version='old')
        with (mock.patch.object(bopos, 'resolve_version', return_value='oldsha'),
              mock.patch.object(bopos, 'request_power_action') as power):
            bopos.run_admin_verb(lambda *_args: bopos.converge_framework(), [], state, reply, '192.0.2.8')
            power.assert_not_called()
        self.assertEqual(reply.calls[0][0], ['/os/rev', ',sssss', 'oldsha', 'persistent', 'node-a', 'err', 'provision'])

    def test_old_framework_without_requirement_is_level_zero(self):
        (self.source / 'systemd/provision-level').unlink()
        self.commit('Old framework fixture')
        self.assertEqual(bopos.converge_framework()['status'], 'ok')


if __name__ == '__main__':
    unittest.main()
