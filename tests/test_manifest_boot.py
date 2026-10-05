"""Real shell/validator harness; services are inert processes, not Pi hardware."""
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest

sys.dont_write_bytecode = True
REPO = Path(__file__).resolve().parents[1]


class ManifestBootTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='bopos-manifest-boot-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        for directory in ('bash', 'python/io', 'patches/live', 'bin', 'run'):
            (self.root / directory).mkdir(parents=True)
        for relative in ('bash/start.sh', 'bash/start-engine.sh',
                         'python/manifest.py', 'python/io_protocol.py',
                         'python/io_catalog.py', 'python/paramgen.py', 'python/logpipe.py',
                         'python/performance_mode.py'):
            shutil.copy2(REPO / relative, self.root / relative)
        # Both long-lived service slots remain actual OS processes, but perform
        # no audio, networking or I2C. Cleanup only ever kills these fixture PIDs.
        for relative in ('python/bopos.py', 'python/io/main.py'):
            (self.root / relative).write_text('import time\nwhile True: time.sleep(1)\n')
        self.write_script('bash/stop.sh', '''#!/bin/bash
printf 'stopped\n' >> "$(dirname "$0")/../run/full-stop"
for file in "$(dirname "$0")/../run/"*.pid; do
  [ -f "$file" ] || continue
  kill "$(cat "$file")" 2>/dev/null || true
  rm -f "$file"
done
''')
        self.write_script('bin/ip', '#!/bin/bash\necho "1.1.1.1 dev harness"\n')
        self.patch = self.root / 'patches/live'
        (self.root / 'patches/active_patch.txt').write_text('live\n')
        (self.patch / 'entry.txt').write_text('fixture entrypoint\n')
        self.candidate = {'engine': 'fixture-engine', 'entrypoint': 'entry.txt',
                          'params': [{'name': 'gain', 'type': 'f'}], 'events': []}
        self.write_manifest(self.candidate)
        self.env = dict(os.environ, BOPOS_ENGINE_SURVIVAL_WAIT='0.2', PATH=str(self.root / 'bin') + os.pathsep + os.environ['PATH'])
        self.addCleanup(self.stop_services)

    def write_script(self, relative, content):
        path = self.root / relative
        path.write_text(content)
        path.chmod(0o755)

    def write_manifest(self, candidate):
        (self.patch / 'bopos.patch.json').write_text(json.dumps(candidate))

    def stop_services(self):
        for path in (self.root / 'run').glob('*.pid'):
            try:
                os.kill(int(path.read_text()), signal.SIGTERM)
            except (OSError, ValueError):
                pass

    def run_boot(self):
        log = self.root / 'boot.log'
        with log.open('w') as output:
            result = subprocess.run(['bash', str(self.root / 'bash/start.sh')],
                                    env=self.env, stdout=output, stderr=subprocess.STDOUT,
                                    timeout=10)
        return result, log.read_text()

    def assert_services_alive(self):
        for name in ('bopos', 'io'):
            pid = int((self.root / f'run/{name}.pid').read_text())
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                logs = [path.read_text() for path in (self.root / 'run').glob('*.log')]
                self.fail(f"{name} process {pid} died: {logs}; boot: {(self.root / 'boot.log').read_text()}")
        for name in ('engine', 'pd', 'jackd'):
            self.assertFalse((self.root / f'run/{name}.pid').exists())
        self.assertFalse((self.root / 'run/full-stop').exists())

    def test_retired_type_manifest_keeps_both_services_alive(self):
        result, output = self.run_boot()
        self.assertEqual(result.returncode, 0, output)
        self.assertIn('type was removed', output)
        self.assertIn('PATCH REQUIRES A VALID bopos.patch.json', output)
        self.assert_services_alive()
        # An engine-only launch is still an error, so fetch/switch callers do
        # not claim that an invalid patch was successfully started.
        strict = subprocess.run(['bash', str(self.root / 'bash/start-engine.sh')],
                                capture_output=True, text=True, env=self.env, timeout=5)
        self.assertEqual(strict.returncode, 1)
        self.assert_services_alive()

    def test_missing_and_malformed_manifests_also_stay_online(self):
        for content in (None, '{broken'):
            with self.subTest(content=content):
                path = self.patch / 'bopos.patch.json'
                if content is None:
                    path.unlink()
                else:
                    path.write_text(content)
                result, output = self.run_boot()
                self.assertEqual(result.returncode, 0, output)
                self.assertIn('PATCH REQUIRES A VALID bopos.patch.json', output)
                self.assert_services_alive()
                self.stop_services()

    def test_post_validation_failure_still_stops_partial_stack(self):
        # Keep the real validator and startup prefix; replace only hardware
        # launch with a failed partially-started engine (arbitrary exit 65).
        path = self.root / 'bash/start-engine.sh'
        source = path.read_text()
        prefix = source[:source.index('# Assets are exposed')]
        path.write_text(prefix + '''
sleep 30 &
echo $! > "$RUN_DIR/engine.pid"
exit 65
''')
        self.write_manifest({'engine': 'fixture-engine', 'entrypoint': 'entry.txt',
                             'params': [], 'events': []})
        result, output = self.run_boot()
        self.assertEqual(result.returncode, 65, output)
        self.assertIn('stopping the partial stack', output)
        self.assertTrue((self.root / 'run/full-stop').exists())
        self.assertFalse(list((self.root / 'run').glob('*.pid')))


