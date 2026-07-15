import asyncio
import csv
import json
import math
import os
import re
import time


SCHEMA = 1
FACILITATOR_COMMANDS = frozenset(("restart-engine", "updatebopos", "reboot", "shutdown"))
FINGERPRINT_RE = re.compile(r"[0-9a-f]{64}")


def observed_active_patch(device):
    """Return the strongest currently observed active patch name."""
    listing = device.get("patches")
    if isinstance(listing, list):
        active = next((patch.get("name") for patch in listing
                       if isinstance(patch, dict) and patch.get("active")), None)
        if active:
            return active
    report = device.get("report")
    if isinstance(report, dict) and isinstance(report.get("patch"), str):
        return report["patch"]
    return None


def reconcile_patch_switch_success(device):
    """Clear an attempt only when observation proves its target is active."""
    attempt = device.get("patch_switch")
    if (isinstance(attempt, dict) and attempt.get("patch")
            and observed_active_patch(device) == attempt["patch"]):
        device["patch_switch"] = None
        return True
    return False


def reconcile_patch_switch_observation(device):
    """Apply a late terminal observation to an existing attempt."""
    if reconcile_patch_switch_success(device):
        return "success"
    attempt = device.get("patch_switch")
    active = observed_active_patch(device)
    if (isinstance(attempt, dict) and attempt.get("status") == "timeout"
            and active and active != attempt.get("patch")):
        attempt.update(status="failed",
                       reason=f"Observed active patch {active!r}, not {attempt['patch']!r}.")
        return "failed"
    return None


def patch_badge(device, desired):
    """Derive one device's fleet-patch convergence badge (fp-0 sec 3).

    `desired` is {"name", "fingerprint"} — the staged fleet patch, with the
    fingerprint resolved against the live host catalog when the host still
    carries the patch — or None when no fleet patch is staged. Unset outranks
    everything: with nothing staged there is nothing to converge on. Badges
    are derived on every broadcast and never stored as a verdict.
    """
    if not desired or not desired.get("name"):
        return "unset"
    name = desired["name"]
    if not device.get("online"):
        return "unknown"
    switch = device.get("patch_switch")
    switch_status = switch.get("status") if isinstance(switch, dict) else None
    if switch_status in ("failed", "timeout"):
        if switch.get("patch") == name:
            return switch_status
        switch = None  # terminal attempt for a superseded/manual target
    if device.get("patches") is None:
        return "unknown"
    fetch_phase = (device.get("fetch") or {}).get("patch:" + name)
    if switch or fetch_phase in ("sent", "queued", "fetching"):
        return "switching"
    listing = device["patches"]
    entry = next((patch for patch in listing if patch.get("name") == name), None)
    if entry is None:
        return "missing"
    active = next((patch.get("name") for patch in listing if patch.get("active")), None)
    if active != name:
        return "mismatch"
    node_fingerprint = entry.get("fingerprint")
    if not node_fingerprint or not desired.get("fingerprint"):
        return "stale_unverified"  # names match but identity cannot be checked
    if node_fingerprint != desired["fingerprint"]:
        return "stale"
    return "current"


