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
import shlex
import sys
import tempfile
try:
    from . import io_protocol
    from .io_catalog import PERIPHERAL_TYPES
    from .paramgen import wire_number
except ImportError:
    import io_protocol
    from io_catalog import PERIPHERAL_TYPES
    from paramgen import wire_number

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
# momentary named fires; fields carry typed scalars.
MAX_EVENT_FIELDS = 16
MAX_EVENT_INT = 2 ** 24
_MISSING = object()


def param_wire_type(declaration):
    """Return the unchanged OSC scalar tag for a validated control kind."""
    if not isinstance(declaration, dict):
        return None
    kind = declaration.get("kind")
    return PARAM_KINDS.get(kind) if isinstance(kind, str) else None


def event_scalar(value):
    """Validate a manifest-independent event scalar; preserve its OSC tag."""
    if isinstance(value, str):
        if not 1 <= len(value) <= 255 or any(not 33 <= ord(c) <= 126 for c in value):
            raise ValueError("event text must be 1–255 printable ASCII bytes without whitespace")
        return value
    if isinstance(value, bool):
        raise ValueError("event numbers must not be booleans")
    if isinstance(value, int):
        if abs(value) > MAX_EVENT_INT:
            raise ValueError("event integer exceeds 2^24")
        return value
    if isinstance(value, float) and wire_number(value, "f"):
        rounded = float(format(value, ".6g"))
        if wire_number(rounded, "f"):
            return rounded
    raise ValueError("event field must be a finite OSC float, integer or text")


def event_values(values):
    """Check the wire limits without consulting a manifest."""
    values = list(values)
    if len(values) > MAX_EVENT_FIELDS:
        raise ValueError("events support at most 16 fields")
    return [event_scalar(value) for value in values]


def declared_event(manifest, identity):
    """Find an event by canonical identity in a validated manifest."""
    if manifest is None:
        return None
    return next((event for event in manifest.get("events", ())
                 if qualify_param(event) == identity), None)


def coerce_event_values(declaration, values):
    """Coerce supplied fields only; never fill missing fields or defaults.

    Undeclared events keep the historical numeric-float convention, with
    strings added as text. Declared kinds determine tags regardless of JSON's
    loss of the integer/float distinction.
    """
    values = list(values)
    if declaration is None:
        return event_values([coerce_event_field({"kind": "float"}, value)
                             if isinstance(value, (int, float)) else value
                             for value in values])
    fields = declaration.get("fields", ())
    if len(values) > len(fields):
        raise ValueError("event has more values than declared fields")
    return event_values([coerce_event_field(field, value)
                         for field, value in zip(fields, values)])


def coerce_event_field(field, value):
    """Check/coerce one value against a validated field declaration.

    Integral numeric inputs become OSC integers; text never coerces numbers.
    Out-of-range values are rejected rather than clamped.
    """
    tag = param_wire_type(field)
    if tag == "s":
        if not isinstance(value, str):
            raise ValueError("event text must be a string")
    elif tag in ("i", "f"):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("event numeric field must be a number")
        if not wire_number(value, tag):
            raise ValueError("event number does not fit its OSC type")
        if tag == "i":
            if value != int(value):
                raise ValueError("event integer field must be integral")
            value = int(value)
        else:
            value = float(value)
        if field.get("min") is not None and value < field["min"]:
            raise ValueError("event value below min")
        if field.get("max") is not None and value > field["max"]:
            raise ValueError("event value above max")
    else:
        raise ValueError("unknown event field kind")
    return event_scalar(value)


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
    error = _validate_entry(manifest, patch_path, require_entrypoint)
    if error is not None:
        return None, error
    for check in (_validate_params, _validate_events, _validate_io_modules,
                  _validate_caps):
        error = check(manifest)
        if error is not None:
            return None, error
    return manifest, None


def _validate_entry(manifest, patch_path, require_entrypoint):
    engine = manifest.get("engine", "pd")
    if not isinstance(engine, str) or not engine.strip() or '\0' in engine:
        return "engine must be a non-empty string"
    manifest["engine"] = engine.strip()

    entrypoint = manifest.get("entrypoint")
    if (not isinstance(entrypoint, str) or not entrypoint.strip()
            or '\0' in entrypoint):
        return "entrypoint must be a non-empty string"
    entrypoint = entrypoint.strip()
    normalized_entrypoint = os.path.normpath(entrypoint)
    if (os.path.isabs(entrypoint) or normalized_entrypoint == ".."
            or normalized_entrypoint.startswith(".." + os.sep)):
        return "entrypoint must stay inside the patch directory"
    patch_root = os.path.realpath(patch_path)
    resolved_entrypoint = os.path.realpath(
        os.path.join(patch_path, normalized_entrypoint))
    try:
        contained = os.path.commonpath((patch_root, resolved_entrypoint)) == patch_root
    except ValueError:
        contained = False
    if not contained:
        return "entrypoint must resolve inside the patch directory"
    manifest["entrypoint"] = entrypoint
    if (require_entrypoint
            and not os.path.isfile(os.path.join(patch_path, normalized_entrypoint))):
        return f"entrypoint {entrypoint!r} not found in {patch_path}"
    return None


