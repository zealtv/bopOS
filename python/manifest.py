# manifest.py
"""
bopos.patch.json loader/validator (OSC contract section 8).

One validator, three consumers: bopos.py (/os/params, /os/report, /patch
validation), bash/start-engine.sh (CLI mode below), and tests. The manifest
is the single source of truth for what starts a patch and what can be
controlled; validation exists so it can't silently drift.
"""

import json
import math
import os
import re
import sys
import tempfile

MANIFEST_NAME = "bopos.patch.json"
PARAM_NAME = re.compile(r"[A-Za-z0-9_-]+")
PARAM_TYPES = ("i", "f", "s")
CUE_ID = re.compile(r"[^\x00\r\n]{1,64}")


def raw(patch_path):
    """Verbatim manifest text, or None. /os/params serves exactly this."""
    try:
        with open(os.path.join(patch_path, MANIFEST_NAME)) as source:
            return source.read()
    except OSError:
        return None


def validate(candidate, patch_path, require_entrypoint=True):
    """Validate an in-memory manifest candidate for ``patch_path``.

    The dashboard editor uses this before replacing the on-disk manifest, so
    the exact same rules govern authored and loaded manifests.  New-patch may
    set ``require_entrypoint=False`` only when Bob's PD template is absent;
    the resulting manifest stays structurally valid but the patch catalog
    correctly reports it unlaunchable until ``main.pd`` is supplied.
    """
    if not isinstance(candidate, dict):
        return None, f"{MANIFEST_NAME} must be a JSON object"
    # Validation supplies the normalized engine value, but never mutates a
    # caller-owned dictionary while deciding whether it is safe to write.
    manifest = dict(candidate)
    if not isinstance(manifest, dict):
        return None, f"{MANIFEST_NAME} must be a JSON object"

    engine = manifest.get("engine", "pd")
    if not isinstance(engine, str) or not engine.strip():
        return None, "engine must be a non-empty string"
    manifest["engine"] = engine.strip()

    entrypoint = manifest.get("entrypoint")
    if not isinstance(entrypoint, str) or not entrypoint.strip():
        return None, "entrypoint must be a non-empty string"
    entrypoint = entrypoint.strip()
    normalized_entrypoint = os.path.normpath(entrypoint)
    if (os.path.isabs(entrypoint) or normalized_entrypoint == ".."
            or normalized_entrypoint.startswith(".." + os.sep)):
        return None, "entrypoint must stay inside the patch directory"
    patch_root = os.path.realpath(patch_path)
    resolved_entrypoint = os.path.realpath(
        os.path.join(patch_path, normalized_entrypoint))
    try:
        contained = os.path.commonpath((patch_root, resolved_entrypoint)) == patch_root
    except ValueError:
        contained = False
    if not contained:
        return None, "entrypoint must resolve inside the patch directory"
    manifest["entrypoint"] = entrypoint
    if (require_entrypoint
            and not os.path.isfile(os.path.join(patch_path, normalized_entrypoint))):
        return None, f"entrypoint {entrypoint!r} not found in {patch_path}"

    params = manifest.get("params", [])
    if not isinstance(params, list):
        return None, "params must be a list"
    param_names = set()
    for param in params:
        if not isinstance(param, dict):
            return None, f"param {param!r} must be an object"
        name = param.get("name")
        if not isinstance(name, str) or PARAM_NAME.fullmatch(name) is None:
            return None, f"bad param name {name!r}"
        if name in param_names:
            return None, f"duplicate param name {name!r}"
        param_names.add(name)
        if param.get("type") not in PARAM_TYPES:
            return None, f"param {name}: type must be one of {'/'.join(PARAM_TYPES)}"
        low, high, default = param.get("min"), param.get("max"), param.get("default")
        numbers = [v for v in (low, high, default) if v is not None]
        if any(not isinstance(v, (int, float)) or isinstance(v, bool)
               or not math.isfinite(v) for v in numbers):
            return None, f"param {name}: min/max/default must be numbers"
        if low is not None and high is not None and low > high:
            return None, f"param {name}: min {low} > max {high}"
        if default is not None:
            if low is not None and default < low:
                return None, f"param {name}: default {default} below min {low}"
            if high is not None and default > high:
                return None, f"param {name}: default {default} above max {high}"
        if "role" in param:
            return None, (f"param {name}: role was removed (2026-07-12); "
                          "facilitator controls come from facilitator:true, "
                          "inspection from /report")
        facilitator = param.get("facilitator")
        if facilitator is not None and not isinstance(facilitator, bool):
            return None, f"param {name}: facilitator must be true or false"
        if "group" in param and not isinstance(param["group"], str):
            return None, f"param {name}: group must be a string"

    cues = manifest.get("cues", [])
    if not isinstance(cues, list):
        return None, "cues must be a list"
    cue_ids = set()
    for cue in cues:
        if not isinstance(cue, dict):
            return None, f"cue {cue!r} must be an object"
        cue_id = cue.get("id")
        if not isinstance(cue_id, str):
            return None, f"cue id {cue_id!r} must be a string"
        if CUE_ID.fullmatch(cue_id) is None:
            return None, f"cue id {cue_id!r}: use 1–64 characters without newlines"
        if cue_id in cue_ids:
            return None, f"duplicate cue id {cue_id!r}"
        cue_ids.add(cue_id)
        for field in ("label", "description"):
            if field in cue and not isinstance(cue[field], str):
                return None, f"cue {cue_id!r}: {field} must be a string"

    for key, kind in (("caps", "caps"), ("slots", "slots")):
        values = manifest.get(key, [])
        if not isinstance(values, list) or any(not isinstance(v, str) for v in values):
            return None, f"{kind} must be a list of strings"

    return manifest, None


