"""Host-only PSKs. Never attach this object or its values to public state."""
import json
import os
import tempfile


class WifiSecrets:
    def __init__(self, data_dir):
        self.path = os.path.join(data_dir, "state", "wifi-secrets.json")
        self.values = {}
        self.pending = {}
        self.invalid = False
        try:
            with open(self.path, encoding="utf-8") as source:
                document = json.load(source)
            if not isinstance(document, dict) or set(document) != {"secrets", "pending"}:
                raise ValueError("invalid")
            value, pending = document["secrets"], document["pending"]
            if not isinstance(value, dict) or any(
                    not isinstance(k, str) or not isinstance(v, str)
                    or not 8 <= len(v) <= 63 or any(not 32 <= ord(c) <= 126 for c in v)
                    for k, v in value.items()):
                raise ValueError("invalid")
            if not isinstance(pending, dict) or any(not isinstance(uid, str) or not isinstance(names, list)
                    or any(not isinstance(name, str) or name not in value for name in names)
                    for uid, names in pending.items()):
                raise ValueError("invalid")
            os.chmod(self.path, 0o600)
            self.values = value
            self.pending = {uid: set(names) for uid, names in pending.items()}
        except FileNotFoundError:
            self.invalid = os.path.lexists(self.path)
        except (OSError, ValueError):
            self.invalid = True

    def save(self, values, pending=None):
        if self.invalid:
            raise OSError("invalid")
        directory = os.path.dirname(self.path)
        os.makedirs(directory, mode=0o700, exist_ok=True)
        fd, temporary = tempfile.mkstemp(dir=directory, prefix=".wifi-")
        pending = self.pending if pending is None else pending
        pending = {uid: set(names) & set(values) for uid, names in pending.items() if set(names) & set(values)}
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as target:
                json.dump({"secrets": values, "pending": {uid: sorted(names) for uid, names in pending.items()}}, target)
                target.flush()
                os.fsync(target.fileno())
            os.replace(temporary, self.path)
            self.values = dict(values)
            self.pending = pending
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
