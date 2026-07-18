"""Show playback engine (show-tab stitch 3).

Asyncio state machine that drives a loaded `show_model` document: per-step
start/stop/pause/resume, duration timers, play-n-times re-emission, and
then-action resolution (§4 of `.notes/show-tab-design-2026-07-18.md`). This
module is deliberately separable -- it imports only `show_model` and stdlib,
never `server`; the OSC send path (an `OSCBridge` instance) and a WS
broadcast callback are handed to the constructor, so the engine never opens
a socket of its own and never re-derives `OSCBridge`'s send logic.

Message emission always goes through existing `OSCBridge` methods, keyed by
address kind:
  - `/cue`      -> `fire_cue` (forward_sync) or `fire_cue_now` (immediate) --
                   the only two cue senders that exist, so behavior always
                   matches every other tab's cue traffic exactly.
  - `/p/<name>` -> `set_param(selector, name, value)` once per selector in
                   the message's `target` list -- each entry is already the
                   literal selector (design note sec 2 + 5c amendment),
                   never re-derived.
  - anything else (including `/pt`) -> `send(address, args)` verbatim. A show
    message's `args` already carry the exact wire-order OSC arguments for
    its address (this is how `/pt`'s selector-free contract plane -- and any
    future raw address -- round-trips without a second sender disagreeing
    with the first). `OSCBridge.upsert_point`/`send_editor_point` manage
    durable installation point state and the private editor relay
    respectively; a scripted show step blasting one `/pt` frame is neither,
    so reusing `send()` directly (still the one relay socket, no new one)
    avoids mutating state this step never intended to own.
"""

import asyncio
import logging
import os
import random
import time

import show_model

log = logging.getLogger("bopos.show_engine")

# Guards a chain of duration_s==0 (finite play_count) then-action
# resolutions that never yields to the event loop -- e.g. two steps with
# duration_s==0 whose then_actions goto each other. Each step-to-step
# transition (fresh `_begin`) consumes one unit; hitting zero stops
# playback and logs rather than hanging the process.
MAX_SYNCHRONOUS_RESOLUTIONS = 50


