"""The public tree must read and test correctly without the private paths.

Development happens in a private repository whose tree also holds work
tracking, memory and agent notes. A release export drops those paths and
publishes the rest, so no exported file may name them: the reader of the public
repository would meet dangling links and references to material they cannot
see. The same goes for installation specifics that stay out of the public repo.

The scan covers the files a release would export: in a Git checkout, tracked
and not-yet-added files outside the private set; in a plain copy of the tree
(an export, or a scratch copy with the private paths removed), every file
outside the private set. The check therefore passes in both trees.

Exceptions are narrow and explicit (EXCEPTIONS). Each names one file and says
why it may mention a private path.
"""

import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import fixture_git

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]

# The export allowlist, shared with tools/release.sh: one "public <entry>" or
# "private <entry>" per line. A release export leaves the private entries out.
MANIFEST = ROOT / "tools" / "release-manifest"


def read_manifest(path=MANIFEST):
    """{top-level entry: "public" or "private"} from the release manifest."""
    kinds = {}
    for line in Path(path).read_text().splitlines():
        fields = line.split("#", 1)[0].split()
        if not fields:
            continue
        if len(fields) != 2 or fields[0] not in ("public", "private"):
            raise ValueError("%s: bad line %r" % (path, line))
        if kinds.get(fields[1], fields[0]) != fields[0]:
            raise ValueError("%s: %s is both public and private" % (path, fields[1]))
        kinds[fields[1]] = fields[0]
    return kinds


PRIVATE_TOP_LEVEL = frozenset(
    name for name, kind in read_manifest().items() if kind == "private")

# Trees that belong to other projects, not to this export's own text.
THIRD_PARTY = ("pd/bop/",)

# path -> reason it may name a private path. Add to this only when removing the
# mention would make the file wrong.
EXCEPTIONS = {
    "tests/test_public_tree.py":
        "defines the patterns it searches for, so it must spell them",
    "tools/release-manifest":
        "names the private top-level entries so that the export can leave them out",
}

DOTDIRS = r"(?:glean|loom|lore|nest|groundhog|claude|codex|obsidian|worktrees)"
PATTERNS = {
    "private dot-directory path":
        re.compile(r"(?<![\w-])\." + DOTDIRS + r"(?![\w-])"),
    "private primitive script":
        re.compile(r"\b(?:loom|glean|lore|groundhog)\.sh\b"),
    "private primitive name or record id":
        re.compile(r"\b(?:loom|glean|lore|nestlings?|groundhog)\b", re.IGNORECASE),
    "private agent notes file":
        re.compile(r"\b(?:AGENTS|CLAUDE)\.md\b"),
    "installation specifics":
        re.compile(r"kite[ -]?choir|\bkc-test\b|broadwalk|\bPCB order\b", re.IGNORECASE),
}


def private(relative):
    return relative.split("/", 1)[0] in PRIVATE_TOP_LEVEL


def is_git_checkout(root):
    toplevel = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"], cwd=root,
        env=fixture_git.environment(), capture_output=True, text=True)
    return (toplevel.returncode == 0
            and Path(toplevel.stdout.strip()).resolve() == root.resolve())


def candidate_files(root):
    if is_git_checkout(root):
        names = subprocess.check_output(
            ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
            cwd=root, env=fixture_git.environment()).decode("utf-8").split("\0")
        names = [name for name in names if name]
    else:
        names = []
        for directory, subdirs, files in os.walk(root):
            relative_dir = Path(directory).relative_to(root).as_posix()
            if relative_dir == ".":
                relative_dir = ""
            subdirs[:] = [d for d in subdirs if d not in (".git", "__pycache__")]
            names.extend((relative_dir + "/" + name).lstrip("/") for name in files)
    for name in sorted(set(names)):
        path = root / name
        if (private(name) or name.startswith(THIRD_PARTY)
                or path.is_symlink() or not path.is_file()):
            continue
        yield name


def leaks(root, exceptions=EXCEPTIONS):
    found = []
    for name in candidate_files(root):
        if name in exceptions:
            continue
        data = (root / name).read_bytes()
        if b"\0" in data[:8192]:
            continue  # binary: images and the like
        for number, line in enumerate(data.decode("utf-8", "replace").splitlines(), 1):
            for label, pattern in PATTERNS.items():
                match = pattern.search(line)
                if match:
                    found.append("%s:%d: %s: %r" % (name, number, label, match.group(0)))
    return found


class PublicTreeTests(unittest.TestCase):
    def test_public_files_name_no_private_path(self):
        found = leaks(ROOT)
        self.assertEqual(found, [], "Public files reach private paths or specifics "
                         "(release exports drop those paths):\n" + "\n".join(found))

    def test_exceptions_still_exist_and_are_justified(self):
        for name, reason in EXCEPTIONS.items():
            self.assertTrue(reason.strip(), name)
            self.assertTrue((ROOT / name).is_file(), "stale exception: " + name)

    def test_patterns_match_private_references_and_spare_public_prose(self):
        samples = {
            "see .loom/threads/x": True,
            "[notes](.glean/findings/INDEX.md)": True,
            "../.lore/items/a": True,
            "`./.loom/loom.sh status`": True,
            "glean.sh fetch": True,
            "lore:2026-11-11-note": True,
            "(glean: playwright-gotchas)": True,
            "the loom stitch": True,
            "see AGENTS.md": True,
            "Kite Choir 2": True,
            "kite-choir-brains": True,
            "the Northern Broadwalk site": True,
            "a 54-unit PCB order": True,
            "tune-v2 and the loomed fabric": False,
            "folklore and glean-less": False,
            "a nested .nested dir": False,
            "docs/ARCHITECTURE.md and .github/workflows": False,
        }
        for text, expected in samples.items():
            hit = any(pattern.search(text) for pattern in PATTERNS.values())
            if text == "folklore and glean-less":
                hit = any(p.search(text) for label, p in PATTERNS.items()
                          if label != "private primitive name or record id")
            with self.subTest(text=text):
                self.assertEqual(hit, expected)

    def test_private_paths_are_not_scanned_but_public_files_are(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, text in {
                ".loom/threads/a.md": "private notes about .loom/",
                "AGENTS.md": "mentions loom.sh",
                "inbox": "x",
                "README.md": "clean",
                "docs/guide.md": "see [work](.loom/threads/a.md)",
                "pd/bop/readme.md": "someone else's .loom/ file",
                "tools/ok.py": "# fine\n",
            }.items():
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text)
            (root / "docs/image.png").write_bytes(b"\0\x89PNG .loom/")
            self.assertEqual(
                leaks(root),
                ["docs/guide.md:1: private dot-directory path: '.loom'",
                 "docs/guide.md:1: private primitive name or record id: 'loom'"])

    def test_explicit_exception_is_honoured(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "a.py").write_text("# .loom/\n")
            self.assertEqual(leaks(root, exceptions={"a.py": "fixture"}), [])
            self.assertEqual(len(leaks(root, exceptions={})), 2)


if __name__ == "__main__":
    unittest.main()
