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

# per-file digests keyed by path, invalidated by stat signature, so repeated
# fingerprints (a Zero answering /os/patches) re-hash only changed files
_file_hashes = {}


def directory_manifest(root):
    """Return the canonical {"files": [{path, size, sha256}, ...]} manifest."""
    files = []
    for directory, dirs, names in os.walk(root):
        dirs[:] = sorted(name for name in dirs
                         if not name.startswith(".")
                         and not os.path.islink(os.path.join(directory, name)))
        for name in sorted(names):
            if (name.startswith(".") or name.endswith(".part")
                    or os.path.islink(os.path.join(directory, name))):
                continue
            path = os.path.join(directory, name)
            stat = os.stat(path)
            signature = (stat.st_ino, stat.st_mtime_ns, stat.st_ctime_ns, stat.st_size)
            cached = _file_hashes.get(path)
            if cached is None or cached[0] != signature:
                hasher = hashlib.sha256()
                with open(path, "rb") as source:
                    for chunk in iter(lambda: source.read(1024 * 1024), b""):
                        hasher.update(chunk)
                digest = hasher.hexdigest()
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


def fingerprint(root):
    return manifest_fingerprint(directory_manifest(root))
