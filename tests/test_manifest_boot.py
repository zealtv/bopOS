"""Real shell/validator harness; services are inert processes, not Pi hardware."""
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
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
                         'python/manifest.py', 'python/logpipe.py'):
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
        self.env = dict(os.environ, PATH=str(self.root / 'bin') + os.pathsep + os.environ['PATH'])
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


if __name__ == '__main__':
    unittest.main()
