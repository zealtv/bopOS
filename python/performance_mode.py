"""Remembered Performance mode and the common development-operation gate.

The mode has its own durable file, independent of patch, project and the
ephemeral engine store. /dev/shm is Linux tmpfs; other hosts keep logs in
bounded process memory rather than falling back to a disk-backed /tmp.
"""

import hashlib
import json
import os
import tempfile


LOCKED = frozenset({
    "io-stream", "io-write", "stream-to-editor", "probe", "monitor-send",
    "wifi-config", "patch", "droppatch", "patch-fetch", "patch-edit",
    "manifest-save", "new-version",
})


def allows(active, operation):
    """One gate for current handlers and the later IO streaming stitches."""
    return not bool(active) or operation not in LOCKED


def load(path):
    try:
        with open(path, encoding="utf-8") as source:
            value = json.load(source)
        return value is True or (type(value) is int and value == 1)
    except (OSError, ValueError):
        return False


def save(path, active):
    """One atomic durable write on change; repeated fleet asserts do no IO."""
    active = bool(active)
    if load(path) == active:
        return False
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".performance-", dir=directory)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as target:
            json.dump(active, target)
            target.flush()
            os.fsync(target.fileno())
        os.replace(temporary, path)
        directory_fd = os.open(directory, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return True


def ram_directory(root):
    if not os.path.isdir("/dev/shm") or not os.path.ismount("/dev/shm"):
        return None
    identity = hashlib.sha256(os.path.realpath(root).encode()).hexdigest()[:12]
    return os.path.join("/dev/shm", "bopos-" + identity)
