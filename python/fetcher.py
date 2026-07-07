"""Convergent asset fetching for bopOS nodes."""

import hashlib
import json
import os
import shutil
import subprocess
import urllib.parse
import urllib.request


def _valid_slot(slot):
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


def _http_fetch(uri, destination):
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
    return True, "fetched {} files".format(len(files))


def _file_fetch(uri, destination):
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
    return True, "synced {} files".format(len(files))


def fetch(uri, slot, assets_root):
    try:
        if not isinstance(uri, str):
            raise ValueError("URI must be a string")
        if not _valid_slot(slot):
            raise ValueError("invalid slot")
        destination = os.path.join(assets_root, slot)
        scheme = urllib.parse.urlparse(uri).scheme.lower()
        if scheme in ("http", "https"):
            return _http_fetch(uri, destination)
        if scheme == "file":
            return _file_fetch(uri, destination)
        if scheme == "gdrive":
            if slot != "samplepacks":
                raise ValueError("gdrive requires the samplepacks slot")
            script = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))),
                                  "bash", "getsamples.sh")
            result = subprocess.run(["bash", script])
            return (result.returncode == 0,
                    "getsamples exit {}".format(result.returncode))
        return False, "unsupported URI scheme"
    except Exception as error:
        return False, str(error)
