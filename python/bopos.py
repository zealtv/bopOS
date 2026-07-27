
import shutil
import subprocess
import re
import json
import signal
import shlex


import os, sys
from time import sleep, monotonic_ns
from csv import reader
from pyOSC3 import OSCServer, OSCClient, OSCMessage, OSCError, decodeOSC
from sync_node import SyncState, EventScheduler
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
import groups as group_protocol
import paramgen
import asset_slots
import audio_config
import log_config
import nodelog

BOPOS_DIR = os.path.realpath(os.path.join(os.path.dirname(os.path.realpath(__file__)), ".."))
ASSETS_ROOT = os.path.join(BOPOS_DIR, "assets")
NETWORK_SYS = "/sys/class/net"
PROC_DIR = "/proc"
LED_SYS = "/sys/class/leds"
HOSTNAME_RE = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?")
HOSTNAME_HELPER = "/usr/local/sbin/bopos-set-hostname"

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


_engine_send_warned_at = 0  # monotonic_ns of the last dropped-send warning


def send_to_engine(message):
    """Serialize access to pyOSC3's shared bopos-to-engine client.

    The engine's localhost port (6661) is closed during the window between
    bopos.py binding the LAN listener and Pure Data opening its port, and again
    whenever the engine restarts. A send in that window raises
    ConnectionRefusedError (Errno 111). That must never escape into a caller:
    ConnectionRefusedError is an OSError, and an unwrapped raise inside a LAN
    handler propagated up to lan_listener_loop, whose `except OSError` mistook
    it for a *listener* failure and tore the LAN socket down mid-startup -- so a
    freshly-flashed node went unresponsive in the Dashboard while SSH stayed up.
    Swallow connection-level errors here (returning False) so no call site can
    leak them; deliver_engine_context redelivers durable state once the port is
    open again (see heartbeat_loop). Returns True iff the datagram was sent.

    Note: pyOSC3's OSCClient.send catches the socket error and re-raises it
    wrapped in OSCClientError, which is *not* an OSError -- so `except OSError`
    alone never caught the refusal on a real Pi (only in tests that faked a raw
    ConnectionRefusedError). We must catch pyOSC3's OSCError base too, or the
    refusal escapes and kills whatever thread issued the send (it killed the
    heartbeat thread via deliver_engine_context on a cold boot).
    """
    global _engine_send_warned_at
    with engine_client_lock:
        try:
            client.send(message)
            return True
        except (OSError, OSCError) as error:
            now = monotonic_ns()
            if now - _engine_send_warned_at > 5_000_000_000:
                print("WARNING: engine send dropped (engine not ready?):", error)
                _engine_send_warned_at = now
            return False


def read_node_config(path=None):
    config = {"HB_TARGET": "255.255.255.255", "HB_RSSI": "1", "MIXER_CONTROL": None,
              "SOUNDCARD": None, "UPDATE_MODEL": "persistent", "AUDIO_CHANNELS": "2",
              "JACK_SAMPLE_RATE": "44100", "JACK_PERIOD_SIZE": "512",
              "JACK_NPERIODS": "2", "LOG_DESTINATION": "internal"}
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
                try:
                    parsed = shlex.split(value, comments=True, posix=True)
                    value = parsed[0] if len(parsed) == 1 else value
                except ValueError:
                    pass
                if key in config:
                    config[key] = value or (None if key in ("MIXER_CONTROL", "SOUNDCARD")
                                            else config[key])
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
        stored_enabled = self.store.get("device_enabled")
        if stored_enabled and stored_enabled[0] in (0, 1, False, True):
            self.device_enabled = bool(stored_enabled[0])
        else:
            legacy_muted = self.store.get("device_muted")
            self.device_enabled = not bool(
                legacy_muted and legacy_muted[0] in (1, True))
            if self.store.put("device_enabled", [int(self.device_enabled)]):
                self.store.delete("device_muted")
        self.mute_all = False
        self.elements = resolve_elements(self.store)
        self.groups = group_protocol.stored_group_ids(self.store.get("groups"))
        self.points = {}  # current /pt field: id -> (x, y, r, f); silence = hold
        self.reports = {}
        self.reports_lock = threading.Lock()
        self.audio_status = "active"
        self.audio_error = None


node_state = NodeState()

# The log facility resolves its destination per entry from the live node
# config, so a `usb` choice follows a hot-inserted stick and falls back to
# internal when it is absent -- no restart, no dropped entries (contract
# sec 4.2 /log; log-destination design .loom/tied/1-logging-seed-design/ §3).
nodelog.configure(lambda: log_config.effective_dir(node_state.config))


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
    context_delivered = False
    while True:
        alive = engine_alive()
        if alive == 1:
            # The engine is (newly) ready: redeliver durable context that may
            # have been sent (and dropped) while its port was still closed.
            # engine_alive() can lead PD actually binding its port, so retry on
            # later beats until the redelivery is accepted -- never let a refusal
            # escape this loop (that killed the heartbeat thread on a cold boot).
            if not context_delivered:
                context_delivered = deliver_engine_context(state)
        else:
            context_delivered = False
        try:
            sock.sendto(build_heartbeat(state).getBinary(),
                        (state.config.get("HB_TARGET") or "255.255.255.255", 5550))
        except Exception as error:
            print("WARNING: heartbeat send failed:", error)
        hb_wake.wait(2.0 if state.id == -1 else 10.0)
        hb_wake.clear()


def selector_matches(selector, device_id, memberships=()):
    return group_protocol.selector_matches(selector, device_id, memberships)


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


# ALSA playback-switch control names we know how to toggle, DAC-specific first.
# DigiAMP+/pcm512x DACs expose "Digital"; generic/onboard cards use the rest.
KNOWN_MIXER_CONTROLS = ("Digital", "Master", "PCM", "Speaker", "Headphone", "Analogue")


