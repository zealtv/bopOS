"""Durable human aliases for physical devices.

The generator is deliberately local and pinned: aliases are product copy, not
an external-name package whose updates could rename an installation. Resolved
records are persisted immediately; the deterministic probe is only allocation
logic for a UID without a registry entry.
"""

import hashlib
import math
import re


GENERATOR_VERSION = 1
ALIAS_RE = re.compile(r"[A-Za-z]{2,12} [A-Za-z]{2,12}")

# Freda Sparks is the ratified seed and tone reference. Keep both at index 0.
GIVEN_NAMES = (
    "Freda", "Amara", "Amina", "Anya", "Asha", "Ayla", "Bayo", "Ciro",
    "Dalia", "Diego", "Eira", "Elif", "Enzo", "Esme", "Farah", "Hana",
    "Hugo", "Imani", "Ines", "Ivo", "Jaya", "Juno", "Kaito", "Kenji",
    "Kira", "Lani", "Leila", "Lila", "Lior", "Luca", "Mala", "Malik",
    "Mara", "Mateo", "Mina", "Mira", "Miro", "Nala", "Nia", "Niko",
    "Noor", "Omar", "Orla", "Pavel", "Priya", "Rami", "Ravi", "Remy",
    "Rina", "Rosa", "Sami", "Sana", "Sora", "Talia", "Tariq", "Theo",
    "Tova", "Uma", "Vera", "Yara", "Yuki", "Zain", "Zola", "Zuri",
)

CHARACTER_WORDS = (
    "Sparks", "Bloom", "Comet", "Echo", "Halo", "Neon", "Orbit", "Pepper",
    "Prism", "Rocket", "Tempo", "Velvet", "Breeze", "Chrome", "Cloud", "Copper",
    "Coral", "Dancer", "Dusk", "Ember", "Falcon", "Flash", "Frost", "Glow",
    "Gold", "Groove", "Harbor", "Honey", "Indigo", "Jazz", "Kite", "Laser",
    "Lotus", "Lunar", "Maple", "Melody", "Mist", "Moon", "Moss", "Nova",
    "Onyx", "Peach", "Pearl", "Pixel", "Pulse", "Quartz", "Rain", "Reef",
    "Ribbon", "River", "Satin", "Scout", "Shine", "Silver", "Solar", "Sonic",
    "Star", "Storm", "Sugar", "Tiger", "Vinyl", "Wave", "Willow", "Zephyr",
)


def clean_alias(value):
    """Return the canonical custom spelling, or None when it is invalid."""
    if not isinstance(value, str):
        return None
    value = " ".join(value.split())
    return value if ALIAS_RE.fullmatch(value) else None


def alias_key(value):
    cleaned = clean_alias(value)
    return cleaned.casefold() if cleaned is not None else None


def _permutation(uid):
    total = len(GIVEN_NAMES) * len(CHARACTER_WORDS)
    digest = hashlib.sha256(
        b"bopos-device-alias-v1\0" + str(uid).strip().casefold().encode("utf-8")
    ).digest()
    start = int.from_bytes(digest[:8], "big") % total
    step = int.from_bytes(digest[8:16], "big") % total or 1
    while math.gcd(step, total) != 1:
        step = (step + 1) % total or 1
    return start, step, total


def candidate(uid, probe=0):
    """Return one pinned candidate; probes visit every pair exactly once."""
    start, step, total = _permutation(uid)
    if isinstance(probe, bool) or not isinstance(probe, int) or not 0 <= probe < total:
        raise ValueError("alias probe outside generator range")
    index = (start + probe * step) % total
    given_index, word_index = divmod(index, len(CHARACTER_WORDS))
    return f"{GIVEN_NAMES[given_index]} {CHARACTER_WORDS[word_index]}"


def allocate(uid, registry):
    """Allocate the first unowned pair in this UID's deterministic sequence."""
    occupied = {alias_key(entry.get("alias"))
                for other_uid, entry in registry.items() if other_uid != uid
                and isinstance(entry, dict)}
    _start, _step, total = _permutation(uid)
    for probe in range(total):
        alias = candidate(uid, probe)
        if alias.casefold() not in occupied:
            return {"alias": alias, "source": "generated",
                    "generator": GENERATOR_VERSION, "device_muted": False}
    raise ValueError("device alias registry exhausted")


def clean_registry(value):
    """Validate a persisted registry as one case-insensitively unique map."""
    if value is None:
        return {}
    if not isinstance(value, dict):
        return None
    cleaned, owners = {}, {}
    for uid, entry in value.items():
        if not isinstance(uid, str) or not uid or not isinstance(entry, dict):
            return None
        alias = clean_alias(entry.get("alias"))
        source = entry.get("source")
        generator = entry.get("generator")
        if (alias is None or source not in ("generated", "custom")
                or isinstance(generator, bool) or not isinstance(generator, int)
                or generator < 1):
            return None
        key = alias.casefold()
        if key in owners and owners[key] != uid:
            return None
        owners[key] = uid
        device_muted = entry.get("device_muted", False)
        if not isinstance(device_muted, bool):
            return None
        cleaned[uid] = {"alias": alias, "source": source, "generator": generator,
                        "device_muted": device_muted}
    return cleaned


def set_custom(registry, uid, value):
    alias = clean_alias(value)
    if alias is None:
        return None, "Alias must be two short words using letters A-Z only."
    key = alias.casefold()
    owner = next((other_uid for other_uid, entry in registry.items()
                  if other_uid != uid and alias_key(entry.get("alias")) == key), None)
    if owner is not None:
        return None, f"Alias is already used by device …{owner[-8:]}."
    return {"alias": alias, "source": "custom", "generator": GENERATOR_VERSION,
            "device_muted": bool(registry.get(uid, {}).get("device_muted", False))}, None