class ShowEngine:
    def __init__(self, bridge, broadcast, seed=None):
        self.bridge = bridge
        self.broadcast = broadcast  # async callable(message_type, data)
        if seed is None:
            # No existing mechanism threads a run-context seed into the
            # dashboard process (python/runcontext.py's BOPOS_SEED is
            # delivered to PD engine launches, not this process) -- reuse
            # the same env var name so a caller (or the verify harness) can
            # set it for reproducibility; unset falls back to OS randomness.
            seed = os.environ.get("BOPOS_SEED")
        self.random = random.Random(seed)
        self.show = show_model.empty_show("")
        # uid -> {"state": "playing"|"paused", "iteration": int,
        #         "expiry_mono": float|None, "remaining_s": float|None,
        #         "timer": asyncio.TimerHandle|None}
        # Stopped steps have no entry (matches the design note's broadcast
        # example, which only lists playing/paused steps).
        self.playback = {}
        # section key (tuple of step uids in the section) -> list of uids
        # remaining in the current other_in_section shuffle bag.
        self.section_bags = {}
        # uids whose most recent then-action resolution was a goto to a
        # since-deleted uid; surfaced once on the next show_playback
        # broadcast then cleared (design note sec 4, "one-cycle" flag).
        self._goto_missing = set()

    # ----------------------------------------------------------------
    # Document lookups
    # ----------------------------------------------------------------

    def step_by_uid(self, uid):
        for item in self.show["items"]:
            if item["kind"] == "step" and item["uid"] == uid:
                return item
        return None

    def _section_key(self, uid):
        section = show_model.section_for(self.show, uid)
        return tuple(item["uid"] for item in section) if section else None

    def _adjacent_step_uid(self, uid, direction):
        step_uids = [item["uid"] for item in self.show["items"] if item["kind"] == "step"]
        try:
            index = step_uids.index(uid)
        except ValueError:
            return None
        target = index + direction
        return step_uids[target] if 0 <= target < len(step_uids) else None

    def _adjacent_section_first_uid(self, uid, direction):
        keys = [tuple(item["uid"] for item in section)
                for section in show_model.sections(self.show)]
        current = self._section_key(uid)
        try:
            index = keys.index(current)
        except ValueError:
            return None
        target = index + direction
        return keys[target][0] if 0 <= target < len(keys) else None

    def _pick_other_in_section(self, uid):
        """Per-section shuffle-bag pick, excluding immediate repeats.

        Starts as every step in the section except `uid` (the step whose
        then-action just resolved); each resolution pops one pick, and an
        emptied bag resets to the full section minus the step just picked
        (design note sec 4) so the very next pick still can't repeat it.
        A one-step section has no eligible "other" -- returns None.
        """
        key = self._section_key(uid)
        if key is None:
            return None
        bag = self.section_bags.get(key)
        if not bag:
            bag = [item for item in key if item != uid]
        if not bag:
            return None
        pick = bag.pop(self.random.randrange(len(bag)))
        if not bag:
            bag = [item for item in key if item != pick]
        self.section_bags[key] = bag
        return pick

    # ----------------------------------------------------------------
    # Message emission
    # ----------------------------------------------------------------

    def _emit_messages(self, step):
        forward_sync = step.get("forward_sync", False)
        for message in step["messages"]:
            self._send_message(message, forward_sync)

    def _send_message(self, message, forward_sync):
        address, target = message["address"], message["target"]
        args = [arg["value"] for arg in message["args"]]
        if address == "/cue":
            cue_id = str(args[0]) if args else ""
            if forward_sync:
                self.bridge.fire_cue(cue_id)
            else:
                # The existing "immediate cue path" (osc_bridge.py) -- same
                # sender as fire_editor_cue, shared_time_ns == now.
                self.bridge.fire_cue_now(cue_id)
        elif address.startswith("/p/") and len(address) > 3:
            name = address[len("/p/"):]
            # 5c: target is a selector list; fan one datagram out per
            # selector. A seat covered twice (listed and in a listed group)
            # receives the write twice -- harmless, params are idempotent
            # full-state writes, so no set-algebra here. The model already
            # collapses exact duplicates and lets "all" subsume the rest.
            selectors = target if isinstance(target, list) else [target]
            for selector in selectors:
                self.bridge.set_param(selector, name, args[0] if args else 0)
        else:
            self.bridge.send(address, args)

    # ----------------------------------------------------------------
    # Timer plumbing
    # ----------------------------------------------------------------

    def _cancel_timer(self, uid, freeze_remaining=False):
        state = self.playback.get(uid)
        if state is None:
            return
        timer = state.get("timer")
        if timer is not None:
            timer.cancel()
        state["timer"] = None
        if freeze_remaining and state.get("expiry_mono") is not None:
            state["remaining_s"] = max(0.0, state["expiry_mono"] - time.monotonic())
        state["expiry_mono"] = None

    def _arm_timer(self, uid, duration):
        state = self.playback[uid]
        state["expiry_mono"] = time.monotonic() + duration
        state["remaining_s"] = duration
        state["timer"] = asyncio.get_running_loop().call_later(
            duration, self._timer_fired, uid)

    def _timer_fired(self, uid):
        asyncio.ensure_future(self._on_expiry(uid))

    async def _on_expiry(self, uid):
        step = self.step_by_uid(uid)
        state = self.playback.get(uid)
        if step is None or state is None or state["state"] != "playing":
            return
        state["timer"] = None
        play_count = step["play_count"]
        if play_count is None or state["iteration"] < play_count:
            state["iteration"] += 1
            self._emit_messages(step)
            self._arm_timer(uid, step["duration_s"])
        else:
            await self._resolve_then_actions(uid, step, MAX_SYNCHRONOUS_RESOLUTIONS)
        await self._broadcast_playback()

    # ----------------------------------------------------------------
    # Core start / stop / transition
    # ----------------------------------------------------------------

    async def _begin(self, uid, budget):
        """Fresh (iteration=1) start of `uid` -- the shared "step_start"
        semantics used by the public entry point and every then-action that
        lands on a step (play_again, next/previous step or section, any/
        other-in-section, goto)."""
        if budget <= 0:
            log.warning("show engine: synchronous resolution budget exceeded; stopping")
            return
        budget -= 1
        step = self.step_by_uid(uid)
        if step is None:
            return
        self._cancel_timer(uid)
        self.playback[uid] = {"state": "playing", "iteration": 1,
                              "remaining_s": None, "expiry_mono": None, "timer": None}
        await self._run_iterations(uid, step, budget)

    async def _run_iterations(self, uid, step, budget):
        self._emit_messages(step)
        duration = step["duration_s"]
        if duration > 0:
            self._arm_timer(uid, duration)
            return
        # duration_s == 0 -- only valid with a finite play_count (enforced by
        # show_model at write time), so this resolves synchronously.
        play_count = step["play_count"]
        state = self.playback[uid]
        while state["iteration"] < play_count:
            state["iteration"] += 1
            self._emit_messages(step)
        await self._resolve_then_actions(uid, step, budget)

    async def _stop_step(self, uid):
        self._cancel_timer(uid)
        self.playback.pop(uid, None)
        # Bag reaping is deliberately NOT done here: a then-action transition
        # stops the old step and starts the new one as two separate awaits
        # (_transition), so mid-transition the section can transiently look
        # fully stopped even though playback continues one step later in the
        # same section -- checking here would wipe the bag every single hop.
        # _reap_stale_bags() (called once the whole trigger has settled,
        # right before every broadcast) is the stable point for this check.

    async def _transition(self, from_uid, to_uid, budget):
        await self._stop_step(from_uid)
        await self._begin(to_uid, budget)

    async def _goto_or_stop(self, from_uid, to_uid, budget):
        if to_uid is None:
            await self._stop_step(from_uid)
        else:
            await self._transition(from_uid, to_uid, budget)

    # ----------------------------------------------------------------
    # Then-action resolution
    # ----------------------------------------------------------------

    async def _resolve_then_actions(self, uid, step, budget):
        actions = step["then_actions"]
        if not actions:
            action = {"type": "stop"}
        elif len(actions) == 1:
            action = actions[0]
        else:
            action = self.random.choice(actions)
        await self._execute_then_action(uid, step, action, budget)

    async def _execute_then_action(self, uid, step, action, budget):
        kind = action["type"]
        if kind == "stop":
            await self._stop_step(uid)
        elif kind == "play_again":
            await self._begin(uid, budget)
        elif kind == "next_step":
            await self._goto_or_stop(uid, self._adjacent_step_uid(uid, 1), budget)
        elif kind == "previous_step":
            await self._goto_or_stop(uid, self._adjacent_step_uid(uid, -1), budget)
        elif kind == "any_in_section":
            section = show_model.section_for(self.show, uid)
            candidates = [item["uid"] for item in section] if section else [uid]
            await self._transition(uid, self.random.choice(candidates), budget)
        elif kind == "other_in_section":
            await self._goto_or_stop(uid, self._pick_other_in_section(uid), budget)
        elif kind == "goto":
            target_uid = action["target_uid"]
            if self.step_by_uid(target_uid) is None:
                self._goto_missing.add(uid)
                await self._stop_step(uid)
            else:
                await self._transition(uid, target_uid, budget)
        elif kind == "next_section":
            await self._goto_or_stop(uid, self._adjacent_section_first_uid(uid, 1), budget)
        elif kind == "previous_section":
            await self._goto_or_stop(uid, self._adjacent_section_first_uid(uid, -1), budget)

    # ----------------------------------------------------------------
    # Public transport API -- one call per WS transport message
    # ----------------------------------------------------------------

    async def step_start(self, uid):
        if self.step_by_uid(uid) is None:
            return
        self._goto_missing.discard(uid)
        await self._begin(uid, MAX_SYNCHRONOUS_RESOLUTIONS)
        await self._broadcast_playback()

    async def step_stop(self, uid):
        await self._stop_step(uid)
        await self._broadcast_playback()

    async def step_pause(self, uid):
        state = self.playback.get(uid)
        if state is None or state["state"] != "playing":
            return
        self._cancel_timer(uid, freeze_remaining=True)
        state["state"] = "paused"
        await self._broadcast_playback()

    async def step_resume(self, uid):
        state = self.playback.get(uid)
        if state is None or state["state"] != "paused":
            return
        step = self.step_by_uid(uid)
        if step is None:
            await self._stop_step(uid)
            await self._broadcast_playback()
            return
        remaining = state.get("remaining_s") or 0.0
        state["state"] = "playing"
        state["expiry_mono"] = time.monotonic() + remaining
        state["timer"] = asyncio.get_running_loop().call_later(
            remaining, self._timer_fired, uid)
        await self._broadcast_playback()

    async def step_trigger_next(self, uid):
        """Resolve `then_actions` immediately, regardless of remaining time
        or iterations left (design note sec 3, `step_trigger_next` row)."""
        state = self.playback.get(uid)
        step = self.step_by_uid(uid)
        if state is None or step is None:
            return
        self._cancel_timer(uid)
        await self._resolve_then_actions(uid, step, MAX_SYNCHRONOUS_RESOLUTIONS)
        await self._broadcast_playback()

    async def stop_all_steps(self):
        for uid in list(self.playback):
            self._cancel_timer(uid)
        self.playback.clear()
        self.section_bags.clear()
        self._goto_missing.clear()
        await self._broadcast_playback()

    # ----------------------------------------------------------------
    # Snapshot / broadcast
    # ----------------------------------------------------------------

    def _reap_stale_bags(self):
        """Discard any section's shuffle bag once every step in that section
        is stopped (design note sec 4: per-section, per continuous-play
        episode). Called once a whole trigger has fully settled -- see the
        comment in `_stop_step` for why this can't be checked eagerly there.
        """
        for key in list(self.section_bags):
            if not any(item in self.playback for item in key):
                del self.section_bags[key]

    def snapshot(self):
        """Full `show_playback` payload (design note sec 3)."""
        self._reap_stale_bags()
        steps = {}
        now = time.monotonic()
        for uid, state in self.playback.items():
            if state["state"] == "playing" and state.get("expiry_mono") is not None:
                remaining = max(0.0, state["expiry_mono"] - now)
            else:
                remaining = state.get("remaining_s")
            key = self._section_key(uid)
            steps[uid] = {"state": state["state"], "iteration": state["iteration"],
                         "remaining_s": remaining,
                         "section_bag": self.section_bags.get(key) if key is not None else None}
        for uid in self._goto_missing:
            if uid not in steps:
                steps[uid] = {"state": "stopped", "iteration": 0,
                             "remaining_s": None, "section_bag": None}
            steps[uid]["goto_missing"] = True
        return {"steps": steps}

    async def _broadcast_playback(self):
        snapshot = self.snapshot()
        self._goto_missing.clear()
        await self.broadcast("show_playback", snapshot)
