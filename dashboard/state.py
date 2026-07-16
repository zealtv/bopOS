import asyncio
import copy
import csv
import json
import math
import os
import re
import time


SCHEMA = 1
FACILITATOR_COMMANDS = frozenset(("restart-engine", "updatebopos", "reboot", "shutdown"))
FINGERPRINT_RE = re.compile(r"[0-9a-f]{64}")
MAX_GROUP_ID = 0x7fffffff


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
                     "groups": {}, "next_group_id": 0,
                     "devices": {}, "muted": False,
                     "room": dict(self.DEFAULT_ROOM), "master": 1.0, "presets": {},
                     "facilitator_commands": [],
                     "fleet_patch": None,
                     "params_patch": None,
                     "listener": None,
                     "simulation": {"active": False, "status": "off"},
                     "points": {}}  # /pt geometry, runtime-only (not in durable())
        self._save_task = None
        self._load_invalid = False
        self.last_venue_rebind = {"rebound": [], "waiting": []}
        self._load()
        if self.data["listener"] is None:
            self.data["listener"] = self.default_listener()
        if (not self._load_invalid and not self.data["seats"] and devices_file
                and os.path.exists(devices_file)):
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
                groups = self.clean_groups(loaded.get("groups", {}))
                next_group_id = self.clean_next_group_id(
                    loaded.get("next_group_id"), groups,
                    missing="next_group_id" not in loaded)
                rebuilt = self.clean_seats(loaded["seats"], groups)
                if groups is None or next_group_id is None or rebuilt is None:
                    self._load_invalid = True
                    return
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
                self.data["seats"] = rebuilt
                self.data["groups"] = groups
                self.data["next_group_id"] = next_group_id
            else:
                self._load_invalid = True
        except FileNotFoundError:
            pass
        except (OSError, ValueError, TypeError):
            self._load_invalid = True

    def _runtime_device(self, uid, values=None, virtual=False):
        values = values or {}
        return {
            "uid": uid, "id": values.get("id", -1),
            "hostname": values.get("hostname", ""), "virtual": bool(virtual),
            "online": False, "last_seen": None, "ip": None, "version": None,
            "revoking_assignment": False,
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
            "group_sync": None,  # runtime full-state membership convergence
        }

    def _import_seed(self, path):
        with open(path, newline="", encoding="utf-8") as source:
            rows = csv.reader(source, skipinitialspace=True)
            next(rows, None)
            for row in rows:
                if len(row) < 3:
                    continue
                uid, name = row[0].strip(), row[1].strip()
                device_id = self.clean_seat_id(row[2].strip())
                if device_id is None or not uid:
                    continue
                positions = []
                for key, index in (("pos1", 3), ("pos2", 4)):
                    if len(row) > index:
                        try:
                            positions.append([float(item) for item in row[index].split()])
                        except ValueError:
                            pass
                if (device_id < 0 or str(device_id) in self.seats
                        or any(seat.get("bound") == uid for seat in self.seats.values())):
                    continue
                self.seats[str(device_id)] = {"id": device_id, "name": name,
                    "positions": positions, "params": {}, "groups": [], "bound": uid}

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
                "groups": {str(group["id"]): dict(group)
                           for group in self.data.get("groups", {}).values()},
                "next_group_id": self.data.get("next_group_id", 0),
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
        seat_id = self.clean_seat_id(value.get("id"))
        if seat_id is None:
            return None
        positions = self.clean_positions(value.get("positions", []))
        if seat_id < 0 or positions is None:
            return None
        name = str(value.get("name", "")).strip()[:32]
        # no per-seat patch: the desired patch is fleet-scoped (fp-0, Bob Q1);
        # a "patch" key in an older state file is dropped silently here
        params = value.get("params", {})
        groups = self.clean_group_ids(value.get("groups", []))
        bound = value.get("bound")
        if bound is not None:
            if not isinstance(bound, str) or not bound.strip():
                return None
            bound = bound.strip()
        if groups is None:
            return None
        return {"id": seat_id, "name": name, "positions": positions,
                "params": dict(params) if isinstance(params, dict) else {},
                "groups": groups,
                "bound": bound}

    @staticmethod
    def clean_seat_id(value):
        if isinstance(value, bool):
            return None
        if isinstance(value, int):
            return value if value >= 0 else None
        if isinstance(value, str) and re.fullmatch(r"0|[1-9][0-9]*", value.strip()):
            return int(value.strip())
        return None

    @staticmethod
    def clean_group_id(value):
        if isinstance(value, bool):
            return None
        if isinstance(value, int):
            return value if 0 <= value <= MAX_GROUP_ID else None
        if isinstance(value, str) and re.fullmatch(r"0|[1-9][0-9]*", value.strip()):
            parsed = int(value.strip())
            return parsed if parsed <= MAX_GROUP_ID else None
        return None

    @classmethod
    def clean_group_ids(cls, value):
        if not isinstance(value, (list, tuple)):
            return None
        cleaned = []
        for raw in value:
            group_id = cls.clean_group_id(raw)
            if group_id is None or group_id in cleaned:
                return None
            cleaned.append(group_id)
        return sorted(cleaned)

    @classmethod
    def clean_group(cls, value):
        if not isinstance(value, dict):
            return None
        group_id = cls.clean_group_id(value.get("id"))
        if group_id is None:
            return None
        name = value.get("name", "")
        if not isinstance(name, str):
            return None
        return {"id": group_id, "name": name.strip()[:48]}

    @classmethod
    def clean_groups(cls, value):
        if not isinstance(value, dict):
            return None
        rebuilt = {}
        for key, raw in value.items():
            group = cls.clean_group(raw)
            if (group is None or str(group["id"]) != str(key)
                    or str(group["id"]) in rebuilt):
                return None
            rebuilt[str(group["id"])] = group
        return dict(sorted(rebuilt.items(), key=lambda item: int(item[0])))

    @staticmethod
    def clean_next_group_id(value, groups, missing=False):
        if groups is None:
            return None
        floor = max((group["id"] for group in groups.values()), default=-1) + 1
        if missing:
            return floor
        if (isinstance(value, bool) or not isinstance(value, int)
                or value < floor or value > MAX_GROUP_ID + 1):
            return None
        return value

    def clean_seats(self, value, groups=None):
        if not isinstance(value, dict):
            return None
        groups = self.data.get("groups", {}) if groups is None else groups
        if groups is None:
            return None
        known_groups = {int(group_id) for group_id in groups}
        rebuilt, bound = {}, set()
        for key, raw in value.items():
            seat = self.clean_seat(raw)
            if seat is None or str(seat["id"]) != str(key) or str(seat["id"]) in rebuilt:
                return None
            uid = seat.get("bound")
            if uid and uid in bound:
                return None
            if not set(seat["groups"]).issubset(known_groups):
                return None
            uid and bound.add(uid)
            rebuilt[str(seat["id"])] = seat
        return rebuilt

    def create_group(self, name=""):
        """Create a never-reused canonical group ID and persist its allocator."""
        cleaned = self.clean_group({"id": 0, "name": name})
        if cleaned is None:
            return None, "Group names must be text."
        group_id = self.clean_next_group_id(
            self.data.get("next_group_id"), self.data.get("groups", {}))
        if group_id is None or group_id > MAX_GROUP_ID:
            return None, "No group IDs are available."
        group = {"id": group_id, "name": cleaned["name"]}
        previous = copy.deepcopy(self.data.get("groups", {}))
        previous_next = self.data.get("next_group_id", 0)
        self.data.setdefault("groups", {})[str(group_id)] = group
        self.data["next_group_id"] = group_id + 1
        self.data["groups"] = dict(sorted(
            self.data["groups"].items(), key=lambda item: int(item[0])))
        try:
            self.save()
        except (OSError, TypeError, ValueError):
            self.data["groups"] = previous
            self.data["next_group_id"] = previous_next
            return None, "Could not save the group; no changes were made."
        return group, None

    def rename_group(self, group_id, name):
        group_id = self.clean_group_id(group_id)
        candidate = self.clean_group({"id": group_id, "name": name})
        key = str(group_id)
        if candidate is None:
            return None, "Group names must be text."
        if key not in self.data.get("groups", {}):
            return None, "Group no longer exists."
        previous = dict(self.data["groups"][key])
        self.data["groups"][key] = candidate
        try:
            self.save()
        except (OSError, TypeError, ValueError):
            self.data["groups"][key] = previous
            return None, "Could not save the group; no changes were made."
        return candidate, None

    def delete_group(self, group_id):
        group_id = self.clean_group_id(group_id)
        key = str(group_id)
        if group_id is None or key not in self.data.get("groups", {}):
            return None, "Group no longer exists."
        previous_groups = copy.deepcopy(self.data["groups"])
        previous_memberships = {key: list(seat.get("groups", []))
                                for key, seat in self.seats.items()}
        removed = self.data["groups"].pop(key)
        for seat in self.seats.values():
            seat["groups"] = [item for item in seat.get("groups", [])
                              if item != group_id]
        try:
            self.save()
        except (OSError, TypeError, ValueError):
            self.data["groups"] = previous_groups
            for seat_key, membership in previous_memberships.items():
                self.seats[seat_key]["groups"] = membership
            return None, "Could not delete the group; no changes were made."
        return removed, None

    def set_seat_groups(self, seat_id, group_ids):
        seat_id = self.clean_seat_id(seat_id)
        seat = self.seats.get(str(seat_id))
        cleaned = self.clean_group_ids(group_ids)
        if seat is None:
            return None, "Seat no longer exists."
        if (cleaned is None or not set(cleaned).issubset(
                {group["id"] for group in self.data.get("groups", {}).values()})):
            return None, "Choose existing groups without duplicates."
        previous = list(seat.get("groups", []))
        seat["groups"] = cleaned
        try:
            self.save()
        except (OSError, TypeError, ValueError):
            seat["groups"] = previous
            return None, "Could not save Seat membership; no changes were made."
        return seat, None

    def seats_for_group(self, group_id):
        group_id = self.clean_group_id(group_id)
        if group_id is None or str(group_id) not in self.data.get("groups", {}):
            return []
        return sorted((seat for seat in self.seats.values()
                       if group_id in seat.get("groups", [])),
                      key=lambda seat: seat["id"])

    def set_group_param(self, group_id, name, value):
        members = self.seats_for_group(group_id)
        for seat in members:
            seat.setdefault("params", {})[name] = value
            uid = seat.get("bound")
            if uid in self.devices:
                self.devices[uid].setdefault("params", {})[name] = value
            for device in self.devices.values():
                if (device.get("virtual")
                        and str(device.get("seat_id")) == str(seat["id"])):
                    device.setdefault("params", {})[name] = value
        return members

    def reindex_seat(self, old_id, new_id):
        old_id, new_id = self.clean_seat_id(old_id), self.clean_seat_id(new_id)
        if old_id is None or new_id is None:
            return None, "Seat IDs must be non-negative integers."
        old_key, new_key = str(old_id), str(new_id)
        if old_key not in self.seats:
            return None, "Seat no longer exists."
        if old_id == new_id:
            return self.seats[old_key], None
        if new_key in self.seats:
            return None, f"Seat ID {new_id} already exists."
        seats = copy.deepcopy(self.seats)
        presets = copy.deepcopy(self.data.get("presets", {}))
        if not isinstance(presets, dict):
            return None, "Seat presets are malformed; no changes were made."
        for preset in presets.values():
            if not isinstance(preset, dict):
                return None, "Seat presets are malformed; no changes were made."
            values = preset.get("seats")
            if values is None:
                continue
            if not isinstance(values, dict):
                return None, "Seat presets are malformed; no changes were made."
            if new_key in values:
                return None, f"A preset already contains Seat ID {new_id}."
            if old_key in values:
                values[new_key] = values.pop(old_key)
        seat = seats.pop(old_key)
        seat["id"] = new_id
        seats[new_key] = seat
        if self.clean_seats(seats) is None:
            return None, "The reindexed Seat would make the installation invalid."
        previous_seats, previous_presets = self.data["seats"], self.data.get("presets", {})
        self.data["seats"], self.data["presets"] = seats, presets
        try:
            self.save()
        except (OSError, TypeError, ValueError):
            self.data["seats"], self.data["presets"] = previous_seats, previous_presets
            return None, "Could not save the reindexed Seat; no changes were made."
        return seat, None

    def delete_seat(self, seat_id):
        key = str(seat_id)
        if key not in self.seats:
            return None
        seats = copy.deepcopy(self.seats)
        presets = copy.deepcopy(self.data.get("presets", {}))
        seat = seats.pop(key)
        if not isinstance(presets, dict):
            return None
        for preset in presets.values():
            if not isinstance(preset, dict):
                return None
            values = preset.get("seats")
            if values is not None and not isinstance(values, dict):
                return None
            if values is not None:
                values.pop(key, None)
        previous_seats, previous_presets = self.data["seats"], self.data.get("presets", {})
        self.data["seats"], self.data["presets"] = seats, presets
        try:
            self.save()
        except (OSError, TypeError, ValueError):
            self.data["seats"], self.data["presets"] = previous_seats, previous_presets
            return None
        return seat

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

    def reconcile_fleet_params(self, patch_name, identities, defaults):
        """Apply a staged same-patch schema revision without identity guesses.

        Unchanged qualified identities retain their values, new identities use
        declared defaults when present, and removed identities are pruned.
        A patch-name transition remains a full reset via reset_fleet_params().
        """
        if self.data.get("params_patch") != patch_name:
            self.reset_fleet_params(patch_name, defaults)
            return
        active = tuple(identities)
        for seat in self.seats.values():
            previous = seat.get("params", {})
            seat["params"] = {
                identity: previous.get(identity, defaults[identity])
                for identity in active
                if identity in previous or identity in defaults
            }
        for device in self.devices.values():
            seat = self.seat_for_uid(device["uid"])
            if seat is not None:
                device["params"] = dict(seat["params"])

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
        temporary = path + ".tmp"
        snapshot = self.durable()
        snapshot["name"] = name
        with open(temporary, "w", encoding="utf-8") as target:
            json.dump(snapshot, target, indent=2, sort_keys=True)
            target.write("\n")
        os.replace(temporary, path)

    def read_venue(self, name):
        path = os.path.join(self.venues_dir(), name + ".json")
        try:
            with open(path, encoding="utf-8") as source:
                loaded = json.load(source)
        except (OSError, ValueError):
            return None, None
        if (not isinstance(loaded, dict) or loaded.get("schema") != SCHEMA
                or not isinstance(loaded.get("seats"), dict)):
            return None, None
        groups = self.clean_groups(loaded.get("groups", {}))
        next_group_id = self.clean_next_group_id(
            loaded.get("next_group_id"), groups,
            missing="next_group_id" not in loaded)
        rebuilt = self.clean_seats(loaded["seats"], groups)
        if groups is None or next_group_id is None or rebuilt is None:
            return None, None
        loaded = dict(loaded)
        loaded["groups"] = groups
        loaded["next_group_id"] = next_group_id
        return loaded, rebuilt

    def load_venue(self, name, prepared=None):
        # replace the current installation with a saved venue; keeps live
        # runtime fields (online/ip/…) only for devices the venue also knows
        loaded, source_seats = prepared or self.read_venue(name)
        if loaded is None:
            return False
        rebuilt = {}
        rebound, waiting = [], []
        for key, source_seat in source_seats.items():
            seat = dict(source_seat)
            uid = seat.get("bound")
            if uid not in self.devices or not self.devices[uid].get("online"):
                if uid:
                    waiting.append({"id": seat["id"], "uid": uid})
            elif uid:
                rebound.append({"id": seat["id"], "uid": uid})
            rebuilt[str(seat["id"])] = seat
        keys = ("name", "room", "master", "presets", "facilitator_commands", "groups",
                "next_group_id",
                "fleet_patch", "params_patch", "listener", "seats", "simulation")
        previous = {key: copy.deepcopy(self.data.get(key)) for key in keys}
        previous_rebind = copy.deepcopy(self.last_venue_rebind)
        self.data["name"] = name
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
        self.data["groups"] = loaded.get("groups", {})
        # Venue structure can roll back, but the wire-identity allocator never
        # may: nodes offline during a venue load can retain any ID ever issued.
        self.data["next_group_id"] = max(
            int(self.data.get("next_group_id", 0)),
            int(loaded.get("next_group_id", 0)))
        self.data["seats"] = rebuilt
        self.last_venue_rebind = {"rebound": rebound, "waiting": waiting}
        try:
            self.save()
        except (OSError, TypeError, ValueError):
            for key, value in previous.items():
                self.data[key] = value
            self.last_venue_rebind = previous_rebind
            return False
        return True

    async def close(self):
        if self._save_task and not self._save_task.done():
            self._save_task.cancel()
            self.save()