def _alsa_card_ids():
    """ALSA card id strings in index order, e.g. ['vc4hdmi', 'DigiAMP']."""
    ids = []
    try:
        with open("/proc/asound/cards") as source:
            for line in source:
                match = re.match(r"\s*\d+\s+\[(\S+)\s*\]", line)
                if match:
                    ids.append(match.group(1))
    except OSError:
        pass
    return ids


def _is_hdmi_card(card_id):
    lowered = card_id.lower()
    return "hdmi" in lowered or "vc4" in lowered


def mute_targets(state=None):
    """(card, control) pairs to try for amixer mute, best first.

    A configured SOUNDCARD/MIXER_CONTROL wins; otherwise the DAC is auto-detected
    by skipping HDMI cards (a fresh Pi's default card is the HDMI device, not the
    DAC -- the root of the mute bug). `card` is an ALSA id passed to `amixer -c`;
    None means the default card.
    """
    state = state or node_state
    configured_card = state.config.get("SOUNDCARD") or None
    configured_control = state.config.get("MIXER_CONTROL") or None
    targets = []

    def add(card, control):
        pair = (card, control)
        if control and pair not in targets:
            targets.append(pair)

    # A previously-successful pair is retried first.
    if isinstance(state.mixer_control, tuple):
        add(*state.mixer_control)
    # Explicit configuration (from bopos.config).
    if configured_card or configured_control:
        add(configured_card, configured_control)
        for name in KNOWN_MIXER_CONTROLS:
            add(configured_card, name)
    # Auto-detect: every non-HDMI card, DAC-specific control names first.
    for card_id in _alsa_card_ids():
        if not _is_hdmi_card(card_id):
            for name in KNOWN_MIXER_CONTROLS:
                add(card_id, name)
    # Last resort: the default card with generic names.
    for name in KNOWN_MIXER_CONTROLS:
        add(None, name)
    return targets


def enforce_mute(value, state=None):
    """Mute/unmute via the sound card's mixer, targeting the DAC exactly.

    If no working mixer control is found the mute simply fails -- we never stop
    the engine as a fallback (Bob, 2026-07-23: node-bug fix). A mute must never
    kill audio playback; a node can be shut down if hard silence is required.
    """
    state = state or node_state
    action = "mute" if int(value) == 1 else "unmute"
    for card, control in mute_targets(state):
        argv = ["amixer", "-q"]
        if card:
            argv += ["-c", card]
        argv += ["sset", control, action]
        if run_command(argv) == 0:
            state.mixer_control = (card, control)
            return True
    return False


def output_enabled(state=None):
    state = state or node_state
    return bool(getattr(state, "device_enabled", True)
                and not getattr(state, "mute_all", False))


def set_mute(value, state=None):
    """Apply execution MUTE ALL without changing persistent Device enabled."""
    state = state or node_state
    state.mute_all = int(value) == 1
    return enforce_mute(not output_enabled(state), state)


def set_device_enabled(value, reply_socket, requester, state=None):
    """Persist and acknowledge one exact physical Device enabled state."""
    state = state or node_state
    try:
        value = int(value)
    except (TypeError, ValueError):
        return False
    if value not in (0, 1) or not state.store.put("device_enabled", [value]):
        return False
    state.device_enabled = bool(value)
    if not enforce_mute(not output_enabled(state), state):
        return False
    msg = OSCMessage("/os/enabled")
    msg.append(str(state.uid), 's')
    msg.append(value, 'i')
    msg.append(int(output_enabled(state)), 'i')
    reply_socket.sendto(msg.getBinary(), (requester, 5550))
    return True


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


def set_device_hostname(hostname, reply_socket, requester, state=None):
    """Apply one validated exact-UID hostname and return a terminal receipt."""
    state = state or node_state
    hostname = str(hostname)
    if HOSTNAME_RE.fullmatch(hostname) is None:
        return False
    status = "ok"
    if socket.gethostname() != hostname:
        try:
            completed = subprocess.run(
                ["sudo", "-n", HOSTNAME_HELPER, hostname],
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL, timeout=20, check=False)
            status = "ok" if completed.returncode == 0 else "err"
        except (OSError, subprocess.TimeoutExpired):
            status = "err"
    msg = OSCMessage("/os/hostname")
    msg.append(str(state.uid), 's')
    msg.append(hostname, 's')
    msg.append(status, 's')
    reply_socket.sendto(msg.getBinary(), (requester, 5550))
    if status == "ok":
        hb_wake.set()
    return True


def send_groups_to_engine(state=None):
    """Push the node's current Seat-group membership to the live engine.

    Engine group-context amendment (2026-07-20): a full, sentinel-shaped
    list on every successful membership change, mirroring the launch
    delivery in runcontext.py/start-engine.sh. Callers only invoke this
    after durably committing the new membership, so a rejected or
    failed-to-persist change never reaches here.
    """
    state = state or node_state
    msg = OSCMessage("/groups")
    for group_id in group_protocol.wire_groups(state.groups):
        msg.append(group_id, 'i')
    try:
        send_to_engine(msg)
    except Exception as error:
        print("WARNING: groups send to engine failed:", error)


# --- engine-ready replay boundary -------------------------------------------
# Durable authoritative state the node owns and must (re)deliver once the engine
# opens its port: the Seat id, Seat-group memberships, and the latest *static*
# value of each live parameter. Transient traffic (cues, points) and running
# automation generators (fade/loop/lfo -- forgotten by design across restarts,
# per the parameter-automation ratification) are never buffered or replayed.
param_replay_lock = threading.Lock()
latest_static_params = {}  # canonical param identity -> (ParamSpec, declaration)


def record_static_param(identity_str, spec, declaration):
    """Remember the latest static ('set') value of a param for engine-ready replay."""
    if getattr(spec, "kind", None) != "set":
        # A non-static spec supersedes any stored static value: once a param is
        # being driven by a generator (or explicitly stopped), a stale 'set'
        # must not be replayed over it.
        with param_replay_lock:
            latest_static_params.pop(identity_str, None)
        return
    with param_replay_lock:
        latest_static_params[identity_str] = (spec, declaration)


