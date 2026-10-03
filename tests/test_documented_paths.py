"""Concrete inline paths in current docs must resolve to repository files."""

from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
INLINE_CODE = re.compile(r"(?<!`)`([^`\n]+)`(?!`)")
# These are examples, not framework files. Keep exceptions explicit so a
# misspelled concrete source path cannot silently become a placeholder.
EXAMPLES = {"patches/my-piece/", "instrument/marimba/gain"}


def concrete_paths(text):
    # The contract's revision table preserves historical spellings by design.
    text = text.split("## 15. Revision history", 1)[0]
    for match in INLINE_CODE.finditer(text):
        token = match.group(1)
        if ("/" not in token or any(char.isspace() for char in token)
                or token.startswith(("/", "~", "-")) or "://" in token
                or "=" in token or re.search(r"[<>{}*…]", token)
                or token in EXAMPLES):
            continue
        parts = Path(token).parts
        if any(part in (".loom", ".lore") for part in parts):
            continue
        if parts[0] == "run":  # generated logs, pid files and measurements
            continue
        yield text.count("\n", 0, match.start()) + 1, token


def documented_sources():
    # Tracked component READMEs only: local composer patches are not fixtures.
    tracked = subprocess.check_output(
        ["git", "ls-files", "--", "*.md"], cwd=ROOT, text=True).splitlines()
    for name in tracked:
        path = Path(name)
        if path.parts[0].startswith("."):
            continue  # primitive protocols/history are not component guides
        if (path.name == "README.md"
                or (path.parent == Path("docs") and path.suffix == ".md")):
            yield ROOT / path


def missing_paths(document, root=ROOT):
    return [(line, token) for line, token in concrete_paths(document.read_text())
            if not (root / token).exists()
            and not (document.parent / token).exists()]


class DocumentedPathTests(unittest.TestCase):
    def test_current_documented_paths_exist(self):
        missing = [f"{doc.relative_to(ROOT)}:{line}: {token}"
                   for doc in documented_sources()
                   for line, token in missing_paths(doc)]
        self.assertEqual(missing, [], "Missing documented paths:\n" + "\n".join(missing))

    def test_concrete_typo_is_checked(self):
        self.assertEqual(list(concrete_paths("old `pd/bopos.pd`\nnew `pd/bopos~.pd`")),
                         [(1, "pd/bopos.pd"), (2, "pd/bopos~.pd")])

    def test_missing_file_fails_and_document_relative_file_passes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            doc = root / "README.md"
            doc.write_text("`pd/bopos.pd` `local/guide.md`")
            (root / "local").mkdir()
            (root / "local/guide.md").write_text("guide")
            self.assertEqual(missing_paths(doc, root=root / "elsewhere"),
                             [(1, "pd/bopos.pd")])

    def test_placeholders_and_non_repository_paths_are_allowed(self):
        text = ("`patches/my-piece/` `patches/<name>/main.pd` "
                "`tests/verify_*.py` `run/io.log` `~/bopOS/assets/` "
                "`/os/fetch` `https://example.test/a/b` `instrument/marimba/gain`")
        self.assertEqual(list(concrete_paths(text)), [])

    def test_history_is_ignored(self):
        text = ("`.loom/tied/old/file.md` `.lore/items/old/file.md` "
                "`other-repo/.loom/old`\n## 15. Revision history\n`presets/`")
        self.assertEqual(list(concrete_paths(text)), [])


if __name__ == "__main__":
    unittest.main()
