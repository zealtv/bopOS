import asyncio
import ipaddress
import json
import logging
import math
import os
import random
import re
import socket
import statistics
import sys
import time
from collections import deque

from pythonosc.osc_message import OscMessage
from pythonosc.osc_message_builder import OscMessageBuilder

import points
from state import reconcile_patch_switch_observation

REPO_DIR = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
if REPO_DIR not in sys.path:
    sys.path.insert(0, REPO_DIR)
from python import manifest as patch_manifest


LEGACY_DECLARATIONS = [
    {"name": "gain", "type": "f", "min": 0, "max": 1, "default": 0.75},
    {"name": "gain2", "type": "f", "min": 0, "max": 1, "default": 0.3},
    {"name": "backing", "type": "f", "min": 0, "max": 1, "default": 0.8},
    {"name": "echo", "type": "i", "min": 0, "max": 1, "default": 0},
]
log = logging.getLogger("bopos.osc")

# Clock-sync leader (contract sec 3.1). The dashboard is the leader (resolved
# 2026-07-05): it broadcasts /sync/ping, estimates each device's offset from the
# echoing /sync/pong, and pushes /<id>/sync/offset. Offset math lives leader-side
# (only the leader sees the round trip); the node applies it (sync-2). Values are
# nanoseconds; offset === deviceClock - leaderClock.
SYNC_PING_INTERVAL = 0.5           # mean seconds between pings
SYNC_PING_JITTER = 0.1             # +/- randomization, avoids lockstep pong bursts
SYNC_WINDOW = 16                   # rolling samples kept per device
SYNC_RTT_CEILING_NS = 200_000_000  # discard a pong slower than this outright
SYNC_LOWRTT_BAND = 1.5             # estimate from samples within 1.5x window-min RTT
SYNC_MIN_SAMPLES = 3               # let the estimate settle before pushing
ASSIGN_REPLAY_MIN_SECONDS = 2.0    # bound a broken node's wrong-id ack loop
FETCH_TIMEOUT_SECONDS = 1800       # large media can be slow; UDP loss must still recover
REQUEST_TIMEOUT_SECONDS = 5.0
UNASSIGN_TIMEOUT_SECONDS = 5.0
AUDITION_PARAM_REPLAY_SECONDS = (1.5, 4.0)
GROUP_RETRY_SECONDS = (0.5, 1.0, 2.0)
GROUP_RETRY_EXPIRE_SECONDS = 2.0
ASSET_REQUERY_SECONDS = (0.5, 1.0, 2.0, 4.0)


class OSCProtocol(asyncio.DatagramProtocol):
    def __init__(self, bridge):
        self.bridge = bridge

    def datagram_received(self, data, addr):
        try:
            message = OscMessage(data)
            self.bridge.handle(message.address, list(message.params), addr[0])
        except Exception:
            log.debug("invalid OSC datagram", exc_info=True)


