import asyncio
import ipaddress
import json
import logging
import math
import random
import re
import socket
import statistics
import time
from collections import deque

from pythonosc.osc_message import OscMessage
from pythonosc.osc_message_builder import OscMessageBuilder

import points


LEGACY_DECLARATIONS = [
    {"name": "gain", "type": "f", "min": 0, "max": 1, "default": 0.75, "group": "mix"},
    {"name": "gain2", "type": "f", "min": 0, "max": 1, "default": 0.3, "group": "mix"},
    {"name": "backing", "type": "f", "min": 0, "max": 1, "default": 0.8, "group": "mix"},
    {"name": "echo", "type": "i", "min": 0, "max": 1, "default": 0, "group": "fx"},
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
        self.pending = {"params": deque(), "report": deque(), "patches": deque()}
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

    def send(self, address, args=()):
        self.sender.sendto(self._datagram(address, args), self.destination)

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
        room = self.state.data.get("room") or {}
        if not listener or self.sender is None:
            return
        range_m = math.hypot(float(room.get("width", 0)),
                             float(room.get("depth", 0)))
        if not math.isfinite(range_m) or range_m <= 0:
            return
        packet = self._datagram("/audition/listener", [
            float(listener["x"]), float(listener["y"]),
            float(listener["heading"]), range_m,
        ])
        self.sender.sendto(packet, ("127.0.0.1", self.destination[1]))

    def set_param(self, selector, name, value):
        self.send(f"/{selector}/p/{name}", [value])

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

    def request(self, uid, member):
        device = self.state.devices.get(uid)
        if not device:
            return
        if uid in self.pending[member]:
            return
        self.pending[member].append(uid)
        self.pending_timeouts[(member, uid)] = asyncio.get_running_loop().call_later(
            REQUEST_TIMEOUT_SECONDS, self._expire_request, member, uid)
        self.send(f"/{int(device['id'])}/os/{member}")

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

    def handle(self, address, args, ip):
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
            for seat in self.state.seats.values():
                uid = seat.get("bound")
                if uid and uid.startswith("audition-") and uid in self.state.devices:
                    self.assign(uid, seat["id"], seat["name"], seat["positions"])
            self.send_audition_listener()
            return
        if address == "/hb" and len(args) >= 4:
            uid = str(args[0])
            first_seen = uid not in self.state.devices
            device = self.state.ensure(uid)
            old = {key: device.get(key) for key in ("id", "ip", "version", "engine_alive", "rssi", "online")}
            advertised_id = int(args[1])
            seat = self.state.seat_for_uid(uid)
            configured = seat is not None
            configured_id = int(seat["id"]) if configured else advertised_id
            mismatch = configured and advertised_id != configured_id
            now = time.monotonic()
            last_replay = self._assign_replayed.get(uid, float("-inf"))
            reassign = configured and (not old["online"] or
                                       (mismatch and now - last_replay >=
                                        ASSIGN_REPLAY_MIN_SECONDS))
            if configured and not mismatch:
                self._assign_replayed.pop(uid, None)
            device.update(id=configured_id, version=str(args[2]), engine_alive=int(args[3]),
                          rssi=args[4] if len(args) > 4 else None, ip=ip, online=True,
                          last_seen=time.time())
            if reassign:
                # Dashboard durable assignment is authoritative. Replaying its
                # full state on appearance also restores ephemeral audition
                # nodes' ordered positions after the relay restarts. The ack
                # heartbeat advertises configured_id while already online, so
                # it cannot form a resend loop.
                self.assign(uid, configured_id, seat["name"], seat["positions"])
                self._assign_replayed[uid] = now
            self.broadcast("heartbeat", {"uid": uid, "timestamp": device["last_seen"]})
            new = {key: device.get(key) for key in old}
            if old != new:
                self.broadcast("device_update", device)
            if first_seen or not old["online"]:
                self.state.save_debounced()
                if configured:
                    self.request(uid, "params")
                    self.request(uid, "patches")
            return
        if address == "/os/params":
            device = self._device_for_reply("params", ip)
            if not device:
                return
            if args:
                try:
                    manifest = json.loads(args[0])
                    declarations = manifest.get("params", [])
                except (ValueError, TypeError, AttributeError):
                    log.warning("bad params declaration from %s", ip)
                    return
                device["undeclared"] = False
            else:
                declarations = LEGACY_DECLARATIONS
                device["undeclared"] = True
            device["declared"] = declarations
            seat = self.state.seat_for_uid(device["uid"])
            if seat is not None:
                device["params"] = dict(seat.get("params", {}))
            for declaration in declarations:
                name = declaration.get("name")
                if name and name not in device["params"] and "default" in declaration:
                    device["params"][name] = declaration["default"]
                    if seat is not None:
                        seat["params"][name] = declaration["default"]
            # catch-up push: the dashboard's stored params are the mix of
            # record, so a (re)declaring device gets them back (this is how a
            # device offline during a preset load converges on reconnect);
            # master rides along per the contract sec 4.1 catch-up rule
            if seat is not None:
                for declaration in declarations:
                    name = declaration.get("name")
                    if name and name in device["params"]:
                        self.set_param(int(seat["id"]), name, device["params"][name])
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
                cleaned.append({"name": patch["name"],
                                "active": bool(patch.get("active")),
                                "git": bool(patch.get("git")),
                                "manifest": bool(patch.get("manifest"))})
            device["patches"] = cleaned
            self.broadcast("patches", device)
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
            device["rev"] = {"sha": str(args[0]), "model": str(args[1]), "at": time.time()}
            self.broadcast("rev", device)
            self.request(device["uid"], "patches")
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
