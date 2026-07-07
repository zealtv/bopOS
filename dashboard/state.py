import asyncio
import csv
import json
import os


DURABLE = ("id", "name", "pos1", "pos2", "patch")


class InstallationState:
    def __init__(self, path, devices_file=None):
        self.path = path
        self.data = {"name": "bopOS", "devices": {}, "muted": False}
        self._save_task = None
        self._load()
        if not self.data["devices"] and devices_file and os.path.exists(devices_file):
            self._import_seed(devices_file)
            self.save()

    @property
    def devices(self):
        return self.data["devices"]

    def _load(self):
        try:
            with open(self.path, encoding="utf-8") as source:
                loaded = json.load(source)
            if isinstance(loaded, dict) and isinstance(loaded.get("devices"), dict):
                self.data["name"] = loaded.get("name", "bopOS")
                for uid, durable in loaded["devices"].items():
                    self.devices[uid] = self._runtime_device(uid, durable)
        except (OSError, ValueError, TypeError):
            pass

    def _runtime_device(self, uid, values=None):
        values = values or {}
        params = values.get("params", {})
        # Read old flat parameter values as well as the current params object.
        if not params:
            params = {key: values[key] for key in ("gain", "gain2", "backing", "echo")
                      if key in values}
        return {
            "uid": uid, "id": values.get("id", -1), "name": values.get("name", ""),
            "pos1": values.get("pos1"), "pos2": values.get("pos2"),
            "patch": values.get("patch", "default"), "params": dict(params),
            "online": False, "last_seen": None, "ip": None, "version": None,
            "engine_alive": None, "rssi": None, "report": None,
            "declared": None, "undeclared": False,
        }

    def _import_seed(self, path):
        with open(path, newline="", encoding="utf-8") as source:
            rows = csv.reader(source, skipinitialspace=True)
            next(rows, None)
            for row in rows:
                if len(row) < 3:
                    continue
                uid, name = row[0].strip(), row[1].strip()
                try:
                    device_id = int(float(row[2]))
                except ValueError:
                    continue
                values = {"id": device_id, "name": name}
                for key, index in (("pos1", 3), ("pos2", 4)):
                    if len(row) > index:
                        try:
                            values[key] = [float(item) for item in row[index].split()]
                        except ValueError:
                            pass
                self.devices[uid] = self._runtime_device(uid, values)

    def ensure(self, uid):
        if uid not in self.devices:
            self.devices[uid] = self._runtime_device(uid)
        return self.devices[uid]

    def public(self):
        return self.data

    def durable(self):
        devices = {}
        for uid, device in self.devices.items():
            item = {key: device.get(key) for key in DURABLE if device.get(key) is not None}
            item["params"] = dict(device.get("params", {}))
            devices[uid] = item
        return {"name": self.data.get("name", "bopOS"), "devices": devices}

    def save(self):
        directory = os.path.dirname(os.path.abspath(self.path))
        os.makedirs(directory, exist_ok=True)
        temporary = self.path + ".tmp"
        with open(temporary, "w", encoding="utf-8") as target:
            json.dump(self.durable(), target, indent=2, sort_keys=True)
            target.write("\n")
        os.replace(temporary, self.path)

    def save_debounced(self):
        if self._save_task and not self._save_task.done():
            self._save_task.cancel()
        self._save_task = asyncio.create_task(self._delayed_save())

    async def _delayed_save(self):
        try:
            await asyncio.sleep(1)
            self.save()
        except asyncio.CancelledError:
            pass

    async def close(self):
        if self._save_task and not self._save_task.done():
            self._save_task.cancel()
            self.save()
