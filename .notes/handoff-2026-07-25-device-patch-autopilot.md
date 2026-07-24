# Handoff — device-scoped patch control, bite 2 + design proposals (2026-07-25)

Autopilot session (Opus 4.8), green-lit by Bob to: finish thread-37 bite 2 ready
for hardware, reparent the generator affordance in ahead of presets, and write
HTML design proposals for the four widened-scope items. Budget rule this session:
**5-hour session window only, disregard weekly.**

## State of play

**Device-scoped patch control is now operable end to end in software.** An
operator can pin a patch to one seat-bound device from the Patches tab; the
device converges on its own generation track while the rest of the fleet holds,
a fleet deploy leaves pins intact, a roster pin marker shows it, and "follow
fleet" clears it. All verified headlessly (real dashboard + simfleet +
Playwright, 14/14). Real-Pi/PD behaviour is the one remaining check — recipe
below. The four remaining thread-37 design items (generator affordance, set-patch
hand-off, live-control placement, Control-tab rename) are written up as one
ratification-ready proposal doc and are `.waiting` on Bob.

## Tied this session

- **`2-device-patch-targeting`** (thread 37 bite 2) — commit `9c3f6e1`. Server
  per-device convergence track + `set_device_patch`/`clear_device_patch`, fleet
  deploy respects pins, target picker + roster pin marker + follow-fleet, and
  `tests/verify_device_patch_targeting.py`. Design rationale in the tied stitch's
  `design-per-device-convergence.md`; full detail in its `progress.md`.

## Commits (all on `main`)

- `9c3f6e1` — bite 2 implementation + verification (tied stitch).
- `f502b79` — reparent stitch 38 → `37/3-generator-affordance-design`; scaffold
  design stitches 4/5/6.
- `5156eef` — the four design proposals + `control-surface-proposals.html`;
  stitches 3–6 marked `.waiting`.
- (pending, this note) — CLAUDE.md heals + this handoff + memory pointer.

## Waiting on Bob (ratification gates)

All four are one artifact, section-anchored, each with a `proposal.md` in its stitch:
**https://claude.ai/code/artifact/6f9c395e-f7b0-43f3-b132-dbe1ebc2f780**
(source of record: `.loom/threads/37-device-scoped-patch-control/control-surface-proposals.html`)

| Stitch | Proposal | Recommendation in one line |
|---|---|---|
| `3-generator-affordance-design.waiting` (#p1) | generator affordance | `value ▸ gen` mode switch per numeric row; inline drawer = extracted automation-2 builder. **Bob wants this ahead of 41.** |
| `4-set-patch-handoff-design.waiting` (#p2) | Set patch… hand-off | Device-tab button → pre-scoped picker; humane bind-to-seat for standalone nodes. |
| `5-live-control-placement-design.waiting` (#p3) | live-control placement | one reusable `ControlSurface` component; collapsible under Device diagnostics (subsumes Seats-detail overflow). |
| `6-control-tab-rename-design.waiting` (#p4) | Control tab rename | Dashboard → Control; target filter (all/groups/seat); cues/master strip; reserved Presets shelf. |

Each proposal ends with the specific open questions Bob must settle. **41
(preset primitive) should follow the generator-affordance ratification**, since a
preset captures "values or generator specs" and needs that affordance to exist.

## Recommended next stitch

Bob ratifies `3-generator-affordance-design` (his stated priority), then it
becomes an implementation stitch out of thread 37; `5` (the shared component) is
its natural predecessor if Bob wants the component extracted first. Everything
else in thread 37 stays gated on Bob.

## Hardware verification check (Finn Jet + Ciro Toast) — for Bob or a live rig

Software gates pass; this is the real-Pi/PD adoption check the sim can't do.
Two-device rig: **Finn Jet** (fleet node) + **Ciro Toast** (standalone). See the
`finn-ciro-test-rig` memory. bop000 dev Pi access is in the `bop000-dev-pi-access`
memory.

1. **Bring up the dashboard against the real fleet** (not simfleet) and confirm
   both Pis appear online and **seat-bound** in the roster. A device must be
   bound to a seat to be pinnable (OSC v1.5 targets content by seat) — bind Ciro
   Toast to its own lone seat if it isn't.
2. **Fleet baseline:** Patches tab → target **Whole fleet** → pick a patch →
   **Deploy as fleet patch**. Confirm both Pis converge (both rows `current`) and
   are audibly running that patch.
3. **Pin one device:** Patches tab → target **Ciro Toast** → pick a *different*
   valid patch → button now reads **Pin to device** → confirm. Expect: Ciro
   converges and restarts to the pinned patch (audibly the new patch); Finn stays
   on the fleet patch, untouched. Ciro's row shows the 📌 pin marker; the
   fleet-patch summary shows "1 pinned".
4. **The crucial property — pin survives a fleet deploy:** re-deploy the fleet to
   a third patch (target Whole fleet). Expect: Finn switches to the new fleet
   patch; **Ciro stays on its pinned patch** (still 📌, still `current` against
   its pin) and does **not** switch. This is the correctness guarantee simfleet
   proved; confirm it audibly on hardware.
5. **Follow fleet:** Devices tab → select Ciro → patch diagnostics → **Follow
   fleet patch** → confirm. Expect: pin marker clears; Ciro converges/restarts
   back to the current fleet patch, matching Finn.
6. **Persistence:** restart the dashboard process; confirm a pin set in step 3
   (before clearing) is remembered across restart (durable UID registry) — i.e.
   re-pin, restart dashboard, verify Ciro still reads pinned.

Watch for: engine restart timing on a cold Pi (the sim uses a 2 s stub; real
JACK/PD restart is longer — the badge should pass through `switching` then
`current`, not `failed`/`timeout`); and that a pin restart doesn't disturb the
other device's audio.

## Gotchas found (and healed)

- **Playwright `data-uid` collision** — seat rows *and* device rows both carry
  `data-uid`, so an unscoped `.device-row[data-uid=…]` click hits the hidden
  seat row from the inactive tab. Scope to `#device-roster …`. Healed into
  CLAUDE.md testing gotcha (12).
- **simfleet needed no change** — it is protocol-reactive with per-device patch
  state, so singleton-targeted convergence already reaches only that device.
  Recorded in the tied stitch so nobody hunts for a missing simulator edit.
- **CLAUDE.md "Next sweep" was stale** (still framed 29 as tier-1 in-progress).
  Added a dated pointer at that section head to this handoff.

## Usage at stop

The `claude-usage` meter returned **HTTP 401 (token expired)** at wind-down, so a
precise reading isn't available — a credential-refresh artifact, not a cap hit.
Earlier in the session the **5-hour session cap read 4–9%** (fresh) and the
weekly all-models cap read **82%** (resets 2026-07-27T09:00Z; disregarded per
Bob's instruction). Next session: run any `claude` command to refresh the token,
then `~/repos/ai-kit/tools/claude-usage` for a clean reading.

## Protected worktree items left untouched (as required)

`dashboard/shows/test.json` (user-owned, modified) and
`.notes/handoff-2026-07-24-control-surface-presets.md` (pre-existing
modification) were **not** staged in any commit — every commit staged explicit
paths.
