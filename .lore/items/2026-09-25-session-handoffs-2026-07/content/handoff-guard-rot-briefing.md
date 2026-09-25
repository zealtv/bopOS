# Briefing — the tied-guard rot session

> **Closed 2026-07-27:** thread `27-tied-guard-rot` established the living
> `tests/` workflow and retired the tied guard archive from maintenance. The
> final disposition is in
> `.loom/tied/08-archive-retirement-ledger/retirement-ledger.md`. Everything
> below is retained as historical intake context, not current workflow.

> **Bob's ruling, 2026-07-23 (supersedes the framing below):** "We want durable,
> maintainable tests for appropriate surfaces. Running tests of tied stitches was
> the wrong pattern." So this session is **not** "decide a sweep script + repair 39
> reds." It is a **two-tier split**: (1) promote the guards that assert *durable
> contracts* (OSC wire/contract, manifest schema, identity/fingerprint, mute
> safety, fetch convergence) into a **living `tests/` suite organized by code
> surface** and run in CI/pre-tie; (2) **retire the rest** as authoring artifacts
> (recorded, never silent-deleted, never maintained-in-place). Rationale: 6
> diagnoses = 0 defects (the guards catch nothing as a persisted net), and the
> tied-per-stitch layout files guards by *stitch* not *code surface*, which is why
> they rot and why "re-run neighbours" was the wrong instrument. The "39/71 red" is
> now *input to the triage*, not a to-do list. Full framing at the top of
> `.loom/threads/27-tied-guard-rot.waiting/instructions.md`. The three questions
> below are largely answered by this ruling (no sweep over the archive; the living
> suite is the detector) — keep them for context, not as open decisions.

Written 2026-07-22 at Bob's request: he wants to take the guard-sweep decision
and the cleanup in a **fresh session**, not from the proposal cold. This file is
that session's starting point. Read it, then
`.loom/tied/23-waveform-marker-guard-regression/proposal-guard-sweep.md` for the
long form.

> **Stale ordering (corrected 2026-07-23):** The sentence below recorded the
> 2026-07-22 order and is superseded by `CLAUDE.md`'s holistic order:
> **31 → 32 → 33 → 34 → 27 → 20 → 25**. Thread 27 still needs Bob's fresh
> session, but no longer waits for thread 20; thread 21 was dropped.

Historical instruction, no longer operative: do not start this session until
threads `20-console-dock` and `21-theme-cyan-tint` are done.

## The one-paragraph version

168 tied guards live in `.loom/tied/*/verify_*.py`. Nobody re-runs them, so they
rot as deliberate changes land elsewhere. Of the 71 that need no browser,
**39 fail on clean `main`**. Every failure diagnosed so far — six now, across
threads `23` and `28` — has been a **stale guard, not a runtime defect**. No
regression has been found. The open question is what to do about it: triage the
backlog, and decide whether a sweep script earns its place.

## What is already settled (don't redo)

| thread | finding |
|---|---|
| `23-waveform-marker-guard-regression` | 4 red guards, all stale. Repaired. Measured the 39/71. |
| `28-fleet-mute-semantics` | The one suspected *live* defect — fleet-overlay mute — is **not** a defect. Safety intact. Guard repaired. |

Six diagnoses, six stale guards, zero defects. That is the single most important
input to the decision below.

## The failure pattern, which is the actual insight

Guards did not go red because the system got worse. They went red because
**the guard pinned more than its subject**:

- an exact `uid_command` list, when it cared about one verb — so it broke the
  first time an additive convergence verb was added;
- a whole sentence of UI copy, when it cared about an affordance existing;
- a specific CSS mechanism, when it cared about "the fade carries a finite
  duration";
- a pre-revision *ruling* Bob had since reversed (`28`).

Two consequences for the cleanup: most repairs are "re-target the assertion at
its real subject", and **a red guard here is weak evidence of a bug and strong
evidence someone changed a shared surface without re-running neighbours.**

## The three questions to settle

1. **Sweep script: yes/no, blocking or advisory?**
   My recommendation: **cleanup first, then advisory only.** Standing up a
   detector that reports 39 red on day one guarantees it gets ignored — the
   exact dynamic that produced the rot. Never in a pre-commit hook: the
   browser-free set alone takes ~8 minutes, the Playwright set far longer.
2. **Is a script even the right instrument?**
   Worth genuinely considering "no". If the cause is authors not re-running
   neighbours, the fix is a house rule at the moment of change, not a detector
   weeks later. My recommendation is the rule regardless of the script:
   *a stitch touching a shared surface (OSC bridge, `state.py`, the manifest, a
   wire verb, shared CSS tokens) re-runs the tied guards for neighbouring
   stitches before tying.*
3. **How much of the backlog is worth repairing at all?**
   Some guards may be genuinely obsolete rather than stale. Retiring one is
   legitimate — but per CLAUDE.md it is a *decision to record*, not a silent
   delete.

## Practical notes for whoever runs it

- **Run guards from the repo root.** Some use cwd-relative paths; running from
  the copy's directory silently changes the result. This produced a wrong first
  number (40 vs the correct 39).
- **4 of 71 cannot be run under the copy-out rule at all** — they read a sibling
  file from their own tied directory. Copy the whole directory.
- **1 of 71 needs `sclang`** (not installed): environment, not rot.
- **The 97 Playwright suites are unswept.** The first one anybody looked at
  (`verify_live_controls_browser.py`, found by `28`) was red. Assume the true
  figure is above 39; sweep the browser set early rather than hoping.
- Evidence lives in `.loom/tied/23-waveform-marker-guard-regression/`:
  `sweep-reporoot-results.txt` (**the trustworthy run**),
  `sweep-scratch-cwd-results.txt` (do **not** quote — cwd artifacts),
  `sweep-failure-logs.tar.gz` (last 30 lines of each failure).
- Sampled drift signatures, expect more of the same:
  `AttributeError: 'FakeOSC' object has no attribute 'unassign'`;
  `AttributeError: 'AuditionRig' object has no attribute 'param_declarations'`.
- Repair convention, already house rule: fix **in place** with an inline comment
  naming the superseding stitch, and record the supersession in that stitch's
  `decisions.md`. Never delete, never leave red.
  Worked examples: `.loom/tied/03-divider-rule-styling/decisions.md`,
  `.loom/tied/28-fleet-mute-semantics/decisions.md`.
- **When you invert an assertion, check you are not deleting a property.** In
  `28`, inverting "fleet blocks device mute" would have removed the only safety
  assertion in that block, so a new `effective_muted` check went in alongside.
  The repaired guard is stronger than the original.

## Where the work is laid out

`.loom/threads/27-tied-guard-rot` (`.waiting`) — the triage thread, with the
classification table and suggested starting points. Split it per area; ~33
guards is several stitches, not one.
