# Ground truth — bopOS↔patch seam council (2026-07-10)

Verified facts about the current state, with where each was established. Where
the seed (`seed.md`) and this file disagree, this file wins. Facts marked
**[contract-text]** are ratified spec that may not be implemented yet; facts
marked **[testimony]** are Bob's statements about deployed installations, not
verifiable in this repo — treat as requirements, not code facts.

## The contract

1. `docs/OSC-CONTRACT.md` v1.0, ratified 2026-07-07 (council record in
   `.lore/items/2026-07-07-osc-schema-council/`). Grammar:
   `/<selector>/<plane>/<member>` controller→fleet, `/<plane>/<member>`
   node→controller. Framework planes (`/os`, `/io`, `/sync`, `/cue`, `/pt`)
   are a **closed set**; `/p/*` is open and **entirely patch-owned** — "the
   only place output semantics live" (§3).
2. §1 currently assigns to the framework "the sync/cue/spatial control plane"
   and to the dashboard "control-plane state, spatial math, and scene
   authoring". §4 blesses dashboard-computed per-device `/p/gain` as "the
   correct first implementation… fine ≤ ~12 nodes", with broadcast `/pt` +
   node-side falloff only "at fleet scale". **This framing was overturned in
   principle on 2026-07-10** (`.notes/spatial-redesign-plan-2026-07-10.md`)
   but no amendment is written — amending §1/§4 is part of this session's
   output space.
3. §14 ("rejected by design") includes: capability broadcast/registry, runtime
   param introspection, telemetry streaming, envelope-carrying cues, per-device
   spatial gain broadcast at fleet scale, per-host branching in semantics.
4. Full-state idempotent law (§4): every fleet command is full-state; resend
   always safe. Broadcast is scarce/lossy (WiFi, no MAC-layer ACK) — reserved
   for low-rate, idempotent, genuinely one-to-many messages.
5. PD's OSC floats are 32-bit (§12, CLAUDE.md): >6 significant figures must
   cross as strings; absolute time never enters an engine.

## Master gain — the type case of dashboard-side enactment

6. There is **no master-gain message on the wire.** The dashboard composes it:
   `dashboard/osc_bridge.py:135-144` (`send_device_param`) multiplies the
   stored per-device mix by `state.data["master"]` and sends the *product* as
   the device's volume param (`/<id>/p/<name>`). `resend_volumes`
   (`osc_bridge.py:146-153`) re-sends every device's volume when master moves.
   A patch never learns the master value; a device offline during a master
   move converges only via the params catch-up push (`osc_bridge.py:237-241`).
7. The volume param is resolved by `volume_param()` (`osc_bridge.py:44-54`):
   the declared param with `role:"volume"`, else the param literally named
   `gain`, else None. `role` (`"volume"`, `"meter"`) was ratified 2026-07-08
   (contract §8).

## Facilitator surface

8. `/facilitator` is implemented and tied (2026-07-08):
   `dashboard/static/facilitator.html` renders per-device **volume cards**
   only, plus one **Master** slider and a **SILENCE ALL** button (spam-safe
   `/all/os/mute`). The control set is **fixed in code** — there is no
   mechanism to promote arbitrary patch params or bopOS commands onto it.
9. The ratified facilitator proposal
   (`.lore/items/2026-07-08-facilitator-view-proposal/content/proposal.md`)
   includes a **scope guard: no admin verbs, no assignment** on the
   facilitator view. The seed asks for bopOS commands (shutdown, reboot,
   update patch) on the facilitator surface — **in tension with that guard**;
   the council should address it, Bob arbitrates at ratification.

## How values actually reach a patch