def deliver_engine_context(state=None):
    """Redeliver id, groups, and latest static params to a freshly-ready engine.

    Idempotent full-state: harmless on the normal launch path (the engine also
    pulls /id via /config and gets launch-time run context), essential when the
    Dashboard mutated assignment/groups/params during the window the engine port
    was closed and those sends were dropped.
    """
    state = state or node_state
    msg = OSCMessage("/id")
    msg.append(state.id, 'i')
    # engine_alive() goes true on pid+JACK, which can be a beat before Pure Data
    # actually binds its OSC port -- so this first send may still be refused.
    # Report that so heartbeat_loop retries rather than dropping the redelivery.
    if not send_to_engine(msg):
        return False
    send_groups_to_engine(state)
    with param_replay_lock:
        pending = list(latest_static_params.items())
    for identity_str, (spec, declaration) in pending:
        try:
            param_generator.apply(identity_str, spec, declaration)
        except Exception as error:
            print("WARNING: param replay failed for", identity_str, ":", error)
    return True


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
    if not 0 <= new_id <= group_protocol.INT32_MAX:
        return False
    changing_seat = new_id != state.id
    if changing_seat:
        # Omission is the safe intermediate state: old groups must be durable
        # before the new Seat can become routable.
        if not state.store.put("groups", []):
            return False
        state.groups = ()
        send_groups_to_engine(state)
    if not state.store.put("assignment", [new_id, name] + positions):
        return False
    state.id = new_id
    msg = OSCMessage("/id")
    msg.append(new_id, 'f')
    try:
        send_to_engine(msg)
    except Exception:
        pass
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
    if not state.store.put("groups", []):
        return False
    state.groups = ()
    send_groups_to_engine(state)
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


def apply_groups(args, reply_socket, requester, state=None):
    """Apply one UID-attributable, validated full membership replacement."""
    state = state or node_state
    if not args or not isinstance(args[0], str) or args[0] != state.uid:
        return False
    memberships = group_protocol.group_ids(args[1:])
    if memberships is None or not state.store.put("groups", memberships):
        return False
    state.groups = memberships
    send_groups_to_engine(state)
    msg = OSCMessage("/os/groups")
    msg.append(str(state.uid), 's')
    for group_id in memberships:
        msg.append(group_id, 'i')
    reply_socket.sendto(msg.getBinary(), (requester, 5550))
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


def rev_reply(reply_socket, requester, state=None, status=None, phase=None):
    # /os/rev <sha> <model> <uid> -- attributable convergence (v1.5, sec 7).
    state = state or node_state
    state.version = resolve_version()
    msg = OSCMessage("/os/rev")
    msg.append(str(state.version), 's')
    msg.append(str(state.update_model), 's')
    msg.append(str(state.uid), 's')
    if status is not None:
        msg.append(str(status), 's')
        msg.append(str(phase or "unknown"), 's')
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
    if result:
        try:
            # a listing just paid for the hashes; persist them so the next
            # engine launch resolves its run-context patch-fingerprint
            identity.save_hash_cache(patches_dir)
        except OSError as error:
            print("WARNING: patch fingerprint cache save failed:", error)
    return result


asset_warm_lock = threading.Lock()
asset_warm_thread = None


def _asset_warm_loop(assets_root):
    try:
        # On Linux nice is per-thread. If a platform rejects it, warming still
        # remains off the OSC thread and correctness does not depend on it.
        try:
            os.nice(10)
        except OSError:
            pass
        identity.warm_hash_cache(assets_root)
    except OSError as error:
        print("WARNING: asset fingerprint warm failed:", error)


def warm_asset_cache(assets_root=None):
    """Start at most one low-priority asset cache warm without blocking."""
    global asset_warm_thread
    assets_root = assets_root or ASSETS_ROOT
    with asset_warm_lock:
        if asset_warm_thread is not None and asset_warm_thread.is_alive():
            return asset_warm_thread
        asset_warm_thread = threading.Thread(target=_asset_warm_loop,
                                             args=(assets_root,), daemon=True)
        asset_warm_thread.start()
        return asset_warm_thread


def initialise_asset_cache(assets_root=None):
    assets_root = assets_root or ASSETS_ROOT
    try:
        identity.load_hash_cache(assets_root)
    except OSError as error:
        print("WARNING: asset fingerprint cache load failed:", error)
    return warm_asset_cache(assets_root)


patch_warm_lock = threading.Lock()
patch_warm_thread = None


def _patch_warm_loop(patches_dir):
    try:
        try:
            os.nice(10)
        except OSError:
            pass
        identity.warm_hash_cache(patches_dir)
    except OSError as error:
        print("WARNING: patch fingerprint warm failed:", error)


def warm_patch_cache(patches_dir=None):
    """Start at most one low-priority patch cache warm without blocking.

    Warming persists patches/.hashcache.json, which is what lets the
    launch-time run context resolve patch-fingerprint (contract v1.7)
    instead of degrading to "unknown"."""
    global patch_warm_thread
    patches_dir = patches_dir or os.path.join(BOPOS_DIR, "patches")
    with patch_warm_lock:
        if patch_warm_thread is not None and patch_warm_thread.is_alive():
            return patch_warm_thread
        patch_warm_thread = threading.Thread(target=_patch_warm_loop,
                                             args=(patches_dir,), daemon=True)
        patch_warm_thread.start()
        return patch_warm_thread


def initialise_patch_cache(patches_dir=None):
    patches_dir = patches_dir or os.path.join(BOPOS_DIR, "patches")
    try:
        identity.load_hash_cache(patches_dir)
    except OSError as error:
        print("WARNING: patch fingerprint cache load failed:", error)
    return warm_patch_cache(patches_dir)


def installed_assets(assets_root=None):
    """Return installed slots without ever hashing on the reply path."""
    assets_root = assets_root or ASSETS_ROOT
    result = []
    needs_warm = False
    for name in asset_slots.installed_names(assets_root):
        path = os.path.join(assets_root, name)
        try:
            info = identity.cached_directory_info(path)
        except OSError:
            info = {"fingerprint": None, "files": 0, "bytes": 0}
        entry = {"name": name, "fingerprint": info["fingerprint"],
                 "files": info["files"], "bytes": info["bytes"]}
        needs_warm = needs_warm or entry["fingerprint"] is None
        result.append(entry)
    if needs_warm:
        warm_asset_cache(assets_root)
    return result


