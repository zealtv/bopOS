# facilitator-view — build record (2026-07-08)

Built per the ratified proposal (lore `2026-07-08-facilitator-view-proposal`;
Bob's ruling: `role: "volume"` — "works", no objection to Q2–Q6).

## What was built

- **`/facilitator`** route on the same server/websocket: one card per assigned
  device (name, status dot, big touch slider), master row, SILENCE ALL ⇄
  RESUME (`/all/os/mute`), Sound check (`/all/aloha 1`), preset chips. Dark,
  portrait+landscape, PWA (`manifest.webmanifest` + `icon-180.png` +
  apple-touch meta) so add-to-home-screen goes fullscreen on iPad.
- **`role` manifest field** (shared with sensor-data-view's `role: "meter"`):
  contract §8 note, `python/manifest.py` validation (role must be a non-empty
  string; at most one `role:"volume"`; `warnings()` advises when nothing is
  usable as a volume), `patches/default/bopos.patch.json` marks `gain`.
- **Volume resolution** (`osc_bridge.volume_param`, mirrored in
  `facilitator.js`): role `volume` → literal `gain` → none (status-only card
  badged "no volume param").
- **VCA master (Q2):** stored params are the *mix*; the wire gets
  `mix × master` for a device's volume param only (`send_device_param`).
  Master moves re-send every assigned device's volume (`resend_volumes`).
  Master persists in `installation.json`.
- **Presets (Q5):** `presets.<name> = {master, devices: {uid: {param: value}}}`
  in `installation.json` (so they ride venue save/load for free). Save is
  tech-dashboard-only (prompt + overwrite confirm); load from either view.
- **Catch-up push:** on every `/os/params` declaration merge for an assigned
  device, the dashboard pushes its stored params back (scaled volume, meters
  excluded) — this is how a device offline during a preset load converges
  when it reappears.

## Deltas / judgment calls beyond the proposal text

1. Broadcast `/all/p/<name>` sends from the tech dashboard bypass master
   scaling (per-device volume params can differ; broadcast is a tech power
   tool). Documented here rather than guessed at wire level.
2. simfleet gained `--manifest <path>` so the no-volume-param case is testable
   headless (protocol features land in the simulator in the same stitch).
3. Facilitator status dot: green = online *and* engine alive (a crashed engine
   can't sound; "no technical detail" means no amber state either).
4. `dashboard/README.md` added (Bob asked for fire-it-up instructions).

## Verification

`verify_facilitator.py` — 19 checks, all passing: manifest validator units,
sliders render, PWA endpoints, wire-level master scaling (0.8 × 0.5 = 0.4 seen
by simfleet), mute on/off, aloha, preset save (tech) → chip → load
(facilitator) with mix restore + scaled re-send, scope guard (no admin verbs in
the view), persistence of master + preset, and the no-volume-manifest
degradation. Regression: tied `verify_patch_install.py` still passes.
Screenshots `01`–`03` in this stitch. Real-iPad touch pass is Bob's.
