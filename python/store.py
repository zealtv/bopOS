# store.py
"""
Framework persistence store (OSC contract section 10).

One JSON file per key so a power cut can at worst lose the key being
written, never the whole store; writes are tmp+rename atomic. Ephemeral
hosts (update_model: ephemeral) get the same API backed by a RAM dict —
they sacrifice persistence by design, not by crashing.
"""

import json
import os
import re

KEY_PATTERN = re.compile(r"[A-Za-z0-9._-]+$")


def valid_key(key):
    return bool(KEY_PATTERN.match(str(key))) and not str(key).startswith(".")


class Store:
    def __init__(self, root, persistent=True):
        self.root = root
        self.persistent = persistent
        self.memory = {}

    def path(self, key):
        return os.path.join(self.root, str(key))

    def put(self, key, values):
        if not valid_key(key):
            print(f"store: refusing invalid key {key!r}")
            return False
        values = list(values)
        if not self.persistent:
            self.memory[str(key)] = values
            return True
        try:
            os.makedirs(self.root, exist_ok=True)
            tmp = self.path(key) + ".tmp"
            with open(tmp, "w") as target:
                json.dump(values, target)
            os.replace(tmp, self.path(key))
            return True
        except OSError as error:
            print(f"store: could not persist {key!r}: {error}")
            return False

    def get(self, key):
        if not valid_key(key):
            print(f"store: refusing invalid key {key!r}")
            return []
        if not self.persistent:
            return list(self.memory.get(str(key), []))
        try:
            with open(self.path(key)) as source:
                values = json.load(source)
                return values if isinstance(values, list) else []
        except (OSError, ValueError):
            return []

    def delete(self, key):
        if not valid_key(key):
            return
        if not self.persistent:
            self.memory.pop(str(key), None)
            return
        try:
            os.remove(self.path(key))
        except OSError:
            pass