def run_admin_verb(callback, args, state, reply_socket=None, requester=None):
    # serialized so two provisioning verbs can't interleave in one git tree
    with admin_lock:
        outcome = None
        try:
            outcome = callback('', '', [str(value) for value in args], '')
        except Exception as error:
            print("WARNING: admin verb failed:", error)
            outcome = {"status": "err", "phase": "exception"}
        if reply_socket is not None:
            # after convergence, so the sha is the post-action one
            if isinstance(outcome, dict):
                rev_reply(reply_socket, requester, state,
                          outcome.get("status", "err"), outcome.get("phase", "unknown"))
            else:
                rev_reply(reply_socket, requester, state)
        if (isinstance(outcome, dict) and outcome.get("status") == "ok"
                and outcome.get("reboot")):
            if not request_power_action("reboot") and reply_socket is not None:
                rev_reply(reply_socket, requester, state, "err", "reboot")


def audio_report(state=None):
    state = state or node_state
    return {
        "configured": audio_config.from_node_config(state.config),
        "active": audio_config.read_active(
            os.path.join(BOPOS_DIR, "run", "audio-config.json")),
        "cards": audio_config.discover_cards(),
        "status": getattr(state, "audio_status", "active"),
        "error": getattr(state, "audio_error", None),
    }


def log_report(state=None):
    state = state or node_state
    return log_config.status_object(state.config)


def log_config_reply(reply_socket, requester, status, state=None):
    # /os/log-config <uid> <ok|err> <json> -- the json is the complete log
    # state object (configured/effective/usb_present). Mirrors audio-config,
    # minus the phase arg: applying a destination is atomic and needs no
    # transactional restart/rollback.
    state = state or node_state
    msg = OSCMessage("/os/log-config")
    msg.append(str(state.uid), 's')
    msg.append(str(status), 's')
    msg.append(json.dumps(log_report(state), separators=(",", ":")), 's')
    reply_socket.sendto(msg.getBinary(), (requester, 5550))


def apply_log_config(payload, reply_socket, requester, state=None):
    """Persist one bounded log destination (internal|usb). No engine restart:
    logging is independent of audio; the destination hook picks up the new
    config on the next entry."""
    state = state or node_state
    try:
        candidate = log_config.validate(json.loads(str(payload)))
    except (ValueError, TypeError):
        log_config_reply(reply_socket, requester, "err", state)
        return False
    config_path = os.path.join(BOPOS_DIR, "bopos.config")
    try:
        log_config.update_config_file(config_path, candidate["destination"])
        state.config = read_node_config(config_path)
    except (OSError, ValueError):
        log_config_reply(reply_socket, requester, "err", state)
        return False
    log_config_reply(reply_socket, requester, "ok", state)
    return True


def audio_config_reply(reply_socket, requester, status, phase, state=None):
    state = state or node_state
    msg = OSCMessage("/os/audio-config")
    msg.append(str(state.uid), 's')
    msg.append(str(status), 's')
    msg.append(str(phase), 's')
    msg.append(json.dumps(audio_report(state), separators=(",", ":")), 's')
    reply_socket.sendto(msg.getBinary(), (requester, 5550))


def _restart_audio_engine():
    stop_script = os.path.join(BOPOS_DIR, "bash", "stop-engine.sh")
    start_script = os.path.join(BOPOS_DIR, "bash", "start-engine.sh")
    if run_command([stop_script]) != 0:
        return False
    return run_command([start_script], wait_for_start=True) == 0


def _restore_config(path, existed, content, mode):
    if existed:
        audio_config.atomic_write(path, content, mode)
    else:
        try:
            os.unlink(path)
        except FileNotFoundError:
            pass


def apply_audio_config(payload, reply_socket, requester, state=None):
    """Apply one complete audio configuration and recover the prior engine."""
    state = state or node_state
    # Audio restart must not interleave with patch switching, framework
    # convergence, or another lifecycle action.
    with admin_lock:
        try:
            candidate = json.loads(str(payload))
            candidate = audio_config.validate(
                candidate, audio_config.discover_cards())
        except (ValueError, TypeError) as error:
            state.audio_status = "error"
            state.audio_error = str(error)
            audio_config_reply(reply_socket, requester, "err", "invalid", state)
            return False

        config_path = os.path.join(BOPOS_DIR, "bopos.config")
        try:
            with open(config_path, "rb") as source:
                previous_content = source.read()
            previous_mode = os.stat(config_path).st_mode & 0o777
            existed = True
        except FileNotFoundError:
            previous_content, previous_mode, existed = b"", 0o644, False
        previous_config = dict(state.config)
        state.audio_status = "applying"
        state.audio_error = None

        failure = None
        try:
            audio_config.update_config_file(config_path, candidate)
            if not _restart_audio_engine():
                failure = "JACK did not start with the requested settings."
            else:
                state.config = read_node_config(config_path)
                audio_config.write_active(
                    os.path.join(BOPOS_DIR, "run", "audio-config.json"),
                    candidate)
                # Enabling output is best-effort on cards without a switch;
                # disabling output is a hard safety condition.
                mute_ok = enforce_mute(not output_enabled(state), state)
                if not output_enabled(state) and not mute_ok:
                    failure = "The restarted card could not enforce output safety."
        except (OSError, ValueError) as error:
            failure = "Could not persist or start the requested settings: {}".format(error)

        if failure is None:
            state.audio_status = "active"
            state.audio_error = None
            audio_config_reply(reply_socket, requester, "ok", "applied", state)
            return True

        try:
            _restore_config(config_path, existed, previous_content, previous_mode)
            state.config = previous_config
            recovered = _restart_audio_engine()
            if recovered:
                active = audio_config.from_node_config(previous_config)
                audio_config.write_active(
                    os.path.join(BOPOS_DIR, "run", "audio-config.json"), active)
                enforce_mute(not output_enabled(state), state)
                state.audio_status = "rolled-back"
                state.audio_error = failure
                audio_config_reply(
                    reply_socket, requester, "err", "rolled-back", state)
                return False
        except OSError:
            recovered = False
        state.audio_status = "error"
        state.audio_error = failure + " Recovery of the previous settings failed."
        audio_config_reply(
            reply_socket, requester, "err", "rollback-failed", state)
        return False


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
        "contract_version": "1.14",
        "groups": list(getattr(state, "groups", ())),
        "device_enabled": bool(getattr(state, "device_enabled", True)),
        "mute_all": bool(getattr(state, "mute_all", False)),
        "output_enabled": output_enabled(state),
        "audio": audio_report(state),
        "log": log_report(state),
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
    """Dispatch the exact UID allowlist and its narrow argument verbs."""
    if member == "enabled" and len(args) == 1:
        return set_device_enabled(args[0], reply_socket, requester, state)
    if member == "hostname" and len(args) == 1:
        hostname = str(args[0])
        if HOSTNAME_RE.fullmatch(hostname) is None:
            return False
        threading.Thread(target=set_device_hostname,
                         args=(hostname, reply_socket, requester, state),
                         daemon=True).start()
        return True
    if member == "audio-config" and len(args) == 1:
        threading.Thread(target=apply_audio_config,
                         args=(args[0], reply_socket, requester, state),
                         daemon=True).start()
        return True
    if member == "log-config" and len(args) == 1:
        threading.Thread(target=apply_log_config,
                         args=(args[0], reply_socket, requester, state),
                         daemon=True).start()
        return True
    if member not in UID_ADMIN_VERBS or args:
        return False
    if member == "identify":
        return identify(state=state)
    if member == "report":
        return report_reply(reply_socket, requester, state)
    if member == "unassign":
        return apply_unassign(state)
    return dispatch_admin_verb(member, args, state, reply_socket, requester)