def _normalize_param_metadata(param):
    legacy_dashboard = param.pop("facilitator", _MISSING)
    if legacy_dashboard is not _MISSING and not isinstance(legacy_dashboard, bool):
        return f"param {param.get('name')}: facilitator must be true or false"
    if ("dashboard" in param and legacy_dashboard is not _MISSING
            and param["dashboard"] != legacy_dashboard):
        return (f"param {param.get('name')!r}: dashboard and legacy "
                "facilitator values conflict")
    if "dashboard" not in param and legacy_dashboard is not _MISSING:
        param["dashboard"] = legacy_dashboard
    # ``group`` was presentation-only. Accept old manifests, but do not
    # preserve it in the normalized model or any subsequent save.
    param.pop("group", None)
    return None


def _validate_param_kind(param):
    name = param["name"]
    if "type" in param:
        return (f"param {name}: type was removed (2026-07-28); "
                f"use kind ({'/'.join(PARAM_KINDS)})")
    kind = param.get("kind")
    if not isinstance(kind, str) or kind not in PARAM_KINDS:
        return f"param {name}: kind must be one of {'/'.join(PARAM_KINDS)}"
    options = param.get("options")
    if kind == "enum":
        if (not isinstance(options, list)
                or not 2 <= len(options) <= MAX_PARAM_OPTIONS):
            return (f"param {name}: options must be a list of 2–"
                    f"{MAX_PARAM_OPTIONS} labels")
        if any(not isinstance(label, str)
               or OPTION_LABEL.fullmatch(label) is None for label in options):
            return (f"param {name}: each option must be 1–32 characters "
                    "without newlines")
        if len(set(options)) != len(options):
            return f"param {name}: option labels must be unique"
        # The indices are the value range, so min/max are derived rather
        # than authored. Accepting a matching pair keeps a round-tripped
        # manifest (the editor saves what it loaded) valid.
        for key, derived in (("min", 0), ("max", len(options) - 1)):
            if param.get(key) is None:
                param[key] = derived
            elif param[key] != derived:
                return (f"param {name}: {key} is derived from options "
                        f"({derived}), not authored")
    elif options is not None:
        return f"param {name}: options only apply to kind enum"
    if kind == "toggle":
        # The binary range is derived rather than authored. Accepting a
        # matching pair keeps a round-tripped manifest (the editor saves
        # what it loaded) valid, while a different pair remains an error.
        for key, derived in (("min", 0), ("max", 1)):
            if param.get(key) is None:
                param[key] = derived
            elif param[key] != derived:
                return (f"param {name}: {key} is derived for kind "
                        f"toggle ({derived}), not authored")
    return None


def _validate_param_values(param):
    name, kind = param["name"], param["kind"]
    low, high, default = param.get("min"), param.get("max"), param.get("default")
    if kind == "text":
        if "min" in param or "max" in param:
            return f"param {name}: min/max do not apply to kind text"
        if default is not None and not isinstance(default, str):
            return f"param {name}: text default must be a string"
    else:
        numbers = [v for v in (low, high, default) if v is not None]
        if any(not wire_number(v, PARAM_KINDS[kind]) for v in numbers):
            return f"param {name}: min/max/default must be numbers"
    if kind == "enum" and default is not None and default != int(default):
        return f"param {name}: default {default} is not an option index"
    if kind == "toggle" and default is not None and default not in (0, 1):
        return f"param {name}: toggle default must be 0 or 1"
    if low is not None and high is not None and low > high:
        return f"param {name}: min {low} > max {high}"
    if default is not None:
        if low is not None and default < low:
            return f"param {name}: default {default} below min {low}"
        if high is not None and default > high:
            return f"param {name}: default {default} above max {high}"
    if "role" in param:
        return (f"param {name}: role was removed (2026-07-12); "
                "dashboard controls come from dashboard:true, "
                "inspection from /report")
    dashboard = param.get("dashboard")
    if dashboard is not None and not isinstance(dashboard, bool):
        return f"param {name}: dashboard must be true or false"
    return None


