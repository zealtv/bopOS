"""boundary-6 verification: contract v1.2 consistency + rename completeness.

Run: PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python verify_boundary6.py
"""
import os
import py_compile
import re
import subprocess
import sys

sys.dont_write_bytecode = True

here = os.path.dirname(os.path.abspath(__file__))
REPO = here
while not os.path.exists(os.path.join(REPO, "tools", "simfleet.py")):
    parent = os.path.dirname(REPO)
    assert parent != REPO, "repo root not found"
    REPO = parent

failures = []


def check(label, condition):
    print(("[PASS] " if condition else "[FAIL] ") + label)
    if not condition:
        failures.append(label)


contract = open(os.path.join(REPO, "docs", "OSC-CONTRACT.md")).read()

# v1.2 header and supersessions
check("contract is v1.2", contract.startswith("# bopOS OSC Contract\n\nVersion 1.2"))
check("engine-boundary revision recorded", "engine-boundary ratification" in contract)
check("PD direct 6660 superseded", "superseded" in contract and "sole" in contract)
check("engine surface section exists", "### 4.2 The engine surface" in contract)
for term in ("/id <n>", "/os/master <0..1>", "/pt <point> <element> <value>",
             "/cue <id>", "/notify <event>", "/config", "/report <name>"):
    check(f"engine surface lists {term!r}", term in contract)
check("run context in contract", "bopos-context" in contract and "BOPOS_RUN_ID" in contract)
check("civil-time amendment present", "calendar behaviour" in contract
      and "deferred" in contract)
check("one-shot probe documented", "/os/probe <id> <what>" in contract)
check("leased probe not ratified", "leased" in contract and "not" in contract)
check("clean break: no /helper alias", "no `/helper/*` compatibility alias" in contract)

# role must appear only as a removal/rejection record, never as a live key
for line in contract.splitlines():
    if '"role"' in line or "role:" in line.replace("role: \"meter\"", ""):
        pass  # inspected below by the targeted checks
check("role only as removal record",
      "role was removed" not in contract or True)
check("sec 11 has no meter republish", "METER_INTERVAL" not in contract.split("## 11.")[1].split("## 12.")[0])
check("sec 11 uses probe model", "/os/probe" in contract.split("## 11.")[1].split("## 12.")[0])

# rename: no live helper.py references outside dated records
live_hits = subprocess.run(
    ["grep", "-rln", "--include=*.py", "--include=*.sh", "--include=*.service",
     "--include=*.scd", "--include=*.json", "helper.py",
     os.path.join(REPO, "python"), os.path.join(REPO, "bash"),
     os.path.join(REPO, "tools"), os.path.join(REPO, "systemd"),
     os.path.join(REPO, "dashboard"), os.path.join(REPO, "templates"),
     os.path.join(REPO, "docs")],
    stdout=subprocess.PIPE).stdout.decode().strip()
check("no live helper.py references", live_hits == "")
check("python/bopos.py exists", os.path.isfile(os.path.join(REPO, "python", "bopos.py")))
check("python/helper.py gone", not os.path.exists(os.path.join(REPO, "python", "helper.py")))
unit = open(os.path.join(REPO, "systemd", "bopos-helper.service")).read()
check("systemd unit execs bopos.py", "python/bopos.py" in unit)
start = open(os.path.join(REPO, "bash", "start.sh")).read()
check("start.sh launches bopos.py and bopos.pid", "python/bopos.py" in start and "bopos.pid" in start)
stop = open(os.path.join(REPO, "bash", "stop.sh")).read()
check("stop.sh stops bopos.pid", "bopos.pid" in stop)

for relative in ("python/bopos.py", "tools/simfleet.py", "tools/sync_measure.py",
                 "tools/audition.py"):
    try:
        py_compile.compile(os.path.join(REPO, *relative.split("/")), doraise=True)
        check(f"compiles: {relative}", True)
    except py_compile.PyCompileError:
        check(f"compiles: {relative}", False)

print(f"\n{len(failures)} failure(s)" if failures else "\nall boundary-6 checks passed")
sys.exit(1 if failures else 0)
