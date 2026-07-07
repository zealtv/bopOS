# dashboard-1-core — deltas from the design doc (2026-07-08)

`.notes/dashboard-development-context.md` predates the ratified contract
(`docs/OSC-CONTRACT.md` v1.0) and the node-side work now landed (hb-identity,
assign-persistence, patch-manifest). These deltas supersede the doc where they
conflict; everything else in the doc stands.

## 1. Identity comes from the heartbeat — no IP correlation

The doc's §10 "challenge" (heartbeats carry no identity; correlate by source
IP / ARP) is obsolete. helper.py now sends
`/hb <uid> <id> <version> <engine-alive> [rssi]` every 10 s (2 s while
unassigned). The dashboard keys everything by **uid** (== MAC on Pis), exactly
what `installation.json` wanted anyway. Source IP is recorded per device as a
return path only. Legacy `/rpt … hb` messages are ignored for liveness (they
carry no uid; PD's version report is dead wiring anyway — see
`pd-edits-for-bob.md` observations). `engine-alive` and `rssi` are displayed:
"box up, engine crashed" vs "box gone" are the two mid-show failures an
artist must tell apart (contract §6).

Consequence: a Pi must be running current bopOS (git pull, no PD edit needed)
to appear in this dashboard. That is the intended migration path — the
stitch's "unmodified Pis" bar predates the contract and is met in spirit:
no reflash, no PD edit, no port change; just the normal `/os/update` pull.

## 2. Controls render from the declaration (patch-manifest landed)

The stitch caveat asked for a generic parameter-list component; the contract
work it anticipated has landed, so phase 1 goes straight there:

- On device select (and on first online), the dashboard sends
  `/<id>/os/params` and renders controls from the `/os/params <json>` reply:
  type `f`/`i` with min/max/default → slider (int step for `i`; 0/1 int
  range → toggle), type `s` → text input. `group` clusters controls.
- Empty reply (no manifest) → the legacy four (gain, gain2, backing, echo)
  with a visible **"undeclared"** badge (contract §8's fail-loud).
- Param values go out as `/<sel>/p/<name> <value>`.

## 3. Wire compatibility matrix (until Bob's PD edits land)

One place in `osc_bridge.py` (`LEGACY_COMPAT = True`) controls the
transitional spellings; each is one line to delete later:

| action | v1 form sent | legacy form also sent while LEGACY_COMPAT |
|---|---|---|
| param value | `/<sel>/p/<name> <v>` | `/<sel>/<name> <v>` for gain/gain2/backing/echo only (PD `route p` not landed yet) |
| reboot/shutdown/update/getsamples/patch/addpatch/pullpatch/restart-engine | — (node has no `/os/*` admin listener yet; contract §7 rename pending node-side) | `/<sel>/helper/<verb>` |
| aloha (announce request) | — | `/<sel>/aloha 1` |
| identify / mute / ping / params / report / assign / store / load | `/<sel>/os/<member>` (helper.py answers today) | — |

When the node-side §7 verbs land, the admin row flips to `/os/*` in one
switch. The dashboard never sends `/helper/*` and `/os/*` duplicates for the
same verb — exactly one spelling per verb per era.

## 4. Scope additions (cheap now, contract-backed)

- **Master mute** button: `/all/os/mute <0|1>` — safety-critical, node-side
  implemented, spam-safe (§6). The one output control the framework owns.
- **Identify** button per device: `/<id>/os/identify` (locate on install day).
- **Report** panel per device: `/<id>/os/report` facts rendered in the
  detail view (engine, has_i2c, has_wifi, audio_channels, screen, patch,
  uptime, git_rev, update_model, contract_version).

Facilitator view, spatial map, presets, assignment flow: still phases 2/3,
not here.

## 5. Environment

Dev/test venv (fastapi, uvicorn[standard], python-osc, websockets) lives at
`<session-scratchpad>/dashvenv`; this box has pip 24.0 (the "laptop has no
pip" note in the old stitch was about a different machine or stale — wheel
tricks not needed here). `dashboard/requirements.txt` is the durable record.
Verification target: `tools/simfleet.py --target 127.0.0.1`, which speaks
every row of the matrix above.
