"""Canonical directory identity shared by the host catalog and the nodes.

One walk, one fingerprint: the dashboard's distribution catalog and each
node's /os/patches listing compute content identity from the same code, so
the same bytes always yield the same 64-hex value (contract sec 7). The walk
excludes dot-prefixed entries (which covers .git), symlinks, and in-flight
.part files -- exactly what the host serves for fetch.
"""

import hashlib
import json
import os
import threading
import time

# per-file digests keyed by path, invalidated by stat signature, so repeated
# fingerprints (a Zero answering /os/patches) re-hash only changed files
_file_hashes = {}
_cache_lock = threading.RLock()


def _signature(stat):
    return (stat.st_ino, stat.st_mtime_ns, stat.st_ctime_ns, stat.st_size)


def _walk_files(root):
    """Yield canonical-walk files as (absolute path, stat)."""
    for directory, dirs, names in os.walk(root):
        dirs[:] = sorted(name for name in dirs
                         if not name.startswith(".")
                         and not os.path.islink(os.path.join(directory, name)))
        for name in sorted(names):
            if (name.startswith(".") or name.endswith(".part")
                    or os.path.islink(os.path.join(directory, name))):
                continue
            path = os.path.join(directory, name)
            yield path, os.stat(path)


def _cache_path(root):
    return os.path.join(os.path.abspath(root), ".hashcache.json")


def load_hash_cache(root):
    """Load and garbage-collect the persistent cache for an assets root."""
    root = os.path.abspath(root)
    try:
        with open(_cache_path(root)) as source:
            value = json.load(source)
    except (OSError, TypeError, ValueError):
        value = {}
    entries = value.get("files", {}) if isinstance(value, dict) else {}
    loaded = 0
    with _cache_lock:
        prefix = root + os.sep
        for path in list(_file_hashes):
            if path.startswith(prefix):
                del _file_hashes[path]
        if isinstance(entries, dict):
            for relative, entry in entries.items():
                if not isinstance(relative, str) or not isinstance(entry, dict):
                    continue
                path = os.path.abspath(os.path.join(root, relative.replace("/", os.sep)))
                signature = entry.get("signature")
                digest = entry.get("sha256")
                if (not path.startswith(prefix) or not os.path.isfile(path)
                        or os.path.islink(path) or not isinstance(signature, list)
                        or len(signature) != 4 or not isinstance(digest, str)
                        or len(digest) != 64
                        or any(char not in "0123456789abcdef" for char in digest.lower())):
                    continue
                try:
                    current = _signature(os.stat(path))
                except OSError:
                    continue
                if tuple(signature) == current:
                    _file_hashes[path] = (current, digest.lower())
                    loaded += 1
    # Rewriting also removes stale/deleted and malformed entries.
    save_hash_cache(root)
    return loaded


def save_hash_cache(root):
    """Atomically persist valid entries below an assets root."""
    root = os.path.abspath(root)
    os.makedirs(root, exist_ok=True)
    prefix = root + os.sep
    files = {}
    with _cache_lock:
        for path, (signature, digest) in _file_hashes.items():
            if not path.startswith(prefix) or not os.path.isfile(path):
                continue
            relative = os.path.relpath(path, root).replace(os.sep, "/")
            if any(part.startswith(".") for part in relative.split("/")):
                continue
            files[relative] = {"signature": list(signature), "sha256": digest}
        target = _cache_path(root)
        temporary = target + ".tmp"
        with open(temporary, "w") as output:
            json.dump({"version": 1, "files": files}, output,
                      sort_keys=True, separators=(",", ":"))
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, target)


def seed_hashes(root, directory, files):
    """Seed verified manifest hashes without reading file contents again."""
    root = os.path.abspath(root)
    directory = os.path.abspath(directory)
    prefix = root + os.sep
    with _cache_lock:
        for item in files:
            path = os.path.abspath(os.path.join(directory, item["path"]))
            if not path.startswith(prefix) or not os.path.isfile(path) or os.path.islink(path):
                continue
            _file_hashes[path] = (_signature(os.stat(path)), item["sha256"].lower())
    save_hash_cache(root)


def cached_directory_info(root):
    """Return fresh size/counts and a fingerprint only when fully cached.

    This function never reads file contents, so it is safe on the OSC reply
    path. A changed stat signature makes the fingerprint unknown until warm.
    """
    files = []
    complete = True
    total = 0
    with _cache_lock:
        for path, stat in _walk_files(root):
            total += stat.st_size
            cached = _file_hashes.get(path)
            if cached is None or cached[0] != _signature(stat):
                complete = False
                digest = None
            else:
                digest = cached[1]
            files.append({"path": os.path.relpath(path, root).replace(os.sep, "/"),
                          "size": stat.st_size, "sha256": digest})
    fingerprint_value = None
    if complete:
        fingerprint_value = manifest_fingerprint({"files": files})
    return {"fingerprint": fingerprint_value, "files": len(files), "bytes": total}


def warm_hash_cache(root):
    """Hash missing/changed files below root and persist the result."""
    # Yield after each MiB. Regular host/patch fingerprint calls retain their
    # unthrottled behavior; only the node's background asset warm pays this.
    directory_manifest(root, chunk_delay=0.01)
    save_hash_cache(root)


def directory_manifest(root, chunk_delay=0):
    """Return the canonical {"files": [{path, size, sha256}, ...]} manifest."""
    files = []
    for path, stat in _walk_files(root):
        signature = _signature(stat)
        with _cache_lock:
            cached = _file_hashes.get(path)
        if cached is None or cached[0] != signature:
            hasher = hashlib.sha256()
            with open(path, "rb") as source:
                for chunk in iter(lambda: source.read(1024 * 1024), b""):
                    hasher.update(chunk)
                    if chunk_delay:
                        time.sleep(chunk_delay)
            digest = hasher.hexdigest()
            with _cache_lock:
                _file_hashes[path] = (signature, digest)
        else:
            digest = cached[1]
        files.append({"path": os.path.relpath(path, root).replace(os.sep, "/"),
                      "size": stat.st_size, "sha256": digest})
    files.sort(key=lambda item: item["path"])
    return {"files": files}


def manifest_fingerprint(manifest):
    """sha256 of the canonical-JSON manifest -- the wire/catalog identity."""
    canonical = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(canonical).hexdigest()


def valid_asset_slot(value):
    """Return whether value safely names one visible assets/ child.

    Inventory observes every top-level non-dot directory, so fetch and removal
    accept that same namespace rather than a narrower ASCII token grammar.
    Patch names retain their separate, stricter grammar.
    """
    return (isinstance(value, str) and bool(value) and not value.startswith(".")
            and "/" not in value and "\\" not in value and "\x00" not in value)


def fingerprint(root):
    return manifest_fingerprint(directory_manifest(root))
