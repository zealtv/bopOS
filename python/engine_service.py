"""Observe the engine unit's cgroup, never unrelated same-name processes."""
import os

# Units explicitly use system.slice. Pi OS uses unified cgroups; retain the
# systemd controller path for older Pi OS images using cgroup v1.
CGROUP_DIR = os.path.join('/sys/fs/cgroup' if os.path.exists('/sys/fs/cgroup/cgroup.controllers')
                         else '/sys/fs/cgroup/systemd', 'system.slice/bopos-engine.service')
ACTIVE_FILE = '/run/bopos-engine/active'
COMMAND = ['/usr/bin/sudo', '-n', '/usr/bin/systemctl']


def command(action, no_block=False):
    return COMMAND + (['--no-block'] if no_block else []) + [action, 'bopos-engine.service']


def alive(name, proc='/proc'):
    # ExecStartPost publishes active only after a successful launch. systemd
    # removes the RuntimeDirectory on stop/failure, including this marker.
    # No systemctl subprocess is needed on the heartbeat path.
    if not os.path.exists(ACTIVE_FILE):
        return 0
    try:
        with open(os.path.join(CGROUP_DIR, 'cgroup.procs')) as source:
            pids = source.read().split()
        names = set()
        for pid in pids:
            try:
                with open(os.path.join(proc, pid, 'comm')) as source:
                    names.add(source.read().strip())
            except OSError:
                continue
        return int('jackd' in names and name in names)
    except OSError:
        return 0