def load(patch_path):
    """Return (manifest-dict, error-string). Exactly one of them is None."""
    text = raw(patch_path)
    if text is None:
        return None, f"no {MANIFEST_NAME} in {patch_path}"
    try:
        candidate = json.loads(text)
    except ValueError as error:
        return None, f"{MANIFEST_NAME} is not valid JSON: {error}"
    return validate(candidate, patch_path)


def write_atomic(patch_path, candidate, require_entrypoint=True):
    """Validate and atomically replace a patch manifest.

    Returns the normalized manifest and ``None`` on success, or ``None`` and
    an error without changing the destination.  The temporary file lives in
    the patch directory so ``os.replace`` is an atomic same-filesystem rename.
    """
    manifest, error = validate(candidate, patch_path, require_entrypoint)
    if manifest is None:
        return None, error
    destination = os.path.join(patch_path, MANIFEST_NAME)
    temporary = None
    try:
        fd, temporary = tempfile.mkstemp(
            prefix=f".{MANIFEST_NAME}.", suffix=".part", dir=patch_path)
        with os.fdopen(fd, "w", encoding="utf-8") as target:
            json.dump(manifest, target, indent=2, ensure_ascii=False,
                      allow_nan=False)
            target.write("\n")
            target.flush()
            os.fsync(target.fileno())
        os.replace(temporary, destination)
        temporary = None
        return manifest, None
    except (OSError, TypeError, ValueError) as write_error:
        return None, f"could not write {MANIFEST_NAME}: {write_error}"
    finally:
        if temporary is not None:
            try:
                os.unlink(temporary)
            except OSError:
                pass


def warnings(manifest):
    """Non-fatal advisories for a manifest that load() accepted."""
    notes = []
    params = manifest.get("params", [])
    if params and not any(param.get("facilitator") is True for param in params):
        notes.append("no param with facilitator:true: "
                     "the facilitator device card will be status-only")
    return notes


def main():
    """CLI for the launcher: prints eval-able ENGINE=/ENTRYPOINT= lines.

    Exit 0: valid manifest. Exit 1: missing or invalid manifest. Contract
    v1.3 makes the manifest mandatory, so this CLI never emits fallback launch
    values.
    """
    patch_path = sys.argv[1]
    manifest, error = load(patch_path)
    if manifest is not None:
        print(f"ENGINE='{manifest['engine']}'")
        print(f"ENTRYPOINT='{manifest['entrypoint']}'")
        for note in warnings(manifest):
            print(f"manifest: warning: {note}", file=sys.stderr)
        return 0
    print(f"manifest: {error}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