# Param-declaration lookup cache: /p/* traffic can arrive at slider-drag
# rates, and a Zero 2 W must not re-read and re-validate the manifest JSON
# per datagram. One stat() per message; reparse only on path/mtime change.
_declared_params = {"path": None, "mtime": None, "params": {}}


def declared_param(identity):
    patch_path = active_patch_path()
    if not patch_path:
        return None
    try:
        mtime = os.stat(os.path.join(patch_path, manifest.MANIFEST_NAME)).st_mtime_ns
    except OSError:
        return None
    if _declared_params["path"] != patch_path or _declared_params["mtime"] != mtime:
        data, _error = manifest.load(patch_path)
        params = {}
        if data is not None:
            for item in data.get("params", []):
                params[manifest.qualify_param(item)] = item
        _declared_params.update(path=patch_path, mtime=mtime, params=params)
    return _declared_params["params"].get(identity)


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
    memberships = getattr(state, "groups", ())
    if len(parts) >= 3 and selector_matches(parts[0], state.id, memberships):
        shaped = relay.shape_provided_term(parts, args)
        if shaped is not None:
            address, shaped_args = shaped
            if address.startswith("/p/"):
                declaration = declared_param(address[3:])
                param_identity = address[3:]
                param_type = manifest.param_wire_type(declaration)
                if param_type in ("f", "i"):
                    try:
                        spec = paramgen.parse_message(shaped_args, param_type)
                    except paramgen.ParamGrammarError as error:
                        print(f"WARNING: {address} parameter grammar: {error}")
                        return True
                    record_static_param(param_identity, spec, declaration)
                    return param_generator.apply(param_identity, spec, declaration)
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
    if (len(parts) >= 3 and parts[1] == "e"
            and selector_matches(parts[0], state.id, memberships)):
        identity_parts = parts[2:]
        event_identity = "/".join(identity_parts)
        if (len(identity_parts) > manifest.MAX_PARAM_SEGMENTS
                or any(manifest.PARAM_NAME.fullmatch(part) is None
                       for part in identity_parts)
                or len(event_identity.encode("ascii")) > manifest.MAX_PARAM_IDENTITY_BYTES
                or not 1 <= len(args) <= manifest.MAX_EVENT_ARITY + 1
                or not isinstance(args[0], str)
                or any(not isinstance(value, float) for value in args[1:])):
            return True
        try:
            elements = [float(value) for value in args[1:]]
        except (TypeError, ValueError):
            return True
        shared_time = str(args[0])
        if shared_time == "0":
            fire_event_to_engine(event_identity, elements)
            return True
        try:
            event_scheduler.schedule(int(shared_time), event_identity, elements)
        except (TypeError, ValueError):
            pass
        return True
    if parts == ["cue"] and len(args) >= 2:
        try:
            cue_scheduler.schedule(int(str(args[1])), str(args[0]), [])
        except (TypeError, ValueError):
            pass
        return True
    if (len(parts) == 3 and parts[1] == "sync" and parts[2] == "offset"
            and args and selector_matches(parts[0], state.id, memberships)):
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
    if parts == ["all", "os", "groups"]:
        return apply_groups(args, reply_socket, source[0], state)
    if parts == ["all", "os", "assign"]:
        return apply_assign(args, state)
    if (len(parts) != 3 or parts[1] != "os"
            or not selector_matches(parts[0], state.id, memberships)):
        return False
    if parts[2] == "assign":
        # Assignment is an exact literal-all administrative envelope, never a
        # generalized Seat/group-addressed framework verb.
        return False
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
        asset_slot = identity.valid_asset_slot(slot)
        patch_slot = re.fullmatch(r"patch:[A-Za-z0-9_-]+", slot)
        if not asset_slot and patch_slot is None:
            _fetched_reply(reply_socket, source[0], slot, "err")
            return True
        queue_fetch(uri, slot, source[0], reply_socket)
        return True
    if parts[2] == "patches":
        msg = OSCMessage("/os/patches")
        msg.append(json.dumps(installed_patches(), separators=(",", ":")), 's')
        reply_socket.sendto(msg.getBinary(), (source[0], 5550))
        return True
    if parts[2] == "assets":
        msg = OSCMessage("/os/assets")
        msg.append(json.dumps(installed_assets(), separators=(",", ":")), 's')
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
    # Every engine asks /config after opening port 6661. Always return the
    # authoritative resolved identity. Seat names and the legacy bopos.devices
    # export never mutate the OS hostname; that belongs only to the exact-UID
    # /os/hostname action.
    msg = OSCMessage("/id")
    msg.append(node_state.id, 'i')
    send_to_engine(msg)


