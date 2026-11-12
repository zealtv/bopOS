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
        for directory in ('bash/run', 'python/io', 'patches/live', 'run', 'runtime'):
            (self.root / directory).mkdir(parents=True)
        for relative in ('bash/run/service.sh', 'bash/run/engine.sh',
                         'python/manifest.py', 'python/io_protocol.py',
                         'python/io_catalog.py', 'python/paramgen.py', 'python/logpipe.py',
                         'python/performance_mode.py', 'python/boot_state.py'):
            shutil.copy2(REPO / relative, self.root / relative)
        # Actual foreground OS processes under the two real wrappers. The
        # fixture answers on stdin/stdout, without networking/audio/I2C hardware.
        for relative in ('python/bopos.py', 'python/io/main.py'):
            (self.root / relative).write_text('import sys\nfor line in sys.stdin: print("answered", flush=True)\n')
        self.patch = self.root / 'patches/live'
        (self.root / 'patches/active_patch.txt').write_text('live\n')
        (self.patch / 'entry.txt').write_text('fixture entrypoint\n')
        self.candidate = {'engine': 'fixture-engine', 'entrypoint': 'entry.txt',
                          'params': [{'name': 'gain', 'type': 'f'}], 'events': []}
        self.write_manifest(self.candidate)
        self.env = dict(os.environ, RUNTIME_DIRECTORY=str(self.root / 'runtime'))
        self.services = []
        self.addCleanup(self.stop_services)

    def write_script(self, relative, content):
        path = self.root / relative
        path.write_text(content)
        path.chmod(0o755)

    def write_manifest(self, candidate):
        (self.patch / 'bopos.patch.json').write_text(json.dumps(candidate))

    def stop_services(self):
        for process, output in self.services:
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            process.wait(timeout=5)
            process.stdin.close()
            output.close()
        self.services.clear()

    def run_engine(self):
        return subprocess.run(['bash', str(self.root / 'bash/run/engine.sh')],
                              env=self.env, capture_output=True, text=True, timeout=5)

    def run_boot(self):
        for mode in ('daemon', 'io'):
            output = (self.root / (mode + '.out')).open('w')
            process = subprocess.Popen(['bash', str(self.root / 'bash/run/service.sh'), mode],
                                       stdin=subprocess.PIPE, stdout=output, stderr=output,
                                       env=self.env, text=True, start_new_session=True)
            self.services.append((process, output))
        return self.run_engine()

    def assert_services_answer(self):
        for (process, _output), log in zip(self.services, ('bopos', 'io')):
            self.assertIsNone(process.poll())
            process.stdin.write('request\n')
            process.stdin.flush()
            path = self.root / ('run/' + log + '.log')
            for _ in range(100):
                if path.exists() and 'answered' in path.read_text():
                    break
                time.sleep(0.02)
            else:
                self.fail(log + ' did not answer')
        self.assertFalse((self.root / 'runtime/engine.pid').exists())

    def test_retired_type_manifest_keeps_both_services_alive_and_answering(self):
        result = self.run_boot()
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn('type was removed', result.stderr)
        self.assertIn('PATCH REQUIRES A VALID bopos.patch.json', result.stderr)
        self.assert_services_answer()
        self.assertEqual(self.run_engine().returncode, 1)
        self.assert_services_answer()

    def test_missing_and_malformed_manifests_also_stay_online(self):
        for content in (None, '{broken'):
            with self.subTest(content=content):
                path = self.patch / 'bopos.patch.json'
                if content is None:
                    path.unlink()
                else:
                    path.write_text(content)
                result = self.run_boot()
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertIn('PATCH REQUIRES A VALID bopos.patch.json', result.stderr)
                self.assert_services_answer()
                self.stop_services()

    def test_post_validation_failure_is_also_isolated_from_connectivity(self):
        path = self.root / 'bash/run/engine.sh'
        source = path.read_text()
        path.write_text(source[:source.index('# Assets are exposed')] + '\nexit 65\n')
        self.write_manifest(dict(self.candidate, params=[]))
        result = self.run_boot()
        self.assertEqual(result.returncode, 65, result.stderr)
        self.assert_services_answer()


class EngineLaunchTests(unittest.TestCase):
    write_script = ManifestBootTests.write_script

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='bopos-engine-launch-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        for directory in ('bash/run', 'bin', 'patches/live', 'run', 'runtime'):
            (self.root / directory).mkdir(parents=True)
        (self.root / 'patches/active_patch.txt').write_text('live\n')
        (self.root / 'cards').write_text('DigiAMP\n')
        # Only the ALSA hardware predicate is substituted in the real launcher.
        source = (REPO / 'bash/run/engine.sh').read_text()
        self.write_script('bash/run/engine.sh', source.replace(
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
        # Like the real probe, report ready only once the server has started:
        # here, once the fake jackd has recorded its pid. Answering sooner let
        # the launcher's cleanup kill jackd before it wrote to `launched`.
        # BOPOS_JACK_START_TIMEOUT=0 allows one probe, so the wait lives here.
        self.write_script('bin/jack_lsp', '''#!/bin/bash
[ "$CASE" != jack-timeout ] && [ "$CASE" != jack-death ] || exit 1
for _ in $(seq 250); do
  [ -s "$FIXTURE_ROOT/launched" ] && exit 0
  sleep 0.02
done
exit 1
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
                        FIXTURE_ROOT=str(self.root), RUNTIME_DIRECTORY=str(self.root / 'runtime'),
                        BOPOS_JACK_START_TIMEOUT='0')
        self.groups = []
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
        for process in self.groups:
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            process.wait(timeout=5)
        self.groups.clear()

    def invoke(self, mode, engine='pd'):
        log = self.root / 'output.log'
        env = dict(self.env, CASE=mode, FIXTURE_ENGINE=engine)
        if mode == 'jack-death':
            env['BOPOS_JACK_START_TIMEOUT'] = '1'
        with log.open('w') as output:
            result = subprocess.Popen(
                ['bash', str(self.root / 'bash/run/engine.sh')],
                env=env, stdout=output, stderr=subprocess.STDOUT, start_new_session=True)
            self.groups.append(result)
            result.wait(timeout=10)
        # The fixture supervisor models unit isolation; real systemd cgroup
        # cleanup and main-process death are separately checked on the Pi.
        if result.returncode != 0:
            self.stop_launched()
        # Let fixture children publish their PIDs even when the old launcher
        # returns immediately; cleanup must also work on the failing baseline.
        time.sleep(0.1)
        return result.returncode, log.read_text()

    def assert_failed_cleanup(self):
        self.assertFalse((self.root / 'runtime/engine.pid').exists())
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

    def test_success_publishes_only_systemd_main_pid(self):
        for engine in ('pd', 'fixture-engine'):
            with self.subTest(engine=engine):
                status, output = self.invoke('success', engine)
                self.assertEqual(status, 0, output)
                pid = int((self.root / 'runtime/engine.pid').read_text())
                os.kill(pid, 0)
                self.assertIn(pid, self.launched_pids())
                self.assertFalse((self.root / 'run/engine.pid').exists())
                self.assertFalse((self.root / 'run/jackd.pid').exists())
                self.assertFalse((self.root / 'run/pd.pid').exists())
                self.assertFalse((self.root / 'run/engine.name').exists())
                (self.root / 'runtime/engine.pid').unlink()
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