class OSCBridge:
    def __init__(self, state, broadcast, listen_port, send_port, target):
        self.state = state
        self.broadcast = broadcast
        self.listen_port = listen_port
        self.destination = (target, send_port)
        self.transport = None
        self.sender = None
        self.pending = {"params": deque(), "report": deque(), "patches": deque(),
                        "assets": deque()}
        # v1.3 distribution replies carry slot + phase/status but no uid. Real
        # nodes are normally attributable by source IP; the ordered records are
        # the fallback for simfleet, whose devices share one loopback address.
        self.fetch_pending = {}
        self.pending_timeouts = {}
        self._sync = {}        # uid -> {"offsets": deque, "rtts": deque}
        self._sync_seq = 0
        self._sync_sent = {}   # uid -> last sync ws-broadcast time (throttle)
        self._ping_task = None
        self._points_task = None
        self._points_started = time.monotonic()  # motion clock zero
        self._assign_replayed = {}  # uid -> monotonic time of last full replay
        self._unassign_replayed = {}  # stale unbound uid -> last repair send
        self._unassign_waiters = {}  # uid -> future; suppresses authoritative replay
        self._audition_param_replays = set()
        self._group_pending = {}  # uid -> latest full-state membership attempt
        # uid -> bounded retry generation for inventories whose background
        # fingerprint warming has not completed yet.
        self._asset_requeries = {}

    async def start(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if hasattr(socket, "SO_REUSEPORT"):
            try:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            except OSError:
                pass
        sock.bind(("", self.listen_port))
        sock.setblocking(False)
        loop = asyncio.get_running_loop()
        self.transport, _ = await loop.create_datagram_endpoint(lambda: OSCProtocol(self), sock=sock)
        self.sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sender.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self._ping_task = asyncio.create_task(self.sync_ping_loop())
        self._points_task = asyncio.create_task(self.points_loop())

    def close(self):
        if self._ping_task:
            self._ping_task.cancel()
        if self._points_task:
            self._points_task.cancel()
        if self.transport:
            self.transport.close()
        if self.sender:
            self.sender.close()
        for records in self.fetch_pending.values():
            for record in records:
                record.get("timeout") and record["timeout"].cancel()
        for timeout in self.pending_timeouts.values():
            timeout.cancel()
        for waiter in self._unassign_waiters.values():
            if not waiter.done():
                waiter.cancel()
        self._unassign_waiters.clear()
        for record in self._group_pending.values():
            record.get("timeout") and record["timeout"].cancel()
        self._group_pending.clear()
        for record in self._asset_requeries.values():
            record.get("timeout") and record["timeout"].cancel()
        self._asset_requeries.clear()
        for replay in self._audition_param_replays:
            replay.cancel()
        self._audition_param_replays.clear()

    def schedule_audition_param_replay(self, uid):
        """Replay dashboard-owned controls after a managed patch can receive.

        Process-alive heartbeats precede Pd patch graph readiness on macOS.
        The immediate declaration exchange remains the fast path; two bounded
        retries converge both ordinary and slower-loading patches without a
        permanent control stream.
        """
        loop = asyncio.get_running_loop()
        expected_device = self.state.devices.get(uid)
        for delay in AUDITION_PARAM_REPLAY_SECONDS:
            holder = {}

            def replay(device_uid=uid, device_generation=expected_device,
                       replay_holder=holder):
                self._audition_param_replays.discard(replay_holder["handle"])
                device = self.state.devices.get(device_uid)
                mode = self.state.data.get("supervisor", {}).get("mode", "off")
                if device is device_generation \
                        and device.get("virtual") and device.get("online") \
                        and mode in {"simulate", "edit"}:
                    self.request(device_uid, "params")

            handle = loop.call_later(delay, replay)
            holder["handle"] = handle
            self._audition_param_replays.add(handle)

    async def sync_ping_loop(self):
        # leader broadcasts /sync/ping ~2 Hz, jittered so N nodes don't pong in
        # lockstep (HB does 500+-100 ms). leaderTime is echoed back in the pong,
        # so the leader stays stateless. Always on: tight-sync assumes the
        # dashboard is running (contract sec 3.1).
        try:
            while True:
                self._sync_seq = (self._sync_seq + 1) & 0x7fffffff
                self.send("/sync/ping", [self._sync_seq, str(time.monotonic_ns())])
                await asyncio.sleep(SYNC_PING_INTERVAL
                                    + random.uniform(-SYNC_PING_JITTER, SYNC_PING_JITTER))
        except asyncio.CancelledError:
            pass

    @staticmethod
    def _console_args(args):
        # WS console tap payloads must be JSON-safe; OSC args are normally
        # str/int/float already, anything exotic degrades to its repr.
        return [arg if isinstance(arg, (str, int, float, bool)) else str(arg)
                for arg in args]

    def send(self, address, args=()):
        self.sender.sendto(self._datagram(address, args), self.destination)
        # Console tap (design note sec 3): everything the dashboard sends,
        # any tab. Always-on; filtering is client-side. Guarded: sends can
        # legally happen before the asyncio loop exists.
        try:
            self.broadcast("osc_out", {"ts": time.time(), "address": address,
                                       "args": self._console_args(args),
                                       "target": self.destination[0]})
        except RuntimeError:
            pass

    def set_target(self, host):
        self.destination = (str(host), self.destination[1])

    @staticmethod
    def _datagram(address, args=()):
        builder = OscMessageBuilder(address=address)
        for value in args:
            if isinstance(value, float):
                value = float(format(value, ".6g"))
            builder.add_arg(value)
        return builder.build().dgram

    def send_audition_listener(self):
        """Send the private listener frame only to the local audition relay."""
        listener = self.state.data.get("listener")
        if not self.state.data.get("simulation", {}).get("active"):
            return
        if not listener or self.sender is None:
            return
        # The listener's own range (audition-falloff/2-range-widget) drives
        # the audition falloff; fall back to the default range for
        # missing/invalid range (older persisted state, pre-widget clients).
        try:
            range_m = float(listener.get("range"))
        except (TypeError, ValueError):
            range_m = None
        if range_m is None or not math.isfinite(range_m) or range_m <= 0:
            range_m = self.state.default_range()
        if not math.isfinite(range_m) or range_m <= 0:
            return
        packet = self._datagram("/audition/listener", [
            float(listener["x"]), float(listener["y"]),
            float(listener["heading"]), range_m,
        ])
        self.sender.sendto(packet, ("127.0.0.1", self.destination[1]))

    def send_editor_element(self, element):
        self.send("/audition/editor-element", [int(element)])

    def set_param(self, selector, name, value):
        self.send(f"/{selector}/p/{name}", [value])

    def set_group_param(self, group_id, name, value):
        """Update all durable member mirrors, then emit one group datagram."""
        group_id = self.state.clean_group_id(group_id)
        if group_id is None or str(group_id) not in self.state.data.get("groups", {}):
            return None
        members = self.state.set_group_param(group_id, name, value)
        self.state.save_debounced()
        self.set_param(f"g{group_id}", name, value)
        member_ids = {seat["id"] for seat in members}
        for device in self.state.devices.values():
            seat = self.state.seat_for_uid(device["uid"])
            if seat is not None and seat["id"] in member_ids:
                self.broadcast("device_update", device)
        return members

    def send_master(self, selector="all"):
        # provided term (contract sec 4.1): idempotent full-state; the engine
        # multiplies it into its own output stage, so the wire carries raw
        # mixes only — no dashboard-side composition (seam ruling R1)
        self.send(f"/{selector}/os/master",
                  [float(self.state.data.get("master", 1.0))])

    def fire_cue(self, cue_id, lead_ms=500):
        """Schedule one named fleet cue in leader monotonic time."""
        lead_ms = min(max(int(lead_ms), 100), 10000)
        shared_time_ns = time.monotonic_ns() + lead_ms * 1_000_000
        self.send("/cue", [str(cue_id), str(shared_time_ns)])
        return shared_time_ns, lead_ms

    def fire_cue_now(self, cue_id):
        """Fire through the normal cue scheduler at its earliest deadline."""
        shared_time_ns = time.monotonic_ns()
        self.send("/cue", [str(cue_id), str(shared_time_ns)])
        return shared_time_ns

    def _points_elapsed(self):
        return time.monotonic() - self._points_started

    def send_points_frame(self):
        # one atomic full-state frame (contract sec 4.1). /pt is selector-less,
        # so the catch-up "unicast" to a reappearing device is a re-broadcast
        # every other node applies idempotently.
        self.send("/pt", points.frame_args(self.state.data.get("points") or {},
                                           self._points_elapsed()))

    def set_points(self, new_points):
        # full-state replace mirroring the wire frame; devices release points
        # that vanished. Resets the motion clock so paths sweep from the top.
        self.state.data["points"] = new_points
        self._points_started = time.monotonic()
        self.send_points_frame()

    def upsert_point(self, point):
        # sparse authoring edit: one point on the wire, the rest hold
        if point.get("motion"):
            point["motion"]["started"] = self._points_elapsed()
        self.state.data.setdefault("points", {})[point["id"]] = point
        self.send("/pt", points.sparse_args(point, self._points_elapsed()))

    def send_editor_point(self, point):
        # Editor scratch uses the same /pt seam without joining the durable or
        # installation-wide point model. The edit supervisor owns the relay.
        self.send("/pt", points.sparse_args(point, 0.0))

    def clear_editor_point(self, point_id):
        self.send("/pt/clear", [int(point_id)])

    def clear_point(self, point_id):
        if (self.state.data.get("points") or {}).pop(point_id, None) is not None:
            self.send("/pt/clear", [int(point_id)])

    async def points_loop(self):
        # ~25 Hz only while a point moves; a static set is one frame (sent by
        # the mutators above) then silence — silence = hold (contract sec 4.1)
        try:
            while True:
                await asyncio.sleep(1.0 / points.RATE_HZ)
                current = self.state.data.get("points") or {}
                if any(points.is_dynamic(point) for point in current.values()):
                    self.send_points_frame()
                    elapsed = time.monotonic() - self._points_started
                    evaluated = {str(point_id): list(points.current_xy(point, elapsed))
                                 for point_id, point in current.items()}
                    self.broadcast("point_frame", {"points": evaluated})
        except asyncio.CancelledError:
            pass

    def action(self, selector, verb):
        self.send(f"/{selector}/os/{verb}")

    def uid_command(self, uid, verb, args=()):
        self.send("/all/os/to", [str(uid), str(verb), *args])

    def uid_action(self, uid, verb):
        self.uid_command(uid, verb)

    def set_device_mute(self, uid, value):
        """Send one exact-UID persistent physical-box mute intent."""
        self.uid_command(uid, "mute", [int(bool(value))])

    def set_device_hostname(self, uid, hostname):
        """Send one exact-UID alias-derived hostname target."""
        self.uid_command(uid, "hostname", [str(hostname)])

    async def unassign(self, uid, timeout=UNASSIGN_TIMEOUT_SECONDS):
        """Request id=-1 and hold assignment replay until its heartbeat ack."""
        device = self.state.devices.get(uid)
        if not device or device.get("virtual"):
            return False
        existing = self._unassign_waiters.get(uid)
        if existing is not None:
            return bool(await asyncio.shield(existing))
        waiter = asyncio.get_running_loop().create_future()
        self._unassign_waiters[uid] = waiter
        device["revoking_assignment"] = True
        self.broadcast("device_update", device)
        self.uid_command(uid, "unassign")
        try:
            return bool(await asyncio.wait_for(waiter, timeout))
        except asyncio.TimeoutError:
            return False
        finally:
            if self._unassign_waiters.get(uid) is waiter:
                self._unassign_waiters.pop(uid, None)

    def fetch(self, uid, uri, slot, fingerprint):
        device = self.state.devices.get(uid)
        if not device or int(device.get("id", -1)) < 0:
            return
        records = self.fetch_pending.setdefault(slot, deque())
        if any(record["uid"] == uid for record in records):
            return False  # one generation per device/slot; never mislabel coalesced bytes
        record = {"uid": uid, "fingerprint": fingerprint, "phase": "sent"}
        record["timeout"] = asyncio.get_running_loop().call_later(
            FETCH_TIMEOUT_SECONDS, self._expire_fetch, slot, record)
        records.append(record)
        device.setdefault("fetch", {})[slot] = "sent"
        self.send(f"/{int(device['id'])}/os/fetch", [uri, slot])
        self.broadcast("device_update", device)
        return True

    def fetch_matches(self, uid, slot, fingerprint):
        """Whether an existing generation is already fetching these bytes.

        A superseding fleet operation may observe an identical in-flight
        generation, but must never relabel or attach to different bytes.
        """
        return any(record["uid"] == uid and record["fingerprint"] == fingerprint
                   for record in self.fetch_pending.get(slot, ()))

    def request(self, uid, member):
        device = self.state.devices.get(uid)
        if not device:
            return False
        if uid in self.pending[member]:
            return False
        self.pending[member].append(uid)
        self.pending_timeouts[(member, uid)] = asyncio.get_running_loop().call_later(
            REQUEST_TIMEOUT_SECONDS, self._expire_request, member, uid)
        if member == "report":
            self.uid_command(uid, "report")
        elif int(device.get("id", -1)) >= 0:
            self.send(f"/{int(device['id'])}/os/{member}")
        else:
            self._finish_request(member, uid)
            try:
                self.pending[member].remove(uid)
            except ValueError:
                pass
            return False
        return True

    def request_assets(self, uid, reset=True):
        """Query one inventory, optionally starting a fresh retry generation."""
        if reset:
            previous = self._asset_requeries.pop(uid, None)
            if previous:
                previous.get("timeout") and previous["timeout"].cancel()
        return self.request(uid, "assets")

    def _cancel_asset_requery(self, uid):
        record = self._asset_requeries.pop(uid, None)
        if record:
            record.get("timeout") and record["timeout"].cancel()

    def _schedule_asset_requery(self, uid):
        device = self.state.devices.get(uid)
        if device is None or not device.get("online"):
            self._cancel_asset_requery(uid)
            return
        listing = device.get("assets")
        unresolved = isinstance(listing, list) and any(
            item.get("fingerprint") is None for item in listing)
        if not unresolved:
            self._cancel_asset_requery(uid)
            return
        record = self._asset_requeries.setdefault(
            uid, {"attempts": 0, "timeout": None})
        if record.get("timeout") is not None:
            return
        if record["attempts"] >= len(ASSET_REQUERY_SECONDS):
            return
        delay = ASSET_REQUERY_SECONDS[record["attempts"]]
        record["timeout"] = asyncio.get_running_loop().call_later(
            delay, self._requery_assets, uid, record)

    def _requery_assets(self, uid, record):
        if self._asset_requeries.get(uid) is not record:
            return
        record["timeout"] = None
        if self.request(uid, "assets"):
            record["attempts"] += 1
        # If a request is already in flight, its reply or expiry resumes the
        # bounded sequence; do not spin another timer alongside it.

    def os_command(self, selector, member, args=()):
        self.send(f"/{selector}/os/{member}", args)

    def assign(self, uid, device_id, name, elements=()):
        # idempotent full-state; only the node whose uid matches applies it,
        # and it persists the lot for standalone operation (contract sec 5).
        # Element positions ride along: one x y pair per element, pair order
        # = element index (true N — the fixed pos1/pos2 spelling is retired).
        args = [str(uid), int(device_id), str(name)]
        for position in elements or ():
            args += [float(position[0]), float(position[1])]
        self.send("/all/os/assign", args)
        device = self.state.devices.get(uid)
        seat = self.state.seat_for_uid(uid)
        if device is not None and seat is not None and int(seat["id"]) == int(device_id):
            # Assignment and membership are separate UDP transactions. Never
            # send them back-to-back: reordering could install the new Seat's
            # groups while the node still routes under its old Seat. A later
            # matching-id heartbeat is the convergence gate.
            record = self._group_pending.pop(uid, None)
            if record:
                record.get("timeout") and record["timeout"].cancel()
            device["group_sync"] = {"status": "awaiting_assignment",
                                    "desired": list(seat.get("groups", []))}

    @staticmethod
    def _wire_group_ids(values):
        if not isinstance(values, (list, tuple)):
            return None
        if any(isinstance(value, bool) or not isinstance(value, int) for value in values):
            return None
        if any(value < 0 or value > 0x7fffffff for value in values):
            return None
        if len(set(values)) != len(values):
            return None
        return tuple(sorted(values))

    def send_groups(self, uid, groups=None):
        """Start a bounded full-state membership convergence attempt."""
        device = self.state.devices.get(uid)
        seat = self.state.seat_for_uid(uid)
        if (device is None or seat is None or not device.get("online")
                or self.sender is None):
            if device is not None:
                device["group_sync"] = {"status": "offline", "desired":
                                        list(seat.get("groups", [])) if seat else []}
            return False
        if (device.get("group_sync") or {}).get("status") == "awaiting_assignment":
            # Membership may change while assignment convergence is in flight.
            # Keep the latest desired state visible, but do not put it on UDP
            # until a later heartbeat proves the node routes as this Seat.
            device["group_sync"] = {"status": "awaiting_assignment",
                                    "desired": list(seat.get("groups", []))}
            self.broadcast("device_update", device)
            return False
        desired = self._wire_group_ids(
            list(seat.get("groups", [])) if groups is None else list(groups))
        if desired is None:
            return False
        previous = self._group_pending.pop(uid, None)
        if previous:
            previous.get("timeout") and previous["timeout"].cancel()
        record = {"desired": desired, "attempts": 1, "retry_index": 0,
                  "timeout": None}
        self._group_pending[uid] = record
        self.send("/all/os/groups", [str(uid), *desired])
        device["group_sync"] = {"status": "pending", "desired": list(desired),
                                "attempts": 1}
        self.broadcast("device_update", device)
        self._schedule_group_retry(uid, record)
        return True

    def _schedule_group_retry(self, uid, record):
        loop = asyncio.get_running_loop()
        index = record["retry_index"]
        delay = (GROUP_RETRY_SECONDS[index]
                 if index < len(GROUP_RETRY_SECONDS) else GROUP_RETRY_EXPIRE_SECONDS)
        record["timeout"] = loop.call_later(delay, self._retry_groups, uid, record)

    def _retry_groups(self, uid, record):
        if self._group_pending.get(uid) is not record:
            return
        index = record["retry_index"]
        device = self.state.devices.get(uid)
        seat = self.state.seat_for_uid(uid)
        current = tuple(seat.get("groups", [])) if seat else None
        if (device is None or seat is None or not device.get("online")
                or current != record["desired"]):
            self._group_pending.pop(uid, None)
            if device is not None:
                device["group_sync"] = {"status": "offline" if not device.get("online")
                                        else "superseded",
                                        "desired": list(current or ())}
                self.broadcast("device_update", device)
            if device is not None and seat is not None and device.get("online"):
                self.send_groups(uid)
            return
        if index >= len(GROUP_RETRY_SECONDS):
            self._group_pending.pop(uid, None)
            device["group_sync"] = {"status": "timeout",
                                    "desired": list(record["desired"]),
                                    "attempts": record["attempts"]}
            self.broadcast("device_update", device)
            return
        self.send("/all/os/groups", [str(uid), *record["desired"]])
        record["attempts"] += 1
        record["retry_index"] += 1
        device["group_sync"] = {"status": "pending",
                                "desired": list(record["desired"]),
                                "attempts": record["attempts"]}
        self.broadcast("device_update", device)
        self._schedule_group_retry(uid, record)

    def _finish_groups(self, uid, observed, source):
        device = self.state.devices.get(uid)
        seat = self.state.seat_for_uid(uid)
        if device is None or seat is None:
            return
        desired = tuple(seat.get("groups", []))
        if not device.get("online"):
            record = self._group_pending.pop(uid, None)
            if record:
                record.get("timeout") and record["timeout"].cancel()
            device["group_sync"] = {"status": "offline", "desired": list(desired)}
            self.broadcast("device_update", device)
            return
        if observed == desired:
            record = self._group_pending.pop(uid, None)
            if record:
                record.get("timeout") and record["timeout"].cancel()
            device["group_sync"] = {"status": "current", "desired": list(desired),
                                    "source": source}
            self.broadcast("device_update", device)
        elif device.get("online"):
            # A stale receipt/report is useful evidence, but it must not reset
            # an already bounded attempt for the same latest desired state.
            # Let that attempt's existing retry schedule continue to timeout.
            record = self._group_pending.get(uid)
            if record is None or record.get("desired") != desired:
                self.send_groups(uid)

    def _device_for_reply(self, kind, ip, payload=None):
        if kind == "report" and isinstance(payload, dict) and payload.get("uid") in self.state.devices:
            uid = payload["uid"]
            try:
                self.pending[kind].remove(uid)
            except ValueError:
                pass
            self._finish_request(kind, uid)
            return self.state.devices[uid]
        matches = [device for device in self.state.devices.values() if device.get("ip") == ip]
        if len(matches) == 1:
            uid = matches[0]["uid"]
            try:
                self.pending[kind].remove(uid)
            except ValueError:
                pass
            self._finish_request(kind, uid)
            return matches[0]
        if self.pending[kind]:
            uid = self.pending[kind].popleft()
            self._finish_request(kind, uid)
            return self.state.devices.get(uid)
        return None

    def _finish_request(self, member, uid):
        timeout = self.pending_timeouts.pop((member, uid), None)
        if timeout:
            timeout.cancel()

    def _expire_request(self, member, uid):
        self.pending_timeouts.pop((member, uid), None)
        try:
            self.pending[member].remove(uid)
        except ValueError:
            pass
        if member == "assets":
            self._schedule_asset_requery(uid)

    def handle(self, address, args, ip):
        # Console tap (design note sec 3): everything observed on the LAN
        # receive side, heartbeats included. Always-on; filtering is
        # client-side. Same no-loop guard as the outgoing tap.
        try:
            self.broadcast("osc_in", {"ts": time.time(), "address": address,
                                      "args": self._console_args(args),
                                      "source": ip})
        except RuntimeError:
            pass
        if address == "/audition/ready":
            try:
                local = ipaddress.ip_address(ip).is_loopback
            except ValueError:
                local = False
            if not local:
                return
            # A relay restart can be faster than the normal offline threshold.
            # Its private ready frame requests the complete dashboard-owned
            # assignments and listener without weakening heartbeat rate limits.
            mode = str(args[1]) if len(args) > 1 else "simulate"
            if mode == "simulate":
                for seat in self.state.seats.values():
                    uid = seat.get("bound")
                    if uid and uid.startswith("audition-") and uid in self.state.devices:
                        self.assign(uid, seat["id"], seat["name"], seat["positions"])
                self.send_audition_listener()
            return
        if address == "/hb" and len(args) >= 4:
            uid = str(args[0])
            supervisor_mode = self.state.data.get("supervisor", {}).get("mode", "off")
            audition_uid = re.fullmatch(r"audition-\d{4}", uid) is not None
            try:
                local = ipaddress.ip_address(ip).is_loopback
            except ValueError:
                local = False
            # Managed audition identities exist only on the private loopback
            # relay and only while its supervisor owns that relay.  A delayed
            # heartbeat must not resurrect a phantom installation device.
            if audition_uid and (supervisor_mode == "off" or not local):
                return
            first_seen = uid not in self.state.devices
            device = self.state.ensure(uid)
            sim_active = supervisor_mode == "simulate"
            if sim_active and audition_uid:
                try:
                    index = int(uid.rsplit("-", 1)[1]) - 1
                    seats = sorted(self.state.seats.values(), key=lambda item: item["id"])
                    device["virtual"] = True
                    device["seat_id"] = seats[index]["id"] if 0 <= index < len(seats) else None
                except (ValueError, IndexError):
                    device["seat_id"] = None
            elif supervisor_mode == "edit" and audition_uid:
                device["virtual"] = True
                device["editor"] = True
                device["seat_id"] = None
            alias_created = False
            if not device.get("virtual"):
                try:
                    _alias, alias_created = self.state.ensure_device_alias(uid)
                except ValueError as error:
                    log.error("could not allocate device alias for %s: %s", uid, error)
                else:
                    if alias_created:
                        self.state.save_debounced()
            old = {key: device.get(key) for key in (
                "id", "ip", "version", "engine_alive", "rssi", "online",
                "revoking_assignment")}
            advertised_id = int(args[1])
            seat = self.state.seat_for_uid(uid)
            if device.get("virtual") and device.get("seat_id") is not None:
                seat = self.state.seats.get(str(device["seat_id"]))
            unassign_waiter = self._unassign_waiters.get(uid)
            revoking = unassign_waiter is not None
            now = time.monotonic()
            stale_unbound = (seat is None and not device.get("virtual")
                             and advertised_id != -1)
            pending_offline_revoke = (bool(device.get("revoking_assignment"))
                                      and unassign_waiter is None)
            if ((stale_unbound or pending_offline_revoke)
                    and advertised_id != -1 and unassign_waiter is None):
                last_unassign = self._unassign_replayed.get(uid, float("-inf"))
                if now - last_unassign >= ASSIGN_REPLAY_MIN_SECONDS:
                    self.uid_command(uid, "unassign")
                    self._unassign_replayed[uid] = now
                device["revoking_assignment"] = True
                revoking = True
            elif advertised_id == -1:
                device["revoking_assignment"] = False
                self._unassign_replayed.pop(uid, None)
            elif (seat is not None and unassign_waiter is None
                    and not pending_offline_revoke):
                # A timed-out transaction leaves durable binding authoritative.
                device["revoking_assignment"] = False
            configured = seat is not None and not revoking
            configured_id = int(seat["id"]) if configured else (-1 if revoking else advertised_id)
            mismatch = configured and advertised_id != configured_id
            last_replay = self._assign_replayed.get(uid, float("-inf"))
            allow_replay = not sim_active or device.get("virtual")
            reassign = configured and allow_replay and (not old["online"] or
                                       (mismatch and now - last_replay >=
                                        ASSIGN_REPLAY_MIN_SECONDS))
            if configured and not mismatch:
                self._assign_replayed.pop(uid, None)
            device.update(id=configured_id, version=str(args[2]), engine_alive=int(args[3]),
                          rssi=args[4] if len(args) > 4 else None, ip=ip, online=True,
                          last_seen=time.time())
            if (revoking and advertised_id == -1 and unassign_waiter is not None
                    and not unassign_waiter.done()):
                unassign_waiter.set_result(True)
            if reassign:
                # Dashboard durable assignment is authoritative. Replaying its
                # full state on appearance also restores ephemeral audition
                # nodes' ordered positions after the relay restarts. The ack
                # heartbeat advertises configured_id while already online, so
                # it cannot form a resend loop.
                self.assign(uid, configured_id, seat["name"], seat["positions"])
                self._assign_replayed[uid] = now
            if configured and not reassign and advertised_id == configured_id:
                desired_groups = tuple(seat.get("groups", []))
                pending_groups = self._group_pending.get(uid)
                sync = device.get("group_sync") or {}
                current = (sync.get("status") == "current"
                           and tuple(sync.get("desired", ())) == desired_groups)
                pending = (pending_groups is not None
                           and pending_groups.get("desired") == desired_groups)
                if not current and not pending:
                    if sync.get("status") == "awaiting_assignment":
                        device["group_sync"] = {
                            "status": "assignment_confirmed",
                            "desired": list(desired_groups)}
                    self.send_groups(uid)
            if not device.get("virtual"):
                # Heartbeat is a convergence edge. Old nodes safely ignore the
                # additive UID verb and remain publicly unconfirmed.
                self.set_device_mute(uid, self.state.device_muted_for(uid))
            self.broadcast("heartbeat", {"uid": uid, "timestamp": device["last_seen"]})
            new = {key: device.get(key) for key in old}
            if old != new:
                self.broadcast("device_update", device)
            if alias_created:
                # A device_update projects the resolved alias but cannot add
                # the new durable registry record to an already-open browser.
                # Converge that host-global identity state immediately so
                # Rename/Reset semantics do not depend on discovery preceding
                # the WebSocket connection.
                self.broadcast("state", self.state.public())
            if first_seen or not old["online"]:
                self.state.save_debounced()
                # Asset inventory is useful for assigned and unassigned
                # devices alike. A missing reply deliberately leaves None.
                self.request_assets(uid)
                if first_seen:
                    self.request(uid, "report")
                if device.get("editor"):
                    # The one edit instance is the mini-map's sole element.
                    # Its (0, 0) coordinate renders at the centre of that map.
                    self.assign(uid, 0, "Patch editor", ((0.0, 0.0),))
                    editor = self.state.data.get("editor", {})
                    self.send_editor_element(editor.get("point_element", 0))
                    for point in editor.get("points", {}).values():
                        self.send_editor_point(point)
                if configured or device.get("editor"):
                    self.request(uid, "params")
                    self.request(uid, "patches")
                    if first_seen and device.get("virtual"):
                        self.schedule_audition_param_replay(uid)
            return
        if address == "/os/groups" and args:
            uid = str(args[0])
            observed = self._wire_group_ids(list(args[1:]))
            if uid not in self.state.devices or observed is None:
                return
            self._finish_groups(uid, observed, "receipt")
            return
        if address == "/os/mute" and len(args) >= 3:
            uid = str(args[0])
            device = self.state.devices.get(uid)
            if device is None or device.get("virtual"):
                return
            try:
                observed = int(args[1])
                effective = int(args[2])
            except (TypeError, ValueError):
                return
            if (isinstance(args[1], bool) or isinstance(args[2], bool)
                    or observed not in (0, 1) or effective not in (0, 1)):
                return
            device["mute_observed"] = bool(observed)
            device["effective_muted"] = bool(effective)
            device["mute_pending_at"] = None
            self.broadcast("device_update", device)
            return
        if address == "/os/hostname" and len(args) >= 3:
            uid, hostname, status = str(args[0]), str(args[1]), str(args[2])
            device = self.state.devices.get(uid)
            if (device is None or device.get("virtual")
                    or status not in ("ok", "err")
                    or device.get("hostname_target") not in (None, hostname)):
                return
            device["hostname_target"] = hostname
            device["hostname_status"] = status
            if status == "ok":
                device["hostname"] = hostname
            self.broadcast("device_update", device)
            return
        if address == "/os/params":
            device = self._device_for_reply("params", ip)
            if not device:
                return
            device["active_asset_slots"] = None
            active_asset_slots = None
            if args:
                try:
                    manifest = json.loads(args[0])
                    declarations = manifest.get("params", [])
                except (ValueError, TypeError, AttributeError):
                    log.warning("bad params declaration from %s", ip)
                    return
                slots = manifest.get("slots", [])
                if isinstance(slots, list) and all(isinstance(slot, str) for slot in slots):
                    active_asset_slots = list(dict.fromkeys(
                        slot for slot in slots if slot))
                device["undeclared"] = False
            else:
                declarations = LEGACY_DECLARATIONS
                device["undeclared"] = True
            device["declared"] = declarations
            seat = self.state.seat_for_uid(device["uid"])
            editor = bool(device.get("editor"))
            if editor:
                device["params"] = dict(self.state.data.get("editor", {}).get("params", {}))
            elif seat is not None:
                device["params"] = dict(seat.get("params", {}))
            try:
                qualified = [(declaration, patch_manifest.qualify_param(declaration))
                             for declaration in declarations]
            except ValueError:
                log.warning("invalid qualified params declaration from %s", ip)
                return
            device["active_asset_slots"] = active_asset_slots
            for declaration, identity in qualified:
                if identity not in device["params"] and "default" in declaration:
                    device["params"][identity] = declaration["default"]
                    if seat is not None:
                        seat["params"][identity] = declaration["default"]
            # catch-up push: the dashboard's stored params are the mix of
            # record, so a (re)declaring device gets them back (this is how a
            # device offline during a preset load converges on reconnect);
            # master rides along per the contract sec 4.1 catch-up rule
            if editor:
                for _declaration, identity in qualified:
                    if identity in device["params"]:
                        self.set_param(int(device.get("id", 0)), identity,
                                       device["params"][identity])
                self.send_master(int(device.get("id", 0)))
            elif seat is not None:
                for _declaration, identity in qualified:
                    if identity in device["params"]:
                        self.set_param(int(seat["id"]), identity,
                                       device["params"][identity])
                self.send_master(int(seat["id"]))
                if self.state.data.get("points"):
                    self.send_points_frame()
            self.broadcast("params_declaration", device)
            return
        if address == "/os/report" and args:
            try:
                report = json.loads(args[0])
            except (ValueError, TypeError):
                return
            device = self._device_for_reply("report", ip, report)
            if device:
                device["report"] = report
                if isinstance(report.get("hostname"), str):
                    device["hostname"] = report["hostname"]
                if isinstance(report.get("device_muted"), bool):
                    device["mute_observed"] = report["device_muted"]
                if isinstance(report.get("muted"), bool):
                    device["effective_muted"] = report["muted"]
                if (isinstance(report.get("device_muted"), bool)
                        and isinstance(report.get("muted"), bool)):
                    device["mute_pending_at"] = None
                reconcile_patch_switch_observation(device)
                observed_groups = self._wire_group_ids(report.get("groups"))
                if observed_groups is None:
                    seat = self.state.seat_for_uid(device["uid"])
                    if seat is not None and device.get("online"):
                        self.send_groups(device["uid"])
                else:
                    self._finish_groups(device["uid"], observed_groups, "report")
                if not device.get("virtual"):
                    self.set_device_mute(
                        device["uid"], self.state.device_muted_for(device["uid"]))
                self.broadcast("report", device)
            return
        if address == "/os/patches" and args:
            device = self._device_for_reply("patches", ip)
            if not device:
                return
            try:
                listing = json.loads(args[0])
            except (ValueError, TypeError):
                return
            if not isinstance(listing, list):
                return
            cleaned = []
            for patch in listing:
                if not isinstance(patch, dict) or not isinstance(patch.get("name"), str):
                    continue
                entry = {"name": patch["name"],
                         "active": bool(patch.get("active")),
                         "git": bool(patch.get("git")),
                         "manifest": bool(patch.get("manifest"))}
                # v1.4 additive content identity; absent (old node) stays absent
                fingerprint = patch.get("fingerprint")
                if isinstance(fingerprint, str) and re.fullmatch(r"[0-9a-f]{64}", fingerprint):
                    entry["fingerprint"] = fingerprint
                cleaned.append(entry)
            device["patches"] = cleaned
            reconcile_patch_switch_observation(device)
            self.broadcast("patches", device)
            return
        if address == "/os/assets":
            device = self._device_for_reply("assets", ip)
            if not device:
                return
            uid = device["uid"]
            try:
                listing = json.loads(args[0]) if args else None
            except (ValueError, TypeError):
                listing = None
            if not isinstance(listing, list):
                device["assets"] = None
                device["assets_observed_at"] = None
                device["assets_quarantine"] = [{"reason": "malformed top-level inventory"}]
                self._cancel_asset_requery(uid)
                log.warning("bad asset inventory from %s: expected JSON list", ip)
                self.broadcast("assets", device)
                return
            cleaned, quarantine = [], []
            for index, asset in enumerate(listing):
                name = asset.get("name") if isinstance(asset, dict) else None
                if (not isinstance(name, str) or not name or name.startswith(".")
                        or "/" in name or "\\" in name or "\x00" in name):
                    quarantine.append({"index": index, "reason": "missing or unsafe name"})
                    log.warning("quarantined unnamed asset inventory entry %d from %s",
                                index, ip)
                    continue
                fingerprint = asset.get("fingerprint")
                fingerprint_ok = (fingerprint is None or
                                  (isinstance(fingerprint, str) and
                                   re.fullmatch(r"[0-9a-f]{64}", fingerprint)))
                files, size = asset.get("files"), asset.get("bytes")
                counts_ok = (isinstance(files, int) and not isinstance(files, bool)
                             and files >= 0 and isinstance(size, int)
                             and not isinstance(size, bool) and size >= 0)
                if not fingerprint_ok or not counts_ok:
                    cleaned.append({"name": name, "fingerprint": None,
                                    "files": None, "bytes": None, "unknown": True})
                    quarantine.append({"index": index, "name": name,
                                       "reason": "malformed inventory facts"})
                    log.warning("quarantined malformed asset inventory entry %r from %s",
                                name, ip)
                    continue
                cleaned.append({"name": name, "fingerprint": fingerprint,
                                "files": files, "bytes": size})
            device["assets"] = cleaned
            device["assets_observed_at"] = time.time()
            device["assets_quarantine"] = quarantine
            self.broadcast("assets", device)
            self._schedule_asset_requery(uid)
            return
        if address == "/os/fetch-progress" and len(args) >= 2:
            slot, phase = str(args[0]), str(args[1])
            record = self._fetch_record(slot, ip, phase)
            if record and phase in ("queued", "fetching"):
                record["phase"] = phase
                device = self.state.devices.get(record["uid"])
                if device:
                    device.setdefault("fetch", {})[slot] = phase
                    self.broadcast("device_update", device)
            return
        if address == "/os/fetched" and len(args) >= 2:
            slot, status = str(args[0]), str(args[1])
            record = self._fetch_record(slot, ip, "terminal")
            if not record:
                return
            pending = self.fetch_pending.get(slot)
            try:
                pending.remove(record)
            except (AttributeError, ValueError):
                pass
            if not pending:
                self.fetch_pending.pop(slot, None)
            record.get("timeout") and record["timeout"].cancel()
            device = self.state.devices.get(record["uid"])
            if device:
                device.setdefault("fetch", {})[slot] = "ok" if status == "ok" else "err"
                if status == "ok":
                    device.setdefault("distribution", {})[slot] = record["fingerprint"]
                    self.state.save_debounced()
                self.broadcast("device_update", device)
                if status == "ok" and slot.startswith("patch:"):
                    self.request(record["uid"], "patches")
                elif not slot.startswith("patch:"):
                    self.request_assets(record["uid"])
            return
        if address == "/os/rev" and len(args) >= 2:
            device = None
            if len(args) >= 3 and str(args[2]) in self.state.devices:
                device = self.state.devices[str(args[2])]  # proposed uid extension
            else:
                matches = [item for item in self.state.devices.values() if item.get("ip") == ip]
                device = matches[0] if len(matches) == 1 else None
            if not device:
                log.warning("unattributable /os/rev from %s: %r", ip, args)
                return
            receipt = {"sha": str(args[0]), "model": str(args[1]), "at": time.time()}
            if len(args) >= 4:
                receipt["status"] = str(args[3])
                receipt["phase"] = str(args[4]) if len(args) >= 5 else "unknown"
            device["rev"] = receipt
            attempt = device.get("patch_switch")
            if isinstance(attempt, dict) and receipt.get("status", "ok") == "ok":
                attempt["status"] = "reconciling"
                attempt["receipt_at"] = time.time()
            self.broadcast("rev", device)
            if receipt.get("status") == "err":
                return
            for member in ("patches", "params", "report"):
                self.request(device["uid"], member)
            self.request_assets(device["uid"])
            return
        if address == "/sync/pong" and len(args) >= 4:
            self.handle_pong(args)
            return
        if address in ("/os/pong", "/os/load"):
            log.debug("ignored %s %r", address, args)

    def _fetch_record(self, slot, ip, phase):
        records = self.fetch_pending.get(slot, ())
        if not records:
            return None
        matches = [record for record in records
                   if self.state.devices.get(record["uid"], {}).get("ip") == ip]
        candidates = matches or list(records)
        expected = ({"queued": "sent", "fetching": "queued"}.get(phase))
        if expected:
            return next((record for record in candidates
                         if record["phase"] == expected), candidates[0])
        return next((record for record in candidates
                     if record["phase"] in ("fetching", "queued", "sent")), candidates[0])

    def _expire_fetch(self, slot, record):
        pending = self.fetch_pending.get(slot)
        if not pending or record not in pending:
            return
        # Keep an expired tombstone ahead of any retry: v1.3 has no request id,
        # so allowing a new generation could make a late old receipt certify
        # newer bytes falsely. A late terminal still consumes this record.
        record["phase"] = "expired"
        device = self.state.devices.get(record["uid"])
        if device:
            device.setdefault("fetch", {})[slot] = "timeout"
            self.broadcast("device_update", device)

    @staticmethod
    def _sync_estimate(window):
        # favour the low-RTT samples (least queuing delay, so least asymmetric
        # one-way error -- NTP intuition), then median for robustness to WiFi
        # jitter. Falls back to the whole window if the low-RTT band is empty.
        offsets, rtts = list(window["offsets"]), list(window["rtts"])
        floor = min(rtts) * SYNC_LOWRTT_BAND
        best = [offset for offset, rtt in zip(offsets, rtts) if rtt <= floor]
        return int(statistics.median(best or offsets))

    def handle_pong(self, args):
        # /sync/pong <seq> <leaderTimeNs> <uid> <deviceTimeNs>: the leader
        # timestamps arrival, recovers its send time from the echoed leaderTime,
        # and estimates offset = (deviceTime + oneWay) - leaderNow.
        leader_now = time.monotonic_ns()
        try:
            send_time, uid, device_time = int(args[1]), str(args[2]), int(args[3])
        except (TypeError, ValueError):
            return
        device = self.state.devices.get(uid)
        seat = self.state.seat_for_uid(uid)
        if device is None or seat is None:
            return  # only assigned devices are synced and pushed
        rtt = leader_now - send_time
        if rtt < 0 or rtt > SYNC_RTT_CEILING_NS:
            return  # bogus clock, or a pong too delayed to be usable
        one_way = rtt // 2
        offset = (device_time + one_way) - leader_now
        window = self._sync.setdefault(uid, {"offsets": deque(maxlen=SYNC_WINDOW),
                                             "rtts": deque(maxlen=SYNC_WINDOW)})
        window["offsets"].append(offset)
        window["rtts"].append(rtt)
        estimate = self._sync_estimate(window)
        device["sync"] = {"offset": estimate, "rtt": rtt, "min_rtt": min(window["rtts"]),
                          "samples": len(window["offsets"]), "at": time.time()}
        if len(window["offsets"]) >= SYNC_MIN_SAMPLES:
            self.send(f"/{int(seat['id'])}/sync/offset", [str(estimate)])
        now = time.time()
        if now - self._sync_sent.get(uid, 0) >= 0.2:
            self._sync_sent[uid] = now
            self.broadcast("sync", {"uid": uid, **device["sync"]})
