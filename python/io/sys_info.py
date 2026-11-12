# sys_info.py
"""
Device facts for /system/info (and the granular /system/* queries) -- the
data a default-patch discovery beacon announces. Stdlib only.
"""

import os
import socket
import subprocess


def get_hostname():
    return socket.gethostname()


def get_ip():
    """Primary outbound-interface IP. The UDP 'connect' sends no packets; it
    just selects the route, so this works offline too."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def get_uptime():
    """Seconds since boot (int)."""
    with open("/proc/uptime") as f:
        return int(float(f.read().split()[0]))


def _repo_root():
    return os.path.realpath(os.path.join(os.path.dirname(__file__), "..", ".."))


def get_git_rev():
    """Short git SHA of the bopOS checkout, or 'unknown'."""
    try:
        return subprocess.check_output(
            ["git", "-C", _repo_root(), "rev-parse", "--short", "HEAD"],
            text=True, stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        return "unknown"


def get_active_patch():
    """Name from patches/active_patch.txt, or 'none'."""
    try:
        with open(os.path.join(_repo_root(), "patches", "active_patch.txt")) as f:
            return f.read().strip() or "none"
    except OSError:
        return "none"
