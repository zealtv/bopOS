import asyncio
import csv
import json
import math
import os


DURABLE = ("id", "name", "pos1", "pos2", "patch")
FACILITATOR_COMMANDS = frozenset(("restart-engine", "update", "reboot", "shutdown",
                                  "get_samples"))


class InstallationState:
    # top-down floor plan in metres: origin top-left, x right, y down —
    # the spatial-audio work consumes these coordinates, keep them explicit
    DEFAULT_ROOM = {"width": 10.0, "depth": 8.0, "units": "m"}

    def __init__(self, path, devices_file=None):
        self.path = path
        self.data = {"name": "bopOS", "devices": {}, "muted": False,
                     "room": dict(self.DEFAULT_ROOM), "master": 1.0, "presets": {},
                     "facilitator_commands": [],
                     "listener": None,
                     "points": {}}  # /pt geometry, runtime-only (not in durable())
        self._save_task = None
        self._load()
        if self.data["listener"] is None:
            self.data["listener"] = self.default_listener()
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
                room = self.clean_room(loaded.get("room"))
                if room is not None:
                    self.data["room"] = room
                self.data["master"] = self.clean_master(loaded.get("master"))
                if isinstance(loaded.get("presets"), dict):
                    self.data["presets"] = loaded["presets"]
                self.data["facilitator_commands"] = self.clean_facilitator_commands(
                    loaded.get("facilitator_commands"))
                listener = self.clean_listener(loaded.get("listener"))
                if listener is not None:
                    self.data["listener"] = listener
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
            "sync": None,  # runtime-only clock estimate: {offset, rtt, min_rtt, samples, at}
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
                "room": self.data.get("room", dict(self.DEFAULT_ROOM)),
                "master": self.data.get("master", 1.0),
                "presets": self.data.get("presets", {}),
                "facilitator_commands": self.clean_facilitator_commands(
                    self.data.get("facilitator_commands")),
                "listener": dict(self.data["listener"]),
                "devices": devices}

    def default_listener(self):
        room = self.data.get("room") or self.DEFAULT_ROOM
        return {"x": float(room["width"]) / 2.0,
                "y": float(room["depth"]) / 2.0,
                "heading": 0.0}

    def clean_listener(self, value):
        if not isinstance(value, dict):
            return None
        fields = []
        for key in ("x", "y", "heading"):
            raw = value.get(key)
            if isinstance(raw, bool):
                return None
            try:
                number = float(raw)
            except (TypeError, ValueError):
                return None
            if not math.isfinite(number):
                return None
            fields.append(number)
        room = self.data.get("room") or self.DEFAULT_ROOM
        width, depth = float(room["width"]), float(room["depth"])
        return {"x": min(max(fields[0], 0.0), width),
                "y": min(max(fields[1], 0.0), depth),
                "heading": fields[2] % 360.0}

    @staticmethod
    def clean_facilitator_commands(value):
        if not isinstance(value, list):
            return []
        cleaned = []
        for command in value:
            if command in FACILITATOR_COMMANDS and command not in cleaned:
                cleaned.append(command)
        return cleaned

    @staticmethod
    def clean_master(value):
        try:
            return min(max(float(value), 0.0), 1.0)
        except (TypeError, ValueError):
            return 1.0

    @staticmethod
    def clean_room(value):
        if not isinstance(value, dict):
            return None
        dimensions = []
        for key in ("width", "depth"):
            raw = value.get(key)
            if isinstance(raw, bool):
                return None
            try:
                dimension = float(raw)
            except (TypeError, ValueError):
                return None
            if not math.isfinite(dimension) or not 0 < dimension <= 1000:
                return None
            dimensions.append(dimension)
        return {"width": dimensions[0], "depth": dimensions[1], "units": "m"}

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
                        "rssi", "report", "declared", "undeclared", "rev", "sync"):
                if uid in live:
                    device[key] = live[uid][key]
            rebuilt[uid] = device
        self.data["name"] = loaded.get("name", name)
        room = self.clean_room(loaded.get("room"))
        if room is not None:
            self.data["room"] = room
        self.data["master"] = self.clean_master(loaded.get("master"))
        self.data["presets"] = loaded["presets"] if isinstance(loaded.get("presets"), dict) else {}
        self.data["facilitator_commands"] = self.clean_facilitator_commands(
            loaded.get("facilitator_commands"))
        self.data["listener"] = (self.clean_listener(loaded.get("listener"))
                                 or self.default_listener())
        self.data["devices"] = rebuilt
        self.save()
        return True

    async def close(self):
        if self._save_task and not self._save_task.done():
            self._save_task.cancel()
            self.save()
