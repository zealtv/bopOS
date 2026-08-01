# 43-live-param-checkbox-nosend

**BUG (dashboard).** On the facilitator "Dashboard" view (`All & Groups` →
**All Seats** card, patch `fire-button` with params `red-button` /
`green-button` / `shutdown-button`), toggling a promoted **live-param
checkbox** does not take effect: the server rejects it with
**"That live parameter or target is unavailable."** — confirmed via an alert
(see Fix #2 below). Sliders and the **"Send all"** button (`replay_live_params`)
on the *same card* work. Surfaced 2026-07-24 while hardware-verifying thread
`42-node-logging` on Ciro Toast (seat 1). **Thread 42 / logging is complete and
hardware-verified — this is a pre-existing dashboard live-control defect.**

> Handoff written for a fresh, more capable context. The paradox below
> (§"The paradox") is unresolved and is the crux. **Do not re-derive from
> scratch — start at "Do this first" and instrument, don't reason.**

---

## Current working-tree state (UNCOMMITTED — inherited by the next session)

Two edits to `dashboard/static/js/facilitator.js`, both correct standalone,
**keep them**, but neither fixes the bug:

1. **Line ~312** matcher broadened
   `input[type="checkbox"][data-automated="true"]` →
   `input[type="checkbox"][data-live-param]`, so a *plain* live-param checkbox
   sets `interacting = true` on pointerdown and survives the heartbeat
   `renderCards()` (line ~366) through the pointerup→change cycle. Effect: the
   checkbox now visibly *flashes* on click (gesture survives) instead of doing
   nothing — but it then **reverts** because the value is never recorded
   server-side. Comment at ~316 updated (names thread 43).
2. **New `ws.on("error", …)`** handler (after the `connection` handler, ~line
   285) — the facilitator view had **no error handler at all**, so every server
   `ws_error` (`{type:"error"}`, server.py `ws_error` ~1474) was silently
   buffered by `ws.js` and never shown. This is why the rejection looked like
   "nothing happened, no error". Now `alert()`s the message like
   `dashboard.js:211`. **This is what surfaced the "unavailable" message.**

`server.py` is UNTOUCHED. No other files changed for thread 43 (the many other
modified files in `git status` are the uncommitted-but-pushed... no — thread 42
was committed+pushed as `d1ba842`; anything else modified predates this bug).

## The paradox (the crux — resolve this)

The rejection comes from `server.py` `set_live_param` (~339):

```python
elif kind == "set_live_param":
    scope = str(data.get("scope", ""))                         # All card → "all"
    declaration = self.live_param_declaration(data.get("name"))# name = "green-button"
    cleaned = self.clean_editor_value(declaration, data.get("value"))  # value = 1
    seats, selector = self.live_param_target(scope, data.get("id"))
    if declaration is None or cleaned is None or seats is None:
        await self.ws_error(ws, "That live parameter or target is unavailable.")
        return
```

For an **All-Seats toggle of green-button = 1**, every branch should be
non-None, yet one is None at runtime:

- **`declaration`** — client sends `name = input.dataset.paramPath =
  declaration.identity`. Server `live_param_declaration(name)` matches
  `item["identity"] == name` over `live_control_declarations()`, whose identity
  is `manifest.qualify_param(item)`. **Verified on disk:** `qualify_param` of the
  flat `fire-button` params returns exactly `"green-button"`/`"red-button"`/
  `"shutdown-button"` (reproduced with `python/manifest.py` load of
  `patches/fire-button` — load error None, all `dashboard: True`). The client's
  `live_controls.declarations` come from the *same* `live_control_declarations()`
  via `public_state()` (server.py ~1452). So identities should be identical →
  declaration found. (Ruled-out-on-disk, NOT confirmed at runtime.)
- **`cleaned`** — `clean_editor_value` (~1518) returns None only for
  wrong-type / bool / non-integer / out-of-range. Checkbox sends numeric `1`
  (facilitator.js send(): `input.checked ? 1 : 0`), int, in [0,1] → returns 1.
  **BUT** if the value ever arrives as JSON `true` (Python `bool`),
  `isinstance(value, bool)` → return None. Worth verifying the *actual wire
  value and its type*.
- **`seats`** — `live_param_target("all", None)` returns
  `(list(self.state.seats.values()), "all")` — never None for scope "all" (11
  seats exist). Only None if `scope` is NOT `"all"/"seat"/"group"`, or a
  seat/group id fails to resolve.

**`replay_live_params` ("Send all") works** because it iterates the server's
*own* `live_control_declarations()` identities and calls `set_param` directly —
it never does the client-name lookup, the `clean_editor_value` step, or
`live_param_target`. So the failing branch is one of those three, exercised
only by `set_live_param`.

Running server confirmed: **PID 576**, `dashboard/server.py --host 0.0.0.0`,
cwd `/Users/bob/repos/bopOS`, HTTP/ws on **localhost:8080**, state
`dashboard/installation.json` (`params_patch = "fire-button"`; seat 0 → Finn
`2c:cf:67:b3:0a:58`, seat 1 → Ciro `dc:a6:32:25:9b:28`). So it reads the same
files analysed above — which is *why* the paradox is sharp.

## Do this first (instrument, don't reason)

The disk code says it can't reject; it does. Get the runtime truth in one shot:

1. **Make the rejection self-describing.** Temporarily change the `set_live_param`
   error to report the culprit, e.g.:
   ```python
   if declaration is None or cleaned is None or seats is None:
       await self.ws_error(ws, f"unavailable: scope={scope!r} name={data.get('name')!r} "
           f"value={data.get('value')!r}({type(data.get('value')).__name__}) "
           f"decl={declaration is not None} clean={cleaned is not None} seats={seats is not None}")
       return
   ```
   Restart the dashboard (it's `server.py`, needs a process restart — the user
   restarts it; or coordinate), **hard-reload the browser** (Cmd-Shift-R, the JS
   fixes are static assets), toggle green-button on **All Seats**, read the
   alert. That names the None branch and shows the exact scope/name/value/type.
   Alternatively/additionally: read the raw outbound ws frame in the browser
   DevTools → Network → WS to see precisely what the checkbox sends.
2. From the culprit, the fix is likely small and one of:
   - **value-as-bool** → coerce or accept in `clean_editor_value`, and/or fix the
     client to send a number (it appears to already);
   - **scope wrong/empty** → fix how the checkbox's `data-live-scope` is threaded
     (`scopeAttrs`, facilitator.js ~171) or the payload build in `send()` (~508);
   - **name/identity mismatch at runtime** → diff the client's
     `installation.live_controls.declarations[].identity` against the server's
     `live_control_declarations()` identities for `fire-button` (a
     stale/transformed broadcast, or a qualify_param divergence).
3. Then **live-confirm on hardware** if the rig is up (toggle All-Seats /
   Seat-1 → watch `/…/p/*` in the Outgoing monitor AND a new line append in
   Ciro's log), and write a **durable `tests/` Playwright verify** (NOT a tied
   guard, per the 2026-07-23 ruling) that clicks a live checkbox under simfleet
   heartbeat cadence and asserts (a) the `/…/p/<name>` wire message and (b) the
   `installation.json` seat-param update. The heartbeat cadence is the essential
   repro condition — a static page won't reproduce the re-render race that Fix #1
   addresses, and may or may not reproduce the server rejection (instrument to
   learn whether the rejection is state-dependent). Commit when green.

## Evidence chain — everything BELOW the browser control is proven healthy

Observed live 2026-07-24, Ciro on seat 1, via the `tmux 0:0.0` ssh pane:

- `nodelog` appends correctly (direct `/log` injects to Ciro `:7770`: 6→8
  lines). `/log` handler fine. USB mounts at `/media/bopos-usb`; logs in
  `/media/bopos-usb/bopos-logs/`. The `fire-button` PD patch →
  `to-bopos-log` → `/log` logs correctly.
- **Wire routing to Ciro works:** injecting `/all/p/green-button 1` AND
  `/1/p/green-button 1` straight at Ciro `:6660` both appended
  (`selector_matches("1", 1)` true; Ciro store `assignment=[1,"Seat 1",…]`,
  `groups=[0]`). So the node, patch, routing, and logging are all correct.
- **Ruled out — edit mode:** in Patch Edit the Patch-tab boxes are
  `set_editor_param` → selector `0` (edit instance) which seat-1 Ciro correctly
  ignores; and `set_param`/`set_live_param` are in `edit_blocked_mutations`
  (server.py ~279) so they error *visibly* in edit mode. User was in live fleet
  mode.
- **Ruled out — supervisor_lock:** `set_live_param` is serialized (server.py
  ~266), but so is `replay_live_params`, and **"Send all" emits fine** — so the
  lock is NOT stuck and the serialized path + `set_param` send are healthy.
- **Ruled out — the OSC monitor:** it works (shows `/sync/ping`,
  `/all/os/master`, `/all/os/mute`, and "Send all" `/N/p/*` to
  `255.255.255.255`). Its `!/sync` filter does not hide `/p/*`.
- **CONFIRMED — server rejection:** the alert (Fix #2) shows exactly
  "That live parameter or target is unavailable." → `set_live_param` reaches the
  server and is rejected at the three-way guard. This is the whole ballgame.

## Scope / guardrails

- Dashboard JS/Python + a `tests/` verify only. **No `.pd` edits.**
- Keep Fixes #1 and #2. Do not disturb `set_editor_param` or
  `replay_live_params` (both work).
- Remove any temporary debug error string before tie.
- CLAUDE.md Playwright gotchas apply hard here (heartbeat re-render instability
  is literally the subject): one-shot `page.evaluate` reads, `state="attached"`
  waits, gather rects in one scroll state.

## Two small loose ends from the 42 session (not this bug)

- **`LOG_DESTINATION` persistence:** `grep LOG_DESTINATION ~/bopos.config` on
  Ciro was empty though logs correctly land on USB — confirm the usb choice is
  persisted so a cold boot doesn't fall back to SD. NB: `set_log_config` is a
  serialized mutation too; if it was ever the victim of this same reject/lock
  behaviour it may never have persisted — re-check after 43 is fixed.
- **Stranded internal-SD logs:** old `green`/`red` files in Ciro's
  `~/bopos-logs/` from before the destination switched to USB. Harmless cleanup.
