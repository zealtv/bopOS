"""Strict host-side storage and schema drift helpers for patch presets."""

from __future__ import annotations

import copy
import datetime as dt
import hashlib
import json
import math
import os
import re
import tempfile
import threading
from pathlib import Path

from python import manifest as patch_manifest
from python.paramgen import ParamGrammarError, parse_message


PRESET_VERSION = 1
PRESETS_DIR = "presets"
_PATCH_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*\Z")
_SLUG = re.compile(r"[\w-]{1,48}\Z")
_SCHEMA = re.compile(r"sha256:[0-9a-f]{64}\Z")
_RESERVED_ENTRY_WORDS = frozenset({"stop", "lfo", "loop", "morph"})


class PresetStoreError(ValueError):
    """A preset could not be safely read or written."""


class PresetConflictError(PresetStoreError):
    """A save used a stale revision or collided with another display name."""


def slugify(name):
    """Return the established 48-character preset filename slug."""
    if not isinstance(name, str):
        return ""
    return re.sub(r"[^\w-]", "-", name.strip())[:48]


def schema_projection(manifest):
    """Return the v1.17 canonical parameter-schema projection."""
    if not isinstance(manifest, dict) or not isinstance(manifest.get("params"), list):
        raise PresetStoreError("patch manifest params must be a list")
    projection = []
    for declaration in manifest["params"]:
        try:
            identity = patch_manifest.qualify_param(declaration)
        except ValueError as error:
            raise PresetStoreError(str(error)) from error
        kind = declaration.get("kind")
        options = (list(declaration["options"])
                   if kind == "enum" and isinstance(declaration.get("options"), list)
                   else None)
        projection.append({
            "identity": identity,
            "kind": kind,
            "min": declaration.get("min"),
            "max": declaration.get("max"),
            "options": options,
        })
    projection.sort(key=lambda item: item["identity"].encode("utf-8"))
    return projection


