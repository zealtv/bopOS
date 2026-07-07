
import shutil
import subprocess
import re


import os, sys
from time import sleep
from csv import reader
from pyOSC3 import OSCServer, OSCClient, OSCMessage, decodeOSC
import atexit
import glob
import socket
import threading
import uuid

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

server = OSCServer( ('', 7770) )
client = OSCClient()
client.connect( ('127.0.0.1', 6661) )


def read_node_config(path=None):
    config = {"HB_TARGET": "255.255.255.255", "HB_RSSI": "1", "MIXER_CONTROL": None}
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


def resolve_id(uid, path=None):
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
        self.uid = resolve_uid(argv)
        self.id = resolve_id(self.uid)
        self.version = resolve_version()
        self.mixer_control = None
        self.muted_via_stop = False


node_state = NodeState()


def process_is_pd(pid):
    # exact match, same contract as stop-engine.sh's `pkill -x pd`
    try:
        with open(os.path.join(PROC_DIR, str(pid), "comm")) as source:
            return source.read().strip() == "pd"
    except OSError:
        return False


def engine_alive():
    try:
        with open(os.path.join(BOPOS_DIR, "run", "pd.pid")) as source:
            if process_is_pd(int(source.read().strip())):
                return 1
    except (OSError, ValueError):
        pass
    for path in glob.glob(os.path.join(PROC_DIR, "[0-9]*", "comm")):
        try:
            with open(path) as source:
                if source.read().strip() == "pd":
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
        sleep(2.0 if state.id == -1 else 10.0)


def selector_matches(selector, device_id):
    if selector == "all":
        return True
    try:
        return int(selector) == int(device_id) and str(selector) == str(int(selector))
    except (TypeError, ValueError):
        return False


def run_command(argv):
    try:
        if (len(argv) >= 2 and argv[0] == "bash"
                and os.path.basename(argv[1]) == "start-engine.sh"):
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
        client.send(OSCMessage("/identify"))
    except Exception:
        pass
    flash_led()
    print("IDENTIFY:", state.uid, "id", state.id)
    return True


def handle_lan_datagram(datagram, source, reply_socket, state=None):
    state = state or node_state
    try:
        decoded = decodeOSC(datagram)
    except Exception:
        return False
    if len(decoded) < 2:
        return False
    parts = [part for part in str(decoded[0]).split("/") if part]
    if len(parts) != 3 or parts[1] != "os" or not selector_matches(parts[0], state.id):
        return False
    args = decoded[2:]
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
    if parts[2] == "mute" and args:
        try:
            if int(args[0]) in (0, 1):
                set_mute(int(args[0]), state)
                return True
        except (TypeError, ValueError):
            pass
    return False


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
    current_hostname = socket.gethostname()
    try:
        read_obj = open(config_file, 'r')
    except OSError:
        print('MAC address not found in bopos.devices.csv')
        return
    with read_obj:
        csv_reader = reader(read_obj, skipinitialspace=True)
        macfound = False
        for row in csv_reader:
            if len(row) >= 3 and row[0].strip() == node_state.uid:
                print('MAC address found in bopos.devices')
                macfound = True
                hostname = row[1].strip()
                if current_hostname != hostname:
                    print(f"Hostname change: {current_hostname} -> {hostname}")
                    os.system(f'sudo hostnamectl set-hostname {hostname}')
                    os.system(f"sudo sed -i 's/^127.0.1.1.*/127.0.1.1   {hostname}/' /etc/hosts")
                    os.system('sudo systemctl restart avahi-daemon')
                try:
                    node_state.id = int(float(row[2]))
                except ValueError:
                    node_state.id = -1
                print('setting ID to ' + str(node_state.id))
                msg = OSCMessage("/id")
                msg.append(node_state.id, 'f')
                client.send(msg)
                break
        if not macfound:
            print('MAC address not found in bopos.devices.csv')


def update_callback(path='', tags='', args='', source=''):
    update_script = os.path.join(BOPOS_DIR, "bash/update.sh")
    msg = OSCMessage("/update")
    client.send(msg)
    print("UPDATE!")
    os.system(update_script)

