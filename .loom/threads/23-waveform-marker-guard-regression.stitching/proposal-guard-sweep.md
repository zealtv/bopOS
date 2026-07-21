# Proposal: routine tied-guard sweeps — Bob's call

**Status:** proposal, not implemented. The stitch says raise this before building
it, so nothing here is built.
**Date:** 2026-07-22, from thread `23-waveform-marker-guard-regression`.

## What prompted it

The stitch's own suspicion — "tied guards are not being run routinely, and are
rotting quietly between the sessions that touch their area" — is correct, and
worse than the four known cases suggested.

## The measurement

I ran every **browser-free** tied guard (71 of the 168 in `.loom/tied/`;
Playwright suites excluded as too slow for a first pass) against clean `main`.

**39 of 71 fail.**

The first run gave 40, but I had run them from a scratch directory, and some
guards resolve paths relative to the working directory. Re-running from the repo
root — the way a person would — gave the corrected 39. That correction is itself
a finding: **the number is only trustworthy if the sweep runs guards the way a
human would.**

Breaking the 39 down by what I could establish cheaply:

| class | count | note |
|---|---|---|
| external binary absent (`sclang`) | 1 | not rot; environment |
| guard depends on a sibling file in its tied dir | 4 | **the copy-out rule cannot run these at all** |
| assertion/API failures | ~34 | not yet individually diagnosed |

Sampled from the last group, the failure signatures are the same family this
stitch diagnosed by hand:

- `AttributeError: 'FakeOSC' object has no attribute 'unassign'`
  (`d8-1-seat-model`) — a test double drifted from the real interface;
- `AttributeError: 'AuditionRig' object has no attribute 'param_declarations'`
  (`1-contract-model-relay`) — same shape, renamed attribute;
- `12-dashboard-live-controls`: three behavioural failures about **fleet-overlay
  mute semantics**. This one does not look like drift and may be a real defect.
  It is in the same mute subsystem whose additive convergence verb caused two of
  this stitch's four red guards, which makes it the most interesting single
  thread to pull.

**I have not diagnosed the ~34 individually.** Doing so is a thread, not a
stitch, and the instruction was to raise the sweep question first.

## What the four hand-diagnosed cases showed

All four were **stale guards, zero runtime defects** (details in
`decisions.md`). Three broke because the guard **pinned more than its subject** —
an exact command list where it cared about one verb, a whole sentence where it
cared about an affordance, a CSS mechanism where it cared about "the fade is
annotated with a finite duration". None broke because the system got worse.

This matters for what a sweep is *for*. If most reds are over-specification
rather than regression, a sweep that just goes red is noise; the value is in
forcing the repair at the moment the deliberate change lands, while the author
still knows why.

## Recommendation

**Yes to a sweep, but not as a blocking gate, and not before a cleanup.** Three
parts, in order:

1. **A cleanup thread first.** 39 red guards means a sweep introduced today
   reports "red" permanently and gets ignored — the exact failure mode that let
   this rot accumulate. Triage the ~34 into repair / genuine defect / retire,
   using the same rule CLAUDE.md already states: superseded guards get repaired
   in place with an inline note, not deleted, not left red.
2. **Then a sweep script**, `tools/guard-sweep.sh`, that runs the browser-free
   set from the repo root and reports a table. Fast subset by default; a
   `--browser` flag for the Playwright suites. Explicitly **not** in a
   pre-commit hook — the browser suites take minutes and the fast set takes
   ~8 minutes.
3. **A house rule in CLAUDE.md**: a stitch that changes a shared surface
   (the OSC bridge, `state.py`, the manifest, a wire verb, shared CSS tokens)
   re-runs the guards for *neighbouring* tied stitches before tying, not just
   its own. That is the cause; the sweep is only the detector.

Also worth fixing whichever way you rule: **4 guards cannot be run at all** under
the "copy it out of `.loom/tied/`" rule, because they read sibling files from
their own tied directory. Either the rule needs a "copy the whole directory"
variant, or those guards need to locate their fixtures by repo-marker like they
locate the root.

## What I want from you

Three rulings:

1. Sweep yes/no, and blocking vs advisory.
2. Whether the cleanup thread is authorised now, or waits behind the current
   stage-12 fix pass (threads `20`, `21`, `22`).
3. Whether `12-dashboard-live-controls`' fleet-overlay mute failures should be
   pulled out and investigated immediately as a suspected live defect — my read
   is yes, and ahead of the rest.

Until you rule, I have left a `.waiting` goal stitch,
`27-tied-guard-rot`, holding the evidence, with its blocker naming this
proposal. Nothing in it is claimed.
