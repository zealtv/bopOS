"""Execute real provisioning with root paths and privileged tools substituted."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]


class NodeProvisionTests(unittest.TestCase):
    def test_fresh_install_and_reprovision_publish_level_last(self):
        with tempfile.TemporaryDirectory(prefix='bopos-provision-') as temporary:
            root = Path(temporary)
            for directory in ('bash', 'systemd', 'python', 'bin', 'etc/systemd/system'):
                (root / directory).mkdir(parents=True)
            source = (REPO / 'bash/provision.sh').read_text()
            # Substitute root guard and absolute installation paths only.
            source = source.replace('if [ "${EUID:-$(id -u)}" -ne 0 ]; then', 'if false; then')
            source = source.replace('/etc/', str(root / 'etc') + '/').replace('/usr/local/', str(root / 'local') + '/')
            script = root / 'bash/provision.sh'
            script.write_text(source)
            shutil.copy(REPO / 'bash/bopos', root / 'bash/bopos')
            shutil.copy(REPO / 'bash/rc.local', root / 'bash/rc.local')
            shutil.copy(REPO / 'bopos.config.example', root / 'bopos.config.example')
            for path in (REPO / 'systemd').iterdir():
                if path.is_file():
                    shutil.copy(path, root / 'systemd' / path.name)
            (root / 'python/wifi_config.py').write_text('fixture validator')
            for name in ('install-power-control.sh', 'install-usb-automount.sh', 'install-wifi-powersave.sh'):
                path = root / 'bash' / name
                path.write_text('#!/bin/bash\nexit 0\n')
                path.chmod(0o755)
            for name, body in {
                'chown': 'exit 0\n', 'usermod': 'exit 0\n',
                'systemctl': '''echo "$*" >> "$FIXTURE_ROOT/calls"
if [ "$1" = disable ] && [ ! -f "$FIXTURE_ROOT/etc/systemd/system/$2" ]; then exit 1; fi
''',
                'install': '''exec "$FIXTURE_PYTHON" "$FIXTURE_ROOT/install.py" "$@"\n''',
            }.items():
                path = root / 'bin' / name
                path.write_text('#!/bin/bash\n' + body)
                path.chmod(0o755)
            (root / 'install.py').write_text('''import os, pathlib, shutil, sys
args = sys.argv[1:]
for option in ('-o', '-g', '-m'):
    if option in args:
        index = args.index(option)
        del args[index:index+2]
if '-d' in args:
    args.remove('-d')
    for path in args: pathlib.Path(path).mkdir(parents=True, exist_ok=True)
else:
    target = pathlib.Path(args[-1])
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(args[0], target)
    if target.name == 'provision-level':
        with open(os.environ['FIXTURE_ROOT'] + '/calls', 'a') as output: output.write('marker published\\n')
''')
            env = dict(os.environ, PATH=str(root / 'bin') + os.pathsep + os.environ['PATH'],
                       FIXTURE_ROOT=str(root), FIXTURE_PYTHON=sys.executable)
            for adoption in ('fresh', 'existing'):
                (root / 'calls').write_text('')
                result = subprocess.run(['bash', str(script)], cwd=root, env=env, capture_output=True, text=True, timeout=10)
                self.assertEqual(result.returncode, 0, result.stderr)
                calls = (root / 'calls').read_text().splitlines()
                self.assertEqual('disable bopos.service' in calls, adoption == 'existing')
                self.assertEqual(calls[-1], 'marker published')
                self.assertIn('enable bopos.target', calls)
                self.assertEqual((root / 'etc/bopos/provision-level').read_text(), '1\n')
                self.assertTrue((root / 'local/bin/bopos').exists())
                self.assertTrue((root / 'bopos.config').exists())


if __name__ == '__main__':
    unittest.main()
