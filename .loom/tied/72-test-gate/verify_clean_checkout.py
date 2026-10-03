#!/usr/bin/env python3
"""Check CI fixtures against tracked files, without the local patch library."""
import io
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile

sys.dont_write_bytecode = True
repo = Path(__file__).resolve().parent
while not (repo / "tools/simfleet.py").is_file():
    if repo == repo.parent:
        raise SystemExit("cannot find repository")
    repo = repo.parent

checkout = Path(tempfile.mkdtemp(prefix="bopos-test-gate-"))
archive = subprocess.check_output(["git", "archive", "HEAD"], cwd=repo)
with tarfile.open(fileobj=io.BytesIO(archive)) as source:
    source.extractall(checkout)
for relative in ("tools/run-tests.sh", "tools/install-hooks.sh",
                 "tools/hooks/pre-commit", "tests/test_commit_gate.py",
                 "tests/test_test_runner.py", ".github/workflows/tests.yml"):
    target = checkout / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(repo / relative, target)
log = Path(__file__).resolve().parent / "clean-checkout.log"
print(f"Tracked-only checkout: {checkout}\nResults: {log}", flush=True)
with log.open("w") as output:
    result = subprocess.run([str(checkout / "tools/run-tests.sh"), "all"],
                            cwd=checkout, stdout=output, stderr=subprocess.STDOUT)
print(f"all exit status: {result.returncode}", flush=True)
raise SystemExit(result.returncode)