def getsamples_callback(path='', tags='', args='', source=''):
    update_script = os.path.join(BOPOS_DIR, "bash/getsamples.sh")
    msg = OSCMessage("/getsamples")
    client.send(msg)
    print("UPDATE SAMPLES!")
    os.system(update_script)

def shutdown_callback(path='', tags='', args='', source=''):
    client.send(OSCMessage("/shutdown"))
    print("SHUTDOWN!")
    os.system("systemctl poweroff")

def reboot_callback(path='', tags='', args='', source=''):
    client.send(OSCMessage("/reboot"))
    print("REBOOTING")
    os.system("systemctl reboot")

def checkout_callback(path, tags, args, source):
    client.send(OSCMessage("/checkout"))
    branch = args[0].lstrip('/')
    print("checking out: " + branch)
    os.system(os.path.join(BOPOS_DIR, "bash/checkout.sh ") + branch)
    client.send(OSCMessage("/update"))
    print("UPDATE!")
    os.system(os.path.join(BOPOS_DIR, "bash/update.sh"))

def switch_patch_callback(path='', tags='', args='', source=''):
    patches_dir = os.path.join(BOPOS_DIR, 'patches')
    active_patch_file = os.path.realpath(os.path.join(patches_dir, 'active_patch.txt'))
    if not args or not args[0]:
        print("No patch name provided to /patch")
        return
    patch_name = args[0].strip()
    patch_path = os.path.join(patches_dir, patch_name)
    if not os.path.isdir(patch_path) or not os.path.isfile(os.path.join(patch_path, 'main.pd')):
        print(f"Patch '{patch_name}' not found or has no main.pd")
        return
    current = open(active_patch_file).read().strip() if os.path.exists(active_patch_file) else 'None'
    print(f"Switching patch: {current} -> {patch_name}")
    try:
        with open(active_patch_file, 'w') as target:
            target.write(patch_name + '\n')
    except Exception as error:
        print(f"Failed to write active_patch.txt: {error}")
        return
    os.system(os.path.join(BOPOS_DIR, "bash/stop-engine.sh"))
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
    print("Rebooting...")
    os.system("systemctl reboot")


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
    if not os.path.isfile(os.path.join(dest_dir, 'main.pd')):
        print(f"Warning: cloned patch '{repo}' has no main.pd — it won't load in PD")
    try:
        msg = OSCMessage("/addpatch")
        msg.append(repo)
        client.send(msg)
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


def restart_engine_callback(path='', tags='', args='', source=''):
    stop_script = os.path.join(BOPOS_DIR, "bash/stop-engine.sh")
    start_script = os.path.join(BOPOS_DIR, "bash/start-engine.sh")
    client.send(OSCMessage("/restart-engine"))
    print("RESTARTING ENGINE")
    subprocess.Popen(["bash", "-c", '"$1" && exec "$2"', "restart-engine", stop_script, start_script],
                     start_new_session=True)


def exit_handler():
    print("exiting.  closing server...")
    server.close()


server.addMsgHandler( "/config", config_callback )
server.addMsgHandler( "/update", update_callback )
server.addMsgHandler( "/getsamples", getsamples_callback )
server.addMsgHandler( "/shutdown", shutdown_callback )
server.addMsgHandler( "/reboot", reboot_callback )
server.addMsgHandler( "/checkout", checkout_callback )
server.addMsgHandler( "/patch", switch_patch_callback )
server.addMsgHandler( "/addpatch", add_patch_callback )
server.addMsgHandler( "/pullpatch", pull_active_patch_callback )
server.addMsgHandler( "/restart-engine", restart_engine_callback )

atexit.register(exit_handler)

if __name__ == "__main__":
    server.timeout = 1.0
    threading.Thread(target=heartbeat_loop, daemon=True).start()
    threading.Thread(target=lan_listener_loop, daemon=True).start()
    while True:
        server.handle_request()
