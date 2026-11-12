"""tools/release.sh against Git fixtures: a development repository with
private entries and a submodule pointer, and a "public" bare repository with
history of its own. Nothing here reaches a real remote: every command gets an
explicit local target, the fixture repositories have no remotes, and gh is a
stub on PATH.
"""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import fixture_git
from test_public_tree import MANIFEST, read_manifest

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "release.sh"
GITLINK = "0123456789abcdef0123456789abcdef01234567"
TAG = "v1.2.0"
DATED_CHANGELOG = """# Changelog

## v1.2.0 (2026-11-20): contract 1.3 · provision level 1 · schema 1

- A fixture release.

## v1.1.0 (2026-01-01): contract 1.2 · provision level 1 · schema 1

- An older one.
"""
UNRELEASED_CHANGELOG = DATED_CHANGELOG.replace("(2026-11-20)", "(unreleased)")
NEXT_TAG = "v1.2.1"
NEXT_CHANGELOG = DATED_CHANGELOG.replace("# Changelog\n\n", """# Changelog

## v1.2.1 (2026-11-21): contract 1.3 · provision level 1 · schema 1

- A fixture fix.

""")
# Stands in for git: moves the target's main just before a push, as if
# someone pushed between publish's checks and its own push.
RACE_GIT = """#!/bin/sh
if [ "$1" = push ] && [ -n "${RACE_TO:-}" ]; then
    "$REAL_GIT" --git-dir="$RACE_PUBLIC" update-ref refs/heads/main "$RACE_TO"
fi
exec "$REAL_GIT" "$@"
"""
GH_STUB = """#!/bin/sh
printf '%s\\n' "$*" >> "$GH_LOG"
case "$1 $2" in
    "release view") [ -f "$GH_STATE" ] ;;
    "release create" | "release edit")
        prev=
        for arg in "$@"; do
            [ "$prev" = --notes-file ] && cat "$arg" > "$GH_NOTES"
            prev=$arg
        done
        if [ "$2" = create ]; then
            git --git-dir="$GH_PUBLIC" rev-parse -q --verify "refs/tags/$3" >/dev/null || exit 1
            touch "$GH_STATE"
        fi ;;
    *) exit 1 ;;
esac
"""


def git_env():
    env = fixture_git.environment()
    for key in list(env):
        if key.startswith("BOPOS_RELEASE_"):
            del env[key]
    env.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1",
               GIT_AUTHOR_NAME="Release Fixture",
               GIT_AUTHOR_EMAIL="fixture@example.invalid",
               GIT_COMMITTER_NAME="Release Fixture",
               GIT_COMMITTER_EMAIL="fixture@example.invalid")
    return env


def git(cwd, *args, env=None):
    return subprocess.run(["git", *args], cwd=cwd, env=env or git_env(), check=True,
                          capture_output=True, text=True).stdout.strip()


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


class ReleaseToolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.template_dir = tempfile.TemporaryDirectory(prefix="bopos-release-fixture-")
        template = Path(cls.template_dir.name)
        kinds = read_manifest()
        cls.private = sorted(name for name, kind in kinds.items() if kind == "private")

        dev = template / "dev"
        dev.mkdir()
        git(dev, "init", "-q", "-b", "main")
        for relative in ("tools/release.sh", "tools/release-manifest"):
            target = dev / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / relative, target)
        write(dev / "VERSION", "1.1.0\n")
        write(dev / "CHANGELOG.md", UNRELEASED_CHANGELOG)
        write(dev / "README.md", "fixture\n")
        write(dev / "docs/guide.md", "guide\n")
        write(dev / "pd/adapter.txt", "adapter\n")
        write(dev / ".gitmodules",
              '[submodule "pd/bop"]\n\tpath = pd/bop\n\turl = https://example.invalid/bop\n')
        for name in cls.private:
            if name.startswith("."):
                write(dev / name / "notes.txt", "private\n")
            else:
                write(dev / name, "private\n")
        git(dev, "add", ".")
        # A submodule pointer with an empty directory, as in a clone that
        # hasn't run submodule update.
        git(dev, "update-index", "--add", "--cacheinfo", "160000," + GITLINK + ",pd/bop")
        (dev / "pd/bop").mkdir()
        git(dev, "commit", "-q", "-m", "Start")

        seed = template / "seed"
        seed.mkdir()
        git(seed, "init", "-q", "-b", "main")
        write(seed / "README.md", "old public tree\n")
        write(seed / cls.private[0] / "notes.txt", "already public\n")
        git(seed, "add", ".")
        git(seed, "commit", "-q", "-m", "Old public one")
        write(seed / "README.md", "old public tree, again\n")
        git(seed, "commit", "-q", "-am", "Old public two")
        git(template, "clone", "-q", "--bare", str(seed), "public.git")

        bin_dir = template / "bin"
        bin_dir.mkdir()
        write(bin_dir / "gh", GH_STUB)
        (bin_dir / "gh").chmod(0o755)
        cls.template = template

    @classmethod
    def tearDownClass(cls):
        cls.template_dir.cleanup()

    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="bopos-release-test-")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name) / "fixture"
        shutil.copytree(self.template, self.root, symlinks=True)
        self.dev = self.root / "dev"
        self.public = self.root / "public.git"
        self.seed = self.root / "seed"
        self.probe = self.root / "probe"
        self.probe.mkdir()
        self.env = git_env()
        self.env.update(
            PATH=str(self.root / "bin") + os.pathsep + self.env.get("PATH", ""),
            BOPOS_RELEASE_PUBLIC=str(self.public),
            BOPOS_RELEASE_GITHUB_REPO="none",
            BOPOS_RELEASE_TESTS=('ls -A > "$RELEASE_PROBE/entries" && '
                                 'git rev-parse --show-toplevel > "$RELEASE_PROBE/toplevel" && '
                                 'cat VERSION > "$RELEASE_PROBE/version"'),
            RELEASE_PROBE=str(self.probe),
            GH_LOG=str(self.root / "gh.log"), GH_STATE=str(self.root / "gh.state"),
            GH_NOTES=str(self.root / "gh.notes"), GH_PUBLIC=str(self.public))

    # helpers

    def release(self, *args, public=None):
        return subprocess.run(
            [str(self.dev / "tools/release.sh"), *args, "--public", str(public or self.public)]
            if args and args[0] in ("export", "publish") else
            [str(self.dev / "tools/release.sh"), *args],
            cwd=self.dev, env=self.env, capture_output=True, text=True)

    def ok(self, *args, public=None):
        result = self.release(*args, public=public)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def refused(self, *args, public=None):
        result = self.release(*args, public=public)
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def empty_target(self, name="empty.git"):
        empty = self.root / name
        git(self.root, "init", "-q", "--bare", str(empty))
        return empty

    def dev_git(self, *args):
        return git(self.dev, *args)

    def public_git(self, *args):
        return git(self.public, *args)

    def bump(self, version="1.2.0\n", changelog=DATED_CHANGELOG):
        write(self.dev / "VERSION", version)
        write(self.dev / "CHANGELOG.md", changelog)

    def prepared(self):
        self.bump()
        self.ok("prepare", TAG)

    def exported(self):
        self.prepared()
        self.ok("export", TAG)
        return (self.dev_git("rev-parse", "refs/bopos-release/%s/commit" % TAG),
                self.dev_git("rev-parse", "refs/bopos-release/%s/tag" % TAG))

    def public_state(self):
        return git(self.public, "for-each-ref", "--format=%(refname) %(objectname)")

    def root_exported(self):
        """Prepare and export TAG with --root: (commit, public tag, replaced main)."""
        self.prepared()
        self.ok("export", TAG, "--root")
        return tuple(self.dev_git("rev-parse", "refs/bopos-release/%s/%s" % (TAG, name))
                     for name in ("commit", "tag", "replaces"))

    def move_public_main(self):
        write(self.seed / "README.md", "someone else\n")
        git(self.seed, "commit", "-q", "-am", "Moved")
        git(self.seed, "push", "-q", str(self.public), "main")
        return git(self.seed, "rev-parse", "HEAD")

    def tag_public(self, name="v0.9.0"):
        git(self.seed, "tag", "-a", name, "-m", "an older release")
        git(self.seed, "push", "-q", str(self.public), name)

    # prepare

    def test_prepare_tests_the_exported_tree_then_commits_and_tags(self):
        start = self.dev_git("rev-parse", "HEAD")
        self.bump()
        result = self.ok("prepare", TAG)
        self.assertIn("REPLACED by BOPOS_RELEASE_TESTS", result.stderr)
        self.assertEqual(self.dev_git("log", "-1", "--format=%s"), "Release " + TAG)
        self.assertEqual(self.dev_git("rev-parse", "HEAD^"), start)
        self.assertEqual(self.dev_git("cat-file", "-t", "refs/tags/" + TAG), "tag")
        self.assertEqual(self.dev_git("rev-parse", TAG + "^{commit}"),
                         self.dev_git("rev-parse", "HEAD"))
        message = self.dev_git("cat-file", "tag", "refs/tags/" + TAG)
        self.assertIn("Release tests REPLACED by BOPOS_RELEASE_TESTS", message)
        self.assertIn("Tested public tree: ", message)
        self.assertEqual(self.dev_git("status", "--porcelain"), "")
        # The tests ran in a Git checkout of the exported tree, not the dev tree.
        entries = (self.probe / "entries").read_text().split()
        self.assertIn(".git", entries)
        self.assertIn("VERSION", entries)
        self.assertEqual([name for name in entries if name in self.private], [])
        self.assertNotEqual(Path((self.probe / "toplevel").read_text().strip()).resolve(),
                            self.dev.resolve())
        self.assertEqual((self.probe / "version").read_text(), "1.2.0\n")
        # Re-running once prepared changes nothing.
        head = self.dev_git("rev-parse", "HEAD")
        self.assertIn("already prepared", self.ok("prepare", TAG).stdout)
        self.assertEqual(self.dev_git("rev-parse", "HEAD"), head)

    def assert_prepare_refused(self, needle):
        head = self.dev_git("rev-parse", "HEAD")
        result = self.refused("prepare", TAG)
        self.assertIn(needle, result.stderr)
        self.assertEqual(self.dev_git("rev-parse", "HEAD"), head)
        self.assertEqual(self.dev_git("tag", "-l"), "")
        self.assertFalse((self.probe / "entries").exists(), "release tests ran")
        return result

    def test_prepare_refuses_a_dirty_tree(self):
        self.bump()
        write(self.dev / "README.md", "edited\n")
        self.assert_prepare_refused("changes besides VERSION and CHANGELOG.md")
        self.dev_git("checkout", "--", "README.md")
        write(self.dev / "docs/new.md", "untracked\n")
        self.assert_prepare_refused("docs/new.md")

    def test_prepare_refuses_off_main(self):
        self.dev_git("checkout", "-q", "-b", "elsewhere")
        self.bump()
        self.assert_prepare_refused("not main")

    def test_prepare_refuses_a_version_or_changelog_mismatch(self):
        cases = {
            "VERSION reads '1.2.1'": ("1.2.1\n", DATED_CHANGELOG),
            "isn't dated": ("1.2.0\n", UNRELEASED_CHANGELOG),
            "no section": ("1.2.0\n", DATED_CHANGELOG.replace("v1.2.0", "v1.1.9")),
            "draft": ("1.2.0\n", DATED_CHANGELOG.replace("- A fixture", "**Draft.**\n\n- A")),
            "more than one": ("1.2.0\n", DATED_CHANGELOG + "\n## v1.2.0 (2026-11-21)\n\n- again\n"),
            "is empty": ("1.2.0\n", "## v1.2.0 (2026-11-20)\n\n## v1.1.0 (2026-01-01)\n\n- x\n"),
        }
        for needle, (version, changelog) in cases.items():
            with self.subTest(needle):
                self.bump(version, changelog)
                self.assert_prepare_refused(needle)
        self.assert_prepare_refused_for_bad_tag()

    def assert_prepare_refused_for_bad_tag(self):
        self.bump()
        result = self.refused("prepare", "1.2.0")
        self.assertIn("expected a version tag", result.stderr)

    def test_prepare_refuses_when_release_tests_fail(self):
        self.bump()
        self.env["BOPOS_RELEASE_TESTS"] = 'touch "$RELEASE_PROBE/ran"; exit 3'
        head = self.dev_git("rev-parse", "HEAD")
        result = self.refused("prepare", TAG)
        self.assertIn("release tests failed", result.stderr)
        self.assertTrue((self.probe / "ran").exists())
        self.assertEqual(self.dev_git("rev-parse", "HEAD"), head)
        self.assertEqual(self.dev_git("tag", "-l"), "")
        self.assertEqual((self.dev / "VERSION").read_text(), "1.2.0\n")
        self.assertEqual(self.dev_git("for-each-ref", "refs/bopos-release"), "")

    def test_unknown_top_level_entry_refuses_prepare_and_export(self):
        write(self.dev / "newdir/file.txt", "unclassified\n")
        self.dev_git("add", "newdir")
        self.dev_git("commit", "-q", "-m", "Add an unclassified directory")
        self.bump()
        result = self.assert_prepare_refused("newdir is on neither list")
        self.assertIn("classify every top-level entry", result.stderr)
        # A tag made by hand meets the same check in export.
        self.dev_git("commit", "-q", "-am", "Release " + TAG)
        self.dev_git("tag", "-a", TAG, "-m", "by hand")
        result = self.refused("export", TAG)
        self.assertIn("newdir is on neither list", result.stderr)
        self.assertEqual(self.dev_git("for-each-ref", "refs/bopos-release"), "")

    # export

    def test_export_builds_one_commit_on_the_public_tip_keeping_the_gitlink(self):
        public_tip = self.public_git("rev-parse", "refs/heads/main")
        before = self.public_state()
        commit, public_tag = self.exported()
        self.assertEqual(self.dev_git("rev-list", "--parents", "-n", "1", commit).split(),
                         [commit, public_tip])
        self.assertEqual(self.dev_git("log", "-1", "--format=%B", commit), "bopOS " + TAG)
        names = self.dev_git("ls-tree", "--name-only", commit).split("\n")
        self.assertEqual([name for name in names if name in self.private], [])
        self.assertEqual(sorted(names), sorted(
            [".gitmodules", "CHANGELOG.md", "README.md", "VERSION", "docs", "pd", "tools"]))
        self.assertEqual(self.dev_git("ls-tree", commit, "pd/bop"),
                         "160000 commit %s\tpd/bop" % GITLINK)
        self.assertEqual(self.dev_git("rev-parse", commit + ":pd"),
                         self.dev_git("rev-parse", TAG + ":pd"))
        # The public tag: annotated, named like the dev tag, on the export commit.
        self.assertEqual(self.dev_git("cat-file", "-t", public_tag), "tag")
        tag_text = self.dev_git("cat-file", "tag", public_tag)
        self.assertIn("object " + commit, tag_text)
        self.assertIn("tag " + TAG, tag_text)
        self.assertTrue(tag_text.endswith("bopOS " + TAG))
        # The dev tag still names the dev release commit; nothing was pushed.
        self.assertEqual(self.dev_git("rev-parse", TAG + "^{commit}"),
                         self.dev_git("rev-parse", "HEAD"))
        self.assertEqual(self.public_state(), before)

    def test_export_is_repeatable_and_refuses_once_public_main_moves(self):
        commit, public_tag = self.exported()
        self.ok("export", TAG)
        self.assertEqual(self.dev_git("rev-parse", "refs/bopos-release/%s/commit" % TAG), commit)
        self.assertEqual(self.dev_git("rev-parse", "refs/bopos-release/%s/tag" % TAG), public_tag)
        write(self.seed / "README.md", "someone else\n")
        git(self.seed, "commit", "-q", "-am", "Moved")
        git(self.seed, "push", "-q", str(self.public), "main")
        result = self.refused("export", TAG)
        self.assertIn("differs from this one", result.stderr)
        self.assertEqual(self.dev_git("rev-parse", "refs/bopos-release/%s/commit" % TAG), commit)

    def test_export_refuses_a_tag_that_prepare_did_not_make(self):
        self.bump()
        self.dev_git("commit", "-q", "-am", "Release " + TAG)
        self.dev_git("tag", "-a", TAG, "-m", "by hand")
        result = self.refused("export", TAG)
        self.assertIn("records no release-test run", result.stderr)
        self.dev_git("tag", "-d", TAG)
        self.dev_git("tag", TAG)
        self.assertIn("lightweight", self.refused("export", TAG).stderr)

    # publish

    def test_publish_dry_run_executes_nothing(self):
        self.env["BOPOS_RELEASE_GITHUB_REPO"] = "fixture-owner/fixture-repo"
        self.exported()
        before = self.public_state()
        result = self.ok("publish", TAG, "--dry-run")
        self.assertIn("dry run, not executed: git push --atomic", result.stdout)
        self.assertIn("refs/bopos-release/%s/commit:refs/heads/main" % TAG, result.stdout)
        self.assertIn("dry run, not executed: gh release create " + TAG, result.stdout)
        self.assertIn("dry run, not executed: gh release edit " + TAG, result.stdout)
        self.assertIn("- A fixture release.", result.stdout)
        self.assertEqual(self.public_state(), before)
        self.assertFalse((self.root / "gh.log").exists(), "dry run called gh")

    def test_publish_pushes_commit_and_tag_and_is_idempotent(self):
        self.env["BOPOS_RELEASE_GITHUB_REPO"] = "fixture-owner/fixture-repo"
        commit, public_tag = self.exported()
        self.ok("publish", TAG)
        self.assertEqual(self.public_git("rev-parse", "refs/heads/main"), commit)
        self.assertEqual(self.public_git("rev-parse", "refs/tags/" + TAG), public_tag)
        self.assertEqual(self.public_git("rev-parse", TAG + "^{commit}"), commit)
        calls = (self.root / "gh.log").read_text().splitlines()
        self.assertEqual([call.split()[:2] + call.split()[3:5] for call in calls],
                         [["release", "view", "--repo", "fixture-owner/fixture-repo"],
                          ["release", "create", "--repo", "fixture-owner/fixture-repo"]])
        self.assertIn("--verify-tag", calls[1])
        notes = (self.root / "gh.notes").read_text()
        self.assertTrue(notes.startswith("contract 1.3 · provision level 1 · schema 1\n"), notes)
        self.assertIn("- A fixture release.", notes)
        self.assertNotIn("## ", notes)
        self.assertNotIn("An older one", notes)

        after = self.public_state()
        result = self.ok("publish", TAG)
        self.assertIn("already has %s on main" % TAG, result.stdout)
        self.assertEqual(self.public_state(), after)
        calls = (self.root / "gh.log").read_text().splitlines()
        self.assertEqual([call.split()[1] for call in calls], ["view", "create", "view", "edit"])
        # export after publish recognises the published release.
        self.assertIn("already exported", self.ok("export", TAG).stdout)

    def test_publish_to_a_target_that_is_not_github_makes_no_release(self):
        self.exported()
        result = self.ok("publish", TAG)
        self.assertIn("not on GitHub; no GitHub release", result.stdout)
        self.assertFalse((self.root / "gh.log").exists())

    def test_publish_refuses_when_public_main_moved(self):
        self.exported()
        write(self.seed / "README.md", "someone else\n")
        git(self.seed, "commit", "-q", "-am", "Moved")
        git(self.seed, "push", "-q", str(self.public), "main")
        before = self.public_state()
        result = self.refused("publish", TAG)
        self.assertIn("neither %s's export" % TAG, result.stderr)
        self.assertEqual(self.public_state(), before)

    def test_publish_refuses_a_foreign_tag_on_the_target(self):
        self.exported()
        git(self.seed, "tag", "-a", TAG, "-m", "someone else's")
        git(self.seed, "push", "-q", str(self.public), TAG)
        before = self.public_state()
        self.assertIn("different tag", self.refused("publish", TAG).stderr)
        self.assertEqual(self.public_state(), before)

    # --root: the one-time fresh public history

    def test_root_export_has_no_parent_and_the_tree_of_a_normal_export(self):
        public_tip = self.public_git("rev-parse", "refs/heads/main")
        before = self.public_state()
        normal, _ = self.exported()
        self.dev_git("update-ref", "-d", "refs/bopos-release/%s/commit" % TAG)
        self.dev_git("update-ref", "-d", "refs/bopos-release/%s/tag" % TAG)
        result = self.ok("export", TAG, "--root")
        self.assertIn("--root --replacing " + public_tip, result.stdout)
        commit = self.dev_git("rev-parse", "refs/bopos-release/%s/commit" % TAG)
        self.assertEqual(self.dev_git("rev-list", "--parents", "-n", "1", commit), commit)
        self.assertEqual(self.dev_git("rev-parse", commit + "^{tree}"),
                         self.dev_git("rev-parse", normal + "^{tree}"))
        self.assertEqual(self.dev_git("log", "-1", "--format=%B", commit), "bopOS " + TAG)
        self.assertEqual(self.dev_git("rev-parse", "refs/bopos-release/%s/replaces" % TAG),
                         public_tip)
        public_tag = self.dev_git("rev-parse", "refs/bopos-release/%s/tag" % TAG)
        self.assertEqual(self.dev_git("rev-parse", public_tag + "^{commit}"), commit)
        self.assertIn("(root, replaces %s)" % public_tip[:7], self.ok("list").stdout)
        # Repeatable, and an export without --root doesn't silently replace it.
        self.ok("export", TAG, "--root")
        self.assertEqual(self.dev_git("rev-parse", "refs/bopos-release/%s/commit" % TAG), commit)
        self.assertIn("differs from this one", self.refused("export", TAG).stderr)
        self.assertEqual(self.public_state(), before)

    def test_root_export_goes_stale_when_public_main_moves(self):
        _, _, replaces = self.root_exported()
        self.move_public_main()
        self.assertIn("differs from this one", self.refused("export", TAG, "--root").stderr)
        self.assertEqual(self.dev_git("rev-parse", "refs/bopos-release/%s/replaces" % TAG),
                         replaces)

    def test_root_refuses_a_target_with_release_tags(self):
        self.prepared()
        self.tag_public()
        before = self.public_state()
        result = self.refused("export", TAG, "--root")
        self.assertIn("already has release tags: v0.9.0", result.stderr)
        self.assertEqual(self.dev_git("for-each-ref", "refs/bopos-release/" + TAG), "")
        self.assertEqual(self.public_state(), before)

    def test_root_publish_refuses_tags_that_appear_after_export(self):
        _, _, replaces = self.root_exported()
        self.tag_public()
        before = self.public_state()
        for extra in (("--dry-run",), ()):
            with self.subTest(extra):
                result = self.refused("publish", TAG, "--root", "--replacing", replaces, *extra)
                self.assertIn("already has release tags: v0.9.0", result.stderr)
                self.assertEqual(self.public_state(), before)

    def test_root_publish_needs_root_and_the_replaced_main_spelled_out(self):
        commit, _, replaces = self.root_exported()
        before = self.public_state()
        cases = {
            "is a root commit": (),
            "name the main it replaces with --replacing": ("--root",),
            "isn't the public main": ("--root", "--replacing", commit),
            "wants a commit id": ("--root", "--replacing", "main"),
            "applies to publish --root only": ("--replacing", replaces),
        }
        for needle, extra in cases.items():
            for dry in ((), ("--dry-run",)):
                with self.subTest(needle=needle, dry=dry):
                    self.assertIn(needle, self.refused("publish", TAG, *extra, *dry).stderr)
                    self.assertEqual(self.public_state(), before)
        self.assertIn("applies to export and publish only",
                      self.refused("list", "--root").stderr)

    def test_root_publish_refuses_a_normal_export(self):
        self.exported()
        tip = self.public_git("rev-parse", "refs/heads/main")
        before = self.public_state()
        result = self.refused("publish", TAG, "--root", "--replacing", tip)
        self.assertIn("isn't a root export", result.stderr)
        self.assertEqual(self.public_state(), before)

    def test_root_publish_dry_run_shows_the_forced_push(self):
        _, _, replaces = self.root_exported()
        before = self.public_state()
        result = self.ok("publish", TAG, "--root", "--replacing", replaces, "--dry-run")
        self.assertIn("REPLACING public main " + replaces, result.stdout)
        self.assertIn("dry run, not executed: git push --atomic", result.stdout)
        self.assertIn("--force-with-lease=refs/heads/main:" + replaces, result.stdout)
        self.assertIn("refs/bopos-release/%s/commit:refs/heads/main" % TAG, result.stdout)
        self.assertEqual(self.public_state(), before)

    def test_root_publish_replaces_main_once_then_releases_fast_forward(self):
        commit, public_tag, replaces = self.root_exported()
        self.assertEqual(len(self.public_git("rev-list", "refs/heads/main").split()), 2)
        result = self.ok("publish", TAG, "--root", "--replacing", replaces[:7])
        self.assertIn("history now starts at " + TAG, result.stdout)
        self.assertEqual(self.public_git("rev-list", "refs/heads/main").split(), [commit])
        self.assertEqual(self.public_git("rev-parse", "refs/tags/" + TAG), public_tag)

        # A re-run reports the release and forces nothing.
        after = self.public_state()
        result = self.ok("publish", TAG, "--root", "--replacing", replaces)
        self.assertIn("already has %s on main" % TAG, result.stdout)
        self.assertNotIn("REPLACING", result.stdout)
        self.assertEqual(self.public_state(), after)
        self.assertIn("already exported", self.ok("export", TAG, "--root").stdout)
        self.assertIn("already exported", self.ok("export", TAG).stdout)
        self.assertIn("is a root commit", self.refused("publish", TAG).stderr)

        # The next release is a normal one on top of the root commit.
        self.bump("1.2.1\n", NEXT_CHANGELOG)
        self.ok("prepare", NEXT_TAG)
        self.assertIn("already has release tags: " + TAG,
                      self.refused("export", NEXT_TAG, "--root").stderr)
        self.ok("export", NEXT_TAG)
        next_commit = self.dev_git("rev-parse", "refs/bopos-release/%s/commit" % NEXT_TAG)
        self.assertEqual(self.dev_git("rev-list", "--parents", "-n", "1", next_commit).split(),
                         [next_commit, commit])
        self.assertNotIn("force", self.ok("publish", NEXT_TAG, "--dry-run").stdout)
        self.ok("publish", NEXT_TAG)
        self.assertEqual(self.public_git("rev-list", "refs/heads/main").split(),
                         [next_commit, commit])

    def test_root_publish_refuses_when_public_main_moved_after_export(self):
        _, _, replaces = self.root_exported()
        moved = self.move_public_main()
        before = self.public_state()
        result = self.refused("publish", TAG, "--root", "--replacing", replaces)
        self.assertIn("neither %s's export" % TAG, result.stderr)
        self.assertIn("isn't the public main",
                      self.refused("publish", TAG, "--root", "--replacing", moved).stderr)
        self.assertEqual(self.public_state(), before)

    def test_root_publish_lease_refuses_a_move_during_the_push(self):
        _, _, replaces = self.root_exported()
        write(self.seed / "README.md", "pushed in the meantime\n")
        git(self.seed, "commit", "-q", "-am", "Raced")
        raced = git(self.seed, "rev-parse", "HEAD")
        git(self.seed, "push", "-q", str(self.public), "main:refs/heads/elsewhere")
        race_bin = self.root / "race-bin"
        write(race_bin / "git", RACE_GIT)
        (race_bin / "git").chmod(0o755)
        self.env.update(PATH=str(race_bin) + os.pathsep + self.env["PATH"],
                        REAL_GIT=shutil.which("git", path=self.env["PATH"]),
                        RACE_PUBLIC=str(self.public), RACE_TO=raced)
        result = self.refused("publish", TAG, "--root", "--replacing", replaces)
        self.assertIn("stale info", result.stderr)
        self.assertEqual(self.public_git("rev-parse", "refs/heads/main"), raced)
        self.assertEqual(self.public_git("tag", "-l"), "")

    # --root into an empty target: a plain push

    def test_root_into_an_empty_target_is_a_plain_push(self):
        empty = self.empty_target()
        self.prepared()
        result = self.ok("export", TAG, "--root", public=empty)
        self.assertIn("replaces nothing", result.stdout)
        self.assertIn("next: tools/release.sh publish %s --root --dry-run" % TAG, result.stdout)
        commit = self.dev_git("rev-parse", "refs/bopos-release/%s/commit" % TAG)
        public_tag = self.dev_git("rev-parse", "refs/bopos-release/%s/tag" % TAG)
        self.assertEqual(self.dev_git("rev-list", "--parents", "-n", "1", commit), commit)
        self.assertEqual(self.dev_git("for-each-ref", "refs/bopos-release/%s/replaces" % TAG), "")
        self.ok("export", TAG, "--root", public=empty)
        self.assertIn("differs from this one", self.refused("export", TAG, "--root").stderr)

        dry = self.ok("publish", TAG, "--root", "--dry-run", public=empty).stdout
        push = [line for line in dry.splitlines() if "git push" in line]
        self.assertEqual(len(push), 1, dry)
        self.assertNotIn("force", push[0])
        self.assertIn("is empty", dry)
        self.assertEqual(git(empty, "for-each-ref"), "")
        for extra, needle in (((), "is a root commit"),
                              (("--root", "--replacing", commit), "records no main to replace")):
            with self.subTest(extra):
                self.assertIn(needle, self.refused("publish", TAG, *extra, public=empty).stderr)
                self.assertEqual(git(empty, "for-each-ref"), "")

        self.ok("publish", TAG, "--root", public=empty)
        self.assertEqual(git(empty, "rev-list", "refs/heads/main").split(), [commit])
        self.assertEqual(git(empty, "rev-parse", "refs/tags/" + TAG), public_tag)
        after = git(empty, "for-each-ref", "--format=%(refname) %(objectname)")
        self.assertIn("already has %s on main" % TAG,
                      self.ok("publish", TAG, "--root", public=empty).stdout)
        self.assertEqual(git(empty, "for-each-ref", "--format=%(refname) %(objectname)"), after)

        # The next release fast-forwards from it.
        self.bump("1.2.1\n", NEXT_CHANGELOG)
        self.ok("prepare", NEXT_TAG)
        self.ok("export", NEXT_TAG, public=empty)
        self.ok("publish", NEXT_TAG, public=empty)
        next_commit = self.dev_git("rev-parse", "refs/bopos-release/%s/commit" % NEXT_TAG)
        self.assertEqual(git(empty, "rev-list", "refs/heads/main").split(), [next_commit, commit])

    def test_root_into_a_target_with_refs_but_no_main_refuses(self):
        other = self.empty_target()
        git(self.seed, "push", "-q", str(other), "main:refs/heads/other")
        before = git(other, "for-each-ref", "--format=%(refname) %(objectname)")
        self.prepared()
        self.assertIn("could not fetch main", self.refused("export", TAG, "--root", public=other).stderr)
        # Exported while empty, then the target gains a ref: publish won't push.
        empty = self.empty_target("later.git")
        self.ok("export", TAG, "--root", public=empty)
        git(self.seed, "push", "-q", str(empty), "main:refs/heads/other")
        state = git(empty, "for-each-ref", "--format=%(refname) %(objectname)")
        self.assertIn("name the main it replaces",
                      self.refused("publish", TAG, "--root", public=empty).stderr)
        self.assertEqual(git(empty, "for-each-ref", "--format=%(refname) %(objectname)"), state)
        self.assertEqual(git(other, "for-each-ref", "--format=%(refname) %(objectname)"), before)

    def test_root_export_made_against_a_main_can_publish_into_an_empty_target(self):
        # The old repository retired after export, a fresh empty one in its place.
        commit, _, replaces = self.root_exported()
        empty = self.empty_target()
        self.assertIn("there is no main to replace",
                      self.refused("publish", TAG, "--root", "--replacing", replaces,
                                   public=empty).stderr)
        self.ok("publish", TAG, "--root", public=empty)
        self.assertEqual(git(empty, "rev-list", "refs/heads/main").split(), [commit])

    def test_plain_publish_never_forces(self):
        self.exported()
        dry = self.ok("publish", TAG, "--dry-run").stdout
        push = [line for line in dry.splitlines() if "git push" in line]
        self.assertEqual(len(push), 1, dry)
        self.assertNotIn("force", push[0])
        self.assertNotIn(" +", push[0])
        # Pointed at a main it can't fast-forward, it refuses rather than force.
        self.move_public_main()
        before = self.public_state()
        self.assertIn("neither", self.refused("publish", TAG).stderr)
        self.assertEqual(self.public_state(), before)


class ManifestTests(unittest.TestCase):
    def test_every_tracked_top_level_entry_is_classified(self):
        try:
            names = subprocess.run(
                ["git", "ls-files", "-z", "--cached"], cwd=ROOT, env=fixture_git.environment(),
                capture_output=True, check=True).stdout.decode().split("\0")
        except (OSError, subprocess.CalledProcessError):
            self.skipTest("not a Git checkout")
        top_level = {name.split("/", 1)[0] for name in names if name}
        unclassified = sorted(top_level - set(read_manifest()))
        self.assertEqual(unclassified, [], "classify these in %s (public or private): %s"
                         % (MANIFEST.relative_to(ROOT), ", ".join(unclassified)))

    def test_release_identity_files_are_public(self):
        kinds = read_manifest()
        for name in ("VERSION", "CHANGELOG.md", "tools", ".gitmodules", "pd"):
            with self.subTest(name):
                self.assertEqual(kinds.get(name), "public")


if __name__ == "__main__":
    unittest.main()
