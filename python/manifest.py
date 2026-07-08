# manifest.py
"""
bopos.patch.json loader/validator (OSC contract section 8).

One validator, three consumers: helper.py (/os/params, /os/report, /patch
validation), bash/start-engine.sh (CLI mode below), and tests. The manifest
is the single source of truth for what starts a patch and what can be
controlled; validation exists so it can't silently drift.
"""

import json
import os
import re
import sys

MANIFEST_NAME = "bopos.patch.json"
PARAM_NAME = re.compile(r"[A-Za-z0-9_-]+$")
PARAM_TYPES = ("i", "f", "s")


def raw(patch_path):
    """Verbatim manifest text, or None. /os/params serves exactly this."""
    try:
        with open(os.path.join(patch_path, MANIFEST_NAME)) as source:
            return source.read()
    except OSError:
        return None


def load(patch_path):
    """Return (manifest-dict, error-string). Exactly one of them is None."""
    text = raw(patch_path)
    if text is None:
        return None, f"no {MANIFEST_NAME} in {patch_path}"
    try:
        manifest = json.loads(text)
    except ValueError as error:
        return None, f"{MANIFEST_NAME} is not valid JSON: {error}"
    if not isinstance(manifest, dict):
        return None, f"{MANIFEST_NAME} must be a JSON object"

    engine = manifest.get("engine", "pd")
    if not isinstance(engine, str) or not engine.strip():
        return None, "engine must be a non-empty string"
    manifest["engine"] = engine.strip()

    entrypoint = manifest.get("entrypoint")
    if not isinstance(entrypoint, str) or not entrypoint.strip():
        return None, "entrypoint must be a non-empty string"
    if not os.path.isfile(os.path.join(patch_path, entrypoint)):
        return None, f"entrypoint {entrypoint!r} not found in {patch_path}"

    params = manifest.get("params", [])
    if not isinstance(params, list):
        return None, "params must be a list"
    for param in params:
        if not isinstance(param, dict):
            return None, f"param {param!r} must be an object"
        name = param.get("name")
        if not isinstance(name, str) or not PARAM_NAME.match(name):
            return None, f"bad param name {name!r}"
        if param.get("type") not in PARAM_TYPES:
            return None, f"param {name}: type must be one of {'/'.join(PARAM_TYPES)}"
        low, high, default = param.get("min"), param.get("max"), param.get("default")
        numbers = [v for v in (low, high, default) if v is not None]
        if any(not isinstance(v, (int, float)) or isinstance(v, bool) for v in numbers):
            return None, f"param {name}: min/max/default must be numbers"
        if low is not None and high is not None and low > high:
            return None, f"param {name}: min {low} > max {high}"
        if default is not None:
            if low is not None and default < low:
                return None, f"param {name}: default {default} below min {low}"
            if high is not None and default > high:
                return None, f"param {name}: default {default} above max {high}"
        role = param.get("role")
        if role is not None and (not isinstance(role, str) or not role.strip()):
            return None, f"param {name}: role must be a non-empty string"

    volumes = [param["name"] for param in params if param.get("role") == "volume"]
    if len(volumes) > 1:
        return None, f"at most one param may have role 'volume' (got: {', '.join(volumes)})"

    for key, kind in (("caps", "caps"), ("slots", "slots")):
        values = manifest.get(key, [])
        if not isinstance(values, list) or any(not isinstance(v, str) for v in values):
            return None, f"{kind} must be a list of strings"

    return manifest, None


def warnings(manifest):
    """Non-fatal advisories for a manifest that load() accepted."""
    notes = []
    params = manifest.get("params", [])
    if params and not any(param.get("role") == "volume" or param.get("name") == "gain"
                          for param in params):
        notes.append("no param with role 'volume' (or named 'gain'): "
                     "the facilitator volume card will be status-only")
    return notes


def main():
    """CLI for the launcher: prints eval-able ENGINE=/ENTRYPOINT= lines.

    Exit 0: valid manifest. Exit 3: no manifest, but main.pd exists (legacy
    launch). Exit 1: manifest present but invalid, or nothing to launch —
    the launcher prints the error and falls back to legacy if it can
    (contract section 1: a node never falls silent over a JSON typo).
    """
    patch_path = sys.argv[1]
    manifest, error = load(patch_path)
    if manifest is not None:
        print(f"ENGINE='{manifest['engine']}'")
        print(f"ENTRYPOINT='{manifest['entrypoint']}'")
        for note in warnings(manifest):
            print(f"manifest: warning: {note}", file=sys.stderr)
        return 0
    legacy = os.path.isfile(os.path.join(patch_path, "main.pd"))
    print("ENGINE='pd'")
    print("ENTRYPOINT='main.pd'")
    print(f"manifest: {error}", file=sys.stderr)
    if legacy and error.startswith("no "):
        return 3  # no manifest at all: the quiet legacy case
    return 1      # invalid manifest (or nothing launchable): loud


if __name__ == "__main__":
    sys.exit(main())
