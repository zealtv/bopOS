"""Drive the node-contract-fixes code paths directly via the pyOSC3 stub.

Run with PYTHONPATH=<stubs>:<repo>/python:<repo>/python/io
"""
import os
import sys
import types

import pyOSC3

REPO = "/home/bob/repos/bopOS"
FAILURES = []


def check(label, cond, detail=""):
    status = "PASS" if cond else "FAIL"
    print(f"[{status}] {label}" + (f" -- {detail}" if detail and not cond else ""))
    if not cond:
        FAILURES.append(label)


# --- A. sys_i2c degradation -------------------------------------------------
os.environ.pop("BLINKA_MCP2221", None)
import sys_i2c

check("sys_i2c imports without smbus2", not sys_i2c.HAVE_SMBUS)
check("scan_bus() -> [] without smbus2", sys_i2c.scan_bus() == [])
check("have_bus(99) False (no /dev/i2c-99, no BLINKA)", sys_i2c.have_bus(99) is False)
check("have_bus(1) True (laptop /dev/i2c-1 exists)", sys_i2c.have_bus(1) is True)
os.environ["BLINKA_MCP2221"] = "1"
check("have_bus(99) True with BLINKA_MCP2221 set", sys_i2c.have_bus(99) is True)
os.environ.pop("BLINKA_MCP2221", None)

# --- B. io/main.py /io/create error replies ----------------------------------
import main as io_main

mgr = io_main.IOManager()

pyOSC3.SENT.clear()
io_main.have_bus = lambda bus=1: False
mgr.handle_command("/io/create", "", ["foo", "ads1015", "0x48"], None)
check("/io/create with no bus -> /io/error foo no-bus",
      ("/io/error", ["foo", "no-bus"]) in pyOSC3.SENT, repr(pyOSC3.SENT))

pyOSC3.SENT.clear()
io_main.have_bus = lambda bus=1: True
mgr.handle_command("/io/create", "", ["bar", "nonexistent-type", "0x48"], None)
check("/io/create unknown type -> /io/error bar create-failed",
      ("/io/error", ["bar", "create-failed"]) in pyOSC3.SENT, repr(pyOSC3.SENT))

# --- C. helper.py restart_engine_callback ------------------------------------
sys.argv = ["helper.py", "aa:bb:cc:dd:ee:ff"]
import bopos as helper

popen_calls = []


class FakePopen:
    def __init__(self, argv, **kwargs):
        popen_calls.append((argv, kwargs))


helper.subprocess = types.SimpleNamespace(Popen=FakePopen)

pyOSC3.SENT.clear()
helper.restart_engine_callback()

check("reply /restart-engine sent to PD (6661)",
      ("/restart-engine", []) in pyOSC3.SENT, repr(pyOSC3.SENT))
check("exactly one Popen call", len(popen_calls) == 1, repr(popen_calls))
if popen_calls:
    argv, kwargs = popen_calls[0]
    check("Popen detached (start_new_session)", kwargs.get("start_new_session") is True)
    check("Popen argv references stop-engine.sh then start-engine.sh",
          len(argv) == 6
          and os.path.realpath(argv[4]) == os.path.join(REPO, "bash/stop-engine.sh")
          and os.path.realpath(argv[5]) == os.path.join(REPO, "bash/start-engine.sh"),
          repr(argv))
check("client target is PD port 6661", helper.client.target == ("127.0.0.1", 6661))

print()
if FAILURES:
    print(f"{len(FAILURES)} FAILURE(S): {FAILURES}")
    sys.exit(1)
print("all checks passed")
