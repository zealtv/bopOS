# Handoff — 2026-07-22 autopilot session

Scope was two threads by request: `26-listener-range-fixes` and
`23-waveform-marker-guard-regression`. Both are **fully tied**. Codex/GPT
delegation was unavailable this session (usage spent); everything was done in
the main agent, no subagents needed.

## State of play

Bob's four listener defects are fixed and the Listener toolbar is gone, so all
listener control is now graphical. Separately, the red-guard question is
settled: **all four collected red guards were stale guards, not runtime
defects.** That answer generalised badly — a measured sweep found **39 of the 71
browser-free tied guards fail on clean `main`**, which is now a written proposal
awaiting Bob's ruling and a `.waiting` thread holding the evidence. No new
runtime defect was found this session, but one **suspected** one was surfaced
(see "Decisions awaiting Bob", item 3).

## Tied this session

| stitch | commit |
|---|---|
| `26-listener-range-fixes/01-range-field-rendering-fixes` | `55cd088` |
| `26-listener-range-fixes/02-retire-listener-toolbar` | `1a44ec4` |
| `23-waveform-marker-guard-regression` | `fd3fa21` |

Plus a docs/state commit tying off the loom.

### `26/01` — the interesting bug

Bob reported three rendering defects; **two of them were one bug.**
`clipPathUnits` defaults to `userSpaceOnUse`, which resolves in the coordinate
system of the element *referencing* the clip — and the clipped group sat inside
`<g transform="translate(listener.x listener.y)">`. The room-shaped clip window
was therefore slid by the listener position, its top-left corner landing exactly
on the puck. That is why the wash appeared only down-and-right and squared off
at the listener's x/y, *and* why a solid arc survived outside the room at
bottom-right. Measured proof before the fix, listener at (5,4) in a 10×8 room:
clip offset `[336.4, 269.2]` px at 67.3 px/m — exactly (5 m, 4 m).

The clip moved to an untranslated wrapper; **the radial gradient needed no
change at all** (its `objectBoundingBox` default was always correct). The
stitch had predicted a `gradientUnits="userSpaceOnUse"` fix — diagnosing first
saved making an unnecessary change.

Third defect (field lagging a drag) was separate: one `placeListener()` helper
now serves render, `paintRange()` and the drag.

### `26/02` — toolbar retired

`#listener-bar` and its three controls are gone. Everything it did stays
reachable: collar/wheel/keys for range, tip drag for heading, puck drag for
position. Two replacements were needed — the puck's `aria-label` is now the only
textual statement of the values so it updates per-gesture, and a small
gesture-only on-canvas label shows the value being changed. Bob ruled that
*control* can be graphical; he did not say values must be invisible.

### `23` — the red guards

| # | guard | cause | commit |
|---|---|---|---|
| 1 | waveform marker fade progress | fade progress bar retired **by design** | `fbea2b0` |
| 2 | theme pair | already repaired by `21-theme-cyan-tint` | — |
| 3 | `07-seats-workspace` ×2 | heartbeat became a mute-convergence edge | `d23bba0` |
| 4 | `07-seats-workspace` ×1 | terse-copy pass cut the scraped sentence | `149c794` |

Three of the four broke for the same reason: **the guard pinned more than its
subject** — an exact command list where it cared about one verb, a sentence
where it cared about an affordance, a CSS mechanism where it cared about "the
fade carries a finite duration". None broke because the system got worse. All
three repaired in place per the house rule; the waveform guard is 19/19 and the
seats guards 15/15 plus the browser half green.

## Waiting, and on what

- **`27-tied-guard-rot`** (new, `.waiting`) — the 39-of-71 finding. Blocked on
  three rulings from Bob, stated in
  `.loom/tied/23-waveform-marker-guard-regression/proposal-guard-sweep.md`.
  Evidence preserved in that tied stitch as `sweep-reporoot-results.txt` (the
  trustworthy run), `sweep-scratch-cwd-results.txt` (**do not quote** — cwd
  artifacts) and `sweep-failure-logs.tar.gz`.
- `20-console-dock/01-dock-design` — Bob gate, dock scope.
- `25-message-pill-encoding/01-pill-encoding-design` — Bob gate.
- Everything else unchanged (hardware/Bob gates listed in CLAUDE.md).

## Recommended next stitch

**`20-console-dock/01-dock-design`**, per the stage-12 ordering — but it is a
design gate, so it produces a proposal for Bob rather than an implementation.
If you want implementable work instead, `20-console-dock/02-unified-frame` is a
loose end, though its scope partly depends on the `01` ruling.

## Decisions awaiting Bob

1. **Guard sweep** — yes/no, blocking vs advisory; whether the cleanup thread is
   authorised now or waits behind `20`/`21`.
   (`proposal-guard-sweep.md`, three questions at the end.)
2. **Dock scope** — `20-console-dock/01-dock-design`, which also bears on
   `18/06`.
3. **A suspected live defect.** `12-dashboard-live-controls/`
   `verify_live_controls_backend.py` fails three checks about **fleet-overlay
   mute semantics** ("fleet safety overlay blocks individual mute mutation",
   "fleet release reasserts persistent per-UID state", "host-global device mute
   survives restart"). Unlike everything else sampled in the sweep this does
   **not** look like drift, and it is in the same mute subsystem that turned two
   of this session's guards red. My read: pull it out and investigate ahead of
   the rest of the rot cleanup. Recorded as the recommended first stitch inside
   `27-tied-guard-rot`.

## Gotchas found (all healed in CLAUDE.md)

- **An SVG element's `getBoundingClientRect()` ignores clipping**, so no DOM
  assertion can tell you whether a clipped shape painted outside its clip. The
  `26/01` guard samples screenshot pixels instead (Pillow, now installed in
  `~/.venvs/bopos` and recorded in the test recipe). Take the reference pixel
  from *inside* the same surface you are probing — an outside-the-room reference
  makes every in-room probe "differ" and the check passes vacuously. My first
  draft had exactly that bug and passed pre-fix.
- **Run a copied tied guard from the repo root.** Some use cwd-relative paths;
  running from the copy's directory silently changes the answer. This produced a
  wrong first sweep number (40 vs the correct 39).
- **4 of 71 tied guards cannot be run under the copy-out rule at all** — they
  read a sibling file from their own tied directory. Copy the whole directory.
- **A re-render wipes gesture-local DOM state**, and re-applying it must not
  restart its expiry timer or the heartbeat keeps it alive forever. Use a
  deadline. (Both directions pinned by checks in `26/02`.)
- **`page.mouse.wheel(0, -8000)` is one notch**, not thirty-two — the listener
  wheel steps a fixed 0.25 m per *event*.

## Usage at stop

Well under threshold; the session stopped because both requested threads were
complete, not because of budget.

- weekly (all models): **42%**, resets 2026-07-27T08:59:59Z ← active constraint
- 5-hour session: **25%**, resets 2026-07-22T01:59:59Z

Next session: continue from this handoff.