class InstallationState:
    # top-down floor plan in metres: origin top-left, x right, y down —
    # the spatial-audio work consumes these coordinates, keep them explicit
    DEFAULT_ROOM = {"width": 10.0, "depth": 8.0, "units": "m", "origin": [0.0, 0.0]}

    def __init__(self, path, devices_file=None):
        self.path = path
        self.data = {"schema": SCHEMA, "name": "bopOS", "seats": {},
                     "devices": {}, "muted": False,
                     "room": dict(self.DEFAULT_ROOM), "master": 1.0, "presets": {},
                     "facilitator_commands": [],
                     "fleet_patch": None,
                     "params_patch": None,
                     "listener": None,
                     "simulation": {"active": False, "status": "off"},
                     "points": {}}  # /pt geometry, runtime-only (not in durable())
        self._save_task = None
        self._load()
        if self.data["listener"] is None:
            self.data["listener"] = self.default_listener()
        if not self.data["seats"] and devices_file and os.path.exists(devices_file):
            self._import_seed(devices_file)
            self.save()

    @property
    def devices(self):
        return self.data["devices"]

    @property
    def seats(self):
        return self.data["seats"]

    def _load(self):
        try:
            with open(self.path, encoding="utf-8") as source:
                loaded = json.load(source)
            # Bob's 2026-07-13 ruling is a hard break: pre-seat state is not
            # migrated or partially honoured.
            if (isinstance(loaded, dict) and loaded.get("schema") == SCHEMA
                    and isinstance(loaded.get("seats"), dict)):
                self.data["name"] = loaded.get("name", "bopOS")
                room = self.clean_room(loaded.get("room"))
                if room is not None:
                    self.data["room"] = room
                self.data["master"] = self.clean_master(loaded.get("master"))
                if isinstance(loaded.get("presets"), dict):
                    self.data["presets"] = loaded["presets"]
                self.data["facilitator_commands"] = self.clean_facilitator_commands(
                    loaded.get("facilitator_commands"))
                self.data["fleet_patch"] = self.clean_fleet_patch(loaded.get("fleet_patch"))
                params_patch = loaded.get("params_patch")
                self.data["params_patch"] = (params_patch.strip()
                                             if isinstance(params_patch, str)
                                             and params_patch.strip() else None)
                if self.data["fleet_patch"]:
                    # simulation["patch"] is a read-through of the fleet choice
                    self.data["simulation"]["patch"] = self.data["fleet_patch"]["name"]
                listener = self.clean_listener(loaded.get("listener"))
                if listener is not None:
                    self.data["listener"] = listener
                for key, value in loaded["seats"].items():
                    seat = self.clean_seat(value)
                    if seat is not None and str(seat["id"]) == str(key):
                        self.seats[str(seat["id"])] = seat
        except (OSError, ValueError, TypeError):
            pass

    def _runtime_device(self, uid, values=None, virtual=False):
        values = values or {}
        return {
            "uid": uid, "id": values.get("id", -1),
            "hostname": values.get("hostname", ""), "virtual": bool(virtual),
            "online": False, "last_seen": None, "ip": None, "version": None,
            "engine_alive": None, "rssi": None, "report": None,
            "declared": None, "undeclared": False, "rev": None,
            # Last host-manifest fingerprint acknowledged by this node for each
            # asset slot or patch:<name>. This is the strongest sync fact v1.3
            # exposes: the node receipts success but does not report a hash.
            "distribution": {},
            "fetch": {},  # runtime phase by slot: queued/fetching/ok/err
            # runtime bounded attempt: switching -> reconciling -> failed/timeout;
            # a matching patch observation clears it on success
            "patch_switch": None,
            "patches": None,  # runtime /os/patches listing; None = not queried
            "sync": None,  # runtime-only clock estimate: {offset, rtt, min_rtt, samples, at}
            "params": {},  # runtime declaration/catch-up mirror; durable values live on seat
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
                positions = []
                for key, index in (("pos1", 3), ("pos2", 4)):
                    if len(row) > index:
                        try:
                            positions.append([float(item) for item in row[index].split()])
                        except ValueError:
                            pass
                self.seats[str(device_id)] = {"id": device_id, "name": name,
                    "positions": positions, "params": {}, "bound": uid}

    def ensure(self, uid):
        if uid not in self.devices:
            self.devices[uid] = self._runtime_device(uid)
        return self.devices[uid]

    def public(self):
        return self.data

    def durable(self):
        return {"schema": SCHEMA, "name": self.data.get("name", "bopOS"),
                "room": self.data.get("room", dict(self.DEFAULT_ROOM)),
                "master": self.data.get("master", 1.0),
                "presets": self.data.get("presets", {}),
                "facilitator_commands": self.clean_facilitator_commands(
                    self.data.get("facilitator_commands")),
                "fleet_patch": self.clean_fleet_patch(self.data.get("fleet_patch")),
                "params_patch": self.data.get("params_patch"),
                "listener": dict(self.data["listener"]),
                "seats": {str(seat["id"]): dict(seat)
                          for seat in self.seats.values()}}

    @staticmethod
    def clean_positions(value):
        if not isinstance(value, list):
            return None
        cleaned = []
        for pair in value:
            if not isinstance(pair, (list, tuple)) or len(pair) < 2:
                return None
            try:
                point = [float(pair[0]), float(pair[1])]
            except (TypeError, ValueError):
                return None
            if not all(math.isfinite(item) for item in point):
                return None
            cleaned.append(point)
        return cleaned

    def clean_seat(self, value):
        if not isinstance(value, dict):
            return None
        try:
            seat_id = int(value.get("id"))
        except (TypeError, ValueError):
            return None
        positions = self.clean_positions(value.get("positions", []))
        if seat_id < 0 or positions is None:
            return None
        name = str(value.get("name", "")).strip()[:32]
        # no per-seat patch: the desired patch is fleet-scoped (fp-0, Bob Q1);
        # a "patch" key in an older state file is dropped silently here
        params = value.get("params", {})
        bound = value.get("bound")
        return {"id": seat_id, "name": name, "positions": positions,
                "params": dict(params) if isinstance(params, dict) else {},
                "bound": str(bound) if bound else None}

    def seat_for_uid(self, uid):
        device = self.devices.get(uid)
        if device and device.get("virtual") and device.get("seat_id") is not None:
            return self.seats.get(str(device["seat_id"]))
        return next((seat for seat in self.seats.values() if seat.get("bound") == uid), None)

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
    def clean_fleet_patch(value):
        # one fleet-wide desired patch record (fp-0 sec 1): {name, fingerprint,
        # staged_at, previous}. Anything malformed collapses to None (unset).
        if not isinstance(value, dict):
            return None
        name = str(value.get("name", "")).strip()
        if not name:
            return None

        def fingerprint(raw):
            return raw if isinstance(raw, str) and FINGERPRINT_RE.fullmatch(raw) else None

        try:
            staged_at = float(value.get("staged_at"))
        except (TypeError, ValueError):
            staged_at = None
        previous = value.get("previous")
        if isinstance(previous, dict) and str(previous.get("name", "")).strip():
            previous = {"name": str(previous["name"]).strip(),
                        "fingerprint": fingerprint(previous.get("fingerprint"))}
        else:
            previous = None
        return {"name": name, "fingerprint": fingerprint(value.get("fingerprint")),
                "staged_at": staged_at, "previous": previous}

    def stage_fleet_patch(self, name, fingerprint):
        # rotate `previous` only on a name change: re-staging the same patch
        # (host edit, simulation restart) refreshes fingerprint/staged_at in
        # place so Revert keeps pointing at the last *different* patch
        current = self.data.get("fleet_patch")
        previous = current.get("previous") if current else None
        if current and current.get("name") != name:
            previous = {"name": current["name"], "fingerprint": current.get("fingerprint")}
        self.data["fleet_patch"] = {"name": name, "fingerprint": fingerprint,
                                    "staged_at": time.time(), "previous": previous}
        # simulation["patch"] is a read-through of the fleet choice (fp-0 sec 1)
        self.data["simulation"]["patch"] = name
        return self.data["fleet_patch"]

    def reset_fleet_params(self, patch_name, defaults):
        """Replace the one fleet schema on a patch-name transition.

        Patch parameters are fleet-scoped authoring state even though their
        values live per seat.  A new patch name means a new manifest schema:
        old keys and coincidentally same-named values must not leak across it.
        Runtime mirrors are updated with the same full replacement so the UI
        cannot briefly present the previous schema while engines converge.
        """
        values = dict(defaults)
        for seat in self.seats.values():
            seat["params"] = dict(values)
        for device in self.devices.values():
            if self.seat_for_uid(device["uid"]) is not None:
                device["params"] = dict(values)
        self.data["params_patch"] = patch_name

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
        origin = value.get("origin", [0.0, 0.0])
        if not isinstance(origin, (list, tuple)) or len(origin) < 2:
            return None
        offsets = []
        for raw, limit in zip(origin[:2], dimensions):
            if isinstance(raw, bool):
                return None
            try:
                offset = float(raw)
            except (TypeError, ValueError):
                return None
            if not math.isfinite(offset):
                return None
            offsets.append(min(max(offset, 0.0), limit))
        return {"width": dimensions[0], "depth": dimensions[1], "units": "m",
                "origin": offsets}

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
        if (not isinstance(loaded, dict) or loaded.get("schema") != SCHEMA
                or not isinstance(loaded.get("seats"), dict)):
            return False
        rebuilt = {}
        rebound, waiting = [], []
        for key, value in loaded["seats"].items():
            seat = self.clean_seat(value)
            if seat is None or str(seat["id"]) != str(key):
                return False
            uid = seat.get("bound")
            if uid not in self.devices or not self.devices[uid].get("online"):
                if uid:
                    waiting.append({"id": seat["id"], "uid": uid})
                seat["bound"] = None
            elif uid:
                rebound.append({"id": seat["id"], "uid": uid})
            rebuilt[str(seat["id"])] = seat
        self.data["name"] = loaded.get("name", name)
        room = self.clean_room(loaded.get("room"))
        if room is not None:
            self.data["room"] = room
        self.data["master"] = self.clean_master(loaded.get("master"))
        self.data["presets"] = loaded["presets"] if isinstance(loaded.get("presets"), dict) else {}
        self.data["facilitator_commands"] = self.clean_facilitator_commands(
            loaded.get("facilitator_commands"))
        self.data["fleet_patch"] = self.clean_fleet_patch(loaded.get("fleet_patch"))
        params_patch = loaded.get("params_patch")
        self.data["params_patch"] = (params_patch.strip()
                                     if isinstance(params_patch, str)
                                     and params_patch.strip() else None)
        if self.data["fleet_patch"]:
            self.data["simulation"]["patch"] = self.data["fleet_patch"]["name"]
        else:
            self.data["simulation"].pop("patch", None)
        self.data["listener"] = (self.clean_listener(loaded.get("listener"))
                                 or self.default_listener())
        self.data["seats"] = rebuilt
        self.last_venue_rebind = {"rebound": rebound, "waiting": waiting}
        self.save()
        return True

    async def close(self):
        if self._save_task and not self._save_task.done():
            self._save_task.cancel()
            self.save()
