"""Canonical discovery and launch-context encoding for asset slots."""

import json
import os


def valid_name(value):
    """Return whether value safely names one visible assets/ child."""
    return (
        isinstance(value, str)
        and bool(value)
        and value.isprintable()
        and not value.startswith(".")
        and "/" not in value
        and "\\" not in value
        and "\x00" not in value
    )


def installed_names(assets_root):
    """Return installed top-level asset-slot names in canonical order."""
    try:
        names = os.listdir(assets_root)
    except OSError:
        return []
    return sorted(
        name for name in names
        if valid_name(name)
        and not os.path.islink(os.path.join(assets_root, name))
        and os.path.isdir(os.path.join(assets_root, name))
    )


def installed_paths(assets_root):
    """Return absolute paths for every installed slot, in canonical order."""
    root = os.path.abspath(assets_root)
    return [os.path.join(root, name) for name in installed_names(root)]


def json_list(paths):
    """Encode the non-PD BOPOS_ASSETS value."""
    return json.dumps(list(paths), ensure_ascii=False, separators=(",", ":"))


def fudi_atom(value):
    """Escape one symbol atom for a Pure Data/FUDI startup message."""
    escaped = []
    for character in str(value):
        if character in "\\,;$" or character.isspace():
            escaped.append("\\")
        escaped.append(character)
    return "".join(escaped)


def fudi_list(paths):
    """Encode paths as the trailing atoms of `bopos-context assets ...`."""
    return " ".join(fudi_atom(path) for path in paths)
