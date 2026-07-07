import asyncio
import csv
import json
import os


DURABLE = ("id", "name", "pos1", "pos2", "patch")


class InstallationState:
    # top-down floor plan in metres: origin top-left, x right, y down —
    # the spatial-audio work consumes these coordinates, keep them explicit
    DEFAULT_ROOM = {"width": 10.0, "depth": 8.0, "units": "m"}

    def __init__(self, path, devices_file=None):
        self.path = path
        self.data = {"name": "bopOS", "devices": {}, "muted": False,
                     "room": dict(self.DEFAULT_ROOM)}
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
                room = loaded.get("room")
                if isinstance(room, dict) and room.get("width") and room.get("depth"):
                    self.data["room"] = {"width": float(room["width"]),
                                         "depth": float(room["depth"]), "units": "m"}
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
            "declared": None, "undeclared": False, "rev": None,
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
        return {"name": self.data.get("name", "bopOS"),
                "room": self.data.get("room", dict(self.DEFAULT_ROOM)), "devices": devices}

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

    def venues_dir(self):
        directory = os.path.join(os.path.dirname(os.path.abspath(self.path)), "installations")
        os.makedirs(directory, exist_ok=True)
        return directory

    def list_venues(self):
        try:
            return sorted(name[:-5] for name in os.listdir(self.venues_dir())
                          if name.endswith(".json"))
        except OSError:
            return []

    def save_venue(self, name):
        # snapshot the durable state (name, room, devices) under a venue name;
        # runtime liveness is not part of a venue (presets land here once the
        # facilitator stitch adds them to durable())
        path = os.path.join(self.venues_dir(), name + ".json")
        with open(path, "w", encoding="utf-8") as target:
            json.dump(self.durable(), target, indent=2, sort_keys=True)
            target.write("\n")

    def load_venue(self, name):
        # replace the current installation with a saved venue; keeps live
        # runtime fields (online/ip/…) only for devices the venue also knows
        path = os.path.join(self.venues_dir(), name + ".json")
        try:
            with open(path, encoding="utf-8") as source:
                loaded = json.load(source)
        except (OSError, ValueError):
            return False
        if not isinstance(loaded, dict) or not isinstance(loaded.get("devices"), dict):
            return False
        live = self.data["devices"]
        rebuilt = {}
        for uid, durable in loaded["devices"].items():
            device = self._runtime_device(uid, durable)
            for key in ("online", "last_seen", "ip", "version", "engine_alive",
                        "rssi", "report", "declared", "undeclared", "rev"):
                if uid in live:
                    device[key] = live[uid][key]
            rebuilt[uid] = device
        self.data["name"] = loaded.get("name", name)
        room = loaded.get("room")
        if isinstance(room, dict) and room.get("width") and room.get("depth"):
            self.data["room"] = {"width": float(room["width"]),
                                 "depth": float(room["depth"]), "units": "m"}
        self.data["devices"] = rebuilt
        self.save()
        return True

    async def close(self):
        if self._save_task and not self._save_task.done():
            self._save_task.cancel()
            self.save()