FRAMEWORK_COMMAND_TIMEOUTS = {
    "authorization": 10,
    "restore": 30,
    "fetch": 120,
    "branch": 15,
    "checkout": 60,
    "pull": 180,
    "submodules": 180,
}


def _framework_environment():
    ssh_command = os.environ.get("GIT_SSH_COMMAND", "ssh")
    if "BatchMode" not in ssh_command:
        ssh_command += " -o BatchMode=yes"
    return dict(os.environ, GIT_TERMINAL_PROMPT="0", GCM_INTERACTIVE="never",
                GIT_SSH_COMMAND=ssh_command)


def _bounded_command(argv, cwd, timeout, env=None):
    """Run one admin command in its own process group and reap it completely."""
    process = subprocess.Popen(argv, cwd=cwd, env=env, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, text=True,
                               start_new_session=True)

    def terminate_group():
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            return process.communicate(timeout=2)[0] or ""
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            return process.communicate()[0] or ""

    try:
        output, _unused = process.communicate(timeout=timeout)
        return {"returncode": process.returncode, "stdout": output or "",
                "timed_out": False}
    except subprocess.TimeoutExpired as error:
        output = error.output or ""
        if isinstance(output, bytes):
            output = output.decode(errors="replace")
        tail = terminate_group()
        return {"returncode": process.returncode, "stdout": output + (tail or ""),
                "timed_out": True}
    except BaseException:
        terminate_group()
        raise


def _restore_active_patch(name):
    target = os.path.join(BOPOS_DIR, "patches", "active_patch.txt")
    temporary = target + ".update"
    try:
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(temporary, "w", encoding="utf-8") as destination:
            destination.write(name + "\n")
            destination.flush()
            os.fsync(destination.fileno())
        os.replace(temporary, target)
        return True
    except OSError as error:
        print("active patch restoration failed:", error)
        try:
            os.remove(temporary)
        except OSError:
            pass
        return False


def _framework_command(argv, phase, timeout=None):
    timeout = FRAMEWORK_COMMAND_TIMEOUTS[phase] if timeout is None else timeout
    try:
        result = _bounded_command(argv, BOPOS_DIR, timeout, _framework_environment())
    except Exception as error:
        print("{} command failed to start: {}".format(phase, error))
        return {"status": "err", "phase": phase}
    if result["stdout"]:
        print(result["stdout"], end="" if result["stdout"].endswith("\n") else "\n")
    if result["timed_out"]:
        return {"status": "err", "phase": phase + "-timeout"}
    if result["returncode"] != 0:
        return {"status": "err", "phase": phase}
    return None


def converge_framework(branch=None):
    """Trusted in-process orchestration; remains stable across branch checkout."""
    authorization = _framework_command(
        ["/usr/bin/sudo", "-n", "-l", "/usr/bin/systemctl", "reboot"],
        "authorization")
    if authorization:
        return authorization
    try:
        with open(os.path.join(BOPOS_DIR, "patches", "active_patch.txt"),
                  encoding="utf-8") as source_file:
            active_patch = source_file.read().strip()
    except OSError as error:
        print("active patch selection unavailable:", error)
        return {"status": "err", "phase": "active-patch"}

    outcome = None
    try:
        if branch is not None:
            outcome = _framework_command(
                ["git", "check-ref-format", "--branch", branch], "branch")
        if outcome is None:
            outcome = _framework_command(["git", "restore", "."], "restore")
        if outcome is None and branch is not None:
            remote_refspec = "+refs/heads/{0}:refs/remotes/origin/{0}".format(branch)
            outcome = _framework_command(
                ["git", "-c", "credential.interactive=never", "fetch", "origin",
                 remote_refspec],
                "fetch")
        remote_ref = "refs/remotes/origin/{}".format(branch) if branch is not None else None
        if outcome is None and branch is not None:
            outcome = _framework_command(
                ["git", "show-ref", "--verify", "--quiet", remote_ref], "branch")
        if outcome is None and branch is not None:
            outcome = _framework_command(
                ["git", "checkout", "-B", branch, remote_ref], "checkout")
        if outcome is None and branch is not None:
            outcome = _framework_command(
                ["git", "branch", "--set-upstream-to=origin/{}".format(branch), branch],
                "checkout")
        if outcome is None and branch is None:
            outcome = _framework_command(
                ["git", "-c", "credential.interactive=never", "pull", "--ff-only",
                 "--recurse-submodules"], "pull")
        if outcome is None:
            outcome = _framework_command(["git", "submodule", "sync", "--recursive"],
                                         "submodules")
        if outcome is None:
            outcome = _framework_command(
                ["git", "-c", "credential.interactive=never", "submodule", "update",
                 "--init", "--recursive"], "submodules")
    finally:
        if not _restore_active_patch(active_patch):
            outcome = {"status": "err", "phase": "active-patch"}
    return outcome or {"status": "ok", "phase": "converged", "reboot": True}


def update_bopos_callback(path='', tags='', args='', source=''):
    msg = OSCMessage("/notify")
    msg.append("updatebopos", 's')
    send_to_engine(msg)
    print("UPDATE BOPOS!")
    return converge_framework()

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
    if not args:
        return {"status": "err", "phase": "branch"}
    branch = str(args[0])
    print("checking out: " + branch)
    return converge_framework(branch)

