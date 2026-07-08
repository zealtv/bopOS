import asyncio
import json
import logging
import re
import socket
import time
from collections import deque

from pythonosc.osc_message import OscMessage
from pythonosc.osc_message_builder import OscMessageBuilder


# Wire-compat matrix, in one place. Params are idempotent full-state, so the
# legacy spelling is double-sent while LEGACY_COMPAT is on. Admin verbs are
# NOT idempotent (update runs a pull, reboot reboots): they go out only as
# /<sel>/os/<verb>, answered by helper.py's 6660 listener -- nodes that
# predate the contract keep working from old dashboards via the PD-routed
# 7770 aliases (contract sec 13), but this dashboard needs contract nodes.
LEGACY_COMPAT = True
LEGACY_PARAMS = {"gain", "gain2", "backing", "echo"}
LEGACY_DECLARATIONS = [
    {"name": "gain", "type": "f", "min": 0, "max": 1, "default": 0.75, "group": "mix"},
    {"name": "gain2", "type": "f", "min": 0, "max": 1, "default": 0.3, "group": "mix"},
    {"name": "backing", "type": "f", "min": 0, "max": 1, "default": 0.8, "group": "mix"},
    {"name": "echo", "type": "i", "min": 0, "max": 1, "default": 0, "group": "fx"},
]
log = logging.getLogger("bopos.osc")


