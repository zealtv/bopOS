# Facilitator view — design proposal (RATIFIED 2026-07-08)

**Bob's ruling (2026-07-08): "role: volume — works."** Q1's `role` marker
approved (jointly with sensor-data-view's `role: "meter"`); Q2–Q6 stood
unopposed as recommended. Built the same day — build record in the tied
stitch's `design-decisions.md`.

Stitch: `dashboard/dashboard-2-spatial-facilitator/facilitator-view`.
Source design: `.notes/dashboard-development-context.md` §9 (pre-contract).
This proposal reconciles that sketch with the ratified contract era and asks
the questions the decision gate exists for. Nothing here is built.

## What stays exactly as the design doc sketched it

- `/facilitator` route on the same server, same websocket, thin view
- One full-width card per **assigned** device: name, big touch slider,
  status dot (green/gray, no technical detail)
- Master volume row + Silence All + Start All + preset picker pinned at
  the bottom
- Dark theme, portrait and landscape, no logins
- PWA manifest so add-to-home-screen launches fullscreen on iPad

## Q1 — Which parameter is "the volume"? (the post-contract question)

The old design hardcoded `gain`. Params are now manifest-declared, so the
volume card needs a defined mapping.

**Proposal:** a patch may mark one declared param `"role": "volume"` in
`bopos.patch.json`. Fallback when absent: the param literally named `gain`;
if neither exists, the device card shows status only (no slider), badged
"no volume param". The manifest validator warns when a patch declares
nothing usable as a volume.

- Pro: engine-neutral, no wire change, degrades honestly.
- Alternative rejected: driving `amixer` via a new `/os/volume` verb —
  system volume is a hammer (clicks, no per-patch taper) and a contract
  revision for something the param plane already does.

## Q2 — Master volume semantics

**Proposal: VCA-style proportional scale, dashboard-side.** Each device
keeps its per-device volume `v_i` (the mix, set per-card or by preset);
master `m` (0–1) scales the *sent* value: `/id/p/<volume> v_i × m`. The
mix survives master moves; master 1.0 is "as mixed". Stored in
`installation.json` as `master` + the per-device values.

- Alternative rejected: absolute (master writes every fader) — one nudge
  destroys the spatial mix a technician balanced.
- Note: facilitator cards show `v_i` (the mix position), not `v_i × m`,
  so a facilitator can't tell master from mix by looking at one card.
  Chosen anyway for simplicity; flag if you want the sent value shown.

## Q3 — Silence All

The design doc said "sets all gains to 0". **Proposal: use `/all/os/mute 1`
instead** (the ratified spam-safe safety verb — helper-owned amixer mute,
works even with a crashed engine), with the button flipping to RESUME
(`mute 0`). Gains-to-zero destroys the mix and depends on a live engine;
mute is instant, reversible, and already what the tech dashboard's MUTE ALL
does — one behaviour, two buttons.

## Q4 — Start All

Design doc: aloha to all (audio confirmation). Aloha is legacy PD-side and
already on the tech dashboard. **Proposal:** keep `/all/aloha 1` for now,
renamed on the button as "Sound check"; revisit once the §2 identify-chirp
PD edit lands (then `/all/os/identify` gives a helper-owned chirp that
works per-device too). No new wire.

## Q5 — Presets

**Proposal (data model):**

```json
"presets": {
  "morning-quiet": {
    "master": 0.5,
    "devices": {"<uid>": {"gain": 0.3, "echo": 0}}
  }
}
```

- Partial state: only the params a preset names are touched; positions and
  assignments are never part of a preset.
- **Save** (tech dashboard only): captures current params of all assigned
  devices + master, prompts for a name, overwrite allowed with confirm.
- **Load** (both views): applies master, then per-device `/id/p/<name>`
  sends; devices offline at load time get the values on their next
  heartbeat re-declaration (same catch-up path params already use).
- Facilitator sees a picker with preset names only — no save, no delete.

## Q6 — What facilitators can NOT do (scope guard)

No reboot/shutdown/update, no patch switching, no assignment, no positions,
no per-param access beyond the volume card. The view is: volumes, master,
silence/resume, sound check, presets. Everything else stays in `/`.

## Deltas from the pre-contract design doc (for the record)

1. Volume mapping is declared, not hardcoded `gain` (Q1).
2. Silence All is mute, not gains-to-zero (Q3).
3. No service worker / offline shell in v1 — it's a live-LAN control
   surface; offline it's useless anyway. PWA manifest only.
4. Preset model gains `master` and an explicit `devices` nesting (Q5).

## Verification plan (once ratified)

Simfleet + headless browser like the other dashboard stitches, plus a
manifest-without-volume-param case; real-iPad touch pass is Bob's.
