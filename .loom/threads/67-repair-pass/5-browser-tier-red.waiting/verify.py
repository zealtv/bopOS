"""Run the four repaired journeys, keeping a separate log for each."""
from pathlib import Path
import subprocess
import sys

sys.dont_write_bytecode = True
for repo in Path(__file__).resolve().parents:
    if (repo / "tools/simfleet.py").is_file():
        break
else:
    raise SystemExit("cannot locate bopOS repository")

failed = False
for name in ("verify_control_column_scroll", "verify_control_surface_component",
             "verify_control_tab", "verify_manifest_param_visibility"):
    with (Path(__file__).resolve().parent / (name + ".log")).open("w") as output:
        result = subprocess.run([sys.executable, str(repo / "tests" / (name + ".py"))],
                                cwd=repo, stdout=output, stderr=subprocess.STDOUT)
    print(f"{'PASS' if result.returncode == 0 else 'FAIL'} {name}", flush=True)
    failed = failed or result.returncode != 0
raise SystemExit(1 if failed else 0)
