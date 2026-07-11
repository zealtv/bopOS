# Implementation outline — proposed loom changes after ratification

Written by the council orchestrator from `judgment.md` (2026-07-11). This is a
proposal only: nothing here is implemented, no stitches are created, and no
existing thread is edited until Bob ratifies via the parent
`engine-boundary-ratification` stitch. Where this outline and `judgment.md`
disagree, the judgment wins; where Bob's ratification amends the judgment, the
ratification wins.

## Proposed new children under `engine-boundary-design`

Numbered in dependency order (the judge's §8 sequence). Each is agent-ownable
except the PD edit wave, which is a Bob-owned gate with agent-written specs.

1. **`boundary-1-alias-and-lock`** (agent, Python-only, reversible)
   Add the `/helper/*` → `/os/*` alias inside `handle_lan_datagram` so legacy
   dashboard verbs survive the eventual removal of PD's forward
   (judgment §4.1 — the confirmed alias hole, helper.py:678); add a lock
   around the shared `client.send()` (pre-existing cross-thread race).
   Verify via simfleet: legacy `/<id>/helper/reboot` works with the engine
   killed. This is the ruled first slice; revert = delete the alias.

2. **`boundary-2-pd-parallel-relay`** (agent)
   Drop the `!= "pd"` guard (helper.py:645) so master/`/p/*` relay to PD on
   6661 in parallel with its live 6660 path (idempotent duplicates are
   harmless). Verify on audition rig + simfleet that PD hears every term on
   6661. Proves the local surface before anything is removed.

3. **`boundary-3-helper-slimdown`** (agent)
   Delete the 7770 admin handlers (keep `/config`, `/store`, `/load`; add
   `/report` per the ruled engine→framework surface); add the one-shot
   `/os/probe`; delete `meter_loop` + `METERS`/`METER_INTERVAL`. Includes the
   **helper-death drill** (bench item 1): systemd `Restart=always`, measured
   time-to-restored-control, mute-spam fallback confirmed. If recovery is not
   seconds, stop and surface — the sole-binder ruling is bench-gated on this.

4. **`boundary-4-pd-edit-wave.waiting`** (Bob-owned gate; agent writes specs)
   The specified-not-implemented PD edits: remove the 6660 `netreceive`, the
   `route helper` forward, `route echo`, in-patch id routing, PX/PY; adopt
   the `bopos-*` bus glossary and the `[bopos]` façade in `bopos.pd`; retire
   `bopos.feedback.pd`; parameterize the ingress port (default 6661).
   Agent deliverable: an exact edit spec in the style of
   `.notes/pd-edits-for-bob.md`, plus a verify that exercises the post-edit
   patch headlessly. Bench on production Mac N=1 (bench item 2).

5. **`boundary-5-launch-context`** (agent)
   bopOS-owned run-context generation (seed, run id string, patch, assets)
   delivered at launch via start-engine.sh `-send`/env — ownership moves to
   bopos.py, transport stays launch-time (boot-race veto upheld). SC starter
   gets a `/config` retry loop; `tools/audition.py` drops the fixed-bind
   attempts and unifies its OSC library with helper's.

6. **`boundary-6-contract-v12-and-renames`** (agent, last)
   Contract v1.2 text (§4 table, §4.1 single delivery column, §6 `/os/probe`,
   §8/§11 meter deletion/redefinition, §13 alias note) presented as an
   explicit revision; then the two behavior-free rename commits:
   `helper.py` → `bopos.py`, `bopos.osc.pd` → `bopos.pd`. Renames land only
   after stages 1–3 (never mid-migration; bisectability argument).

Deferred, recorded but not stitched: the **leased probe** (`/<id>/os/probe
<what> <hz> <ttl>`) and the io→bopos.py upstream it needs — wire shape
ratified, build waits until the touch-debug need actually lands (judgment §5,
bench item 5).

## Effects on existing waiting stitches

- `audition-rig/audition-1c-engine-boundary-adoption.waiting` and
  `audition-2a-...waiting`: unblock after ratification; their adoption target
  is the ruled one-topology model (engines take `BOPOS_ENGINE_PORT`, default
  6661; audition = N>1 of the same relay role). Coordinate with `boundary-5`.
- `patch-workflow-friction/friction-1a-engine-boundary-adoption.waiting`:
  unblock after ratification; the starter kit teaches the 6661 surface and
  the `bopos-*` glossary (PD and SC starters become "the same document").
- `pi-zero-performance/zero-2-engine-verdict.waiting`: unchanged, but the
  helper-death drill and relay-cost adjudication (negligible; only
  master/params added at <1 msg/s) feed its evidence base.
- `clock-sync/sync-4`, `dashboard-6`, `spatial-3`: untouched — hardware
  gates, no wire change affects them (nothing new touches the broadcast
  channel).
- Dashboard meters surface: loses its framework-meter feed when `meter_loop`
  goes (stage 3); `role:"meter"` survives as a read-only UI hint for
  patch-published values, and the one-shot probe covers "is box 3
  alive-and-loud". Worth a small dashboard follow-up stitch if Bob wants the
  meters panel to drive probes; not stitched here.

## Ratification checklist for the parent stitch

Per `engine-boundary-ratification/instructions.md`, record: accept/reject/
amend of the sole-binder ruling and its ordering discipline; the naming
rulings (`bopos.py`, `bopos.pd` — both ratified by the judge, Bob confirms);
the meter deletion; the one-shot-first probe; the contract v1.2 scope; which
tied behavior is superseded (seam-5's "PD retains its direct 6660 path"
sentence, audition-1b's fixed-bind noise); the ordered stitches above; and
the deliberately-open items (leased probe timing, production-Mac N=1 bench,
helper-death drill threshold).
