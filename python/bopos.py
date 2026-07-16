
import shutil
import subprocess
import re
import json


import os, sys
from time import sleep, monotonic_ns
from csv import reader
from pyOSC3 import OSCServer, OSCClient, OSCMessage, decodeOSC
from sync_node import SyncState, CueScheduler
import atexit
import glob
import socket
import threading
import uuid
import queue

from store import Store
import identity
import manifest
import fetcher
import pointfield
import relay

BOPOS_DIR = os.path.realpath(os.path.join(os.path.dirname(os.path.realpath(__file__)), ".."))
NETWORK_SYS = "/sys/class/net"
PROC_DIR = "/proc"
LED_SYS = "/sys/class/leds"

io_directory = os.path.join(BOPOS_DIR, "python", "io")
if io_directory not in sys.path:
    sys.path.append(io_directory)
try:
    import sys_wireless
except Exception:
    sys_wireless = None
try:
    import sys_i2c
except Exception:
    sys_i2c = None

server = OSCServer( ('', 7770) )
client = OSCClient()
client.connect( ('127.0.0.1', 6661) )
engine_client_lock = threading.Lock()


def send_to_engine(message):
    """Serialize access to pyOSC3's shared bopos-to-engine client."""
    with engine_client_lock:
        client.send(message)


def read_node_config(path=None):
    config = {"HB_TARGET": "255.255.255.255", "HB_RSSI": "1", "MIXER_CONTROL": None,
              "UPDATE_MODEL": "persistent", "AUDIO_CHANNELS": "2"}
    if path is None:
        path = os.path.join(BOPOS_DIR, "bopos.config")
    try:
        with open(path) as source:
            for line in source:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key, value = key.strip(), value.strip()
                if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                    value = value[1:-1]
                if key in config:
                    config[key] = value or (None if key == "MIXER_CONTROL" else config[key])
    except OSError:
        pass
    return config


def active_patch_path():
    try:
        with open(os.path.join(BOPOS_DIR, "patches", "active_patch.txt")) as source:
            name = source.read().strip()
        return os.path.join(BOPOS_DIR, "patches", name) if name else None
    except OSError:
        return None


