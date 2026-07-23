# 27-tied-guard-rot

**Waiting on thread `20`** (`21-theme-cyan-tint` was **dropped** 2026-07-23, so
it no longer gates this). Bob ruled 2026-07-22, revisited 2026-07-23:

- **Ordering:** this runs *after* `20-console-dock`. The rot is not blocking
  anything and has been accumulating for weeks. **But** Bob flagged the failing
  tests for prominence in the 2026-07-23 holistic re-order — see CLAUDE.md's
  "Next sweep" block for its actual placement, which may lift it above the
  deferred Show polish.
- **The sweep question itself** (script yes/no, blocking vs advisory) Bob will
  take in a **fresh session** with a dedicated briefing rather than deciding it
  from the proposal — see `.notes/handoff-guard-rot-briefing.md`, which is
  written for exactly that session. Do not build `tools/guard-sweep.sh` before
  that session rules.
- **The suspected live defect was pulled out and settled** — thread
  `28-fleet-mute-semantics`, tied 2026-07-22. **Not a defect**: fleet mute
  safety is intact; the guard pinned a ruling Bob himself superseded in
  `18-decoupled-device-mute`. Do not re-investigate it.

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
`.loom/tied/23-waveform-marker-guard-regression/` as
`sweep-reporoot-results.txt` (use this one), `sweep-scratch-cwd-results.txt`
(first run, includes cwd artifacts — do not quote it), and
`sweep-failure-logs.tar.gz`.

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

## Also red, and NOT in the 39

`12-dashboard-live-controls/verify_live_controls_browser.py` times out waiting
for `[data-live-param][data-live-scope="seat"][data-live-id="1"][data-param-path="gate"]`
(found by thread `28`). It is a **Playwright** suite, so it was never in the
71-guard sweep. Not a rename — those attributes are still emitted by
`facilitator.js:172` — so it needs real diagnosis.

It is also the first datum on the **97 unswept Playwright suites**, and it went
red on the first look. Assume the true figure is above 39, and sweep the
Playwright set early rather than assuming the browser suites are healthier.

## Start here if it is authorised

The suspected-defect candidate is **gone** — thread `28` settled it as another
supersession (and repaired the guard). Nothing in the remaining ~33 has been
singled out as more likely than the rest.

Two starting points, either defensible:

- **The `verify_live_controls_browser.py` failure above**, since it is a real
  unknown rather than suspected drift, and it tells us how bad the Playwright
  set is.
- **The API-drift cluster** (`FakeOSC`, `AuditionRig`), which is probably the
  cheapest per guard and will shrink the list fastest.

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
