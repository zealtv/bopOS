# 27-tied-guard-rot

## Bob's ruling (2026-07-23) — the reframing. READ FIRST.

> "We want durable, maintainable tests for appropriate surfaces. Running tests of
> tied stitches was the wrong pattern."

This changes what this thread *is*. It is **not** "repair 39 red guards and stand
up a sweep script." It is a **two-tier split**:

1. **Promote the durable-contract guards into a living `tests/` suite** — the
   minority of the 168 that assert invariants meant to hold *forever*: OSC wire
   shapes / the contract, manifest schema, identity/fingerprint, **mute safety
   semantics**, fetch convergence. Move those out of `.loom/tied/` into `tests/`
   **organized by the code surface they test** (`test_osc_contract.py`,
   `test_fetcher.py`, `test_mute.py`, …), dedupe overlapping assertions, and run
   them in CI / before tie. A living test sits next to the code and is refactored
   in the same commit that changes the code, so it cannot rot the way a tied
   snapshot does.
2. **Retire the rest as authoring artifacts.** A guard that pinned one stitch's UI
   copy, a specific CSS mechanism, or a one-time delivery was proof-of-work, never
   a forever-contract. It did its job at authoring time. It is **not** re-run and
   **not** maintained; it stays as historical record (retirement recorded per
   CLAUDE.md, never a silent delete).

**Why (the evidence):** six diagnoses across threads 23/28 (plus the `hb-identity`
repair in 29/2-fix) found **zero real defects — every red was a stale guard.** As a
persisted regression net the guards are not catching anything; the value they had
was captured at *authoring* time. And the tied-per-stitch organization is the root
cause of the rot: guards are filed by *stitch*, not by *code surface*, so they
can't move with the code and "re-run neighbouring stitches' guards" keys off the
wrong axis (stitch-adjacency, not code-adjacency).

**The discriminating question for each guard:** *does it assert a contract we want
to guarantee forever (→ promote to `tests/`), or did it prove a one-time change
(→ retire)?* That triage — not "fix the reds" — is the substance of this thread.

**Consequences for the sub-sections below:** the "39/71 red" figure is now *input
to the triage*, not a to-do list. The `tools/guard-sweep.sh` question is largely
moot — a living `tests/` suite in CI is the detector; a sweep over the tied archive
is not wanted. Do **not** invest in maintaining or re-running the tied archive.
Cheap thing to start *now* regardless (not gated): when any stitch touches a
genuinely shared surface, write its check straight into a `tests/` file rather than
a new tied guard — this builds tier 1 organically and stops adding to the archive.

---

> **Ordering correction (2026-07-23):** The older “after thread 20” wording
> below is stale. The authoritative holistic order in `CLAUDE.md` elevates this
> thread ahead of deferred Show polish: **31 → 32 → 33 → 34 → 27 → 20 → 25**.
> Thread 27 still waits for Bob's fresh-session discussion, but it does **not**
> wait for thread 20.

Historical context (`21-theme-cyan-tint` was **dropped** 2026-07-23, so it no
longer gates this). Bob ruled 2026-07-22, revisited 2026-07-23:

- **Superseded ordering:** this formerly ran *after* `20-console-dock`. Bob then
  elevated the failing-test cleanup in the 2026-07-23 holistic re-order; see
  `CLAUDE.md`'s "Next sweep" block for the current placement ahead of deferred
  Show polish.
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

## Shape of the work (under the 2026-07-23 reframing)

The old plan below (repair reds → fix copy-out guards → maybe a sweep script →
re-run-neighbours rule) is **superseded** by Bob's two-tier ruling at the top.
The work is now:

1. **Enumerate the durable contracts** worth guaranteeing forever, by *code
   surface* — OSC contract/wire shapes, manifest schema, identity/fingerprint,
   mute safety, fetch convergence, and whatever else the triage surfaces. This is
   the design deliverable; likely a Bob check-in on the list.
2. **Build the living `tests/` suite** for those surfaces — mine the *real
   assertions* out of the relevant tied guards, dedupe, re-express them against
   current code, organize by code surface, wire into CI / a pre-tie run. (Note the
   node bug in `29` was fresh-hardware-specific and invisible to any of this — so
   include the honest limits of what unit/sim tests can catch.)
3. **Retire the rest** — classify each remaining tied guard as *promoted*
   (its assertion moved to the living suite) or *retired* (authoring artifact,
   recorded per CLAUDE.md). No silent deletes; no leaving them red-and-maintained.
4. Once tier 1 exists and runs itself, the tied archive is just history — no
   `tools/guard-sweep.sh` over it, no re-run-neighbours discipline needed.

Split per code surface rather than doing it in one stitch. Sequence the durable
surfaces first (OSC contract, fetcher, mute) since those are the real invariants.

## Sequencing (2026-07-27, slotted into the current program)

Bob asked for this thread to join the active order. Slot: **after
`desktop-ui-overhaul/01-control-panel/1-full-manifest-visibility`, alongside
the `2-control-panel-design` gate, and before the control-panel
implementation wave, `44-event-plane`, and `41-preset-primitive`** — the
durable `tests/` suite this thread creates should exist before those write
their checks into it, and before the event-plane contract amendment churns
more tied guards. Still `.waiting` on Bob's fresh triage session
(`.notes/handoff-guard-rot-briefing.md`); it pairs naturally with the
control-panel design-ratification session.
