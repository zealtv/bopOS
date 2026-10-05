"""Dashboard WebSocket verbs and their dispatch policies.

Handlers keep their original validation and effects. Policy declarations live
beside each handler so adding a verb cannot silently miss a parallel guard set.
"""
import re
import time
import urllib.parse
from dataclasses import dataclass

import device_aliases
import live_params
import points
import show_model
from state import FACILITATOR_COMMANDS
from python import identity, io_protocol, performance_mode, wifi_config
from python import manifest as patch_manifest
from python.paramgen import ParamGrammarError, parse_message


PATCH_NAME_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*")


@dataclass(frozen=True)
class WSPolicy:
    method: str
    # Dispatch locks cover mutations; handler locks preserve transition broadcasts.
    supervisor: str = ""
    manifest: bool = False
    edit_blocked: bool = False
    editor_allowed: bool = False
    live_only: bool = False
    performance: object = False


WS_HANDLERS = {}


def ws_handler(*kinds, **policy):
    def register(method):
        for kind in kinds:
            if kind in WS_HANDLERS:
                raise ValueError(f"Duplicate WebSocket handler: {kind}")
            WS_HANDLERS[kind] = WSPolicy(method.__name__, **policy)
        return method
    return register


def patch_distribution(data):
    return data.get("kind") == "patch"


def starting_editor(data):
    return bool(data.get("active", False))


def patch_action(data):
    return data.get("verb") in {"patch", "droppatch"}


