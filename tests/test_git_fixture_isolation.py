"""Real fixture runs must leave a hook-selected decoy repository untouched."""
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import fixture_git

REPO = Path(__file__).resolve().parents[1]


def snapshot(root):
    return {str(path.relative_to(root)): (path.stat().st_mode,
            hashlib.sha256(path.read_bytes()).hexdigest())
            for path in root.rglob('*') if path.is_file()}


class GitFixtureIsolationTests(unittest.TestCase):
    def test_real_fixtures_ignore_all_hook_git_environment(self):
        with tempfile.TemporaryDirectory(prefix='bopos-git-decoy-') as temporary:
            root = Path(temporary)
            clean = fixture_git.environment()
            def git(*args):
                subprocess.run(['git', '-C', str(root), *args], cwd=root, env=clean,
                               capture_output=True, check=True)
            git('init', '-b', 'main')
            (root / 'sentinel').write_text('untouched decoy\n')
            git('add', 'sentinel')
            git('-c', 'user.name=Decoy', '-c', 'user.email=decoy@example.invalid',
                'commit', '-m', 'Decoy sentinel')
            before = snapshot(root)
            poisoned = dict(os.environ, GIT_DIR=str(root / '.git'),
                            GIT_INDEX_FILE=str(root / '.git/index'),
                            GIT_WORK_TREE=str(root), GIT_CONFIG_COUNT='1',
                            GIT_CONFIG_KEY_0='user.name', GIT_CONFIG_VALUE_0='Poison')
            result = subprocess.run([
                sys.executable, '-m', 'unittest',
                'test_bopos_command', 'test_framework_provision',
                'test_commit_gate', 'test_documented_paths',
                'test_project_storage'], cwd=REPO / 'tests', env=poisoned,
                capture_output=True, text=True, timeout=90)
            self.assertEqual(snapshot(root), before, 'fixture changed the decoy repository')
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