10. Dashboard→fleet traffic is broadcast on **6660**. Both PD
    (`pd/bopos.osc.pd`) and `helper.py` (bind at `python/helper.py:718`) listen
    on 6660 (SO_REUSE*; broadcast datagrams reach both sockets — the
    audition-rig spike verified this port-sharing works on Linux for
    broadcast+selector addressing only). PD routes on the selector; **a patch
    consumes a `/p/*` param only if it has a receiver for it — nothing enforces
    or verifies consumption.** [contract-text §8: "the launcher validates
    declared params before start" — not verified as implemented.]
11. helper→PD localhost is **6661** (`helper.py:43` connects to
    `127.0.0.1:6661`; `/os/load` replies arrive in PD as `/load <key>
    <values…>`). PD→helper is 7770 (PD forwards `route helper` traffic).
    The synced `/cue` fires from helper to the engine on localhost with only
    relative time (§3.1); helper slews the offset.
12. Mute is the one framework-owned output control (`§6`): `helper.py:400-419`
    (`set_mute`) tries `amixer sset <control> mute` (transport-level, below
    patch logic); if no mixer control works it **falls back to stopping the
    engine** (`stop-engine.sh`, restart on unmute). So mute is independent of
    the patch when a mixer exists, and engine-lethal when not.

## Identity, engine model, positions

13. Identity is **per device**: one `uid` (MAC on Pis), one `id`, one `name`.
    Heartbeat `/hb <uid> <id> <version> <engine-alive 0|1> [rssi]` carries a
    **single engine-alive bit** (`§6`).
14. `/all/os/assign <uid> <id> <name> [posx posy pos2x pos2y]` — **the wire
    and node persistence already accept two positions** (`helper.py:491-519`
    parses and persists up to 4 floats). Positions are consumed
    dashboard-side; the node stores but does not use them. The `pos2` slots
    are a Belief-era remnant matching the two-elements-per-device pattern.
15. Engine launch is **one instance per device**: `bash/start-engine.sh`
    launches a single `pd -nogui -jack -open <patch>/<entrypoint>` (manifest
    `engine`/`entrypoint`), writes one `engine.pid`. Localhost ports
    6661/6662/7770/8880 are singletons — a second engine instance on the same
    device would collide with all of them as built.
16. The patch manifest `bopos.patch.json` (§8) declares `engine`, `entrypoint`,
    `params` (name/type/min/max/default/group, optional `role`), `caps`,
    `slots`. helper serves it verbatim on `/os/params`; the dashboard renders
    controls from it. There is **no facilitator/promotion field**.

## Spatial state

17. The `spatial-0` engine (dashboard-computed gain × single point, streamed
    into the volume param at ~25 Hz) was built 2026-07-09 and **reverted**
    2026-07-10 (revert commit `dcce8df`; recoverable at `0ce8821`; record in
    `.loom/tied/spatial-0-engine/`). The falloff curves (`linear`/`smooth`/
    `gauss`) are salvage.
18. The replacement draft
    (`.lore/items/2026-07-10-spatial-points-node-side/content/draft.md`):
    dashboard broadcasts point geometry (`/pt`, arbitrary count, each point =
    x,y + radius + falloff, no level); each device decomposes all points
    locally; helper computes a proximity scalar 0→1 and delivers it to the
    patch as a named value; the patch maps it wherever it likes, upstream of
    its own volume. Open questions listed in the draft §8 (wire encoding
    per-point vs per-frame, receiver naming, manifest declaration y/n, raw
    distance). This draft is an **input** to this council, not a settled
    design.

## Test/dev infrastructure

19. `tools/simfleet.py` (841 lines): N fake devices speaking the real protocol
    (heartbeats 5550, commands 6660). House rule (CLAUDE.md): new protocol
    features land in the simulator in the same stitch. Dashboard verifies run
    headless-Chromium from the `~/.venvs/bopos` venv.
20. Clock-sync software is complete (§3.1 pinned; dashboard is leader;
    `tools/sync_measure.py` is the jitter harness); only the hardware run
    remains.

## Deployed reality [testimony]

21. Belief System ran **five moving points** and **two positioned patch
    instances per Pi** (L/R channels, each with its own position). Kite Choir
    (current) and Playable Streets (upcoming) are stereo devices — one
    positioned element per device — but multi-element is wanted as a future
    capability, possibly restricted to N instances of the *same* patch if that
    simplifies.
22. Standalone operation (network removed after setup) is first-class and
    active installations use it (§5). macOS is the likely
    installation/performance platform for the audition rig even though dev is
    Linux-first (CLAUDE.md).

## House rules binding any design

23. Agents never edit `.pd` files — PD receiver conventions and final
    spellings are **Bob's co-design at ratification**, so designs must flag
    them, not fix them.
24. Migration discipline (§13): zero port changes, no reflash, no flag day;
    transition aliases live exactly one release.
