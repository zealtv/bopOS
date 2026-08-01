"""Node log-destination configuration and effective resolution.

Mirrors the audio-config shape (contract v1.11): a bounded choice persisted in
`bopos.config` as `LOG_DESTINATION`, plus effective resolution against the USB
mount. Feeds `nodelog`'s destination hook and the `/os/log-config` admin
surface. No free paths — the operator picks `internal` or `usb`, nothing to
type wrong from the dashboard.

Ratified design: `.loom/legacy-v1/tied/1-logging-seed-design/` §3. When `usb` is
configured but no stick is mounted, entries fall back to `internal`
(`~/bopos-logs/`) and stay on the SD card — never dropped, never RAM-buffered,
no copy-on-insert catch-up in v1. Hot insert/remove takes effect on the next
write because the effective directory is resolved per entry (a cheap
`os.path.ismount`).
"""

import os
import re
import stat

from audio_config import atomic_write  # reuse the atomic bopos.config writer

DESTINATIONS = ("internal", "usb")
DEFAULT_DESTINATION = "internal"

INTERNAL_DIR = os.path.expanduser("~/bopos-logs")
USB_MOUNT = "/media/bopos-usb"
USB_DIR = os.path.join(USB_MOUNT, "bopos-logs")

CONFIG_KEY = "LOG_DESTINATION"


class LogConfigError(ValueError):
    pass


def configured(config):
    """The persisted choice, defaulting to internal for anything unset/bad."""
    value = str((config or {}).get(CONFIG_KEY) or DEFAULT_DESTINATION).strip().lower()
    return value if value in DESTINATIONS else DEFAULT_DESTINATION


def usb_present():
    try:
        return os.path.ismount(USB_MOUNT)
    except OSError:
        return False


def effective(config):
    """What the node actually logs to now: usb only if chosen *and* mounted."""
    if configured(config) == "usb" and usb_present():
        return "usb"
    return "internal"


def effective_dir(config):
    """The directory nodelog writes to now. Suitable as its destination hook:
    resolved per entry, so a hot USB switch needs no restart."""
    return USB_DIR if effective(config) == "usb" else INTERNAL_DIR


def status_object(config):
    """The complete log state object: configured vs effective vs media
    presence, all visible without SSH (the /os/log-config receipt + report)."""
    return {
        "destination": configured(config),
        "effective": effective(config),
        "usb_present": usb_present(),
    }


def validate(candidate):
    """Parse and bound a `{"destination": "internal"|"usb"}` request."""
    if not isinstance(candidate, dict) or set(candidate) != {"destination"}:
        raise LogConfigError('log-config expects exactly {"destination": …}')
    destination = candidate["destination"]
    if destination not in DESTINATIONS:
        raise LogConfigError(
            "destination must be one of {}".format(", ".join(DESTINATIONS)))
    return {"destination": destination}


def update_config_file(path, destination):
    """Atomically set LOG_DESTINATION in bopos.config, preserving other text."""
    if destination not in DESTINATIONS:
        raise LogConfigError("refusing to persist invalid destination")
    try:
        with open(path) as source:
            lines = source.readlines()
        mode = stat.S_IMODE(os.stat(path).st_mode)
    except FileNotFoundError:
        lines = []
        mode = 0o644

    replacement = "{}={}\n".format(CONFIG_KEY, destination)
    written = False
    output = []
    for line in lines:
        match = re.match(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=", line)
        key = match.group(1) if match else None
        if key == CONFIG_KEY:
            if not written:
                output.append(replacement)
                written = True
            continue
        output.append(line)
    if not written:
        if output and output[-1].strip():
            output.append("\n")
        output.append("# Device-tab log destination.\n")
        output.append(replacement)
    atomic_write(path, "".join(output).encode(), mode)