class EngineLaunchTests(unittest.TestCase):
    write_script = ManifestBootTests.write_script

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='bopos-engine-launch-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        for directory in ('bash', 'bin', 'patches/live', 'run'):
            (self.root / directory).mkdir(parents=True)
        (self.root / 'patches/active_patch.txt').write_text('live\n')
        (self.root / 'cards').write_text('DigiAMP\n')
        # Only the ALSA hardware predicate is substituted in the real launcher.
        source = (REPO / 'bash/start-engine.sh').read_text()
        self.write_script('bash/start-engine.sh', source.replace(
            '/proc/asound/cards', str(self.root / 'cards')))
        self.write_script('bin/python3', '''#!/bin/bash
case "$1" in
  */manifest.py) printf "ENGINE='%s'\\nENTRYPOINT='entry.txt'\\n" "$FIXTURE_ENGINE" ;;
  */runcontext.py)
    [ "$CASE" != context ] || exit 42
    printf "BOPOS_SEED='123'\\nBOPOS_RUN_ID='fixture'\\n" ;;
  */audio_config.py)
    [ "$CASE" != audio ] || exit 43 ;;
esac
''')
        self.write_script('bin/jackd', '''#!/bin/bash
echo $$ >> "$FIXTURE_ROOT/launched"
[ "$CASE" != jack-death ] || exit 88
exec /bin/sleep 60
''')
        self.write_script('bin/jack_lsp', '''#!/bin/bash
[ "$CASE" != jack-timeout ] && [ "$CASE" != jack-death ]
''')
        engine = '''#!/bin/bash
echo $$ >> "$FIXTURE_ROOT/launched"
[ "$CASE" != engine ] || exit 87
[ "$CASE" != clean-exit ] || exit 0
exec /bin/sleep 60
'''
        for name in ('pd', 'fixture-engine'):
            self.write_script('bin/' + name, engine)
        self.env = dict(os.environ,
                        PATH=str(self.root / 'bin') + os.pathsep + os.environ['PATH'],
                        FIXTURE_ROOT=str(self.root), BOPOS_STOP_TIMEOUT='1',
                        BOPOS_JACK_START_TIMEOUT='0')
        self.addCleanup(self.stop_launched)
        self.unrelated = subprocess.Popen(['/bin/sleep', '60'])
        self.addCleanup(self.stop_unrelated)
        (self.root / 'run/bopos.pid').write_text(str(self.unrelated.pid))

    def stop_unrelated(self):
        self.unrelated.terminate()
        self.unrelated.wait(timeout=5)

    def launched_pids(self):
        path = self.root / 'launched'
        return [int(value) for value in path.read_text().split()] if path.exists() else []

    def stop_launched(self):
        for pid in self.launched_pids():
            try:
                os.kill(pid, signal.SIGTERM)
            except ProcessLookupError:
                pass

    def invoke(self, mode, engine='pd'):
        log = self.root / 'output.log'
        env = dict(self.env, CASE=mode, FIXTURE_ENGINE=engine)
        if mode == 'jack-death':
            env['BOPOS_JACK_START_TIMEOUT'] = '1'
        with log.open('w') as output:
            result = subprocess.run(
                ['bash', str(self.root / 'bash/start-engine.sh'), '--skip-invalid-manifest'],
                env=env, stdout=output, stderr=subprocess.STDOUT, timeout=10)
        # Let fixture children publish their PIDs even when the old launcher
        # returns immediately; cleanup must also work on the failing baseline.
        time.sleep(0.1)
        return result.returncode, log.read_text()

    def assert_failed_cleanup(self):
        for name in ('jackd.pid', 'engine.pid', 'pd.pid', 'engine.name'):
            self.assertFalse((self.root / 'run' / name).exists(), name)
        for pid in self.launched_pids():
            for _ in range(50):
                try:
                    os.kill(pid, 0)
                except ProcessLookupError:
                    break
                time.sleep(0.02)
            else:
                self.fail(f'fixture process {pid} survived failed launch')
        self.assertIsNone(self.unrelated.poll())
        self.assertEqual((self.root / 'run/bopos.pid').read_text(),
                         str(self.unrelated.pid))

    def test_run_context_failure_stops_before_audio(self):
        status, output = self.invoke('context')
        self.assertEqual(status, 42, output)
        self.assertEqual(self.launched_pids(), [])
        self.assert_failed_cleanup()

    def test_record_active_failure_stops_jack_before_engine(self):
        status, output = self.invoke('audio')
        self.assertEqual(status, 43, output)
        self.assertEqual(len(self.launched_pids()), 1)
        self.assert_failed_cleanup()

    def test_immediate_engine_exit_cleans_both_engine_branches(self):
        for engine in ('pd', 'fixture-engine'):
            with self.subTest(engine=engine):
                status, output = self.invoke('engine', engine)
                self.assertEqual(status, 87, output)
                self.assert_failed_cleanup()

    def test_success_keeps_processes_and_pid_records(self):
        for engine in ('pd', 'fixture-engine'):
            with self.subTest(engine=engine):
                status, output = self.invoke('success', engine)
                self.assertEqual(status, 0, output)
                for name in ('engine', 'jackd'):
                    pid = int((self.root / f'run/{name}.pid').read_text())
                    os.kill(pid, 0)
                    self.assertIn(pid, self.launched_pids())
                self.assertEqual((self.root / 'run/engine.name').read_text().strip(), engine)
                self.assertEqual((self.root / 'run/pd.pid').exists(), engine == 'pd')
                self.stop_launched()
                for path in (self.root / 'run').glob('*'):
                    if path.name != 'bopos.pid':
                        path.unlink()

    def test_failure_preserves_preexisting_engine_records_and_process(self):
        for name in ('engine.pid', 'pd.pid', 'engine.name'):
            (self.root / 'run' / name).write_text(str(self.unrelated.pid))
        for mode in ('context', 'audio'):
            with self.subTest(mode=mode):
                status, output = self.invoke(mode)
                self.assertNotEqual(status, 0, output)
                self.assertIsNone(self.unrelated.poll())
                for name in ('engine.pid', 'pd.pid', 'engine.name'):
                    self.assertEqual((self.root / 'run' / name).read_text(),
                                     str(self.unrelated.pid))
                self.assertFalse((self.root / 'run/jackd.pid').exists())

    def test_immediate_clean_exit_is_also_launch_failure(self):
        status, output = self.invoke('clean-exit')
        self.assertEqual(status, 1, output)
        self.assert_failed_cleanup()

    def test_patch_start_failure_cleans_published_records(self):
        self.write_script('patches/live/start.sh', '#!/bin/bash\nexit 64\n')
        status, output = self.invoke('success')
        self.assertEqual(status, 64, output)
        self.assert_failed_cleanup()

    def test_jack_failures_clean_only_this_launch(self):
        for mode in ('jack-death', 'jack-timeout'):
            with self.subTest(mode=mode):
                status, output = self.invoke(mode)
                self.assertEqual(status, 1, output)
                self.assert_failed_cleanup()


if __name__ == '__main__':
    unittest.main()
