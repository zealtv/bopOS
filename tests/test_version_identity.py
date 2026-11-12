"""The release version resolver: tagged, ahead of the tag, no VERSION, no git."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import fixture_git

sys.dont_write_bytecode = True
REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'python'))

import version_identity  # noqa: E402


class VersionIdentityTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='bopos-version-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve() / 'checkout'
        self.root.mkdir()

    def git(self, *args):
        return subprocess.run(
            ['git', '-C', str(self.root), '-c', 'user.name=Fixture',
             '-c', 'user.email=fixture@example.invalid', *args],
            cwd=self.root, env=fixture_git.environment(), check=True,
            capture_output=True, text=True).stdout.strip()

    def start_repo(self, version='1.0.0\n'):
        self.git('init', '-b', 'main')
        if version is not None:
            (self.root / 'VERSION').write_text(version)
        self.commit('Release')

    def commit(self, message):
        (self.root / 'file').write_text(message)
        self.git('add', '.')
        self.git('commit', '-m', message)

    def short(self):
        return self.git('rev-parse', '--short=7', 'HEAD')

    def test_tagged_checkout_is_the_plain_release(self):
        self.start_repo()
        self.git('tag', '-a', 'v1.0.0', '-m', 'v1.0.0')  # annotated, as releases are
        info = version_identity.resolve(self.root)
        self.assertEqual(info['version'], '1.0.0')
        self.assertEqual(info['state'], 'release')
        self.assertEqual(info['release'], '1.0.0')
        self.assertEqual(info['git_hash'], self.short())
        self.assertEqual(version_identity.display_version(self.root), '1.0.0')

    def test_dev_checkout_ahead_of_the_tag_counts_commits_and_names_the_hash(self):
        self.start_repo()
        self.git('tag', 'v1.0.0')
        for n in range(3):
            self.commit(f'work {n}')
        info = version_identity.resolve(self.root)
        self.assertEqual(info['version'], f'1.0.0+dev.3.g{self.short()}')
        self.assertEqual(info['state'], 'dev')
        self.assertEqual(info['ahead'], 3)
        self.assertEqual(info['git_hash'], self.short())

    def test_dev_checkout_with_no_release_tag_still_names_the_hash(self):
        self.start_repo()
        info = version_identity.resolve(self.root)
        self.assertEqual(info['version'], f'1.0.0+dev.g{self.short()}')
        self.assertEqual(info['state'], 'dev')
        self.assertIsNone(info['ahead'])

    def test_version_bumped_before_its_tag_counts_from_the_last_release(self):
        self.start_repo()
        self.git('tag', 'v1.0.0')
        (self.root / 'VERSION').write_text('1.1.0\n')
        self.commit('Release v1.1.0 prepared')
        info = version_identity.resolve(self.root)
        self.assertEqual(info['version'], f'1.1.0+dev.1.g{self.short()}')

    def test_checkout_without_version_file_is_unknown_but_keeps_the_hash(self):
        self.start_repo(version=None)
        info = version_identity.resolve(self.root)
        self.assertEqual(info['version'], 'unknown')
        self.assertEqual(info['state'], 'unknown')
        self.assertIsNone(info['release'])
        self.assertEqual(info['git_hash'], self.short())

    def test_malformed_version_file_is_unknown(self):
        for text in ('', 'one\n', '1.0\n', '1.0.0\n2.0.0\n', 'v1.0.0\n'):
            with self.subTest(text=text):
                (self.root / 'VERSION').write_text(text)
                self.assertEqual(version_identity.resolve(self.root)['version'], 'unknown')

    def test_export_without_git_reports_the_version_file(self):
        (self.root / 'VERSION').write_text('1.0.0\n')
        info = version_identity.resolve(self.root)
        self.assertEqual(info['version'], '1.0.0')
        self.assertEqual(info['state'], 'export')
        self.assertIsNone(info['git_hash'])

    def test_no_git_and_no_version_is_unknown(self):
        info = version_identity.resolve(self.root)
        self.assertEqual((info['version'], info['state'], info['git_hash']),
                         ('unknown', 'unknown', None))

    def test_export_inside_another_repository_does_not_borrow_its_hash(self):
        self.start_repo()
        export = self.root / 'exported'
        export.mkdir()
        (export / 'VERSION').write_text('1.0.0\n')
        info = version_identity.resolve(export)
        self.assertEqual((info['version'], info['state'], info['git_hash']),
                         ('1.0.0', 'export', None))

    def test_missing_git_program_degrades_to_the_export_answer(self):
        (self.root / 'VERSION').write_text('1.0.0\n')
        saved = os.environ['PATH']
        os.environ['PATH'] = str(self.root)
        self.addCleanup(os.environ.__setitem__, 'PATH', saved)
        self.assertEqual(version_identity.resolve(self.root)['version'], '1.0.0')

    def test_hook_environment_cannot_redirect_the_resolver(self):
        self.start_repo()
        self.git('tag', 'v1.0.0')
        decoy = self.root.parent / 'decoy'
        decoy.mkdir()
        saved = dict(os.environ)
        os.environ.update(GIT_DIR=str(decoy / '.git'), GIT_INDEX_FILE=str(decoy / 'index'))
        self.addCleanup(lambda: (os.environ.clear(), os.environ.update(saved)))
        self.assertEqual(version_identity.resolve(self.root)['version'], '1.0.0')

    def test_git_short_hash_keeps_the_heartbeat_shorthand_separate(self):
        self.start_repo()
        self.git('tag', 'v1.0.0')
        self.assertEqual(version_identity.git_short_hash(self.root),
                         self.git('rev-parse', '--short', 'HEAD'))
        self.assertIsNone(version_identity.git_short_hash(self.root.parent))

    def test_run_context_version_stays_the_git_shorthand(self):
        import runcontext
        self.start_repo()
        self.git('tag', 'v1.0.0')
        self.assertEqual(runcontext.resolve_version(self.root), self.short())
        self.assertEqual(runcontext.resolve_version(self.root.parent), 'unknown')

    def test_command_line_prints_the_version_and_json(self):
        script = str(REPO / 'python/version_identity.py')
        env = fixture_git.environment()
        plain = subprocess.run([sys.executable, script], capture_output=True, text=True,
                               env=env, check=True).stdout.strip()
        self.assertEqual(plain, version_identity.display_version(REPO))
        full = json.loads(subprocess.run([sys.executable, script, '--json'],
                                         capture_output=True, text=True, env=env,
                                         check=True).stdout)
        self.assertEqual(full['version'], plain)

    def test_the_repository_carries_a_valid_version_file(self):
        self.assertRegex(version_identity.read_release(REPO) or '', r'^\d+\.\d+\.\d+$')


if __name__ == '__main__':
    unittest.main()
