#!/usr/bin/env python3
"""Living guard for runtime-evaluated PEP 604 unions (thread 61/3).

`VirtualNode` in `tools/audition.py` is a dataclass, so its field annotations
are evaluated when the class body runs. `subprocess.Popen | None` is therefore
a plain runtime `TypeError` on Python 3.9 -- an import-time death that takes
the whole supervisor with it before `send_ready()`. On a fresh macOS the
`python3` on PATH is 3.9, `install-dashboard.sh` builds its venv from it, and
*Launch editor* fails with `unsupported operand type(s) for |: 'type' and
'NoneType'` and nothing else.

`from __future__ import annotations` defers the evaluation and costs nothing.
This guard is a source check rather than an interpreter check on purpose: CI
runs one Python, and the failure only appears on another. It flags the
positions where an annotation really is evaluated at runtime -- module and
class level (they land in `__annotations__`) and function signatures
(evaluated at `def` time) -- and ignores annotations inside function bodies,
which are never evaluated at all.
"""

import ast
import sys
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIRS = ("tools", "python", "dashboard")


def defers_annotations(tree):
    return any(isinstance(node, ast.ImportFrom) and node.module == "__future__"
               and any(alias.name == "annotations" for alias in node.names)
               for node in tree.body)


def union_annotations(node):
    """Annotations under `node` that a `|` makes runtime-evaluated."""
    found = []

    def uses_bitor(annotation):
        return annotation is not None and any(
            isinstance(child, ast.BinOp) and isinstance(child.op, ast.BitOr)
            for child in ast.walk(annotation))

    def visit(scope, evaluated):
        for child in ast.iter_child_nodes(scope):
            if isinstance(child, ast.AnnAssign):
                if evaluated and uses_bitor(child.annotation):
                    found.append(child.lineno)
            elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                arguments = child.args
                for argument in (*arguments.posonlyargs, *arguments.args,
                                 *arguments.kwonlyargs, arguments.vararg,
                                 arguments.kwarg):
                    if argument is not None and uses_bitor(argument.annotation):
                        found.append(argument.lineno)
                if uses_bitor(child.returns):
                    found.append(child.lineno)
                # A body's own annotations are never evaluated.
                visit(child, evaluated=False)
                continue
            elif isinstance(child, ast.ClassDef):
                visit(child, evaluated=evaluated)
                continue
            visit(child, evaluated=evaluated)

    visit(node, evaluated=True)
    return found


def sources():
    for directory in SOURCE_DIRS:
        for path in sorted((ROOT / directory).rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            yield path


class RuntimeUnionAnnotationTests(unittest.TestCase):
    def test_no_module_evaluates_a_pep604_union_at_runtime(self):
        offenders = []
        for path in sources():
            tree = ast.parse(path.read_text())
            if defers_annotations(tree):
                continue
            for line in union_annotations(tree):
                offenders.append(f"{path.relative_to(ROOT)}:{line}")
        self.assertEqual(offenders, [], "\n".join([
            "These annotations are evaluated at import time and raise TypeError",
            "on Python < 3.10. Add `from __future__ import annotations` to the",
            "module, or write Optional[...]:", *offenders]))

    def test_the_supervisor_entry_point_defers_annotations(self):
        """The specific module the dashboard spawns, pinned by name.

        The general check above passes the moment someone deletes the union;
        this one keeps the deferral in place for the next one written.
        """
        tree = ast.parse((ROOT / "tools" / "audition.py").read_text())
        self.assertTrue(defers_annotations(tree))


class DetectorTests(unittest.TestCase):
    """The guard's own reach, since a source check that misses is worse than none."""

    def offenders(self, source):
        return union_annotations(ast.parse(source))

    def test_catches_a_dataclass_field(self):
        self.assertTrue(self.offenders(
            "import subprocess\n"
            "class Node:\n"
            "    process: subprocess.Popen | None = None\n"))

    def test_catches_module_level_and_signatures(self):
        self.assertTrue(self.offenders("value: int | None = None\n"))
        self.assertTrue(self.offenders("def f(a: int | None = None): pass\n"))
        self.assertTrue(self.offenders("def f() -> int | None: pass\n"))

    def test_ignores_annotations_inside_a_function_body(self):
        self.assertFalse(self.offenders(
            "def f():\n    value: int | None = None\n    return value\n"))

    def test_ignores_ordinary_bitwise_or(self):
        self.assertFalse(self.offenders("flags = 1 | 2\n"))
        self.assertFalse(self.offenders("def f(a=1 | 2): pass\n"))


if __name__ == "__main__":
    unittest.main()