class WSHandlers:
    def ws_mode_error(self, policy, data):
        editor_scoped = data.get("scope") == "editor"
        if policy and policy.live_only and self.supervisor_mode != "off":
            mode = "Patch Edit" if self.supervisor_mode == "edit" else "Simulation"
            return f"That execution control is unavailable during {mode}."
        if (policy and policy.edit_blocked and self.supervisor_mode == "edit"
                and not (policy.editor_allowed and editor_scoped)):
            return "That execution control is unavailable during Patch Edit."
        if editor_scoped and self.supervisor_mode != "edit":
            return "The patch editor is not running."
        return None

    def ws_performance_locked(self, policy, data):
        locked = policy.performance(data) if callable(policy.performance) else policy.performance
        return locked and getattr(self.state, "performance", False)

    @ws_handler("capture_selection")
    async def _ws_capture_selection(self, kind, data, ws):
        if ws in self.monitor_transport.clients:
            ws.replace(data)

    @ws_handler('set_editor_input',
                supervisor="dispatch")
    async def _ws_set_editor_input(self, kind, data, ws):
        try:
            await self.editor_input.choose(data.get("source"), ws)
        except (ValueError, OSError) as error:
            await self.ws_error(ws, str(error))
        await self.broadcast("state")

    @ws_handler('set_editor_input_value',
                supervisor="dispatch")
    async def _ws_set_editor_input_value(self, kind, data, ws):
        try:
            self.editor_input.set_value(data, ws)
        except ValueError as error:
            await self.ws_error(ws, str(error))

    @ws_handler('set_performance',
                supervisor="dispatch", manifest=True)
    async def _ws_set_performance(self, kind, data, ws):
        active = data.get("active")
        if not isinstance(active, bool):
            return
        try:
            performance_mode.save(self.state.performance_path, active)
        except OSError:
            await self.ws_error(ws, "Performance")
            return
        self.state.performance = active
        if active:
            self.supersede_fleet_operation()
            self.wifi_confirmations.clear()
            if self.supervisor_mode == "edit":
                await self.stop_supervisor()
        self.osc.set_performance(active)
        await self.broadcast("state")

    @ws_handler('monitor_probe',
                supervisor="dispatch", performance=True)
    async def _ws_monitor_probe(self, kind, data, ws):
        uid = data.get("uid")
        ok, error = self.osc.probe(uid, data.get("name"))
        if ws is not None:
            await ws.send_json({
                "type": "monitor_probe_status",
                "data": {"ok": ok, "error": error},
            })

    @ws_handler('monitor_send',
                supervisor="dispatch", performance=True)
    async def _ws_monitor_send(self, kind, data, ws):
        address, args, error = self.clean_monitor_message(data)
        if error:
            if ws is not None:
                await ws.send_json({
                    "type": "monitor_send_result",
                    "data": {"ok": False, "error": error},
                })
            return
        self.osc.send(address, args)
        if ws is not None:
            await ws.send_json({
                "type": "monitor_send_result",
                "data": {"ok": True},
            })

    @ws_handler('set_live_param',
                supervisor="dispatch", edit_blocked=True)
    async def _ws_set_live_param(self, kind, data, ws):
        uid = data.get("uid")
        scope = str(data.get("scope", ""))
        declaration = self.live_param_declaration(
            data.get("name"), self.live_scope_patch(scope, data.get("id")))
        cleaned = self.clean_editor_value(declaration, data.get("value"))
        seats, selector = self.live_param_target(scope, data.get("id"))
        if declaration is None or cleaned is None or seats is None:
            await self.ws_error(ws, "That live parameter or target is unavailable.")
            return
        cleaned = live_params.canonicalize_value(declaration, cleaned)
        param_identity = declaration["identity"]
        previous = {str(seat["id"]): dict(seat.get("params", {})) for seat in seats}
        previous_devices = {uid: dict(device.get("params", {}))
                            for uid, device in self.state.devices.items()}
        for seat in seats:
            seat.setdefault("params", {})[param_identity] = cleaned
            device = self.state.devices.get(seat.get("bound"))
            if device is not None:
                device.setdefault("params", {})[param_identity] = cleaned
            for virtual in self.state.devices.values():
                if (virtual.get("virtual")
                        and str(virtual.get("seat_id")) == str(seat["id"])):
                    virtual.setdefault("params", {})[param_identity] = cleaned
        try:
            self.state.save()
        except (OSError, TypeError, ValueError):
            for seat in seats:
                seat["params"] = previous[str(seat["id"])]
            for uid, params in previous_devices.items():
                if uid in self.state.devices:
                    self.state.devices[uid]["params"] = params
            await self.ws_error(ws, "Could not save the live parameter; no command was sent.")
            return
        self.osc.set_param(selector, param_identity, cleaned)
        await self.broadcast("state")

    @ws_handler('set_live_automation',
                supervisor="dispatch", edit_blocked=True, editor_allowed=True)
    async def _ws_set_live_automation(self, kind, data, ws):
        # The live counterpart of set_live_param: the control surface's
        # generator drawer (37/08) authors a §3.2 argument list rather than
        # a scalar. Targeting is identical -- same scopes, same selector --
        # and osc.set_param already knows how to record a generator and
        # clear one on `stop`, so this is a validation boundary, not a new
        # mechanism. Deliberately no seat["params"] write: a generator's
        # durable value is whatever the node last emitted, and set_param
        # owns the fade-destination case.
        scope = str(data.get("scope", ""))
        declaration = self.live_param_declaration(
            data.get("name"), self.live_scope_patch(scope, data.get("id")))
        seats, selector = self.live_param_target(scope, data.get("id"))
        raw = data.get("args")
        args = None
        if isinstance(raw, list) and raw:
            cleaned_args = [show_model.clean_arg(item) for item in raw]
            if all(item is not None for item in cleaned_args):
                args = [item["value"] for item in cleaned_args]
        declared_type = patch_manifest.param_wire_type(declaration)
        if (declaration is None or seats is None or args is None
                or declared_type not in {"f", "i"}):
            await self.ws_error(
                ws, "That live generator or target is unavailable.")
            return
        try:
            parse_message(args, declared_type)
        except ParamGrammarError as error:
            await self.ws_error(ws, f"That generator is not valid: {error}")
            return
        args = live_params.canonicalize_args(declaration, args)
        if args == ["stop"]:
            try:
                self.store_stopped_automation(seats, declaration)
            except (OSError, TypeError, ValueError):
                await self.ws_error(
                    ws, "Could not save the stopped parameter; no command was sent.")
                return
        self.osc.set_param_for(
            seats, selector, declaration["identity"], args)
        await self.broadcast("state")

    @ws_handler('replay_live_params',
                supervisor="dispatch", edit_blocked=True)
    async def _ws_replay_live_params(self, kind, data, ws):
        scope = str(data.get("scope", ""))
        if scope == "all":
            seats = sorted(self.state.seats.values(), key=lambda item: item["id"])
        elif scope == "seat":
            seat_id = self.state.clean_seat_id(data.get("id"))
            seat = self.state.seats.get(str(seat_id))
            seats = [seat] if seat is not None else None
        else:
            seats = None
        if seats is None or not self.live_control_declarations():
            await self.ws_error(ws, "That live replay target is unavailable.")
            return
        # Replay is deliberately numeric even for All: this is an ordered
        # refresh of each Seat snapshot, not a fleet-wide value overwrite.
        for seat in seats:
            self.replay_live_params_for_seat(seat)

    @ws_handler('set_device_enabled',
                supervisor="dispatch")
    async def _ws_set_device_enabled(self, kind, data, ws):
        enabled_uid = str(data.get("uid", ""))
        raw_value = data.get("value")
        device = self.state.devices.get(enabled_uid)
        if (raw_value not in (0, 1) or isinstance(raw_value, bool)
                or device is None or device.get("virtual")
                or enabled_uid not in self.state.device_registry):
            await self.ws_error(
                ws, "That physical Device enabled target is unavailable.")
            return
        desired = bool(raw_value)
        if not self.state.set_device_enabled(enabled_uid, desired):
            await self.ws_error(
                ws, "Could not save Device enabled; no command was sent.")
            return
        device["enabled_pending_at"] = time.time()
        self.osc.set_device_enabled(enabled_uid, desired)
        await self.broadcast("device_update", device)

    @ws_handler('set_device_hostname',
                supervisor="dispatch")
    async def _ws_set_device_hostname(self, kind, data, ws):
        hostname_uid = str(data.get("uid", ""))
        device = self.state.devices.get(hostname_uid)
        alias = self.state.alias_for(hostname_uid)
        hostname = device_aliases.hostname_for_alias(alias)
        if (device is None or device.get("virtual") or not device.get("online")
                or hostname is None):
            await self.ws_error(ws, "That physical device hostname target is unavailable.")
            return
        device["hostname_target"] = hostname
        device["hostname_status"] = "pending"
        self.osc.set_device_hostname(hostname_uid, hostname)
        await self.broadcast("device_update", device)

    @ws_handler('io_reinit', 'io_scan',
                supervisor="dispatch")
    @ws_handler("io_write", supervisor="dispatch", performance=True)
    async def _ws_io_control(self, kind, data, ws):
        uid = data.get("uid")
        device = self.state.devices.get(str(uid))
        if device is None or device.get('virtual') or not device.get('online'):
            await self.ws_error(ws, 'invalid-arguments')
            return
        if kind == 'io_scan':
            device['io_scan_pending'] = True
            device['io_scan'] = {'status': 'pending', 'at': time.time()}
            self.osc.io_scan(str(uid))
        elif kind == 'io_reinit':
            name = data.get('name')
            if not io_protocol.valid_name(name):
                await self.ws_error(ws, 'invalid-arguments')
                return
            if device.get('io_reinit', {}).get(name, {}).get('status') == 'pending':
                return
            device.setdefault('io_reinit', {})[name] = dict(status='pending', error=None)
            self.osc.io_reinit(str(uid), name)
        else:
            try:
                payload = io_protocol.validate_write(data.get('config'))
            except ValueError:
                await self.ws_error(ws, 'invalid-arguments')
                return
            device['io_write'] = dict(name=payload['name'], command=payload['command'],
                                      status='pending', error=None)
            self.osc.io_write(str(uid), payload)
        # Pending administrative state is an ordered control transition,
        # rather than a replaceable heartbeat/RSSI projection.
        await self.broadcast('device_update', device, priority=True)

    @ws_handler('set_audio_config',
                supervisor="dispatch")
    async def _ws_set_audio_config(self, kind, data, ws):
        audio_uid = str(data.get("uid", ""))
        device = self.state.devices.get(audio_uid)
        config = data.get("config")
        if (device is None or device.get("virtual") or not device.get("online")
                or not isinstance(config, dict)):
            await self.ws_error(
                ws, "That physical Device audio target is unavailable.")
            return
        current_audio = (device.get("report") or {}).get("audio")
        if isinstance(current_audio, dict):
            current_audio["status"] = "applying"
            current_audio["error"] = None
        device["audio_apply"] = {
            "status": "pending",
            "phase": "applying",
            "at": time.time(),
        }
        self.osc.set_audio_config(audio_uid, config)
        await self.broadcast("device_update", device)

    @ws_handler('set_log_config',
                supervisor="dispatch")
    async def _ws_set_log_config(self, kind, data, ws):
        log_uid = str(data.get("uid", ""))
        device = self.state.devices.get(log_uid)
        destination = data.get("destination")
        if (device is None or device.get("virtual") or not device.get("online")
                or destination not in ("internal", "usb")):
            await self.ws_error(
                ws, "That physical Device log target is unavailable.")
            return
        device["log_apply"] = {
            "status": "pending", "phase": "applying", "at": time.time(),
        }
        self.osc.set_log_config(log_uid, destination)
        await self.broadcast("device_update", device)

    @ws_handler('send_wifi_networks', 'set_wifi_networks',
                supervisor="dispatch", performance=True)
    async def _ws_send_wifi_networks(self, kind, data, ws):
        try:
            if kind == "send_wifi_networks":
                if data.get("confirmed") is not True or ws not in self.wifi_confirmations:
                    raise ValueError("invalid")
                config, confirmed_count = self.wifi_confirmations.pop(ws)
            else:
                confirmed_count = None
                config = wifi_config.validate(data.get("config"))
            await self.send_wifi(config, ws, confirmed_count=confirmed_count)
        except (ValueError, OSError):
            await self.ws_error(ws, "invalid")

    @ws_handler('set_editor_param')
    async def _ws_set_editor_param(self, kind, data, ws):
        name, value = str(data.get("name", "")), data.get("value")
        editor = self.state.data["editor"]
        declaration = next((item for item in editor.get("declarations", ())
                            if patch_manifest.qualify_param(item) == name), None)
        cleaned = self.clean_editor_value(declaration, value)
        if self.supervisor_mode == "edit" and cleaned is not None:
            editor.setdefault("params", {})[name] = cleaned
            self.osc.set_param_for(
                [self.editor_target()], 0, name, cleaned)
            await self.broadcast("state")

    @ws_handler('set_editor_point')
    async def _ws_set_editor_point(self, kind, data, ws):
        if self.supervisor_mode != "edit":
            return
        point = points.sanitize_point(data.get("point"))
        if point is None:
            return
        editor = self.state.data["editor"]
        editor.setdefault("points", {})[point["id"]] = point
        self.osc.send_editor_point(point)
        await self.broadcast("editor_points", {"points": editor["points"]})

    @ws_handler('clear_editor_point')
    async def _ws_clear_editor_point(self, kind, data, ws):
        if self.supervisor_mode != "edit":
            return
        try:
            point_id = int(data.get("id"))
        except (TypeError, ValueError):
            return
        editor = self.state.data["editor"]
        if editor.setdefault("points", {}).pop(point_id, None) is not None:
            self.osc.clear_editor_point(point_id)
            await self.broadcast("editor_points", {"points": editor["points"]})

    @ws_handler('set_editor_point_element')
    async def _ws_set_editor_point_element(self, kind, data, ws):
        if self.supervisor_mode != "edit":
            return
        try:
            element = int(data.get("element"))
        except (TypeError, ValueError):
            return
        # Current devices have one or two elements; positions support any number.
        # Widen this editor limit when a device needs more.
        if element not in (0, 1):
            return
        editor = self.state.data["editor"]
        editor["point_element"] = element
        self.osc.send_editor_element(element)
        await self.broadcast("editor_point_element", {"element": element})

    @ws_handler('save_patch_manifest',
                supervisor="dispatch", manifest=True, performance=True)
    async def _ws_save_patch_manifest(self, kind, data, ws):
        await self.save_patch_manifest(data, ws)

    @ws_handler('create_patch',
                supervisor="dispatch", manifest=True, performance=True)
    async def _ws_create_patch(self, kind, data, ws):
        await self.create_patch(data, ws)

    @ws_handler('add_project_patch')
    async def _ws_add_project_patch(self, kind, data, ws):
        await self.add_project_patch(data, ws)

    @ws_handler('new_patch_version',
                supervisor="dispatch", manifest=True, performance=True)
    async def _ws_new_patch_version(self, kind, data, ws):
        await self.new_patch_version(data, ws)

    @ws_handler('action',
                supervisor="dispatch", performance=patch_action)
    async def _ws_action(self, kind, data, ws):
        uid = data.get("uid")
        if data.get("verb") not in {"reboot", "shutdown", "restart-engine", "updatebopos"}:
            return
        scope = data.get("scope")
        if scope is not None:
            selector = self.remote_action_selector(scope, data.get("id"))
            if selector is None:
                await self.ws_error(ws, "That Remote command target is unavailable.")
                return
            self.osc.action(selector, data["verb"])
        elif uid == "all":
            self.osc.action("all", data["verb"])
        elif uid in self.state.devices and not self.state.devices[uid].get("virtual"):
            self.osc.uid_action(uid, data["verb"])

    @ws_handler('identify',
                supervisor="dispatch")
    async def _ws_identify(self, kind, data, ws):
        uid = data.get("uid")
        if uid in self.state.devices:
            self.osc.uid_action(uid, "identify")

    @ws_handler('set_fleet_patch',
                supervisor="dispatch", edit_blocked=True, performance=True)
    async def _ws_set_fleet_patch(self, kind, data, ws):
        if data.get("confirmed") is not True:
            await self.ws_error(ws, "Setting the fleet patch requires confirmation.")
            return
        name = str(data.get("patch", "")).strip()
        # The fleet runs one of the project's patches (66-projects
        # proposal sec 3): add a folder to the project first.
        if name not in self.state.project_patches():
            await self.ws_error(ws, f"Cannot set fleet patch {name!r}: add it to the project first.")
            return
        await self.stage_and_converge(name, ws)

    @ws_handler('retry_fleet_patch',
                supervisor="dispatch", performance=True)
    async def _ws_retry_fleet_patch(self, kind, data, ws):
        uid = data.get("uid")
        await self.retry_fleet_patch(uid, ws)

    @ws_handler('request_patches')
    async def _ws_request_patches(self, kind, data, ws):
        uid = data.get("uid")
        if uid in self.state.devices:
            self.osc.request(uid, "patches")

    @ws_handler('send_distribution',
                supervisor="dispatch", performance=patch_distribution)
    async def _ws_send_distribution(self, kind, data, ws):
        uid = data.get("uid")
        physical_target = (
            uid in self.state.devices
            and not self.state.devices[uid].get("virtual"))
        if (self.state.data["simulation"].get("active")
                and not physical_target):
            if ws is not None:
                await ws.send_json({"type": "error", "data": {"message":
                    "Simulation uses host patches directly; choose a patch and Switch "
                    "the simulated fleet instead of sending files."}})
            return
        catalog = await self.catalog()
        await self.broadcast("distribution", catalog)
        item_kind = str(data.get("kind", ""))
        name = str(data.get("name", ""))
        if item_kind == "asset" and not self.single_asset_target(uid):
            await self.ws_error(
                ws, "Assets require one online, assigned physical device target.")
            return
        requested = [item for group in catalog.values() for item in group
                     if item["kind"] == item_kind and item["name"] == name
                     and (item["kind"] != "patch" or item["valid"])]
        targets = self.distribution_targets(uid)
        if (self.requires_active_confirmation(targets, requested)
                and data.get("confirmed_active") is not True):
            if ws is not None:
                await ws.send_json({"type": "error", "data": {"message":
                    "Sending an active patch requires stop/restart confirmation."}})
            return
        base_urls = {}
        try:
            for device_uid in targets:
                base_urls[device_uid] = self.public_url(ws, device_uid)
        except ValueError as error:
            if ws is not None:
                await ws.send_json({"type": "error", "data": {"message": str(error)}})
            return
        for device_uid in targets:
            for item in requested:
                path = "patches" if item["kind"] == "patch" else "assets"
                slot = "patch:" + item["name"] if item["kind"] == "patch" else item["name"]
                encoded_name = urllib.parse.quote(item["name"], safe="")
                uri = f"{base_urls[device_uid]}/{path}/{encoded_name}/.manifest.json"
                self.osc.fetch(device_uid, uri, slot, item["fingerprint"])

    @ws_handler('drop_distribution',
                supervisor="dispatch", performance=patch_distribution)
    async def _ws_drop_distribution(self, kind, data, ws):
        uid = data.get("uid")
        item_kind, name = str(data.get("kind", "")), str(data.get("name", ""))
        if item_kind == "asset" and not self.single_asset_target(uid):
            await self.ws_error(
                ws, "Assets require one online, assigned physical device target.")
            return
        targets = self.distribution_targets(uid)
        valid_name = (identity.valid_asset_slot(name) if item_kind == "asset"
                      else PATCH_NAME_RE.fullmatch(name) is not None)
        if valid_name and item_kind in ("patch", "asset"):
            verb = "droppatch" if item_kind == "patch" else "dropassets"
            slot = "patch:" + name if item_kind == "patch" else name
            for device_uid in targets:
                selector = self.selector(device_uid)
                if selector is not None:
                    self.osc.os_command(selector, verb, [name])
                    device = self.state.devices[device_uid]
                    device.setdefault("distribution", {}).pop(slot, None)
                    device.setdefault("fetch", {}).pop(slot, None)
                    await self.broadcast("device_update", device)
                    if item_kind == "patch":
                        self.spawn(self.refresh_patches_later(device_uid))
            self.state.save_debounced()

    @ws_handler('refresh_distribution')
    async def _ws_refresh_distribution(self, kind, data, ws):
        await self.broadcast("distribution", await self.catalog())
        # Host edits can change the live desired fingerprint without a node
        # event. Re-emit state so per-device badges immediately expose drift.
        await self.broadcast("state")

    @ws_handler('set_master')
    async def _ws_set_master(self, kind, data, ws):
        master = self.state.clean_master(data.get("value"))
        self.state.data["master"] = master
        self.state.save_debounced()
        self.osc.send_master()
        await self.broadcast("master", {"value": master})

    @ws_handler('set_event_lead')
    async def _ws_set_event_lead(self, kind, data, ws):
        raw_ms = data.get("ms")
        if isinstance(raw_ms, bool):
            await self.ws_error(ws, "Event lead must be a whole number of milliseconds.")
            return
        try:
            ms = int(raw_ms)
        except (TypeError, ValueError):
            await self.ws_error(ws, "Event lead must be a whole number of milliseconds.")
            return
        ms = min(max(ms, 0), 10000)
        self.state.data["event_lead_ms"] = ms
        self.state.save_debounced()
        await self.broadcast("state")

    @ws_handler('set_facilitator_commands',
                supervisor="dispatch")
    async def _ws_set_facilitator_commands(self, kind, data, ws):
        commands = data.get("commands")
        if (not isinstance(commands, list)
                or any(not isinstance(command, str)
                       or command not in FACILITATOR_COMMANDS
                       for command in commands)):
            await self.ws_error(
                ws, "Remote commands must be recognized framework verbs.")
            return
        if not self.state.set_facilitator_commands(commands):
            await self.ws_error(
                ws, "Could not save Remote commands; the previous setting is still active.")
            return
        await self.broadcast("state")

    @ws_handler('fire_event')
    async def _ws_fire_event(self, kind, data, ws):
        event, error = self.validate_event_command(data)
        if error is not None:
            await self.ws_error(ws, error)
            return
        selector, event_identity, elements = event
        try:
            lead_ms = int(data.get("lead_ms", 500))
        except (TypeError, ValueError):
            lead_ms = 500
        shared_time_ns, lead_ms = self.osc.fire_event(
            selector, event_identity, elements, lead_ms)
        await self.broadcast("event_scheduled", {
            "selector": selector,
            "identity": event_identity,
            "elements": elements,
            "shared_time_ns": str(shared_time_ns),
            "lead_ms": lead_ms,
        })

    @ws_handler('fire_editor_event')
    async def _ws_fire_editor_event(self, kind, data, ws):
        if self.supervisor_mode != "edit":
            return
        # The editor drives the local audition engine, which is seat 0 —
        # the same selector `set_editor_param` writes to. The browser sends
        # only an identity and elements, so supply it here.
        event, error = self.validate_event_command(dict(data, selector="0"))
        if error is not None:
            await self.ws_error(ws, error)
            return
        selector, event_identity, elements = event
        shared_time_ns, _lead_ms = self.osc.fire_event(
            selector, event_identity, elements, 0)
        await self.broadcast("editor_event_fired", {
            "identity": event_identity,
            "shared_time_ns": str(shared_time_ns),
        })

    @ws_handler('mute_all',
                supervisor="dispatch")
    async def _ws_mute_all(self, kind, data, ws):
        value = int(bool(data.get("value")))
        self.state.data["muted"] = bool(value)
        self.osc.send_mute_all()
        await self.broadcast("mute_all", {"value": value})

    @ws_handler('set_simulation',
                supervisor="handler")
    async def _ws_set_simulation(self, kind, data, ws):
        async with self.supervisor_lock:
            if bool(data.get("active")):
                if (ws is not None and self.supervisor_mode != "simulate"
                        and data.get("confirmed") is not True):
                    message = ("Leaving Patch edit for Simulation requires confirmation."
                               if self.supervisor_mode == "edit" else
                               "Starting Simulation requires confirmation.")
                    await self.ws_error(ws, message)
                    return
                await self.start_simulation(str(data.get("patch", "")).strip() or None)
            else:
                if (ws is not None and self.supervisor_mode == "simulate"
                        and data.get("confirmed") is not True):
                    await self.ws_error(
                        ws, "Stopping a running simulation requires confirmation.")
                    return
                await self.stop_simulation()
        await self.broadcast("state")

    @ws_handler('set_edit',
                performance=starting_editor, supervisor="handler")
    async def _ws_set_edit(self, kind, data, ws):
        async with self.supervisor_lock:
            active = bool(data.get("active"))
            if (active and ws is not None and self.supervisor_mode != "edit"
                    and data.get("confirmed") is not True):
                message = ("Leaving a running simulation for Patch edit requires confirmation."
                           if self.supervisor_mode == "simulate" else
                           "Starting Patch edit requires confirmation.")
                await self.ws_error(ws, message)
                return
            if (not active and ws is not None and self.supervisor_mode == "edit"
                    and data.get("confirmed") is not True):
                await self.ws_error(ws, "Stopping Patch edit requires confirmation.")
                return
            if active:
                await self.start_edit(str(data.get("patch", "")).strip() or None)
            else:
                await self.stop_edit()
        await self.broadcast("state")

    @ws_handler('relaunch_edit',
                performance=True, supervisor="handler")
    async def _ws_relaunch_edit(self, kind, data, ws):
        async with self.supervisor_lock:
            if self.supervisor_mode == "edit":
                editor = self.state.data["editor"]
                patch_name = editor.get("patch")
                scratch_points = dict(editor.get("points", {}))
                point_element = int(editor.get("point_element", 0))
                await self.stop_edit()
                await self.start_edit(patch_name)
                # Restart/relaunch is still the same edit session. Restore
                # its scratch geometry to the fresh relay without making
                # it durable or joining installation-wide point state.
                if self.supervisor_mode == "edit":
                    self.state.data["editor"]["points"] = scratch_points
                    self.state.data["editor"]["point_element"] = point_element
                    self.osc.send_editor_element(point_element)
                    for point in scratch_points.values():
                        self.osc.send_editor_point(point)
                await self.broadcast("state")

    @ws_handler('add_seat',
                supervisor="dispatch")
    async def _ws_add_seat(self, kind, data, ws):
        seat_id = self.state.clean_seat_id(data.get("id"))
        if seat_id is None:
            await self.ws_error(ws, "Seat IDs must be non-negative integers.")
            return
        seat = self.state.clean_seat({"id": seat_id, "name": data.get("name", ""),
            "positions": data.get("positions", []),
            "params": data.get("params", {}), "bound": None})
        if seat is None:
            await self.ws_error(ws, "Seat IDs must be non-negative integers.")
            return
        if str(seat_id) in self.state.seats:
            await self.ws_error(ws, f"Seat ID {seat_id} already exists.")
            return
        positions = self.state.clean_positions(data.get("positions", []))
        if positions is None:
            return
        self.state.seats[str(seat_id)] = seat
        self.state.data["positions"][str(seat_id)] = positions
        self.state.save_debounced()
        if self.state.data["simulation"].get("active"):
            if self.supervisor_mode == "simulate":
                await self.restart_simulation()
        await self.broadcast("state")

    @ws_handler('create_group',
                supervisor="dispatch")
    async def _ws_create_group(self, kind, data, ws):
        group, error = self.state.create_group(data.get("name", ""))
        if error:
            await self.ws_error(ws, error)
            return
        await self.broadcast("state")
        await self.broadcast("show_warnings", self.show_warnings())

    @ws_handler('rename_group',
                supervisor="dispatch")
    async def _ws_rename_group(self, kind, data, ws):
        group, error = self.state.rename_group(data.get("id"), data.get("name", ""))
        if error:
            await self.ws_error(ws, error)
            return
        await self.broadcast("state")
        await self.broadcast("show_warnings", self.show_warnings())

    @ws_handler('delete_group',
                supervisor="dispatch")
    async def _ws_delete_group(self, kind, data, ws):
        group_id = self.state.clean_group_id(data.get("id"))
        affected = [seat for seat in self.state.seats.values()
                    if group_id in seat.get("groups", [])]
        _removed, error = self.state.delete_group(group_id)
        if error:
            await self.ws_error(ws, error)
            return
        for seat in affected:
            self.sync_seat_groups(seat)
        await self.broadcast("state")
        await self.broadcast("show_warnings", self.show_warnings())

    @ws_handler('set_seat_groups',
                supervisor="dispatch")
    async def _ws_set_seat_groups(self, kind, data, ws):
        seat, error = self.state.set_seat_groups(data.get("id"), data.get("groups"))
        if error:
            await self.ws_error(ws, error)
            return
        self.sync_seat_groups(seat)
        await self.broadcast("state")

    @ws_handler('reindex_seat',
                supervisor="dispatch")
    async def _ws_reindex_seat(self, kind, data, ws):
        seat, error = self.state.reindex_seat(data.get("id"), data.get("new_id"))
        if error:
            await self.ws_error(ws, error)
            return
        self.assign_seat(seat)
        if self.state.data["simulation"].get("active"):
            if self.supervisor_mode == "simulate":
                await self.restart_simulation()
        await self.broadcast("state")
        await self.broadcast("seat_reindexed", {
            "old_id": data.get("id"), "new_id": seat["id"]})

    @ws_handler('update_seat',
                supervisor="dispatch")
    async def _ws_update_seat(self, kind, data, ws):
        seat = self.state.seats.get(str(data.get("id")))
        if seat is None:
            return
        candidate = dict(seat)
        for key in ("name", "params"):
            if key in data:
                candidate[key] = data[key]
        cleaned = self.state.clean_seat(candidate)
        if cleaned is None:
            return
        if "positions" in data:
            positions = self.state.clean_positions(data["positions"])
            if positions is None:
                return
            self.state.data["positions"][str(cleaned["id"])] = positions
        self.state.seats[str(cleaned["id"])] = cleaned
        self.assign_seat(cleaned)
        self.state.save_debounced()
        await self.broadcast("state")

    @ws_handler('remove_seat',
                supervisor="dispatch")
    async def _ws_remove_seat(self, kind, data, ws):
        seat = self.state.seats.get(str(data.get("id")))
        if seat is None:
            return
        removed_uid = seat.get("bound")
        if not await self.revoke_online(removed_uid, ws, "remove this Seat"):
            return
        if self.state.delete_seat(seat["id"]) is None:
            self.replay_current_assignments()
            await self.ws_error(ws, "Could not remove the Seat; no changes were made.")
            return
        self.mark_offline_revoking(removed_uid)
        if self.state.data["simulation"].get("active"):
            if self.supervisor_mode == "simulate":
                await self.restart_simulation()
        await self.broadcast("state")

    @ws_handler('bind_seat',
                supervisor="dispatch")
    async def _ws_bind_seat(self, kind, data, ws):
        seat = self.state.seats.get(str(data.get("id")))
        bind_uid = str(data.get("uid", ""))
        device = self.state.devices.get(bind_uid)
        if (seat is None or device is None or device.get("virtual")
                or device.get("revoking_assignment")):
            await self.ws_error(ws, "Choose a physical device for this Seat.")
            return
        source = next((other for other in self.state.seats.values()
                       if other.get("bound") == bind_uid and other is not seat), None)
        displaced_uid = seat.get("bound") if seat.get("bound") != bind_uid else None
        if (source is not None or displaced_uid) and data.get("confirmed") is not True:
            await self.ws_error(
                ws, "This assignment replaces an existing Seat binding; confirm it first.")
            return
        for changed_uid in (displaced_uid, bind_uid if source is not None else None):
            if not await self.revoke_online(changed_uid, ws, "replace this Seat binding"):
                self.replay_current_assignments()
                return
        previous = {key: item.get("bound") for key, item in self.state.seats.items()}
        if source is not None:
            source["bound"] = None
        seat["bound"] = bind_uid
        try:
            self.state.save()
        except (OSError, TypeError, ValueError):
            for key, bound_uid in previous.items():
                self.state.seats[key]["bound"] = bound_uid
            self.replay_current_assignments()
            await self.ws_error(ws, "Could not save the Seat assignment; no changes were made.")
            return
        self.mark_offline_revoking(displaced_uid)
        if source is not None:
            self.mark_offline_revoking(bind_uid)
        self.assign_seat(seat)
        await self.broadcast("state")

    @ws_handler('unbind_seat',
                supervisor="dispatch")
    async def _ws_unbind_seat(self, kind, data, ws):
        seat = self.state.seats.get(str(data.get("id")))
        if seat is not None:
            if not await self.revoke_online(seat.get("bound"), ws, "unassign this Seat"):
                return
            previous = seat.get("bound")
            seat["bound"] = None
            try:
                self.state.save()
            except (OSError, TypeError, ValueError):
                seat["bound"] = previous
                self.replay_current_assignments()
                await self.ws_error(ws, "Could not save the unassignment; no changes were made.")
                return
            self.mark_offline_revoking(previous)
            await self.broadcast("state")

    @ws_handler('set_device_alias')
    async def _ws_set_device_alias(self, kind, data, ws):
        alias, error = self.state.set_device_alias(
            str(data.get("uid", "")), data.get("alias"))
        if error:
            await self.ws_error(ws, error)
            return
        await self.broadcast("state")

    @ws_handler('reset_device_alias')
    async def _ws_reset_device_alias(self, kind, data, ws):
        alias, error = self.state.reset_device_alias(str(data.get("uid", "")))
        if error:
            await self.ws_error(ws, error)
            return
        await self.broadcast("state")

    @ws_handler('forget_device',
                supervisor="dispatch")
    async def _ws_forget_device(self, kind, data, ws):
        forget_uid = str(data.get("uid", ""))
        device = self.state.devices.get(forget_uid)
        seat = next((item for item in self.state.seats.values()
                     if item.get("bound") == forget_uid), None)
        if seat is not None:
            await self.ws_error(
                ws, f"Unassign {self.state.alias_for(forget_uid) or forget_uid} before forgetting it.")
            return
        registry_entry = self.state.remove_device_alias(forget_uid)
        removed_device = self.state.devices.pop(forget_uid, None)
        if removed_device is not None or registry_entry is not None:
            try:
                self.state.save()
            except (OSError, TypeError, ValueError):
                if removed_device is not None:
                    self.state.devices[forget_uid] = device
                if registry_entry is not None:
                    self.state.device_registry[forget_uid] = registry_entry
                await self.ws_error(ws, "Could not forget the device; no changes were made.")
                return
            await self.broadcast("state")

    @ws_handler('forget_offline_unbound',
                supervisor="dispatch")
    async def _ws_forget_offline_unbound(self, kind, data, ws):
        bound = {seat.get("bound") for seat in self.state.seats.values()}
        removed = {}
        for device_uid in list(self.state.devices):
            if device_uid not in bound and not self.state.devices[device_uid].get("online"):
                removed[device_uid] = (self.state.devices.pop(device_uid),
                                       self.state.remove_device_alias(device_uid))
        if removed:
            try:
                self.state.save()
            except (OSError, TypeError, ValueError):
                for device_uid, (device, registry_entry) in removed.items():
                    self.state.devices[device_uid] = device
                    if registry_entry is not None:
                        self.state.device_registry[device_uid] = registry_entry
                await self.ws_error(ws, "Could not forget offline devices; no changes were made.")
                return
        await self.broadcast("state")

    @ws_handler('set_listener')
    async def _ws_set_listener(self, kind, data, ws):
        listener = self.state.clean_listener(data)
        if listener is None:
            return
        self.state.data["listener"] = listener
        self.state.save_debounced()
        self.osc.send_audition_listener()
        await self.broadcast("listener", listener)

    @ws_handler('set_point',
                supervisor="dispatch", edit_blocked=True)
    async def _ws_set_point(self, kind, data, ws):
        point = points.sanitize_point(data.get("point"),
                                      self.state.data.get("room"))
        if point is None:
            return
        self.osc.upsert_point(point)
        await self.broadcast("points", {"points": self.state.data["points"]})

    @ws_handler('clear_point',
                supervisor="dispatch", edit_blocked=True)
    async def _ws_clear_point(self, kind, data, ws):
        try:
            point_id = int(data.get("id"))
        except (TypeError, ValueError):
            return
        self.osc.clear_point(point_id)
        await self.broadcast("points", {"points": self.state.data["points"]})

    @ws_handler('set_room',
                supervisor="dispatch", edit_blocked=True)
    async def _ws_set_room(self, kind, data, ws):
        room = self.state.clean_room(data)
        if room is not None:
            width, depth = room["width"], room["depth"]
            self.state.data["room"] = room
            for point in self.state.data.get("points", {}).values():
                motion = point.get("motion") or {}
                if motion.get("type") == "bounce":
                    motion["bounds"] = [width, depth]
                    origin = motion.get("origin") or [point["x"], point["y"]]
                    motion["origin"] = [min(max(float(origin[0]), 0.0), width),
                                        min(max(float(origin[1]), 0.0), depth)]
            if self.state.data.get("points"):
                self.osc.send_points_frame()
                await self.broadcast("points", {"points": self.state.data["points"]})
            listener = (self.state.clean_listener(self.state.data.get("listener"))
                        or self.state.default_listener())
            self.state.data["listener"] = listener
            self.osc.send_audition_listener()
            await self.broadcast("listener", listener)
            self.state.save_debounced()
            await self.broadcast("room", self.state.data["room"])

    @ws_handler('create_project', 'open_project', 'rename_project',
                supervisor="dispatch", live_only=True)
    async def _ws_create_project(self, kind, data, ws):
        name = data.get("name")
        try:
            if kind == "create_project":
                self.state.create_project(name)
                await self.open_project(name)
            elif kind == "rename_project":
                self.state.rename_project(name)
                await self.broadcast("state")
            else:
                await self.open_project(name)
        except (OSError, TypeError, ValueError):
            message = {"open_project": "That project could not be opened.",
                       "create_project": "The project could not be created.",
                       "rename_project": "The project could not be renamed."}[kind]
            await self.ws_error(ws, message)

    @ws_handler('create_site',
                supervisor="dispatch", edit_blocked=True)
    async def _ws_create_site(self, kind, data, ws):
        try:
            self.state.create_site(data.get("name"), data.get("source"))
        except (OSError, TypeError, ValueError):
            await self.ws_error(ws, "The site could not be created.")
            return
        for seat in self.state.seats.values():
            self.assign_seat(seat)
            self.sync_seat_groups(seat)
        self.osc.send_audition_listener()
        await self.broadcast("state")

    @ws_handler('select_site',
                supervisor="dispatch", edit_blocked=True)
    async def _ws_select_site(self, kind, data, ws):
        name = data.get("name")
        if not self.state.valid_site_name(name):
            return
        try:
            self.state.select_site(name)
        except (OSError, TypeError, ValueError):
            self.state._load_invalid = True
            self.state._invalid_file_notice(self.state.site_path(name))
            await self.broadcast("state")
            return
        for seat in self.state.seats.values():
            self.assign_seat(seat)
            self.sync_seat_groups(seat)
        self.osc.send_audition_listener()
        await self.broadcast("state")

    @ws_handler('create_show', 'delete_show', 'open_show', 'rename_show',
                supervisor="dispatch")
    async def _ws_create_show(self, kind, data, ws):
        await self.manage_show(kind, data, ws)

    @ws_handler('clear_show')
    async def _ws_clear_show(self, kind, data, ws):
        # Checked inside apply_show_mutation's lock, like the edit itself.
        await self.apply_show_mutation(ws, lambda show: (
            (show, None, "Stop the show before clearing it.") if self.show_playing()
            else show_model.clear_items(show)))

    @ws_handler('undo_show')
    async def _ws_undo_show(self, kind, data, ws):
        await self.undo_show(ws)

    @ws_handler('add_step')
    async def _ws_add_step(self, kind, data, ws):
        await self.apply_show_mutation(ws, show_model.add_step, data.get("after_uid"))

    @ws_handler('add_divider')
    async def _ws_add_divider(self, kind, data, ws):
        await self.apply_show_mutation(ws, show_model.add_divider, data.get("after_uid"))

    @ws_handler('update_step')
    async def _ws_update_step(self, kind, data, ws):
        patch = {key: data[key] for key in
                 ("alias", "duration_s", "play_count", "then_actions")
                 if key in data}
        await self.apply_show_mutation(ws, show_model.update_step, data.get("uid"), patch)

    @ws_handler('update_divider')
    async def _ws_update_divider(self, kind, data, ws):
        patch = {key: data[key] for key in ("alias",) if key in data}
        await self.apply_show_mutation(ws, show_model.update_divider, data.get("uid"), patch)

    @ws_handler('move_item')
    async def _ws_move_item(self, kind, data, ws):
        await self.apply_show_mutation(
            ws, show_model.move_item, data.get("uid"), data.get("after_uid"))

    @ws_handler('remove_item')
    async def _ws_remove_item(self, kind, data, ws):
        # A removed playing step stops once the removal is saved.
        await self.apply_show_mutation(ws, show_model.remove_item, data.get("uid"))

    @ws_handler('duplicate_item')
    async def _ws_duplicate_item(self, kind, data, ws):
        await self.apply_show_mutation(ws, show_model.duplicate_item, data.get("uid"))

    @ws_handler('add_message')
    async def _ws_add_message(self, kind, data, ws):
        await self.apply_show_mutation(
            ws, show_model.add_message, data.get("step_uid"), data.get("message"))

    @ws_handler('update_message')
    async def _ws_update_message(self, kind, data, ws):
        patch = {key: data[key] for key in
                 ("kind", "alias", "address", "args", "target")
                 if key in data}
        await self.apply_show_mutation(ws, show_model.update_message, data.get("uid"), patch)

    @ws_handler('move_message')
    async def _ws_move_message(self, kind, data, ws):
        await self.apply_show_mutation(
            ws, show_model.move_message, data.get("uid"),
            data.get("to_step_uid"), data.get("after_uid"))

    @ws_handler('remove_message')
    async def _ws_remove_message(self, kind, data, ws):
        await self.apply_show_mutation(ws, show_model.remove_message, data.get("uid"))

    @ws_handler('step_start')
    async def _ws_step_start(self, kind, data, ws):
        await self.show_engine.step_start(data.get("uid"))

    @ws_handler('step_stop')
    async def _ws_step_stop(self, kind, data, ws):
        await self.show_engine.step_stop(data.get("uid"))

    @ws_handler('step_pause')
    async def _ws_step_pause(self, kind, data, ws):
        await self.show_engine.step_pause(data.get("uid"))

    @ws_handler('step_resume')
    async def _ws_step_resume(self, kind, data, ws):
        await self.show_engine.step_resume(data.get("uid"))

    @ws_handler('step_trigger_next')
    async def _ws_step_trigger_next(self, kind, data, ws):
        await self.show_engine.step_trigger_next(data.get("uid"))

    @ws_handler('request_params')
    async def _ws_request_params(self, kind, data, ws):
        uid = data.get("uid")
        self.osc.request(uid, "params")

    @ws_handler('request_report')
    async def _ws_request_report(self, kind, data, ws):
        uid = data.get("uid")
        self.osc.request(uid, "report")
