"""Direct checks for the hb-identity stitch.

Run with PYTHONPATH=<pylib>:python:python/io.
"""
import os
import sys
import tempfile
import types

import pyOSC3

FAILURES = []


def check(label, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    print("[{}] {}{}".format(status, label, " -- " + detail if detail and not condition else ""))
    if not condition:
        FAILURES.append(label)


class FakeServer:
    def __init__(self, target):
        self.target = target
        self.handlers = {}

    def addMsgHandler(self, address, callback):
        self.handlers[address] = callback

    def close(self):
        pass


class FakeClient:
    def __init__(self):
        self.target = None
        self.sent = []

    def connect(self, target):
        self.target = target

    def send(self, message):
        self.sent.append(pyOSC3.decodeOSC(message.getBinary()))


pyOSC3.OSCServer = FakeServer
pyOSC3.OSCClient = FakeClient
sys.argv = ["helper.py", "unknown"]
import helper
import sys_wireless


class State:
    def __init__(self, uid="node-uid", device_id=-1):
        self.uid = uid
        self.id = device_id
        self.version = "a1b2c3d"
        self.config = {"HB_TARGET": "127.0.0.1", "HB_RSSI": "1", "MIXER_CONTROL": None}
        self.mixer_control = None
        self.muted_via_stop = False


old_dir = helper.BOPOS_DIR
with tempfile.TemporaryDirectory() as root:
    helper.BOPOS_DIR = root
    os.makedirs(os.path.join(root, "state"))
    with open(os.path.join(root, "state", "uid"), "w") as target:
        target.write("pinned-token\n")
    check("uid token file wins", helper.resolve_uid(["helper.py", "aa:bb"]) == "pinned-token")
    os.unlink(os.path.join(root, "state", "uid"))
    check("uid argv MAC", helper.resolve_uid(["helper.py", "aa:bb"]) == "aa:bb")
    old_discover = helper.discover_primary_mac
    helper.discover_primary_mac = lambda: None
    value = helper.resolve_uid(["helper.py"])
    check("uid falls back to UUID", len(value) == 36 and value.count("-") == 4, value)
    helper.discover_primary_mac = old_discover

    absent = helper.read_node_config(os.path.join(root, "missing"))
    check("node config absent defaults", absent == {"HB_TARGET": "255.255.255.255", "HB_RSSI": "1", "MIXER_CONTROL": None, "UPDATE_MODEL": "persistent"}, repr(absent))
    config_path = os.path.join(root, "bopos.config")
    with open(config_path, "w") as target:
        target.write("# comment\nHB_TARGET='127.0.0.1'\n\nHB_RSSI=\"0\"\nMIXER_CONTROL=Digital\n")
    parsed = helper.read_node_config(config_path)
    check("node config comments and quotes", parsed == {"HB_TARGET": "127.0.0.1", "HB_RSSI": "0", "MIXER_CONTROL": "Digital", "UPDATE_MODEL": "persistent"}, repr(parsed))

    devices = os.path.join(root, "bopos.devices")
    with open(devices, "w") as target:
        target.write("aa:bb,node,7\n")
    check("devices id match", helper.resolve_id("aa:bb", devices) == 7)
    check("devices id miss is -1", helper.resolve_id("cc:dd", devices) == -1)

helper.BOPOS_DIR = old_dir

check("selector all", helper.selector_matches("all", 4))
check("selector numeric", helper.selector_matches("4", 4))
check("selector -1", helper.selector_matches("-1", -1))
check("selector rejects nonnumeric", not helper.selector_matches("x", -1))


class ReplySocket:
    def __init__(self):
        self.calls = []

    def sendto(self, data, target):
        self.calls.append((pyOSC3.decodeOSC(data), target))


request = pyOSC3.OSCMessage("/all/os/ping")
request.append(123, "i")
reply = ReplySocket()
helper.handle_lan_datagram(request.getBinary(), ("10.2.3.4", 43210), reply, State())
check("ping pong bytes and unicast port", reply.calls == [(["/os/pong", ",is", 123, "node-uid"], ("10.2.3.4", 5550))], repr(reply.calls))

identified = []
old_flash = helper.flash_led
helper.flash_led = lambda: identified.append("flash")
helper.client.sent[:] = []
check("identify wrong uid filtered", not helper.identify("other", State()))
check("identify matching uid accepted", helper.identify("node-uid", State()))
check("identify tells PD and flashes", helper.client.sent[-1] == ["/identify", ","] and identified == ["flash"], repr((helper.client.sent, identified)))
helper.flash_led = old_flash

commands = []
old_run = helper.run_command
old_popen = helper.subprocess.Popen


def mixer_success(argv):
    commands.append(argv)
    return 0 if argv[:4] == ["amixer", "-q", "sset", "Digital"] else 1


state = State()
state.config["MIXER_CONTROL"] = "Digital"
helper.run_command = mixer_success
helper.set_mute(1, state)
helper.set_mute(1, state)
check("mute mixer success remembered and reapplied", state.mixer_control == "Digital" and len(commands) == 2, repr(commands))

commands[:] = []
helper.run_command = lambda argv: commands.append(argv) or 1
state = State()
helper.set_mute(1, state)
check("mute degrades to engine stop", state.muted_via_stop and commands[-1][-1].endswith("stop-engine.sh"), repr(commands))
helper.set_mute(0, state)
helper.set_mute(0, state)
start_calls = [argv for argv in commands if argv[-1].endswith("start-engine.sh")]
check("unmute restarts stopped engine once", len(start_calls) == 1 and not state.muted_via_stop, repr(commands))
helper.run_command = old_run
helper.subprocess.Popen = old_popen

old_alive, old_rssi = helper.engine_alive, helper.read_rssi
helper.engine_alive = lambda: 1
helper.read_rssi = lambda state=None: -55
decoded = pyOSC3.decodeOSC(helper.build_heartbeat(State(device_id=3)).getBinary())
check("heartbeat typed args with rssi", decoded == ["/hb", ",sisii", "node-uid", 3, "a1b2c3d", 1, -55], repr(decoded))
helper.read_rssi = lambda state=None: None
decoded = pyOSC3.decodeOSC(helper.build_heartbeat(State(device_id=3)).getBinary())
check("heartbeat omits unavailable rssi", decoded == ["/hb", ",sisi", "node-uid", 3, "a1b2c3d", 1], repr(decoded))
helper.engine_alive, helper.read_rssi = old_alive, old_rssi

old_dir, old_proc = helper.BOPOS_DIR, helper.PROC_DIR
with tempfile.TemporaryDirectory() as root:
    helper.BOPOS_DIR = root
    helper.PROC_DIR = os.path.join(root, "proc")
    os.makedirs(os.path.join(root, "run"))
    os.makedirs(os.path.join(helper.PROC_DIR, "42"))
    with open(os.path.join(root, "run", "pd.pid"), "w") as target:
        target.write("42\n")
    with open(os.path.join(helper.PROC_DIR, "42", "comm"), "w") as target:
        target.write("pd\n")
    check("engine alive from pidfile", helper.engine_alive() == 1)
    with open(os.path.join(root, "run", "pd.pid"), "w") as target:
        target.write("999\n")
    check("engine alive stale pidfile scans proc", helper.engine_alive() == 1)
    with open(os.path.join(helper.PROC_DIR, "42", "comm"), "w") as target:
        target.write("pd-mapper\n")  # exact match only: pkill -x pd is the contract
    check("engine not alive for pd-prefixed stranger", helper.engine_alive() == 0)
helper.BOPOS_DIR, helper.PROC_DIR = old_dir, old_proc

old_wireless = sys_wireless.WIRELESS_PROC
with tempfile.NamedTemporaryFile(mode="w", delete=False) as target:
    target.write("Inter-| sta\n face | quality\n wlp2s0: 0000 55. -61. -256\n")
    wireless_path = target.name
sys_wireless.WIRELESS_PROC = wireless_path
check("wireless None selects first interface", sys_wireless.read_wireless(None) == (-61, 55), repr(sys_wireless.read_wireless(None)))
sys_wireless.WIRELESS_PROC = old_wireless
os.unlink(wireless_path)

print()
if FAILURES:
    print("{} FAILURE(S): {}".format(len(FAILURES), FAILURES))
    sys.exit(1)
print("all checks passed")
