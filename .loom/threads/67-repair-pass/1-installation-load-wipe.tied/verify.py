"""Focused state-load checks; runnable before or after the stitch is tied."""
from pathlib import Path
import subprocess
import sys

sys.dont_write_bytecode = True
for repo in Path(__file__).resolve().parents:
    if (repo / "tools/simfleet.py").is_file():
        break
else:
    raise SystemExit("cannot locate bopOS repository")

subprocess.run([sys.executable, str(repo / "tests/test_state_load_safety.py")],
               cwd=repo, check=True)
subprocess.run(["node", "--check", str(repo / "dashboard/static/js/show.js")],
               cwd=repo, check=True)
