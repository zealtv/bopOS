# 27-tied-guard-rot

**Blocked on Bob.** Three rulings are needed before any of this is workable — see
`.loom/tied/23-waveform-marker-guard-regression/proposal-guard-sweep.md`, which
states them and the evidence. Do not start without them; the first decision is
whether this thread happens at all and whether it outranks the stage-12 fix pass.

## The finding

Thread `23` swept every browser-free tied guard (71 of 168; Playwright suites
excluded as too slow for a first pass) against clean `main`, run from the repo
root.

**39 of 71 fail.**

Thread `23` hand-diagnosed four of them. All four were **stale guards, not
runtime defects**, and three broke for the same reason: the guard **pinned more
than its subject**, so a deliberate, correct change elsewhere turned it red.
Full write-up in `.loom/tied/23-waveform-marker-guard-regression/decisions.md`.

The raw sweep results, and a `tail` of each failure, are preserved in
`.loom/tied/23-waveform-marker-guard-regression/sweep/` — `results.txt` is the
first (scratch-cwd) run, `rerun/results.txt` the corrected repo-root run. Use
`rerun/` — the first run's numbers include cwd artifacts.

## Known classification so far

| class | count | note |
|---|---|---|
| external binary absent (`sclang`) | 1 | environment, not rot |
| reads a sibling file from its own tied dir | 4 | **cannot be run under the copy-out rule at all** |
| assertion / API-drift failures | ~34 | not individually diagnosed |

Sampled signatures from the last group — expect more of the same:

- `AttributeError: 'FakeOSC' object has no attribute 'unassign'` (`d8-1-seat-model`)
- `AttributeError: 'AuditionRig' object has no attribute 'param_declarations'`
  (`1-contract-model-relay`)

## Start here if it is authorised

**`12-dashboard-live-controls/verify_live_controls_backend.py`** — three
behavioural failures about fleet-overlay mute semantics ("fleet safety overlay
blocks individual mute mutation", "fleet release reasserts persistent per-UID
state", "host-global device mute survives restart"). Unlike the rest of the
sample this does **not** look like drift, and it sits in the same mute subsystem
whose additive convergence verb turned two of thread `23`'s guards red. If any
of the 39 is a live defect, this is the candidate. Treat it as its own stitch.

## Shape of the work, once ruled on

1. Triage the ~34 into repair / genuine defect / retire. House rule already
   stated in CLAUDE.md: superseded guards are **repaired in place** with an
   inline comment naming the superseding stitch, and the supersession recorded
   in that stitch's `decisions.md` — never deleted, never left red.
2. Fix the 4 guards that cannot be run under the copy-out rule (either the rule
   grows a copy-the-directory variant, or they locate fixtures by repo-marker
   the way they already locate the root).
3. Only then a `tools/guard-sweep.sh`, if Bob wants one — a permanently-red
   sweep is worse than no sweep.
4. The cause, not the detector: a CLAUDE.md rule that a stitch touching a shared
   surface (OSC bridge, `state.py`, manifest, a wire verb, shared CSS tokens)
   re-runs *neighbouring* tied guards before tying.

Split per area rather than doing 34 in one stitch.
