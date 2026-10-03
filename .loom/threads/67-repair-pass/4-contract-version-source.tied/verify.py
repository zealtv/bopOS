"""Focused report/version verification; works from the tied stitch path."""
from pathlib import Path
import subprocess
import sys

sys.dont_write_bytecode = True
for repo in Path(__file__).resolve().parents:
    if (repo / "tools/simfleet.py").is_file():
        break
else:
    raise SystemExit("cannot locate bopOS repository")

for name in ("test_contract_version.py", "test_device_enabled.py"):
    subprocess.run([sys.executable, str(repo / "tests" / name)], cwd=repo, check=True)
