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
PARAM_KINDS = {
    "float": "f",
    "int": "i",
    "toggle": "i",
    "enum": "i",
    "text": "s",
}
MAX_PARAM_SEGMENTS = 8
MAX_PARAM_IDENTITY_BYTES = 255
# An enum is an integer parameter that names its indices; the wire stays
# `/p/<identity> <int>` (contract §3.2, unchanged). 64 is a UI bound, not a
# protocol one: a select longer than that wants a different control.
MAX_PARAM_OPTIONS = 64
OPTION_LABEL = re.compile(r"[^\x00\r\n]{1,32}")
# Events use the targetable `<target>/e/*` plane. Zero-element events are
# momentary named fires; one to three elements carry patch-defined floats.
MAX_EVENT_ARITY = 3
_MISSING = object()


def param_wire_type(declaration):
    """Return the unchanged OSC scalar tag for a validated control kind."""
    if not isinstance(declaration, dict):
        return None
    return PARAM_KINDS.get(declaration.get("kind"))


def qualify_param(declaration):
    """Return the canonical slash-joined identity for one parameter.

    ``name`` remains the leaf and optional ``path`` entries are its structural
    parents.  This is the one qualification/validation boundary shared by
    manifest consumers; it deliberately defines no escaping or normalization.
    """
    if not isinstance(declaration, dict):
        raise ValueError(f"param {declaration!r} must be an object")
    name = declaration.get("name")
    if not isinstance(name, str) or PARAM_NAME.fullmatch(name) is None:
        raise ValueError(f"bad param name {name!r}")
    path = declaration.get("path", [])
    if not isinstance(path, list):
        raise ValueError(f"param {name}: path must be a list")
    for segment in path:
        if not isinstance(segment, str) or PARAM_NAME.fullmatch(segment) is None:
            raise ValueError(f"param {name}: bad path segment {segment!r}")
    segments = [*path, name]
    if len(segments) > MAX_PARAM_SEGMENTS:
        raise ValueError(
            f"param {name}: qualified identity exceeds {MAX_PARAM_SEGMENTS} segments")
    identity = "/".join(segments)
    if len(identity.encode("ascii")) > MAX_PARAM_IDENTITY_BYTES:
        raise ValueError(
            f"param {name}: qualified identity exceeds {MAX_PARAM_IDENTITY_BYTES} bytes")
    return identity


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
    normalized_params = []
    param_identities = set()
    for original in params:
        if not isinstance(original, dict):
            return None, f"param {original!r} must be an object"
        param = dict(original)
        legacy_dashboard = param.pop("facilitator", _MISSING)
        if legacy_dashboard is not _MISSING and not isinstance(legacy_dashboard, bool):
            return None, f"param {param.get('name')}: facilitator must be true or false"
        if ("dashboard" in param and legacy_dashboard is not _MISSING
                and param["dashboard"] != legacy_dashboard):
            return None, (f"param {param.get('name')!r}: dashboard and legacy "
                          "facilitator values conflict")
        if "dashboard" not in param and legacy_dashboard is not _MISSING:
            param["dashboard"] = legacy_dashboard
        # ``group`` was presentation-only. Accept old manifests, but do not
        # preserve it in the normalized model or any subsequent save.
        param.pop("group", None)
        try:
            identity = qualify_param(param)
        except ValueError as error:
            return None, str(error)
        name = param["name"]
        if identity in param_identities:
            return None, f"duplicate param identity {identity!r}"
        param_identities.add(identity)
        if "type" in param:
            return None, (f"param {name}: type was removed (2026-07-28); "
                          f"use kind ({'/'.join(PARAM_KINDS)})")
        kind = param.get("kind")
        if kind not in PARAM_KINDS:
            return None, f"param {name}: kind must be one of {'/'.join(PARAM_KINDS)}"
        options = param.get("options")
        if kind == "enum":
            if (not isinstance(options, list)
                    or not 2 <= len(options) <= MAX_PARAM_OPTIONS):
                return None, (f"param {name}: options must be a list of 2–"
                              f"{MAX_PARAM_OPTIONS} labels")
            if any(not isinstance(label, str)
                   or OPTION_LABEL.fullmatch(label) is None for label in options):
                return None, (f"param {name}: each option must be 1–32 characters "
                              "without newlines")
            if len(set(options)) != len(options):
                return None, f"param {name}: option labels must be unique"
            # The indices are the value range, so min/max are derived rather
            # than authored. Accepting a matching pair keeps a round-tripped
            # manifest (the editor saves what it loaded) valid.
            for key, derived in (("min", 0), ("max", len(options) - 1)):
                if param.get(key) is None:
                    param[key] = derived
                elif param[key] != derived:
                    return None, (f"param {name}: {key} is derived from options "
                                  f"({derived}), not authored")
        elif options is not None:
            return None, f"param {name}: options only apply to kind enum"
        if kind == "toggle":
            authored_bounds = [key for key in ("min", "max") if key in param]
            if authored_bounds:
                return None, (f"param {name}: {'/'.join(authored_bounds)} "
                              "is derived for kind toggle, not authored")
            param["min"], param["max"] = 0, 1
        low, high, default = param.get("min"), param.get("max"), param.get("default")
        if kind == "text":
            if "min" in param or "max" in param:
                return None, f"param {name}: min/max do not apply to kind text"
            if default is not None and not isinstance(default, str):
                return None, f"param {name}: text default must be a string"
        else:
            numbers = [v for v in (low, high, default) if v is not None]
            if any(not isinstance(v, (int, float)) or isinstance(v, bool)
                   or not math.isfinite(v) for v in numbers):
                return None, f"param {name}: min/max/default must be numbers"
        if kind == "enum" and default is not None and default != int(default):
            return None, f"param {name}: default {default} is not an option index"
        if kind == "toggle" and default is not None and default not in (0, 1):
            return None, f"param {name}: toggle default must be 0 or 1"
        if low is not None and high is not None and low > high:
            return None, f"param {name}: min {low} > max {high}"
        if default is not None:
            if low is not None and default < low:
                return None, f"param {name}: default {default} below min {low}"
            if high is not None and default > high:
                return None, f"param {name}: default {default} above max {high}"
        if "role" in param:
            return None, (f"param {name}: role was removed (2026-07-12); "
                          "dashboard controls come from dashboard:true, "
                          "inspection from /report")
        dashboard = param.get("dashboard")
        if dashboard is not None and not isinstance(dashboard, bool):
            return None, f"param {name}: dashboard must be true or false"
        normalized_params.append(param)
    manifest["params"] = normalized_params

    events = manifest.get("events", [])
    if not isinstance(events, list):
        return None, "events must be a list"
    normalized_events = []
    event_identities = set()
    for original in events:
        if not isinstance(original, dict):
            return None, f"event {original!r} must be an object"
        event = dict(original)
        try:
            identity = qualify_param(event)
        except ValueError as error:
            return None, str(error)
        name = event["name"]
        if identity in event_identities:
            return None, f"duplicate event identity {identity!r}"
        event_identities.add(identity)
        arity = event.get("arity", 1)
        if (not isinstance(arity, int) or isinstance(arity, bool)
                or not 0 <= arity <= MAX_EVENT_ARITY):
            return None, f"event {name}: arity must be 0, 1, 2 or {MAX_EVENT_ARITY}"
        event["arity"] = arity
        # Per-element labels were retired 2026-07-28 (Bob): an event carries
        # one label, its name, and elements are numbered floats. Older
        # manifests are cleaned on read rather than rejected.
        event.pop("labels", None)
        defaults = event.get("defaults")
        if defaults is not None:
            if (not isinstance(defaults, list) or len(defaults) != arity
                    or any(not isinstance(value, (int, float))
                           or isinstance(value, bool) or not math.isfinite(value)
                           for value in defaults)):
                return None, f"event {name}: defaults must be {arity} numbers"
        dashboard = event.get("dashboard")
        if dashboard is not None and not isinstance(dashboard, bool):
            return None, f"event {name}: dashboard must be true or false"
        normalized_events.append(event)
    if normalized_events or "events" in manifest:
        manifest["events"] = normalized_events

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
    if params and not any(param.get("dashboard") is True for param in params):
        notes.append("no param with dashboard:true: "
                     "the dashboard device card will be status-only")
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
