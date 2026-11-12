"""Process ownership fixtures; no systemd instance or audio hardware required."""
import configparser
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.dont_write_bytecode = True
REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'python'))


class ProcessOwnershipTests(unittest.TestCase):
    def test_units_isolate_engine_failure_and_own_their_process_groups(self):
        units = {}
        for name in ('bopos.target', 'bopos.service', 'bopos-io.service', 'bopos-engine.service'):
            unit = configparser.ConfigParser(interpolation=None, strict=False)
            self.assertTrue(unit.read(REPO / 'systemd' / name), name)
            units[name] = unit
        target = units['bopos.target']
        self.assertEqual(set(target['Unit']['Wants'].split()), set(units) - {'bopos.target'})
        self.assertNotIn('Requires', target['Unit'])
        self.assertEqual(target['Install']['WantedBy'], 'multi-user.target')
        for name, unit in units.items():
            if name.endswith('.target'):
                continue
            self.assertEqual(unit['Unit']['PartOf'], 'bopos.target')
            self.assertNotIn('Requires', unit['Unit'])
            self.assertEqual(unit['Service']['KillMode'], 'control-group')
            self.assertNotIn('RemainAfterExit', unit['Service'])
            self.assertIn('/bash/run/', unit['Service']['ExecStart'])
            self.assertNotIn('Install', unit)
            if name != 'bopos-engine.service':
                self.assertEqual(unit['Service']['Restart'], 'always')
                self.assertEqual(unit['Service']['Type'], 'simple')
            else:
                self.assertEqual(unit['Service']['Restart'], 'no')
                self.assertEqual(unit['Service']['Type'], 'forking')
                self.assertEqual(unit['Service']['RuntimeDirectory'], 'bopos-engine')
                self.assertEqual(unit['Service']['PIDFile'], '/run/bopos-engine/engine.pid')
                self.assertGreaterEqual(int(unit['Service']['TimeoutStartSec']), 90)

    def test_no_pid_stopping_or_legacy_entry_points(self):
        for name in ('start.sh', 'stop.sh', 'stop-engine.sh', 'start-engine.sh', 'restart.sh'):
            self.assertFalse((REPO / 'bash' / name).exists(), name)
        self.assertFalse((REPO / 'systemd/bopos-helper.service').exists())
        for path in (REPO / 'bash').rglob('*.sh'):
            self.assertNotIn('pkill', path.read_text(), str(path))

    def test_foreground_wrappers_propagate_python_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'bash/run').mkdir(parents=True)
            (root / 'python/io').mkdir(parents=True)
            (root / 'venv/bin').mkdir(parents=True)
            for name in ('service.sh',):
                shutil.copy(REPO / 'bash/run' / name, root / 'bash/run' / name)
            for name in ('logpipe.py', 'performance_mode.py', 'boot_state.py'):
                shutil.copy(REPO / 'python' / name, root / 'python' / name)
            python = root / 'venv/bin/python'
            python.write_text('#!/bin/bash\ncase "$*" in *logpipe.py*|*boot_state.py*) exec ' + sys.executable + ' "$@" ;; *) echo failed >&2; exit 86 ;; esac\n')
            python.chmod(0o755)
            for mode in ('daemon', 'io'):
                result = subprocess.run(['bash', str(root / 'bash/run/service.sh'), mode],
                                        env=dict(os.environ, HOME=str(root)), capture_output=True, timeout=5)
                self.assertEqual(result.returncode, 86, result.stderr)

    def test_audio_record_only_clears_on_a_later_boot(self):
        import boot_state
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'audio-config.json'
            with mock.patch.object(boot_state, 'boot_time', return_value=100):
                path.write_text('active')
                os.utime(path, (200, 200))
                boot_state.clear_previous_boot(path)
                self.assertTrue(path.exists())
                os.utime(path, (1, 1))
                boot_state.clear_previous_boot(path)
                self.assertFalse(path.exists())

    def test_heartbeat_only_counts_an_active_owned_engine_and_jack(self):
        import engine_service
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            group, proc = root / 'group', root / 'proc'
            group.mkdir()
            for pid, name in ((10, 'jackd'), (11, 'pd'), (12, 'pd')):
                (proc / str(pid)).mkdir(parents=True)
                (proc / str(pid) / 'comm').write_text(name)
            active = root / 'active'
            with (mock.patch.object(engine_service, 'CGROUP_DIR', str(group)),
                  mock.patch.object(engine_service, 'ACTIVE_FILE', str(active))):
                (group / 'cgroup.procs').write_text('10\n')
                active.touch()
                self.assertEqual(engine_service.alive('pd', str(proc)), 0)
                (group / 'cgroup.procs').write_text('10\n11\n')
                self.assertEqual(engine_service.alive('pd', str(proc)), 1)
                (group / 'cgroup.procs').write_text('11\n')
                self.assertEqual(engine_service.alive('pd', str(proc)), 0)
                active.unlink()
                (group / 'cgroup.procs').write_text('10\n11\n')
                self.assertEqual(engine_service.alive('pd', str(proc)), 0)


if __name__ == '__main__':
    unittest.main()