def schema_fingerprint(manifest):
    """Return the canonical ``sha256:<hex>`` schema fingerprint."""
    canonical = json.dumps(
        schema_projection(manifest),
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(canonical).hexdigest()


def _entry_identity(value):
    if not isinstance(value, str):
        raise PresetStoreError("preset parameter identities must be strings")
    parts = value.split("/")
    if (not 1 <= len(parts) <= patch_manifest.MAX_PARAM_SEGMENTS
            or len(value.encode("ascii", "ignore")) != len(value.encode("utf-8"))
            or len(value.encode("ascii")) > patch_manifest.MAX_PARAM_IDENTITY_BYTES
            or any(patch_manifest.PARAM_NAME.fullmatch(part) is None for part in parts)):
        raise PresetStoreError(f"bad preset parameter identity {value!r}")
    return value


def _entry_args(identity, args):
    if not isinstance(args, list) or not args:
        raise PresetStoreError(f"preset param {identity}: args must be a non-empty list")
    if len(args) == 1:
        value = args[0]
        if isinstance(value, str):
            if value in _RESERVED_ENTRY_WORDS:
                raise PresetStoreError(
                    f"preset param {identity}: incomplete or forbidden {value!r} form")
            return list(args)
        if (isinstance(value, bool) or not isinstance(value, (int, float))
                or not math.isfinite(value)):
            raise PresetStoreError(
                f"preset param {identity}: scalar must be a finite number or string")
        return list(args)
    if args[0] not in ("lfo", "loop"):
        raise PresetStoreError(
            f"preset param {identity}: only scalar, lfo, or loop full-state forms are allowed")
    try:
        spec = parse_message(args, "f")
    except ParamGrammarError as error:
        raise PresetStoreError(f"preset param {identity}: {error}") from error
    if spec.kind not in ("lfo", "loop"):
        raise PresetStoreError(
            f"preset param {identity}: only lfo or loop automation is full-state")
    return list(args)


def validate_document(candidate):
    """Validate one persisted document without consulting the current manifest."""
    if not isinstance(candidate, dict):
        raise PresetStoreError("preset must be a JSON object")
    required = {"bopos_preset", "name", "saved", "schema", "params"}
    if set(candidate) != required:
        raise PresetStoreError(
            "preset must contain only bopos_preset, name, saved, schema, and params")
    if (not isinstance(candidate["bopos_preset"], int)
            or isinstance(candidate["bopos_preset"], bool)
            or candidate["bopos_preset"] != PRESET_VERSION):
        raise PresetStoreError(
            f"unsupported bopos_preset version {candidate['bopos_preset']!r}")
    name = candidate["name"]
    if not isinstance(name, str) or not name.strip() or not slugify(name):
        raise PresetStoreError("preset name must produce a non-empty slug")
    saved = candidate["saved"]
    if not isinstance(saved, str):
        raise PresetStoreError("preset saved must be an ISO-8601 timestamp")
    try:
        parsed_saved = dt.datetime.fromisoformat(saved.replace("Z", "+00:00"))
    except ValueError as error:
        raise PresetStoreError("preset saved must be an ISO-8601 timestamp") from error
    if parsed_saved.tzinfo is None:
        raise PresetStoreError("preset saved timestamp must include a timezone")
    schema = candidate["schema"]
    if not isinstance(schema, str) or _SCHEMA.fullmatch(schema) is None:
        raise PresetStoreError("preset schema must be sha256:<64 lowercase hex>")
    params = candidate["params"]
    if not isinstance(params, dict):
        raise PresetStoreError("preset params must be an object")
    normalized_params = {}
    for raw_identity, raw_args in params.items():
        identity = _entry_identity(raw_identity)
        normalized_params[identity] = _entry_args(identity, raw_args)
    return {
        "bopos_preset": PRESET_VERSION,
        "name": name.strip(),
        "saved": saved,
        "schema": schema,
        "params": normalized_params,
    }


def _declarations(manifest):
    return {
        patch_manifest.qualify_param(declaration): declaration
        for declaration in manifest.get("params", ())
    }


def _bounded(value, declaration):
    low, high = declaration.get("min"), declaration.get("max")
    bounded = value
    if low is not None:
        bounded = max(low, bounded)
    if high is not None:
        bounded = min(high, bounded)
    return bounded


def _resolve_args(args, declaration):
    kind = declaration.get("kind")
    if len(args) == 1:
        value = args[0]
        if isinstance(value, str):
            if kind != "text":
                return None, False, "kind changed"
            return list(args), False, None
        if kind == "text":
            return None, False, "kind changed"
        bounded = _bounded(value, declaration)
        return [bounded], bounded != value, None
    if kind not in ("float", "int"):
        return None, False, "kind changed"
    resolved = list(args)
    value_indexes = (2, 3) if args[0] == "lfo" else range(1, len(args), 2)
    clamped = False
    for index in value_indexes:
        value = resolved[index]
        # A loop's optional trailing curve token can occupy an otherwise
        # destination-shaped index; parse_message already validated it.
        if isinstance(value, str):
            continue
        bounded = _bounded(value, declaration)
        resolved[index] = bounded
        clamped = clamped or bounded != value
    return resolved, clamped, None


def resolve_entries(params_or_document, manifest):
    """Resolve sparse preset entries against a current manifest.

    Returns resolved argument lists plus per-entry derived verdicts. A numeric
    scalar carries no redundant source-kind field in the file, so exact
    float/int/toggle/enum ancestry is intentionally not inferred; incompatible
    text/generator category changes are dropped.
    """
    params = (params_or_document.get("params")
              if isinstance(params_or_document, dict)
              and "bopos_preset" in params_or_document
              else params_or_document)
    if not isinstance(params, dict):
        raise PresetStoreError("preset params must be an object")
    declarations = _declarations(manifest)
    resolved = {}
    verdicts = {}
    counts = {"applied": 0, "clamped": 0, "dropped": 0}
    for identity, args in params.items():
        declaration = declarations.get(identity)
        if declaration is None:
            verdicts[identity] = {"status": "dropped", "reason": "identity absent"}
            counts["dropped"] += 1
            continue
        entry, clamped, reason = _resolve_args(args, declaration)
        if entry is None:
            verdicts[identity] = {"status": "dropped", "reason": reason}
            counts["dropped"] += 1
            continue
        resolved[identity] = entry
        status = "clamped" if clamped else "applied"
        verdicts[identity] = {"status": status}
        counts[status] += 1
    return {"params": resolved, "verdicts": verdicts, "counts": counts}


# A descriptive alias for callers that frame the operation as drift handling.
resolve_drift = resolve_entries


class PresetStore:
    """Atomic, compare-and-swap storage below ``patches/<patch>/presets``."""

    def __init__(self, patches_root):
        self.patches_root = os.path.realpath(os.fspath(patches_root))
        self._cache = {}
        self._lock = threading.RLock()

    @staticmethod
    def _stat_signature(stat):
        return (
            stat.st_dev,
            stat.st_ino,
            stat.st_mtime_ns,
            stat.st_ctime_ns,
            stat.st_size,
        )

    @staticmethod
    def _revision(raw):
        return "sha256:" + hashlib.sha256(raw).hexdigest()

    def _patch_root(self, patch):
        if not isinstance(patch, str) or _PATCH_NAME.fullmatch(patch) is None:
            raise PresetStoreError("invalid patch name")
        root = os.path.join(self.patches_root, patch)
        if os.path.islink(root) or not os.path.isdir(root):
            raise PresetStoreError("patch must be a real directory")
        if os.path.commonpath((self.patches_root, os.path.realpath(root))) != self.patches_root:
            raise PresetStoreError("patch escapes patches root")
        return root

    def _presets_root(self, patch, create=False):
        patch_root = self._patch_root(patch)
        root = os.path.join(patch_root, PRESETS_DIR)
        if os.path.lexists(root) and os.path.islink(root):
            raise PresetStoreError("presets directory must not be a symlink")
        if create:
            os.makedirs(root, exist_ok=True)
        if os.path.lexists(root) and not os.path.isdir(root):
            raise PresetStoreError("presets path must be a directory")
        if os.path.commonpath((os.path.realpath(patch_root), os.path.realpath(root))) \
                != os.path.realpath(patch_root):
            raise PresetStoreError("presets directory escapes patch root")
        return root

    def _path(self, patch, slug):
        if not isinstance(slug, str) or _SLUG.fullmatch(slug) is None:
            raise PresetStoreError("invalid preset slug")
        root = self._presets_root(patch)
        path = os.path.join(root, slug + ".json")
        if os.path.commonpath((os.path.realpath(root), os.path.realpath(path))) \
                != os.path.realpath(root):
            raise PresetStoreError("preset path escapes presets directory")
        return path

    def _read_path(self, path):
        if os.path.islink(path):
            raise PresetStoreError("preset file must not be a symlink")
        try:
            stat = os.stat(path, follow_symlinks=False)
        except FileNotFoundError as error:
            raise PresetStoreError("preset not found") from error
        if not os.path.isfile(path):
            raise PresetStoreError("preset path must be a file")
        signature = self._stat_signature(stat)
        cached = self._cache.get(path)
        if cached is not None and cached["signature"] == signature:
            return copy.deepcopy(cached["record"])
        try:
            raw = Path(path).read_bytes()
            candidate = json.loads(raw)
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise PresetStoreError(f"invalid preset JSON: {error}") from error
        document = validate_document(candidate)
        slug = Path(path).stem
        if slugify(document["name"]) != slug:
            raise PresetStoreError(
                "preset display name does not match its filename slug")
        record = {
            "slug": slug,
            "revision": self._revision(raw),
            "document": document,
        }
        self._cache[path] = {"signature": signature, "record": record}
        return copy.deepcopy(record)

    def _path_revision(self, path):
        if os.path.islink(path) or not os.path.isfile(path):
            return None
        try:
            return self._revision(Path(path).read_bytes())
        except OSError:
            return None

    def list(self, patch):
        """List JSON preset files, retaining invalid entries with errors."""
        with self._lock:
            root = self._presets_root(patch)
            if not os.path.isdir(root):
                return []
            result = []
            for filename in sorted(os.listdir(root)):
                if (filename.startswith(".") or filename.endswith(".part")
                        or not filename.endswith(".json")):
                    continue
                path = os.path.join(root, filename)
                slug = filename[:-5]
                try:
                    record = self._read_path(path)
                    document = record["document"]
                    result.append({
                        "slug": slug,
                        "name": document["name"],
                        "saved": document["saved"],
                        "schema": document["schema"],
                        "revision": record["revision"],
                        "valid": True,
                        "error": None,
                    })
                except PresetStoreError as error:
                    result.append({
                        "slug": slug,
                        "name": None,
                        "saved": None,
                        "schema": None,
                        "revision": self._path_revision(path),
                        "valid": False,
                        "error": str(error),
                    })
            return result

    def read(self, patch, slug):
        """Read and validate a preset, returning its document and revision."""
        with self._lock:
            return self._read_path(self._path(patch, slug))

    def save(self, patch, name, params, revision=None, now=None):
        """Create or compare-and-swap overwrite one preset."""
        display_name = name.strip() if isinstance(name, str) else ""
        slug = slugify(display_name)
        if not slug:
            raise PresetStoreError("preset name must produce a non-empty slug")
        if not isinstance(params, dict) or not params:
            raise PresetStoreError("cannot save an empty preset")
        patch_root = self._patch_root(patch)
        manifest, error = patch_manifest.load(patch_root)
        if error is not None:
            raise PresetStoreError(f"cannot fingerprint patch manifest: {error}")
        saved_at = now or dt.datetime.now(dt.timezone.utc)
        if not isinstance(saved_at, dt.datetime) or saved_at.tzinfo is None:
            raise PresetStoreError("save time must be a timezone-aware datetime")
        saved = saved_at.astimezone(dt.timezone.utc).isoformat(
            timespec="seconds").replace("+00:00", "Z")
        document = validate_document({
            "bopos_preset": PRESET_VERSION,
            "name": display_name,
            "saved": saved,
            "schema": schema_fingerprint(manifest),
            "params": params,
        })

        with self._lock:
            root = self._presets_root(patch, create=True)
            path = os.path.join(root, slug + ".json")
            if os.path.lexists(path):
                current = self._read_path(path)
                if current["document"]["name"] != display_name:
                    raise PresetConflictError(
                        f"preset slug {slug!r} already belongs to "
                        f"{current['document']['name']!r}")
                if revision is None or revision != current["revision"]:
                    raise PresetConflictError("preset revision is stale")
            elif revision is not None:
                raise PresetConflictError("preset no longer exists")

            temporary = None
            try:
                fd, temporary = tempfile.mkstemp(
                    prefix=f".{slug}.", suffix=".part", dir=root)
                with os.fdopen(fd, "w", encoding="utf-8") as target:
                    json.dump(document, target, indent=2, ensure_ascii=False,
                              allow_nan=False)
                    target.write("\n")
                    target.flush()
                    os.fsync(target.fileno())
                os.replace(temporary, path)
                temporary = None
                self._cache.pop(path, None)
                return self._read_path(path)
            except (OSError, TypeError, ValueError) as write_error:
                raise PresetStoreError(f"could not write preset: {write_error}") \
                    from write_error
            finally:
                if temporary is not None:
                    try:
                        os.unlink(temporary)
                    except OSError:
                        pass

    def delete(self, patch, slug, revision=None):
        """Delete a preset, optionally refusing a stale revision token."""
        with self._lock:
            path = self._path(patch, slug)
            current_revision = self._path_revision(path)
            if current_revision is None:
                raise PresetStoreError("preset must be a real file")
            if revision is not None and revision != current_revision:
                raise PresetConflictError("preset revision is stale")
            try:
                os.unlink(path)
            except OSError as error:
                raise PresetStoreError(f"could not delete preset: {error}") from error
            self._cache.pop(path, None)
            return True
