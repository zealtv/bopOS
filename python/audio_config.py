"""Node audio configuration, discovery, validation, and persistence."""

import argparse
import json
import os
import re
import shlex
import stat
import subprocess
import tempfile


CONFIG_KEYS = {
    "card": "SOUNDCARD",
    "mixer_control": "MIXER_CONTROL",
    "sample_rate": "JACK_SAMPLE_RATE",
    "period_size": "JACK_PERIOD_SIZE",
    "nperiods": "JACK_NPERIODS",
}
DEFAULTS = {
    "card": "DigiAMP",
    "mixer_control": "Digital",
    "sample_rate": 44100,
    "period_size": 512,
    "nperiods": 2,
}
SAMPLE_RATES = (22050, 32000, 44100, 48000, 88200, 96000)
PERIOD_SIZES = (64, 128, 256, 512, 1024, 2048)
NPERIODS = (2, 3)
_CARD_ID = re.compile(r"[A-Za-z0-9_-]+")
_APLAY_CARD = re.compile(
    r"^card\s+(\d+):\s+([^\s]+)\s+\[([^\]]+)\],\s+device\s+", re.MULTILINE)
_MIXER_CONTROL = re.compile(r"^Simple mixer control '((?:[^']|'')+)'", re.MULTILINE)


class AudioConfigError(ValueError):
    pass


def _integer(value, fallback):
    if isinstance(value, bool):
        return fallback
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def from_node_config(config):
    """Return the canonical five-field object from parsed bopos.config."""
    mixer = config.get("MIXER_CONTROL")
    return {
        "card": str(config.get("SOUNDCARD") or DEFAULTS["card"]),
        "mixer_control": str(mixer) if mixer else None,
        "sample_rate": _integer(config.get("JACK_SAMPLE_RATE"),
                                DEFAULTS["sample_rate"]),
        "period_size": _integer(config.get("JACK_PERIOD_SIZE"),
                                DEFAULTS["period_size"]),
        "nperiods": _integer(config.get("JACK_NPERIODS"),
                            DEFAULTS["nperiods"]),
    }


def _run_text(argv, runner):
    try:
        result = runner(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                        text=True, timeout=2)
    except (OSError, subprocess.SubprocessError, TypeError):
        return ""
    if result.returncode != 0:
        return ""
    return result.stdout or ""


def discover_cards(runner=subprocess.run):
    """List currently visible ALSA playback cards without opening a device."""
    cards = []
    seen = set()
    for match in _APLAY_CARD.finditer(_run_text(["aplay", "-l"], runner)):
        index, card_id, label = int(match.group(1)), match.group(2), match.group(3)
        if card_id in seen or _CARD_ID.fullmatch(card_id) is None:
            continue
        seen.add(card_id)
        controls = []
        mixer_text = _run_text(["amixer", "-c", card_id, "scontrols"], runner)
        for control in _MIXER_CONTROL.findall(mixer_text):
            control = control.replace("''", "'")
            if control not in controls:
                controls.append(control)
        cards.append({
            "id": card_id,
            "index": index,
            "label": label,
            "mixer_controls": controls,
        })
    return sorted(cards, key=lambda item: (item["index"], item["id"]))


def validate(candidate, cards):
    """Validate and normalize a complete wire object against discovery."""
    if not isinstance(candidate, dict) or set(candidate) != set(CONFIG_KEYS):
        raise AudioConfigError("Audio settings must contain exactly five fields.")
    card = candidate.get("card")
    mixer = candidate.get("mixer_control")
    if not isinstance(card, str) or _CARD_ID.fullmatch(card) is None:
        raise AudioConfigError("Choose a detected sound card.")
    available = next((item for item in cards if item.get("id") == card), None)
    if available is None:
        raise AudioConfigError("That sound card is not currently available.")
    if mixer is not None:
        if not isinstance(mixer, str) or mixer not in available.get("mixer_controls", ()):
            raise AudioConfigError("Choose Auto or a detected mixer control.")

    values = {}
    for key, allowed, message in (
            ("sample_rate", SAMPLE_RATES, "Choose a supported sample rate."),
            ("period_size", PERIOD_SIZES, "Choose a supported buffer size."),
            ("nperiods", NPERIODS, "Choose two or three periods.")):
        value = candidate.get(key)
        if isinstance(value, bool) or not isinstance(value, int) or value not in allowed:
            raise AudioConfigError(message)
        values[key] = value
    return {
        "card": card,
        "mixer_control": mixer,
        **values,
    }


def _shell_value(value):
    return "" if value is None else shlex.quote(str(value))


def update_config_file(path, audio):
    """Atomically replace only owned keys while preserving other file text."""
    try:
        with open(path) as source:
            lines = source.readlines()
        mode = stat.S_IMODE(os.stat(path).st_mode)
    except FileNotFoundError:
        lines = []
        mode = 0o644

    replacements = {
        config_key: "{}={}\n".format(config_key, _shell_value(audio[field]))
        for field, config_key in CONFIG_KEYS.items()
    }
    written = set()
    output = []
    for line in lines:
        match = re.match(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=", line)
        key = match.group(1) if match else None
        if key in replacements:
            if key not in written:
                output.append(replacements[key])
                written.add(key)
            continue
        output.append(line)
    missing = [key for key in replacements if key not in written]
    if missing:
        if output and output[-1].strip():
            output.append("\n")
        output.append("# Device-tab audio configuration.\n")
        output.extend(replacements[key] for key in missing)
    atomic_write(path, "".join(output).encode(), mode)


def atomic_write(path, content, mode=0o644):
    directory = os.path.dirname(os.path.realpath(path))
    os.makedirs(directory, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".bopos-config-", dir=directory)
    try:
        with os.fdopen(fd, "wb") as target:
            target.write(content)
            target.flush()
            os.fsync(target.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


def read_active(path):
    try:
        with open(path) as source:
            value = json.load(source)
    except (OSError, ValueError):
        return None
    if not isinstance(value, dict) or set(value) != set(CONFIG_KEYS):
        return None
    if (not isinstance(value.get("card"), str)
            or (value.get("mixer_control") is not None
                and not isinstance(value.get("mixer_control"), str))):
        return None
    for key in ("sample_rate", "period_size", "nperiods"):
        if isinstance(value.get(key), bool) or not isinstance(value.get(key), int):
            return None
    return value


def write_active(path, audio):
    atomic_write(path, (json.dumps(audio, sort_keys=True) + "\n").encode())


def main(argv=None):
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    record = subparsers.add_parser("record-active")
    record.add_argument("path")
    record.add_argument("card")
    record.add_argument("mixer_control")
    record.add_argument("sample_rate", type=int)
    record.add_argument("period_size", type=int)
    record.add_argument("nperiods", type=int)
    args = parser.parse_args(argv)
    if args.command == "record-active":
        write_active(args.path, {
            "card": args.card,
            "mixer_control": args.mixer_control or None,
            "sample_rate": args.sample_rate,
            "period_size": args.period_size,
            "nperiods": args.nperiods,
        })
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