def volume_param(device):
    """The declared param a volume card drives: role 'volume', else literal
    'gain', else None (contract sec 8 / facilitator proposal Q1)."""
    declared = device.get("declared") or []
    for declaration in declared:
        if declaration.get("role") == "volume":
            return declaration.get("name")
    if any(declaration.get("name") == "gain" and declaration.get("role") != "meter"
           for declaration in declared):
        return "gain"
    return None


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
        self.pending = {"params": deque(), "report": deque()}
        self._meter_sent = {}

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

    def close(self):
        if self.transport:
            self.transport.close()
        if self.sender:
            self.sender.close()

    def send(self, address, args=()):
        builder = OscMessageBuilder(address=address)
        for value in args:
            if isinstance(value, float):
                value = float(format(value, ".6g"))
            builder.add_arg(value)
        self.sender.sendto(builder.build().dgram, self.destination)

    def set_param(self, selector, name, value):
        self.send(f"/{selector}/p/{name}", [value])
        if LEGACY_COMPAT and name in LEGACY_PARAMS:
            self.send(f"/{selector}/{name}", [value])

    def send_device_param(self, device, name, value):
        # VCA-style master (facilitator proposal Q2): the stored value is the
        # mix; the wire gets mix x master for the device's volume param.
        # Broadcast /all sends bypass this — they're a tech power tool.
        if name == volume_param(device):
            try:
                value = float(value) * float(self.state.data.get("master", 1.0))
            except (TypeError, ValueError):
                pass
        self.set_param(int(device["id"]), name, value)

    def resend_volumes(self):
        # master moved: re-send every assigned device's volume at the new scale
        for device in self.state.devices.values():
            if int(device["id"]) < 0:
                continue
            name = volume_param(device)
            if name and name in device["params"]:
                self.send_device_param(device, name, device["params"][name])

    def action(self, selector, verb):
        wire_verb = "getsamples" if verb == "get_samples" else verb
        if wire_verb == "aloha":
            self.send(f"/{selector}/aloha", [1])
        else:
            self.send(f"/{selector}/os/{wire_verb}")

    def request(self, uid, member):
        device = self.state.devices.get(uid)
        if not device:
            return
        self.pending[member].append(uid)
        self.send(f"/{int(device['id'])}/os/{member}")

    def os_command(self, selector, member, args=()):
        self.send(f"/{selector}/os/{member}", args)

    def assign(self, uid, device_id, name, pos1=None, pos2=None):
        # idempotent full-state; only the node whose uid matches applies it,
        # and it persists the lot for standalone operation (contract sec 5)
        args = [str(uid), int(device_id), str(name)]
        if pos1 is not None:
            args += [float(pos1[0]), float(pos1[1])]
            if pos2 is not None:
                args += [float(pos2[0]), float(pos2[1])]
        self.send("/all/os/assign", args)

    def _device_for_reply(self, kind, ip, payload=None):
        if kind == "report" and isinstance(payload, dict) and payload.get("uid") in self.state.devices:
            uid = payload["uid"]
            try:
                self.pending[kind].remove(uid)
            except ValueError:
                pass
            return self.state.devices[uid]
        if self.pending[kind]:
            return self.state.devices.get(self.pending[kind].popleft())
        matches = [device for device in self.state.devices.values() if device.get("ip") == ip]
        return matches[0] if len(matches) == 1 else None

    def handle(self, address, args, ip):
        if address == "/hb" and len(args) >= 4:
            uid = str(args[0])
            first_seen = uid not in self.state.devices
            device = self.state.ensure(uid)
            old = {key: device.get(key) for key in ("id", "ip", "version", "engine_alive", "rssi", "online")}
            device.update(id=int(args[1]), version=str(args[2]), engine_alive=int(args[3]),
                          rssi=args[4] if len(args) > 4 else None, ip=ip, online=True,
                          last_seen=time.time())
            self.broadcast("heartbeat", {"uid": uid, "timestamp": device["last_seen"]})
            new = {key: device.get(key) for key in old}
            if old != new:
                self.broadcast("device_update", device)
            if first_seen or not old["online"]:
                self.state.save_debounced()
                if device["id"] >= 0:
                    self.request(uid, "params")
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
            for declaration in declarations:
                name = declaration.get("name")
                if (name and name not in device["params"] and "default" in declaration
                        and declaration.get("role") != "meter"):
                    device["params"][name] = declaration["default"]
            # catch-up push: the dashboard's stored params are the mix of
            # record, so a (re)declaring device gets them back (this is how a
            # device offline during a preset load converges on reconnect)
            if int(device["id"]) >= 0:
                for declaration in declarations:
                    name = declaration.get("name")
                    if name and name in device["params"] and declaration.get("role") != "meter":
                        self.send_device_param(device, name, device["params"][name])
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
                self.broadcast("report", device)
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
            return
        parts = [part for part in address.split("/") if part]
        if len(parts) == 3 and parts[1] == "p" and args:
            self.handle_meter(parts[0], parts[2], args[0])
            return
        if address in ("/os/pong", "/os/load") or address == "/rpt":
            log.debug("ignored %s %r", address, args)

    def handle_meter(self, selector, name, value):
        # inbound /<id>/p/<name>: a live value republished by the patch or
        # helper (contract sec 11). Declared role:"meter" renders as a meter;
        # an undeclared name gets the sec 8 badge; a declared *control* name
        # inbound is not the meter surface and is ignored.
        try:
            device_id = int(selector)
        except ValueError:
            return
        if device_id < 0 or re.fullmatch(r"[A-Za-z0-9_-]+", name) is None:
            return
        matches = [item for item in self.state.devices.values()
                   if int(item["id"]) == device_id]
        if len(matches) != 1:
            return
        device = matches[0]
        declaration = next((item for item in (device.get("declared") or [])
                            if item.get("name") == name), None)
        declared_meter = declaration is not None and declaration.get("role") == "meter"
        if declaration is not None and not declared_meter:
            return
        meters = device.setdefault("meters", {})
        if name not in meters and len(meters) >= 32:
            return  # cap junk from a misbehaving sender
        if not isinstance(value, (int, float)):
            value = str(value)
        now = time.time()
        meters[name] = {"value": value, "at": now, "declared": declared_meter}
        key = (device["uid"], name)
        if now - self._meter_sent.get(key, 0) >= 0.2:
            self._meter_sent[key] = now
            self.broadcast("meter", {"uid": device["uid"], "name": name,
                                     "value": value, "at": now,
                                     "declared": declared_meter})