def switch_patch_callback(path='', tags='', args='', source=''):
    patches_dir = os.path.join(BOPOS_DIR, 'patches')
    active_patch_file = os.path.realpath(os.path.join(patches_dir, 'active_patch.txt'))
    if not args or not args[0]:
        print("No patch name provided to /patch")
        return {"status": "err", "phase": "invalid-name"}
    patch_name = args[0].strip()
    if (patch_name.startswith(".")
            or re.fullmatch(r"[A-Za-z0-9_.-]+", patch_name) is None):
        print("Invalid patch name for /patch")
        return {"status": "err", "phase": "invalid-name"}
    patch_path = os.path.join(patches_dir, patch_name)
    patch_manifest, _error = manifest.load(patch_path)
    if not os.path.isdir(patch_path) or patch_manifest is None:
        print(f"Patch '{patch_name}' not found or has no valid bopos.patch.json")
        return {"status": "err", "phase": "not-found"}
    current = open(active_patch_file).read().strip() if os.path.exists(active_patch_file) else None
    print(f"Switching patch: {current} -> {patch_name}")
    msg = OSCMessage("/notify")
    msg.append("updatepatch", 's')
    send_to_engine(msg)

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
        warm_patch_cache()

    stop_script = os.path.join(BOPOS_DIR, "bash", "stop-engine.sh")
    start_script = os.path.join(BOPOS_DIR, "bash", "start-engine.sh")
    if run_command(["bash", stop_script]) != 0:
        print("Patch switch aborted: failed to stop current engine")
        return {"status": "err", "phase": "stop-failed"}
    hb_wake.set()
    if not select(patch_name):
        run_command(["bash", start_script], wait_for_start=True)
        hb_wake.set()
        return {"status": "err", "phase": "write-failed"}
    if run_command(["bash", start_script], wait_for_start=True) == 0 and engine_alive() == 1:
        print(f"Patch switch complete: {patch_name}")
        hb_wake.set()
        return {"status": "ok", "phase": "switched"}

    print(f"Patch switch failed to start {patch_name}; restoring {current}")
    run_command(["bash", stop_script])
    restored = bool(current) and select(current)
    if restored:
        run_command(["bash", start_script], wait_for_start=True)
    hb_wake.set()
    return {"status": "err", "phase": "start-failed" if restored else "restore-failed"}