def discover_primary_mac():
    interfaces = []
    try:
        result = subprocess.run(["ip", "route", "get", "1.1.1.1"],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode == 0:
            words = result.stdout.decode(errors="replace").split()
            if "dev" in words and words.index("dev") + 1 < len(words):
                interfaces.append(words[words.index("dev") + 1])
    except Exception:
        pass
    try:
        names = sorted(name for name in os.listdir(NETWORK_SYS) if name != "lo")
    except OSError:
        names = []
    for name in names:
        try:
            with open(os.path.join(NETWORK_SYS, name, "operstate")) as source:
                if source.read().strip() == "up" and name not in interfaces:
                    interfaces.append(name)
        except OSError:
            pass
    for name in names:
        if name not in interfaces:
            interfaces.append(name)
    for name in interfaces:
        try:
            with open(os.path.join(NETWORK_SYS, name, "address")) as source:
                value = source.read().strip()
                if value and value != "unknown":
                    return value
        except OSError:
            pass
    return None


def resolve_uid(argv=None):
    if argv is None:
        argv = sys.argv
    try:
        with open(os.path.join(BOPOS_DIR, "state", "uid")) as source:
            token = source.read().strip()
            if token:
                return token
    except OSError:
        pass
    if len(argv) > 1 and argv[1] and argv[1] != "unknown":
        return str(argv[1])
    return discover_primary_mac() or str(uuid.uuid4())


def resolve_id(uid, path=None, store=None):
    # boot resolution order (contract section 5):
    # persisted assignment -> bopos.devices seed -> unassigned
    if store is not None:
        assignment = store.get("assignment")
        if assignment:
            try:
                return int(float(assignment[0]))
            except (TypeError, ValueError):
                pass
    if path is None:
        path = os.path.join(BOPOS_DIR, "bopos.devices")
    try:
        with open(path) as source:
            for row in reader(source, skipinitialspace=True):
                if len(row) >= 3 and row[0].strip() == uid:
                    try:
                        return int(float(row[2].strip()))
                    except ValueError:
                        return -1
    except OSError:
        pass
    return -1


def resolve_elements(store):
    # element positions ride the persisted assignment (contract sec 5):
    # [id, name, x1, y1, x2, y2, ...] -- pair order is the element index
    assignment = store.get("assignment") or []
    values = []
    for value in assignment[2:]:
        try:
            values.append(float(value))
        except (TypeError, ValueError):
            return []
    return [[values[i], values[i + 1]] for i in range(0, len(values) - 1, 2)]


def resolve_version():
    try:
        result = subprocess.run(["git", "-C", BOPOS_DIR, "rev-parse", "--short", "HEAD"],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode == 0:
            version = result.stdout.decode(errors="replace").strip()
            if version:
                return version
    except Exception:
        pass
    return "unknown"


class NodeState:
    def __init__(self, argv=None):
        self.config = read_node_config()
        self.update_model = ("ephemeral" if self.config.get("UPDATE_MODEL") == "ephemeral"
                             else "persistent")
        self.store = Store(os.path.join(BOPOS_DIR, "state", "store"),
                           persistent=(self.update_model == "persistent"))
        self.uid = resolve_uid(argv)
        self.id = resolve_id(self.uid, store=self.store)
        self.version = resolve_version()
        self.mixer_control = None
        self.muted_via_stop = False
        self.elements = resolve_elements(self.store)
        self.points = {}  # current /pt field: id -> (x, y, r, f); silence = hold
        self.reports = {}
        self.reports_lock = threading.Lock()


node_state = NodeState()


def process_is(pid, name):
    try:
        with open(os.path.join(PROC_DIR, str(pid), "comm")) as source:
            return source.read().strip() == name
    except OSError:
        return False


def process_is_pd(pid):
    return process_is(pid, "pd")


def jack_alive():
    try:
        with open(os.path.join(BOPOS_DIR, "run", "jackd.pid")) as source:
            return 1 if process_is(int(source.read().strip()), "jackd") else 0
    except (OSError, ValueError):
        return 0


def expected_engine_name():
    try:
        with open(os.path.join(BOPOS_DIR, "run", "engine.name")) as source:
            name = source.read().strip()
        if name:
            return name
    except OSError:
        pass
    patch_path = active_patch_path()
    if patch_path:
        patch_manifest, _error = manifest.load(patch_path)
        if patch_manifest is not None:
            return os.path.basename(patch_manifest["engine"])
    return "pd"


def engine_alive():
    # The engine is not usable without the framework-owned JACK server. This
    # also keeps heartbeat convergence honest when PD survives a failed audio
    # backend restart.
    if jack_alive() != 1:
        return 0
    name = expected_engine_name()
    try:
        with open(os.path.join(BOPOS_DIR, "run", "engine.pid")) as source:
            if process_is(int(source.read().strip()), name):
                return 1
    except (OSError, ValueError):
        pass
    if name == "pd":
        try:
            with open(os.path.join(BOPOS_DIR, "run", "pd.pid")) as source:
                if process_is_pd(int(source.read().strip())):
                    return 1
        except (OSError, ValueError):
            pass
    for path in glob.glob(os.path.join(PROC_DIR, "[0-9]*", "comm")):
        try:
            with open(path) as source:
                if source.read().strip() == name:
                    return 1
        except OSError:
            pass
    return 0


def read_rssi(state=None):
    state = state or node_state
    if state.config.get("HB_RSSI") == "0" or sys_wireless is None:
        return None
    try:
        rssi, _quality = sys_wireless.read_wireless()
        return rssi
    except Exception:
        return None


def build_heartbeat(state=None):
    state = state or node_state
    msg = OSCMessage("/hb")
    msg.append(str(state.uid), 's')
    msg.append(int(state.id), 'i')
    msg.append(str(state.version), 's')
    msg.append(int(engine_alive()), 'i')
    rssi = read_rssi(state)
    if rssi is not None:
        msg.append(int(rssi), 'i')
    return msg


hb_wake = threading.Event()  # set() to force an immediate beat (assign ack)

fetch_queue = queue.Queue()
fetch_jobs = {}
fetch_lock = threading.Lock()
fetch_worker = None
fetch_active_key = None


def _fetched_reply(reply_socket, requester, slot, status):
    msg = OSCMessage("/os/fetched")
    msg.append(str(slot), 's')
    msg.append(str(status), 's')
    try:
        reply_socket.sendto(msg.getBinary(), (requester, 5550))
    except Exception as error:
        print("WARNING: fetch reply failed:", error)


def _fetch_progress_reply(reply_socket, requester, slot, status):
    """Report only progress states the node can observe honestly."""
    msg = OSCMessage("/os/fetch-progress")
    msg.append(str(slot), 's')
    msg.append(str(status), 's')
    try:
        reply_socket.sendto(msg.getBinary(), (requester, 5550))
    except Exception as error:
        print("WARNING: fetch progress reply failed:", error)


def _fetch_worker_loop():
    global fetch_active_key
    while True:
        key = fetch_queue.get()
        uri, slot = key
        with fetch_lock:
            fetch_active_key = key
            requesters = list(fetch_jobs.get(key, []))
        for reply_socket, requester in requesters:
            _fetch_progress_reply(reply_socket, requester, slot, "fetching")
        active_name = None
        git_managed = False
        if slot.startswith("patch:"):
            patch_name = slot[len("patch:"):]
            active_path = active_patch_path()
            active_name = os.path.basename(active_path) if active_path else None
            git_managed = os.path.lexists(
                os.path.join(BOPOS_DIR, "patches", patch_name, ".git"))
        restart_engine = (slot.startswith("patch:") and not git_managed
                          and active_name == slot[len("patch:"):])
        stopped = False
        if restart_engine:
            stopped = run_command(
                ["bash", os.path.join(BOPOS_DIR, "bash", "stop-engine.sh")]) == 0
        try:
            if git_managed:
                ok, detail = False, "refusing to fetch into a git-managed patch"
            elif restart_engine and not stopped:
                ok, detail = False, "failed to stop active patch engine"
            else:
                ok, detail = fetcher.fetch(uri, slot,
                                           os.path.join(BOPOS_DIR, "assets"),
                                           os.path.join(BOPOS_DIR, "patches"))
        except Exception as error:
            ok, detail = False, str(error)
        finally:
            if stopped:
                start_status = run_command(
                    ["bash", os.path.join(BOPOS_DIR, "bash", "start-engine.sh")],
                    wait_for_start=True)
                if start_status != 0 or engine_alive() != 1:
                    ok = False
                    detail = "{}; failed to restart active patch engine".format(detail)
        with fetch_lock:
            requesters = fetch_jobs.pop(key, [])
            fetch_active_key = None
        print("FETCH {} {}: {} ({})".format(uri, slot, "ok" if ok else "err", detail))
        for reply_socket, requester in requesters:
            _fetched_reply(reply_socket, requester, slot, "ok" if ok else "err")
        fetch_queue.task_done()


def queue_fetch(uri, slot, requester, reply_socket):
    global fetch_worker
    key = (uri, slot)
    with fetch_lock:
        if key in fetch_jobs:
            fetch_jobs[key].append((reply_socket, requester))
            status = "fetching" if fetch_active_key == key else "queued"
        else:
            fetch_jobs[key] = [(reply_socket, requester)]
            fetch_queue.put(key)
            status = "queued"
        # Emit queued before a newly started worker can emit fetching, and hold
        # the lock so a completion cannot overtake a coalesced requester's state.
        _fetch_progress_reply(reply_socket, requester, slot, status)
        if fetch_worker is None or not fetch_worker.is_alive():
            fetch_worker = threading.Thread(target=_fetch_worker_loop, daemon=True)
            fetch_worker.start()


def heartbeat_loop(state=None):
    state = state or node_state
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    while True:
        try:
            sock.sendto(build_heartbeat(state).getBinary(),
                        (state.config.get("HB_TARGET") or "255.255.255.255", 5550))
        except Exception as error:
            print("WARNING: heartbeat send failed:", error)
        hb_wake.wait(2.0 if state.id == -1 else 10.0)
        hb_wake.clear()


def selector_matches(selector, device_id):
    if selector == "all":
        return True
    try:
        return int(selector) == int(device_id) and str(selector) == str(int(selector))
    except (TypeError, ValueError):
        return False


def run_command(argv, wait_for_start=False):
    try:
        if (len(argv) >= 2 and argv[0] == "bash"
                and os.path.basename(argv[1]) == "start-engine.sh"
                and not wait_for_start):
            subprocess.Popen(argv, start_new_session=True)
            return 0
        return subprocess.run(argv).returncode
    except Exception:
        return -1


def mixer_candidates(state=None):
    state = state or node_state
    values = [state.config.get("MIXER_CONTROL"), "Master", "Digital", "PCM", "Speaker", "Headphone"]
    result = []
    for value in values:
        if value and value not in result:
            result.append(value)
    return result


def set_mute(value, state=None):
    state = state or node_state
    mute = int(value) == 1
    candidates = mixer_candidates(state)
    if state.mixer_control in candidates:
        candidates.remove(state.mixer_control)
        candidates.insert(0, state.mixer_control)
    action = "mute" if mute else "unmute"
    succeeded = False
    for control in candidates:
        if run_command(["amixer", "-q", "sset", control, action]) == 0:
            state.mixer_control = control
            succeeded = True
            break
    if mute and not succeeded:
        run_command(["bash", os.path.join(BOPOS_DIR, "bash", "stop-engine.sh")])
        state.muted_via_stop = True
    if not mute and state.muted_via_stop:
        run_command(["bash", os.path.join(BOPOS_DIR, "bash", "start-engine.sh")])
        state.muted_via_stop = False


def flash_led():
    def flash():
        for name in ("ACT", "led0"):
            directory = os.path.join(LED_SYS, name)
            if not os.path.isdir(directory):
                continue
            trigger_path = os.path.join(directory, "trigger")
            brightness_path = os.path.join(directory, "brightness")
            trigger = None
            try:
                with open(trigger_path) as source:
                    match = re.search(r"\[([^]]+)\]", source.read())
                    trigger = match.group(1) if match else None
                with open(trigger_path, "w") as target:
                    target.write("none")
            except Exception:
                pass
            for index in range(6):
                try:
                    with open(brightness_path, "w") as target:
                        target.write(str(index % 2))
                except Exception:
                    pass
                sleep(0.25)
            if trigger:
                try:
                    with open(trigger_path, "w") as target:
                        target.write(trigger)
                except Exception:
                    pass
            return
    threading.Thread(target=flash, daemon=True).start()


def identify(uid=None, state=None):
    state = state or node_state
    if uid is not None and str(uid) != state.uid:
        return False
    try:
        msg = OSCMessage("/notify")
        msg.append("identify", 's')
        send_to_engine(msg)
    except Exception:
        pass
    flash_led()
    print("IDENTIFY:", state.uid, "id", state.id)
    return True


def set_hostname(hostname):
    current_hostname = socket.gethostname()
    if current_hostname == hostname:
        return
    print(f"Hostname change: {current_hostname} -> {hostname}")
    os.system(f'sudo hostnamectl set-hostname {hostname}')
    os.system(f"sudo sed -i 's/^127.0.1.1.*/127.0.1.1   {hostname}/' /etc/hosts")
    os.system('sudo systemctl restart avahi-daemon')


def typed_append(msg, value):
    if isinstance(value, bool):
        msg.append(int(value), 'i')
    elif isinstance(value, int):
        msg.append(value, 'i')
    elif isinstance(value, float):
        msg.append(value, 'f')
    else:
        msg.append(str(value), 's')


def apply_assign(args, state=None):
    # /all/os/assign <uid> <id> <name> [posx posy pos2x pos2y]
    # idempotent full-state; only the node whose uid matches applies it
    state = state or node_state
    if len(args) < 3 or str(args[0]) != state.uid:
        return False
    try:
        new_id = int(float(args[1]))
    except (TypeError, ValueError):
        print(f"assign: bad id {args[1]!r}")
        return False
    name = str(args[2])
    # element positions: one x y pair per element, pair order = element index
    # (contract sec 5, true N -- the old fixed pos1/pos2 spelling is retired)
    positions = []
    for value in args[3:]:
        try:
            positions.append(float(value))
        except (TypeError, ValueError):
            positions = []
            break
    if len(positions) % 2:
        positions = []
    state.id = new_id
    set_hostname(name)
    msg = OSCMessage("/id")
    msg.append(new_id, 'f')
    try:
        send_to_engine(msg)
    except Exception:
        pass
    state.store.put("assignment", [new_id, name] + positions)
    state.elements = [[positions[i], positions[i + 1]]
                      for i in range(0, len(positions) - 1, 2)]
    hb_wake.set()
    print(f"ASSIGNED: id {new_id} name {name}" + (f" pos {positions}" if positions else ""))
    return True


def apply_unassign(state=None):
    """Clear the node-side assignment replica without changing its hostname."""
    state = state or node_state
    # Persist an explicit -1 tombstone rather than deleting the key: otherwise
    # boot resolution would fall through to bopos.devices and resurrect a
    # revoked seed assignment.
    assignment = state.store.get("assignment") or []
    name = str(assignment[1]) if len(assignment) > 1 else socket.gethostname()
    if not state.store.put("assignment", [-1, name]):
        return False
    state.id = -1
    state.elements = []
    msg = OSCMessage("/id")
    msg.append(-1, 'f')
    try:
        send_to_engine(msg)
    except Exception:
        pass
    hb_wake.set()
    print(f"UNASSIGNED: {state.uid}")
    return True


def apply_points(parts, args, state=None):
    # /pt plane (contract sec 4.1): selector-less broadcast geometry, like
    # /cue. Helper owns the proximity math; the engine sees only shaped
    # scalars as /pt <pointId> <element> <v> on 6661 (element 0-based, pair
    # order from the assignment). A removed point releases with one v=0.
    state = state or node_state
    parsed = pointfield.parse_wire(parts, args)
    if parsed is None:
        return False
    kind, payload = parsed
    if kind == "frame":
        removed = set(state.points) - set(payload)
        state.points = payload
        changed = payload
    elif kind == "set":
        point_id, point = payload
        state.points[point_id] = point
        removed = set()
        changed = {point_id: point}
    else:  # clear
        removed = {payload} if payload in state.points else set()
        state.points.pop(payload, None)
        changed = {}
    if not state.elements:
        return True
    entries = pointfield.decompose(changed, state.elements)
    for point_id in sorted(removed):
        for index in range(len(state.elements)):
            entries.append((point_id, index, 0.0))
    for point_id, element, value in entries:
        msg = OSCMessage("/pt")
        msg.append(int(point_id), 'i')
        msg.append(int(element), 'i')
        msg.append(float(value), 'f')
        try:
            send_to_engine(msg)
        except Exception as error:
            print("WARNING: point send to engine failed:", error)
            break
    return True


def relay_provided_term(address, args):
    """Deliver a selector-stripped full-state value to a non-PD engine."""
    msg = OSCMessage(address)
    for value in args:
        typed_append(msg, value)
    try:
        send_to_engine(msg)
        return True
    except Exception as error:
        print("WARNING: provided-term send to engine failed:", error)
        return False


admin_lock = threading.Lock()


def rev_reply(reply_socket, requester, state=None):
    # /os/rev <sha> <model> <uid> -- attributable convergence (v1.5, sec 7).
    state = state or node_state
    state.version = resolve_version()
    msg = OSCMessage("/os/rev")
    msg.append(str(state.version), 's')
    msg.append(str(state.update_model), 's')
    msg.append(str(state.uid), 's')
    try:
        reply_socket.sendto(msg.getBinary(), (requester, 5550))
    except Exception as error:
        print("WARNING: rev reply failed:", error)


def installed_patches():
    """Return the stable, declared patch-listing shape from contract section 7."""
    patches_dir = os.path.join(BOPOS_DIR, "patches")
    active_path = active_patch_path()
    active_name = os.path.basename(active_path) if active_path else None
    result = []
    try:
        names = sorted(os.listdir(patches_dir))
    except OSError:
        names = []
    for name in names:
        # Listing includes git-installed repo names accepted by /os/addpatch,
        # including dots; only hidden/control entries are framework-owned.
        if name.startswith("."):
            continue
        patch_path = os.path.join(patches_dir, name)
        if not os.path.isdir(patch_path):
            continue
        patch_manifest, _error = manifest.load(patch_path)
        entry = {
            "name": name,
            "active": name == active_name,
            "git": os.path.lexists(os.path.join(patch_path, ".git")),
            "manifest": patch_manifest is not None,
        }
        try:
            # same walker as the host catalog (contract sec 7, v1.4); the
            # stat-signature cache keeps repeat listings cheap on a Zero
            entry["fingerprint"] = identity.fingerprint(patch_path)
        except OSError:
            pass  # unreadable content: honest listing without an identity
        result.append(entry)
    return result


def run_admin_verb(callback, args, state, reply_socket=None, requester=None):
    # serialized so two provisioning verbs can't interleave in one git tree
    with admin_lock:
        try:
            callback('', '', [str(value) for value in args], '')
        except Exception as error:
            print("WARNING: admin verb failed:", error)
        if reply_socket is not None:
            # after convergence, so the sha is the post-action one
            rev_reply(reply_socket, requester, state)


def report_reply(reply_socket, requester, state=None):
    state = state or node_state
    patch_path = active_patch_path()
    patch_name = os.path.basename(patch_path) if patch_path else "none"
    patch_manifest = None
    if patch_path:
        patch_manifest, _error = manifest.load(patch_path)
    engine = None
    try:
        with open(os.path.join(BOPOS_DIR, "run", "engine.name")) as source_file:
            engine = source_file.read().strip() or None
    except OSError:
        pass
    if engine is None and patch_manifest is not None:
        engine = patch_manifest["engine"]
    try:
        has_i2c = bool(sys_i2c.have_bus()) if sys_i2c is not None else False
    except Exception:
        has_i2c = False
    try:
        with open(os.path.join(PROC_DIR, "net", "wireless")) as source_file:
            has_wifi = len(source_file.readlines()) > 2
    except OSError:
        has_wifi = False
    try:
        audio_channels = int(state.config.get("AUDIO_CHANNELS"))
    except Exception:
        audio_channels = 2
    try:
        with open(os.path.join(PROC_DIR, "uptime")) as source_file:
            uptime = int(float(source_file.read().split()[0]))
    except Exception:
        uptime = 0
    report = {
        "uid": state.uid,
        "hostname": socket.gethostname(),
        "engine": engine or "pd",
        "has_i2c": has_i2c,
        "has_wifi": has_wifi,
        "audio_channels": audio_channels,
        "screen": patch_manifest is not None and "screen" in patch_manifest.get("caps", []),
        "patch": patch_name,
        "uptime": uptime,
        "git_rev": state.version,
        "update_model": state.update_model,
        "contract_version": "1.5",
    }
    msg = OSCMessage("/os/report")
    msg.append(json.dumps(report), 's')
    reply_socket.sendto(msg.getBinary(), (requester, 5550))
    return True


def dispatch_admin_verb(member, args, state, reply_socket, requester):
    if member in LIFECYCLE_VERBS:
        # lifecycle cannot reply after executing -- reply first (contract sec 7)
        rev_reply(reply_socket, requester, state)
        threading.Thread(target=run_admin_verb,
                         args=(LIFECYCLE_VERBS[member], args, state),
                         daemon=True).start()
        return True
    if member in PROVISION_VERBS:
        if state.update_model != "persistent":
            # ephemeral: the convergence assertion is an honest no-op (sec 7)
            rev_reply(reply_socket, requester, state)
            return True
        threading.Thread(target=run_admin_verb,
                         args=(PROVISION_VERBS[member], args, state,
                               reply_socket, requester),
                         daemon=True).start()
        return True
    return False


UID_ADMIN_VERBS = frozenset({
    "identify", "report", "reboot", "shutdown", "restart-engine",
    "updatebopos", "unassign",
})


def dispatch_uid_admin(member, args, state, reply_socket, requester):
    """Dispatch the exact ratified UID envelope allowlist, all zero-arity."""
    if member not in UID_ADMIN_VERBS or args:
        return False
    if member == "identify":
        return identify(state=state)
    if member == "report":
        return report_reply(reply_socket, requester, state)
    if member == "unassign":
        return apply_unassign(state)
    return dispatch_admin_verb(member, args, state, reply_socket, requester)


def handle_lan_datagram(datagram, source, reply_socket, state=None):
    state = state or node_state
    try:
        decoded = decodeOSC(datagram)
    except Exception:
        return False
    if len(decoded) < 2:
        return False
    parts = [part for part in str(decoded[0]).split("/") if part]
    args = decoded[2:]
    # Relay provided terms to every engine on the common selector-stripped
    # localhost surface; the address shaping is shared with the audition rig.
    if len(parts) >= 3 and selector_matches(parts[0], state.id):
        shaped = relay.shape_provided_term(parts, args)
        if shaped is not None:
            return relay_provided_term(*shaped)
    # clock-sync plane (contract sec 3.1): ping/cue omit the selector (always
    # fleet-wide), offset is per-device. Handled before the /os gate below.
    if parts == ["sync", "ping"] and len(args) >= 2:
        # pong unicast to the leader, echoing seq+leaderTime; deviceTime is our
        # own monotonic clock -- never wall clock (NTP steps must not glitch cues)
        msg = OSCMessage("/sync/pong")
        msg.append(int(args[0]), 'i')
        msg.append(str(args[1]), 's')
        msg.append(str(state.uid), 's')
        msg.append(str(monotonic_ns()), 's')
        reply_socket.sendto(msg.getBinary(), (source[0], 5550))
        return True
    if parts and parts[0] == "pt":
        return apply_points(parts, args, state)
    if parts == ["cue"] and len(args) >= 2:
        try:
            cue_scheduler.schedule(int(str(args[1])), str(args[0]))
        except (TypeError, ValueError):
            pass
        return True
    if (len(parts) == 3 and parts[1] == "sync" and parts[2] == "offset"
            and args and selector_matches(parts[0], state.id)):
        try:
            sync_state.push(int(str(args[0])))
        except (TypeError, ValueError):
            pass
        return True
    if parts == ["all", "os", "to"]:
        if len(args) < 2:
            return False
        if str(args[0]) != state.uid:
            return True
        return dispatch_uid_admin(str(args[1]), list(args[2:]), state,
                                  reply_socket, source[0])
    if len(parts) != 3 or parts[1] != "os" or not selector_matches(parts[0], state.id):
        return False
    if parts[2] == "assign":
        return apply_assign(args, state)
    if parts[2] == "store" and args:
        return state.store.put(str(args[0]), list(args[1:]))
    if parts[2] == "load" and args:
        msg = OSCMessage("/os/load")
        msg.append(str(args[0]), 's')
        for value in state.store.get(str(args[0])):
            typed_append(msg, value)
        reply_socket.sendto(msg.getBinary(), (source[0], 5550))
        return True
    if parts[2] == "params":
        msg = OSCMessage("/os/params")
        patch_path = active_patch_path()
        text = manifest.raw(patch_path) if patch_path else None
        if text is not None:
            msg.append(text, 's')
        reply_socket.sendto(msg.getBinary(), (source[0], 5550))
        return True
    if parts[2] == "fetch":
        if len(args) < 2:
            _fetched_reply(reply_socket, source[0], str(args[1]) if len(args) > 1 else "", "err")
            return True
        uri, slot = str(args[0]), str(args[1])
        asset_slot = re.fullmatch(r"[A-Za-z0-9_-]+", slot)
        patch_slot = re.fullmatch(r"patch:[A-Za-z0-9_-]+", slot)
        if asset_slot is None and patch_slot is None:
            _fetched_reply(reply_socket, source[0], slot, "err")
            return True
        queue_fetch(uri, slot, source[0], reply_socket)
        return True
    if parts[2] == "patches":
        msg = OSCMessage("/os/patches")
        msg.append(json.dumps(installed_patches(), separators=(",", ":")), 's')
        reply_socket.sendto(msg.getBinary(), (source[0], 5550))
        return True
    if parts[2] == "report":
        return report_reply(reply_socket, source[0], state)
    if parts[2] == "ping" and args:
        msg = OSCMessage("/os/pong")
        tag = decoded[1][1:2] if str(decoded[1]).startswith(",") else str(decoded[1])[:1]
        msg.append(args[0], tag or None)
        msg.append(str(state.uid), 's')
        reply_socket.sendto(msg.getBinary(), (source[0], 5550))
        return True
    if parts[2] == "identify":
        identify(args[0] if args else None, state)
        return True
    if parts[2] == "probe" and args:
        what = str(args[0])
        with state.reports_lock:
            values = state.reports.get(what)
        if values is None:
            values = {
                "id": (int(state.id),),
                "uid": (str(state.uid),),
                "version": (str(state.version),),
                "update_model": (str(state.update_model),),
            }.get(what)
        if values is None:
            return True
        msg = OSCMessage("/os/probe")
        msg.append(int(state.id), 'i')
        msg.append(what, 's')
        for value in values:
            typed_append(msg, value)
        reply_socket.sendto(msg.getBinary(), (source[0], 5550))
        return True
    if parts[2] == "mute" and args:
        try:
            if int(args[0]) in (0, 1):
                set_mute(int(args[0]), state)
                return True
        except (TypeError, ValueError):
            pass
    return dispatch_admin_verb(parts[2], args, state, reply_socket, source[0])


def lan_listener_loop(state=None):
    state = state or node_state
    while True:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if hasattr(socket, "SO_REUSEPORT"):
                try:
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
                except OSError:
                    pass
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.bind(("", 6660))
        except OSError as error:
            print("WARNING: CANNOT BIND LAN OSC PORT 6660; RETRYING IN 30 SECONDS:", error)
            sock.close()
            sleep(30)
            continue
        while True:
            try:
                datagram, source = sock.recvfrom(65535)
                handle_lan_datagram(datagram, source, sock, state)
            except OSError as error:
                print("WARNING: LAN OSC LISTENER FAILED; REBINDING:", error)
                sock.close()
                break


def config_callback(path='', tags='', args='', source=''):
    config_file = os.path.join(BOPOS_DIR, "bopos.devices")
    print("loading: ", config_file)
    try:
        read_obj = open(config_file, 'r')
    except OSError:
        print('MAC address not found in bopos.devices.csv')
    else:
        with read_obj:
            csv_reader = reader(read_obj, skipinitialspace=True)
            macfound = False
            for row in csv_reader:
                if len(row) >= 3 and row[0].strip() == node_state.uid:
                    print('MAC address found in bopos.devices')
                    macfound = True
                    set_hostname(row[1].strip())
                    # NodeState already resolved persistence -> seed ->
                    # unassigned at boot. The CSV remains a hostname seed,
                    # never an authority that overwrites a dashboard assignment.
                    print('resolved ID is ' + str(node_state.id))
                    break
            if not macfound:
                print('MAC address not found in bopos.devices.csv')
    # Every engine asks /config after opening port 6661. Always return the
    # authoritative resolved identity, including when no CSV exists.
    msg = OSCMessage("/id")
    msg.append(node_state.id, 'i')
    send_to_engine(msg)


def update_bopos_callback(path='', tags='', args='', source=''):
    update_script = os.path.join(BOPOS_DIR, "bash/update.sh")
    msg = OSCMessage("/notify")
    msg.append("updatebopos", 's')
    send_to_engine(msg)
    print("UPDATE BOPOS!")
    os.system(update_script)

def request_power_action(action):
    status = run_command(["/usr/bin/sudo", "-n", "/usr/bin/systemctl", action])
    if status != 0:
        print("ERROR: {} authorization failed; install systemd/bopos-power.sudoers".format(action))
        return False
    return True


def shutdown_callback(path='', tags='', args='', source=''):
    msg = OSCMessage("/notify")
    msg.append("shutdown", 's')
    send_to_engine(msg)
    print("SHUTDOWN!")
    return request_power_action("poweroff")

def reboot_callback(path='', tags='', args='', source=''):
    msg = OSCMessage("/notify")
    msg.append("reboot", 's')
    send_to_engine(msg)
    print("REBOOTING")
    return request_power_action("reboot")

def checkout_callback(path, tags, args, source):
    msg = OSCMessage("/notify")
    msg.append("checkout", 's')
    send_to_engine(msg)
    branch = args[0].lstrip('/')
    print("checking out: " + branch)
    os.system(os.path.join(BOPOS_DIR, "bash/checkout.sh ") + branch)
    msg = OSCMessage("/notify")
    msg.append("updatebopos", 's')
    send_to_engine(msg)
    print("UPDATE!")
    os.system(os.path.join(BOPOS_DIR, "bash/update.sh"))

def switch_patch_callback(path='', tags='', args='', source=''):
    patches_dir = os.path.join(BOPOS_DIR, 'patches')
    active_patch_file = os.path.realpath(os.path.join(patches_dir, 'active_patch.txt'))
    if not args or not args[0]:
        print("No patch name provided to /patch")
        return
    patch_name = args[0].strip()
    if (patch_name.startswith(".")
            or re.fullmatch(r"[A-Za-z0-9_.-]+", patch_name) is None):
        print("Invalid patch name for /patch")
        return
    patch_path = os.path.join(patches_dir, patch_name)
    patch_manifest, _error = manifest.load(patch_path)
    if not os.path.isdir(patch_path) or patch_manifest is None:
        print(f"Patch '{patch_name}' not found or has no valid bopos.patch.json")
        return
    current = open(active_patch_file).read().strip() if os.path.exists(active_patch_file) else None
    print(f"Switching patch: {current} -> {patch_name}")

    def select(name):
        temporary = active_patch_file + ".tmp"
        try:
            with open(temporary, 'w') as target:
                target.write(name + '\n')
            os.replace(temporary, active_patch_file)
            return True
        except Exception as error:
            print(f"Failed to write active_patch.txt: {error}")
            try:
                os.remove(temporary)
            except OSError:
                pass
            return False

    # Updating an inactive target need not interrupt the currently playing
    # engine. Host-mirrored patches have already converged through /os/fetch.
    if os.path.isdir(os.path.join(patch_path, '.git')):
        print(f"Pulling latest for {patch_name}...")
        try:
            result = subprocess.run(["git", "pull", "--recurse-submodules"], cwd=patch_path,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
            print(result.stdout.decode())
            if result.returncode != 0:
                print(f"git pull failed: {result.stderr.decode()}")
        except Exception as error:
            print(f"git pull failed: {error}")

    stop_script = os.path.join(BOPOS_DIR, "bash", "stop-engine.sh")
    start_script = os.path.join(BOPOS_DIR, "bash", "start-engine.sh")
    if run_command(["bash", stop_script]) != 0:
        print("Patch switch aborted: failed to stop current engine")
        return False
    hb_wake.set()
    if not select(patch_name):
        run_command(["bash", start_script], wait_for_start=True)
        hb_wake.set()
        return False
    if run_command(["bash", start_script], wait_for_start=True) == 0 and engine_alive() == 1:
        print(f"Patch switch complete: {patch_name}")
        hb_wake.set()
        return True

    print(f"Patch switch failed to start {patch_name}; restoring {current}")
    run_command(["bash", stop_script])
    if current and select(current):
        run_command(["bash", start_script], wait_for_start=True)
    hb_wake.set()
    return False


def add_patch_callback(path='', tags='', args='', source=''):
    patches_dir = os.path.join(BOPOS_DIR, 'patches')
    if not args or len(args) < 2:
        print("/addpatch requires two arguments: user and repo")
        return
    user, repo = str(args[0]).strip(), str(args[1]).strip()
    if not re.match(r'^[\w-]+$', user) or not re.match(r'^[\w.-]+$', repo):
        print("Invalid user or repo")
        return
    repo_url, dest_dir = f"https://github.com/{user}/{repo}.git", os.path.join(patches_dir, repo)
    try:
        result = subprocess.run(["git", "ls-remote", repo_url], stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, timeout=10)
        if result.returncode != 0:
            print(f"GitHub repo not found or not accessible: {repo_url}")
            return
    except Exception as error:
        print(f"Error checking repo: {error}")
        return
    if os.path.isdir(dest_dir):
        try:
            print(f"Removing existing patch folder: {dest_dir}")
            shutil.rmtree(dest_dir)
        except Exception as error:
            print(f"Failed to remove existing patch folder: {error}")
            return
    try:
        print(f"Cloning {repo_url} into {dest_dir}...")
        result = subprocess.run(["git", "clone", "--recursive", repo_url, dest_dir],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
        if result.returncode != 0:
            print(f"Failed to clone repo: {result.stderr.decode().strip()}")
            return
        print(f"Cloned {repo_url} into {dest_dir}")
    except subprocess.TimeoutExpired:
        print("Clone timed out after 120s — check network connection")
        return
    except Exception as error:
        print(f"Error cloning repo: {error}")
        return
    _patch_manifest, manifest_error = manifest.load(dest_dir)
    if _patch_manifest is None:
        print(f"Warning: cloned patch '{repo}' will not launch: {manifest_error}")
    try:
        msg = OSCMessage("/addpatch")
        msg.append(repo)
        send_to_engine(msg)
    except Exception as error:
        print(f"Failed to send OSC confirmation: {error}")

def pull_active_patch_callback(path='', tags='', args='', source=''):
    script_path = os.path.join(BOPOS_DIR, 'bash/pull_active_patch.sh')
    print(f"Running: {script_path}")
    try:
        result = subprocess.run(["bash", script_path], timeout=120)
        if result.returncode != 0:
            print(f"pull_active_patch.sh exited with code {result.returncode}")
    except Exception as error:
        print(f"[pull_active_patch_callback] Exception: {error}")


def drop_patch_callback(path='', tags='', args='', source=''):
    if (not args or str(args[0]).startswith(".")
            or re.fullmatch(r"[A-Za-z0-9_.-]+", str(args[0])) is None):
        print("/droppatch requires a valid patch name")
        return
    name = str(args[0])
    active_path = active_patch_path()
    if active_path is not None and os.path.basename(active_path) == name:
        print("Refusing to remove active patch '{}'".format(name))
        return
    target = os.path.join(BOPOS_DIR, "patches", name)
    try:
        if os.path.islink(target) or os.path.isfile(target):
            os.remove(target)
        elif os.path.isdir(target):
            shutil.rmtree(target)
        print("Dropped patch '{}'".format(name))
    except OSError as error:
        print("Failed to drop patch '{}': {}".format(name, error))


def drop_assets_callback(path='', tags='', args='', source=''):
    if not args or re.fullmatch(r"[A-Za-z0-9_-]+", str(args[0])) is None:
        print("/dropassets requires a valid asset slot")
        return
    slot = str(args[0])
    target = os.path.join(BOPOS_DIR, "assets", slot)
    try:
        if os.path.islink(target) or os.path.isfile(target):
            os.remove(target)
        elif os.path.isdir(target):
            shutil.rmtree(target)
        print("Dropped asset slot '{}'".format(slot))
    except OSError as error:
        print("Failed to drop asset slot '{}': {}".format(slot, error))


def restart_engine_callback(path='', tags='', args='', source=''):
    stop_script = os.path.join(BOPOS_DIR, "bash/stop-engine.sh")
    start_script = os.path.join(BOPOS_DIR, "bash/start-engine.sh")
    msg = OSCMessage("/notify")
    msg.append("restart-engine", 's')
    send_to_engine(msg)
    print("RESTARTING ENGINE")
    subprocess.Popen(["bash", "-c", '"$1" && exec "$2"', "restart-engine", stop_script, start_script],
                     start_new_session=True)


def store_callback(path='', tags='', args='', source=''):
    # engine-side persistence: PD routes `store <key> <values...>` here
    if args:
        node_state.store.put(str(args[0]), list(args[1:]))


def load_callback(path='', tags='', args='', source=''):
    # reply goes to PD on 6661 as /load <key> <values...>
    if not args:
        return
    msg = OSCMessage("/load")
    msg.append(str(args[0]), 's')
    for value in node_state.store.get(str(args[0])):
        typed_append(msg, value)
    try:
        send_to_engine(msg)
    except Exception as error:
        print(f"load: could not reply to engine: {error}")


def report_callback(path='', tags='', args='', source=''):
    if len(args) < 2 or re.fullmatch(r"[A-Za-z0-9_-]+", str(args[0])) is None:
        return
    with node_state.reports_lock:
        node_state.reports[str(args[0])] = tuple(args[1:])


# /os/* admin verbs on the 6660 LAN listener call these implementation
# functions directly. Engines cannot issue administrative commands.
LIFECYCLE_VERBS = {
    "reboot": reboot_callback,
    "shutdown": shutdown_callback,
    "restart-engine": restart_engine_callback,
}
PROVISION_VERBS = {
    "updatebopos": update_bopos_callback,
    "checkout": checkout_callback,
    "patch": switch_patch_callback,
    "addpatch": add_patch_callback,
    "pullpatch": pull_active_patch_callback,
    "droppatch": drop_patch_callback,
    "dropassets": drop_assets_callback,
}


def fire_cue_to_engine(cue_id):
    # at the local deadline, the engine sees only the bare cue -- absolute time
    # never enters PD (contract sec 12). PD's patch owns the /cue receiver.
    msg = OSCMessage("/cue")
    typed_append(msg, cue_id)
    try:
        send_to_engine(msg)
    except Exception as error:
        print(f"cue: could not fire to engine: {error}")


sync_state = SyncState()
cue_scheduler = CueScheduler(sync_state, fire_cue_to_engine)


def exit_handler():
    print("exiting.  closing server...")
    server.close()


server.addMsgHandler( "/config", config_callback )
server.addMsgHandler( "/store", store_callback )
server.addMsgHandler( "/load", load_callback )
server.addMsgHandler( "/report", report_callback )

atexit.register(exit_handler)

if __name__ == "__main__":
    server.timeout = 1.0
    cue_scheduler.start()
    threading.Thread(target=heartbeat_loop, daemon=True).start()
    threading.Thread(target=lan_listener_loop, daemon=True).start()
    while True:
        server.handle_request()