def _validate_params(manifest):
    params = manifest.get("params", [])
    if not isinstance(params, list):
        return "params must be a list"
    normalized_params = []
    param_identities = set()
    for original in params:
        if not isinstance(original, dict):
            return f"param {original!r} must be an object"
        param = dict(original)
        error = _normalize_param_metadata(param)
        if error is not None:
            return error
        try:
            identity = qualify_param(param)
        except ValueError as error:
            return str(error)
        if identity in param_identities:
            return f"duplicate param identity {identity!r}"
        param_identities.add(identity)
        error = _validate_param_kind(param)
        if error is not None:
            return error
        error = _validate_param_values(param)
        if error is not None:
            return error
        normalized_params.append(param)
    manifest["params"] = normalized_params
    return None


def _validate_events(manifest):
    events = manifest.get("events", [])
    if not isinstance(events, list):
        return "events must be a list"
    normalized_events = []
    event_identities = set()
    for original in events:
        if not isinstance(original, dict):
            return f"event {original!r} must be an object"
        event = dict(original)
        try:
            identity = qualify_param(event)
        except ValueError as error:
            return str(error)
        name = event["name"]
        if identity in event_identities:
            return f"duplicate event identity {identity!r}"
        event_identities.add(identity)
        if "arity" in event or "defaults" in event:
            return f"event {name}: arity/defaults were removed; use fields"
        fields = event.get("fields", [])
        if not isinstance(fields, list) or len(fields) > MAX_EVENT_FIELDS:
            return f"event {name}: fields must be a list of at most 16 fields"
        normalized_fields, names = [], set()
        optional_seen = False
        for original_field in fields:
            if not isinstance(original_field, dict):
                return f"event {name}: field must be an object"
            field = dict(original_field)
            if any(key in field for key in ("path", "dashboard", "facilitator")):
                return f"event {name}: fields have no path or dashboard"
            try:
                field_name = qualify_param(field)
            except ValueError as error:
                return f"event {name}: {error}"
            if field_name in names:
                return f"event {name}: duplicate field name {field_name!r}"
            names.add(field_name)
            error = _validate_param_kind(field) or _validate_param_values(field)
            if error:
                return f"event {name} field: {error}"
            optional = field.get("optional", False)
            if not isinstance(optional, bool):
                return f"event {name}: optional must be true or false"
            if optional_seen and not optional:
                return f"event {name}: optional fields must trail required fields"
            optional_seen = optional_seen or optional
            if optional and field.get("default") is None:
                return f"event {name}: optional field requires a default"
            try:
                for key in ("min", "max", "default"):
                    if field.get(key) is not None:
                        coerce_event_field(field, field[key])
            except ValueError as error:
                return f"event {name} field {field_name}: {error}"
            field["optional"] = optional
            normalized_fields.append(field)
        event["fields"] = normalized_fields
        event.pop("labels", None)
        dashboard = event.get("dashboard")
        if dashboard is not None and not isinstance(dashboard, bool):
            return f"event {name}: dashboard must be true or false"
        normalized_events.append(event)
    if normalized_events or "events" in manifest:
        manifest["events"] = normalized_events
    return None


def _validate_io_modules(manifest):
    modules = manifest.get("io_modules", [])
    if not isinstance(modules, list):
        return "io_modules must be a list"
    normalized_modules, module_names = [], set()
    for original in modules:
        if not isinstance(original, dict):
            return "IO module must be an object"
        name = original.get("name")
        if not io_protocol.valid_name(name):
            return f"IO module {name!r}: invalid or reserved name"
        if name in module_names:
            return f"duplicate IO module name {name!r}"
        module_names.add(name)
        if (not isinstance(original.get("type"), str)
                or original["type"] not in PERIPHERAL_TYPES):
            return f"IO module {name!r}: unknown type"
        address = original.get("address")
        if (not isinstance(address, str)
                or re.fullmatch(r"0x[0-9a-fA-F]{2}", address) is None
                or not 0x03 <= int(address, 16) <= 0x77):
            return f"IO module {name!r}: address must be 0x03–0x77"
        if "optional" in original and not isinstance(original["optional"], bool):
            return f"IO module {name!r}: optional must be true or false"
        normalized_modules.append(dict(original, address=address.lower()))
    if modules or "io_modules" in manifest:
        manifest["io_modules"] = normalized_modules
    return None


def _validate_caps(manifest):
    for key, kind in (("caps", "caps"), ("slots", "slots")):
        values = manifest.get(key, [])
        if not isinstance(values, list) or any(not isinstance(v, str) for v in values):
            return f"{kind} must be a list of strings"
    return None


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
        print(f"ENGINE={shlex.quote(manifest['engine'])}")
        print(f"ENTRYPOINT={shlex.quote(manifest['entrypoint'])}")
        for note in warnings(manifest):
            print(f"manifest: warning: {note}", file=sys.stderr)
        return 0
    print(f"manifest: {error}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