def add_patch_callback(path='', tags='', args='', source=''):
    patches_dir = os.path.join(BOPOS_DIR, 'patches')
    if not args or len(args) < 2:
        print("/addpatch requires two arguments: user and repo")
        return {"status": "err", "phase": "invalid-args"}
    user, repo = str(args[0]).strip(), str(args[1]).strip()
    if not re.match(r'^[\w-]+$', user) or not re.match(r'^[\w.-]+$', repo):
        print("Invalid user or repo")
        return {"status": "err", "phase": "invalid-name"}
    repo_url, dest_dir = f"https://github.com/{user}/{repo}.git", os.path.join(patches_dir, repo)
    try:
        result = subprocess.run(["git", "ls-remote", repo_url], stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, timeout=10)
        if result.returncode != 0:
            print(f"GitHub repo not found or not accessible: {repo_url}")
            return {"status": "err", "phase": "not-found"}
    except Exception as error:
        print(f"Error checking repo: {error}")
        return {"status": "err", "phase": "not-found"}
    if os.path.isdir(dest_dir):
        try:
            print(f"Removing existing patch folder: {dest_dir}")
            shutil.rmtree(dest_dir)
        except Exception as error:
            print(f"Failed to remove existing patch folder: {error}")
            return {"status": "err", "phase": "remove-failed"}
    try:
        print(f"Cloning {repo_url} into {dest_dir}...")
        result = subprocess.run(["git", "clone", "--recursive", repo_url, dest_dir],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
        if result.returncode != 0:
            print(f"Failed to clone repo: {result.stderr.decode().strip()}")
            return {"status": "err", "phase": "clone-failed"}
        print(f"Cloned {repo_url} into {dest_dir}")
    except subprocess.TimeoutExpired:
        print("Clone timed out after 120s — check network connection")
        return {"status": "err", "phase": "clone-failed"}
    except Exception as error:
        print(f"Error cloning repo: {error}")
        return {"status": "err", "phase": "clone-failed"}
    _patch_manifest, manifest_error = manifest.load(dest_dir)
    if _patch_manifest is None:
        print(f"Warning: cloned patch '{repo}' will not launch: {manifest_error}")
    warm_patch_cache()
    try:
        msg = OSCMessage("/addpatch")
        msg.append(repo)
        send_to_engine(msg)
    except Exception as error:
        print(f"Failed to send OSC confirmation: {error}")
    return {"status": "ok", "phase": "cloned"}

# bash/pull_active_patch.sh's exit codes, mapped to receipt phases. The
# script itself no longer reboots (contract sec 7 receipt-before-reboot);
# a successful pull asks run_admin_verb to request the reboot only after
# the /os/rev receipt has already gone out, mirroring converge_framework.
_PULL_ACTIVE_PATCH_PHASES = {
    1: "active-patch",   # active_patch.txt missing
    2: "not-found",      # no .git repo for the active patch
    3: "not-found",      # cd into the patch dir failed
    4: "pull-failed",    # git pull failed
}


def pull_active_patch_callback(path='', tags='', args='', source=''):
    msg = OSCMessage("/notify")
    msg.append("updatepatch", 's')
    send_to_engine(msg)
    script_path = os.path.join(BOPOS_DIR, 'bash/pull_active_patch.sh')
    print(f"Running: {script_path}")
    try:
        result = subprocess.run(["bash", script_path], timeout=120)
    except subprocess.TimeoutExpired:
        print("[pull_active_patch_callback] timed out")
        return {"status": "err", "phase": "timeout"}
    except Exception as error:
        print(f"[pull_active_patch_callback] Exception: {error}")
        return {"status": "err", "phase": "exception"}
    if result.returncode != 0:
        print(f"pull_active_patch.sh exited with code {result.returncode}")
        phase = _PULL_ACTIVE_PATCH_PHASES.get(result.returncode, "pull-failed")
        return {"status": "err", "phase": phase}
    return {"status": "ok", "phase": "pulled", "reboot": True}


def drop_patch_callback(path='', tags='', args='', source=''):
    if (not args or str(args[0]).startswith(".")
            or re.fullmatch(r"[A-Za-z0-9_.-]+", str(args[0])) is None):
        print("/droppatch requires a valid patch name")
        return {"status": "err", "phase": "invalid-name"}
    name = str(args[0])
    active_path = active_patch_path()
    if active_path is not None and os.path.basename(active_path) == name:
        print("Refusing to remove active patch '{}'".format(name))
        return {"status": "err", "phase": "active-patch"}
    target = os.path.join(BOPOS_DIR, "patches", name)
    try:
        if os.path.islink(target) or os.path.isfile(target):
            os.remove(target)
        elif os.path.isdir(target):
            shutil.rmtree(target)
        print("Dropped patch '{}'".format(name))
        warm_patch_cache()
    except OSError as error:
        print("Failed to drop patch '{}': {}".format(name, error))
        return {"status": "err", "phase": "remove-failed"}
    return {"status": "ok", "phase": "dropped"}


def drop_assets_callback(path='', tags='', args='', source=''):
    if not args or not identity.valid_asset_slot(str(args[0])):
        print("/dropassets requires a valid asset slot")
        return {"status": "err", "phase": "invalid-name"}
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
        return {"status": "err", "phase": "remove-failed"}
    return {"status": "ok", "phase": "dropped"}


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


def log_callback(path='', tags='', args='', source=''):
    # /log <stream> <values...> on localhost 7770 (contract sec 4.2) -- a
    # patch appends one entry to the named node-side log stream. The node
    # stamps it at receipt. Fire-and-forget, no reply. An invalid or missing
    # stream name is dropped with a logged warning by nodelog.append, never
    # fatal. Destination (internal/usb) is stitch 4's concern; here it is the
    # internal default.
    if not args:
        print("WARNING: /log received with no stream")
        return
    nodelog.append(str(args[0]), list(args[1:]))


# /os/* admin verbs on the 6660 LAN listener call these implementation
# functions directly. Engines otherwise cannot issue administrative
# commands, except for the bounded /admin request on 7770 (contract sec
# 4.2, v1.7) dispatched via ENGINE_ADMIN_VERBS below, which reuses these
# same callbacks.
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

# Engine-sent /admin action -> the same implementation callback the LAN
# /os/* verbs use (contract sec 4.2, v1.7). Bounded: only these four names.
ENGINE_ADMIN_VERBS = {
    "update-patch": pull_active_patch_callback,
    "update-bopos": update_bopos_callback,
    "shutdown": shutdown_callback,
    "reboot": reboot_callback,
}


def admin_callback(path='', tags='', args='', source=''):
    # /admin <action> on localhost 7770 -- a patch running on the node may
    # request the same handful of node-lifecycle actions the dashboard
    # already triggers over 6660/os/*. No selector, no reply to the engine:
    # these actions are terminal or restart the engine anyway. run_admin_verb
    # is called with reply_socket=None/requester=None, so its rev_reply path
    # is skipped safely; outcome receipts still flow to the LAN model where
    # a real dashboard-originated requester exists. Unknown/missing actions
    # are logged and otherwise ignored, never fatal.
    if not args:
        print("WARNING: /admin received with no action")
        return
    action = str(args[0])
    callback = ENGINE_ADMIN_VERBS.get(action)
    if callback is None:
        print(f"WARNING: /admin unknown action: {action}")
        return
    threading.Thread(target=run_admin_verb,
                     args=(callback, [], node_state),
                     daemon=True).start()


def fire_cue_to_engine(cue_id, elements=()):
    # at the local deadline, the engine sees only the bare cue -- absolute time
    # never enters PD (contract sec 12). PD's patch owns the /cue receiver.
    # `elements` is the generalized scheduler's payload; a cue has none, and
    # child 4 deletes this path outright.
    msg = OSCMessage("/cue")
    typed_append(msg, cue_id)
    try:
        send_to_engine(msg)
    except Exception as error:
        print(f"cue: could not fire to engine: {error}")


def fire_event_to_engine(identity, elements):
    # Absolute shared time stays in Python. The engine sees only the relative,
    # selector-free event fire and its 0–3 float elements.
    msg = OSCMessage("/e/" + identity)
    for element in elements:
        msg.append(float(f"{float(element):.6g}"), 'f')
    try:
        send_to_engine(msg)
    except Exception as error:
        print(f"event: could not fire to engine: {error}")


sync_state = SyncState()
event_scheduler = EventScheduler(sync_state, fire_event_to_engine)
# Child 4 retires `/cue`; until then the compatibility alias gives it the
# generalized payload shape while both schedulers share the one SyncState.
cue_scheduler = EventScheduler(
    sync_state, fire_cue_to_engine, log_label="cue")
param_generator = paramgen.GeneratorEngine(
    lambda identity, args: relay_provided_term("/p/" + identity, args), sync_state)


def exit_handler():
    print("exiting.  closing server...")
    event_scheduler.stop()
    cue_scheduler.stop()
    param_generator.close()
    nodelog.close()
    server.close()


server.addMsgHandler( "/config", config_callback )
server.addMsgHandler( "/store", store_callback )
server.addMsgHandler( "/load", load_callback )
server.addMsgHandler( "/report", report_callback )
server.addMsgHandler( "/log", log_callback )
server.addMsgHandler( "/admin", admin_callback )

atexit.register(exit_handler)

if __name__ == "__main__":
    server.timeout = 1.0
    event_scheduler.start()
    cue_scheduler.start()
    initialise_asset_cache()
    initialise_patch_cache()
    # Persistent Device enabled is enforced as the helper comes up, before or
    # alongside the independently managed engine launch.
    enforce_mute(not output_enabled(node_state), node_state)
    threading.Thread(target=heartbeat_loop, daemon=True).start()
    threading.Thread(target=lan_listener_loop, daemon=True).start()
    while True:
        server.handle_request()
