"""Convergent asset and patch fetching for bopOS nodes."""

import hashlib
import json
import os
import shutil
import tempfile
import urllib.parse
import urllib.request

try:
    from . import manifest as patch_manifest
    from . import identity
except ImportError:
    import manifest as patch_manifest
    import identity


def _valid_patch_slot(slot):
    return (isinstance(slot, str) and bool(slot)
            and all(char.isascii() and (char.isalnum() or char in "_-") for char in slot))


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_path(path):
    if not isinstance(path, str) or not path or "\x00" in path:
        raise ValueError("path must be a non-empty string")
    path = path.replace("\\", "/")
    if path.startswith("/") or os.path.isabs(path) or (len(path) >= 2 and path[1] == ":"):
        raise ValueError("absolute paths are not allowed")
    parts = path.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise ValueError("path contains an unsafe component")
    return os.path.join(*parts)


def parse_manifest(value):
    if isinstance(value, (bytes, bytearray, str)):
        try:
            value = json.loads(value)
        except (TypeError, ValueError) as error:
            raise ValueError("invalid manifest JSON: {}".format(error))
    if not isinstance(value, dict) or set(value) != {"files"}:
        raise ValueError("manifest must contain only a files member")
    if not isinstance(value["files"], list):
        raise ValueError("manifest files must be a list")
    result = []
    seen = set()
    for item in value["files"]:
        if not isinstance(item, dict) or set(item) != {"path", "size", "sha256"}:
            raise ValueError("each file needs path, size, and sha256")
        relative = safe_path(item["path"])
        size = item["size"]
        digest = item["sha256"]
        if isinstance(size, bool) or not isinstance(size, int) or size < 0:
            raise ValueError("file size must be a non-negative integer")
        if (not isinstance(digest, str) or len(digest) != 64
                or any(char not in "0123456789abcdefABCDEF" for char in digest)):
            raise ValueError("file sha256 must be 64 hexadecimal characters")
        key = relative.replace(os.sep, "/")
        if key in seen:
            raise ValueError("duplicate manifest path: {}".format(key))
        seen.add(key)
        result.append({"path": relative, "size": size, "sha256": digest.lower()})
    return result


def file_matches(path, item):
    try:
        return os.path.getsize(path) == item["size"] and sha256(path) == item["sha256"]
    except OSError:
        return False


def plan_file(path, item):
    return "skip" if file_matches(path, item) else "download"


def _prune(root, wanted):
    if not os.path.isdir(root):
        return
    wanted = {os.path.normpath(path) for path in wanted}
    for directory, dirs, files in os.walk(root, topdown=False):
        for name in files:
            path = os.path.join(directory, name)
            relative = os.path.normpath(os.path.relpath(path, root))
            if relative not in wanted:
                os.remove(path)
        for name in dirs:
            path = os.path.join(directory, name)
            try:
                os.rmdir(path)
            except OSError:
                pass


def _reject_symlinks(root, allowed=None):
    """Refuse convergence through any existing destination symlink."""
    allowed = allowed or {}
    if os.path.islink(root):
        raise ValueError("destination must not be a symlink")
    if not os.path.isdir(root):
        return
    for directory, dirs, files in os.walk(root, followlinks=False):
        for name in dirs + files:
            path = os.path.join(directory, name)
            if not os.path.islink(path):
                continue
            expected = allowed.get(os.path.abspath(path))
            if expected is None or os.path.realpath(path) != os.path.realpath(expected):
                raise ValueError("destination contains a symlink")


def _download(url, target, item):
    part = target + ".part"
    for _attempt in range(3):
        try:
            part_exists = os.path.isfile(part)
            offset = os.path.getsize(part) if part_exists else 0
            if part_exists and offset >= item["size"]:
                os.remove(part)
                offset = 0
            request = urllib.request.Request(url)
            if offset:
                request.add_header("Range", "bytes={}-".format(offset))
            with urllib.request.urlopen(request, timeout=30) as response:
                append = offset > 0 and getattr(response, "status", response.getcode()) == 206
                with open(part, "ab" if append else "wb") as output:
                    shutil.copyfileobj(response, output, 1024 * 1024)
            if file_matches(part, item):
                os.replace(part, target)
                return True
        except Exception:
            continue
    return False


def _http_fetch(uri, destination, cache_root=None):
    with urllib.request.urlopen(uri, timeout=30) as response:
        files = parse_manifest(response.read())
    os.makedirs(destination, exist_ok=True)
    for item in files:
        target = os.path.join(destination, item["path"])
        if plan_file(target, item) == "skip":
            continue
        os.makedirs(os.path.dirname(target), exist_ok=True)
        url_path = item["path"].replace(os.sep, "/")
        quoted_path = urllib.parse.quote(url_path, safe="/")
        if not _download(urllib.parse.urljoin(uri, quoted_path), target, item):
            return False, "failed to fetch {}".format(url_path)
    _prune(destination, [item["path"] for item in files])
    if cache_root is not None:
        identity.seed_hashes(cache_root, destination, files)
    return True, "fetched {} files".format(len(files))


