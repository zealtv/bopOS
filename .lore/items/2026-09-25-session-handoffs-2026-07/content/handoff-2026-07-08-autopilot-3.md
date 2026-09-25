# Handoff — 2026-07-08 session 3 (post-ratification)

## State of play

Bob ratified the manifest `role` field ("role: volume works / role: meter is
consistent"), which unblocked both waiting dashboard stitches — and with them
the **entire dashboard thread: all four phases are now tied**. The
`/facilitator` view and the live-meters surface are built, browser-verified,
and documented in contract §8/§11 (additive). The `dashboard` goal stitch is
`.waiting` only on its own tie condition: Bob using it as the daily driver on
a real installation. Bob's scene-language design brief (Ableton clip grid,
follow actions, the language requirements, node-side spatial primitives) is
captured verbatim in `scene-language-spec/bob-design-notes-2026-07-08.md` —
that stitch is **co-design with Bob, never solo**. The audition-rig
port-sharing spike passed on Linux. `dashboard/README.md` is the quickstart
Bob asked for (server + simfleet + both URLs).

**Not yet pushed** — the branch is 19 commits ahead of origin/main
(this session's 5 plus earlier unpushed work). Bob still needs to `git push`.

## Tied / progressed this session

- **facilitator-view** — `bbf42fb`. `/facilitator`: volume cards
  (role→gain→status-only resolution), VCA master (stored mix × master on the
  wire, re-send on master moves), SILENCE ALL ⇄ RESUME over `/os/mute`,
  Sound check (`/all/aloha`), presets (`{master, devices:{uid:{param:v}}}`
  in installation.json, save tech-side, load both views), PWA
  (webmanifest/icon/apple meta), declaration catch-up push. `role` field:
  contract §8 + manifest.py validation + default patch marks `gain`.
  simfleet grew `--manifest`. 19-check verify.
- **sensor-data-view** — `2d0c721`. Outbound `/<id>/p/<name>` meters:
  helper.py `METERS`/`METER_INTERVAL` republisher (registry: rssi,
  cpu_temp), dashboard runtime-only meters store (never in presets/durable/
  push-back), declared meters as live bars, undeclared inbound → §8 badge,
  5 Hz browser throttle, simfleet random-walk emission, default patch
  declares a `level` meter. 9-check verify + both regressions.
- **dashboard-2, dashboard-4 tied; dashboard goal → `.waiting`** — `c323342`
  (real-rig adoption is the tie condition, noted in the goal stitch).
- **audition-0-port-spike** — Linux half done, `.waiting` on macOS. Shared
  6660 **works** on Linux with stock PD netreceive (SO_REUSEADDR); one
  broadcast → every instance replies. Unicast to a shared port reaches
  exactly ONE process → audible instances must use broadcast+selector only.
  `results.md` has the matrix + a one-command macOS test for Bob.

## Waiting on Bob (nothing blocks agent work)

1. `git push` (19 commits).
2. **macOS spike run** — one command, bottom of
   `.loom/threads/audition-rig/audition-0-port-spike.waiting/results.md`.
3. **PD edits list** (`.loom/tied/osc-schema-contract/pd-edits-for-bob.md`)
   plus one new item: the default patch declares a `level` meter — PD sends
   `/<id>/p/level <v>` to 5550 (few Hz) to light it up on real nodes.
   Related spike finding: legacy bopos.osc.pd errors on the `all` selector
   (`couldn't convert all to float`) — helper.py owns `all`; harmless today,
   worth folding into the §13 migration notes.
4. **Real-rig adoption** of the dashboard (ties the goal) + iPad touch pass
   on `/facilitator`; per-stitch hardware checks as listed in each tie.
5. **Scene-language co-design session** — when Bob wants it; his brief is in
   the stitch, deferred by his own note until after rollout needs settle.

## Recommended next (fresh session)

- **`clock-sync`** — now the head of the critical path.
- Or free-floating: `sample-distribution` (builds on `/os/fetch` + dashboard
  assets), `pi-zero-performance` measurement half (script + docs; hardware
  verification stays flagged for Bob), `patch-workflow-friction` (dashboard
  checkbox done; remaining items are template repo + docs).

## Gotchas (healed where noted)

- Killing the `pd` wrapper PID leaves the real `pd` alive (watchdog/fork) —
  the spike's second run found the first run's instances still listening.
  Healed: spike_pd.sh now warns; don't blanket-pkill on Bob's machines.
- CLAUDE.md thread-ordering section updated to post-dashboard reality
  (healed).
- The dev venv lives in this session's scratchpad; rebuild per CLAUDE.md
  (pip works on this box). All three dashboard verify suites pass as of
  `2d0c721`.

## Usage at stop

Weekly **Fable at 87%** (Bob authorized up to 95 for this run; stopped early
because every remaining loose end is a multi-hour build). Resets
**2026-07-13T09:00Z**. Session cap 59%, weekly all-models 53% — the weekly
Fable cap is the binding one for any follow-on session before Monday.