def _file_fetch(uri, destination, cache_root=None):
    parsed = urllib.parse.urlparse(uri)
    if parsed.netloc not in ("", "localhost"):
        raise ValueError("file URI host is not local")
    source = urllib.request.url2pathname(parsed.path)
    if not os.path.isdir(source):
        raise ValueError("file source is not a directory")
    files = []
    for directory, dirs, names in os.walk(source):
        dirs[:] = [name for name in dirs if not name.startswith(".")]
        for name in names:
            if name.startswith(".") or name.endswith(".part"):
                continue
            source_path = os.path.join(directory, name)
            relative = safe_path(os.path.relpath(source_path, source))
            files.append({"path": relative, "size": os.path.getsize(source_path),
                          "sha256": sha256(source_path)})
    os.makedirs(destination, exist_ok=True)
    for item in files:
        target = os.path.join(destination, item["path"])
        if plan_file(target, item) == "skip":
            continue
        os.makedirs(os.path.dirname(target), exist_ok=True)
        part = target + ".part"
        shutil.copyfile(os.path.join(source, item["path"]), part)
        if not file_matches(part, item):
            return False, "failed to verify {}".format(item["path"])
        os.replace(part, target)
    _prune(destination, [item["path"] for item in files])
    if cache_root is not None:
        identity.seed_hashes(cache_root, destination, files)
    return True, "synced {} files".format(len(files))


def _landing(slot, assets_root, patches_root):
    if slot.startswith("patch:"):
        name = slot[len("patch:"):]
        if not _valid_patch_slot(name):
            raise ValueError("invalid patch name")
        root = patches_root or os.path.join(os.path.dirname(assets_root), "patches")
        destination = os.path.join(root, name)
        # A strict name already excludes traversal. The realpath check also
        # refuses a pre-existing symlink that would make convergence prune
        # files outside the framework's patches root.
        if os.path.commonpath((os.path.realpath(root), os.path.realpath(destination))) \
                != os.path.realpath(root):
            raise ValueError("patch destination escapes patches root")
        if os.path.lexists(destination) and not os.path.isdir(destination):
            raise ValueError("patch destination must be a directory")
        if os.path.lexists(os.path.join(destination, ".git")):
            raise ValueError("refusing to fetch over a git-managed patch")
        return destination, True
    if not identity.valid_asset_slot(slot):
        raise ValueError("invalid slot")
    return os.path.join(assets_root, slot), False


def _converge(uri, destination, scheme, cache_root=None):
    if scheme in ("http", "https"):
        return _http_fetch(uri, destination, cache_root)
    if scheme == "file":
        return _file_fetch(uri, destination, cache_root)
    return False, "unsupported URI scheme"


def _patch_fetch(uri, destination, scheme, assets_root):
    """Converge and validate off to the side, then atomically replace."""
    root = os.path.dirname(destination)
    os.makedirs(root, exist_ok=True)
    legacy_link = os.path.join(destination, "bop", "samplepacks")
    legacy_target = os.path.join(assets_root, "samplepacks")
    allowed = ({os.path.abspath(legacy_link): legacy_target}
               if os.path.islink(legacy_link) else {})
    _reject_symlinks(destination, allowed)
    staging = tempfile.mkdtemp(prefix=".fetch-{}-".format(os.path.basename(destination)),
                               dir=root)
    backup = None
    try:
        if os.path.isdir(destination):
            def ignore_legacy(directory, names):
                if (os.path.realpath(directory)
                        == os.path.realpath(os.path.join(destination, "bop"))
                        and "samplepacks" in names
                        and os.path.islink(os.path.join(directory, "samplepacks"))):
                    return {"samplepacks"}
                return set()

            shutil.copytree(destination, staging, dirs_exist_ok=True,
                            ignore=ignore_legacy)
        ok, detail = _converge(uri, staging, scheme)
        if not ok:
            return ok, detail
        _value, error = patch_manifest.load(staging)
        if error is not None:
            return False, "fetched patch manifest invalid: {}".format(error)
        if os.path.isdir(destination):
            backup = tempfile.mkdtemp(
                prefix=".previous-{}-".format(os.path.basename(destination)), dir=root)
            os.rmdir(backup)
            os.replace(destination, backup)
        try:
            os.replace(staging, destination)
            staging = None
        except Exception:
            if backup is not None and not os.path.lexists(destination):
                os.replace(backup, destination)
                backup = None
            raise
        if backup is not None:
            shutil.rmtree(backup, ignore_errors=True)
            backup = None
        return True, detail
    finally:
        if staging is not None:
            shutil.rmtree(staging, ignore_errors=True)
        if backup is not None and os.path.isdir(backup):
            if not os.path.lexists(destination):
                os.replace(backup, destination)
            else:
                shutil.rmtree(backup, ignore_errors=True)


def fetch(uri, slot, assets_root, patches_root=None):
    try:
        if not isinstance(uri, str):
            raise ValueError("URI must be a string")
        if not isinstance(slot, str):
            raise ValueError("slot must be a string")
        destination, is_patch = _landing(slot, assets_root, patches_root)
        scheme = urllib.parse.urlparse(uri).scheme.lower()
        if is_patch:
            return _patch_fetch(uri, destination, scheme, assets_root)
        _reject_symlinks(destination)
        return _converge(uri, destination, scheme, assets_root)
    except Exception as error:
        return False, str(error)
