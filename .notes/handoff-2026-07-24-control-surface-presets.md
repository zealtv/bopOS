# Handoff — patching-session intake: order of work (2026-07-24)

Context: Bob's first full editor→simulator→device patching session produced a
braindump (lore `2026-07-24-patching-session-braindump`) plus three same-day
conversational extensions, all intaken onto the loom this session. This note
fixes the order of work. Each item's authoritative spec is its stitch
`instructions.md` — this is the map, not the territory.

## The order

**1. `39-remove-installed-pack-from-device`** — workable now, pre-existing.
Device-side uninstall of an installed asset pack from the Asset tab. Small,
self-contained, fully specced with file:line anchors. First because it was
already the queue head and nothing new depends on it.

**2. `40-precision-param-input`** — workable, no design gate. Typed float
entry beside every param slider (live-control surface + patch-editor panel;
Show inspector is verify-only — already typed). Second because it pays off
Bob's patching sessions immediately, and the thread-37 design assumes
typed-entry-capable controls exist — landing it first keeps the surface
design honest.

**3. `37-device-scoped-patch-control/1-device-patch-control-design`** —
**Bob-gated design session** (`.waiting`; needs Bob live or a written
proposal he ratifies). Scope was widened 2026-07-24 and Bob confirmed: it
now owns (a) per-device patch targeting (the original scope, with its
partial ratifications — fleet patch = bulk-set over per-node desired patch,
Patch-tab switch authority, Device-tab "Set patch…" shortcut), (b) the
**reusable control-surface component** and its three hosts (patch editor /
Device tab / Control tab), (c) the **Dashboard → Control rename** + target
filter (all/groups/seat) + cues-master-presets placement and the
cue-section shrink, and (d) the **per-param generator affordance** on the
surface (reuse the `automation-2` builder GUI). Third because both
remaining items sit on this surface.

**4. `41-preset-primitive/1-preset-architecture-design`** — **Bob-gated
design**, right behind (or interleaved with) 37's session since the surface
hosts the preset save/load UI. The stitch carries everything ruled so far:
presets are manifest-scoped and capture **values or generator specs**;
save-from-editor, load per seat/group/all, collections; Show-tab triggering
with optional duration+curve interpolation; **hard takeover is the global
model** (preset apply = fan-out of ordinary per-param messages, no
layer/lock; a direct set mid-morph wins on that param); and the
generator-interpolation mechanism is **open** — the proposal must compare
the output-crossfade mix function against generator-arg interpolation
(Bob: "if there is a more elegant approach I might prefer it") and
recommend with wire-shape deltas.

**5. Implementation stitches out of 37, then 41** — laid out as children
after each ratification. Expect 37's implementation to subsume the old
Seats-detail vertical-overflow complaint (don't patch it separately).

**6. Resume the pre-existing backlog** in its standing order: 27 guard-rot
(Bob's fresh briefed session, `.notes/handoff-guard-rot-briefing.md`),
then deferred items per CLAUDE.md's Next sweep (35 logging seed, 34
fleet-patch global state + 33b network config in feature-backlog,
20/07-map-tab, tier 3–5 gates).

## Why this order

39 and 40 are the only ungated workable items and both are small; they
clear the runway. 37 before 41 because the preset UI lives on the surface
37 designs — designing presets first would force guesses about their home.
40 before 37's implementation because the shared surface should be born
with precision entry, not retrofitted.

## For the executing model

- Every stitch above is specced in its own `instructions.md` with file:line
  anchors (39, 40) or a full decision inventory + open-questions list
  (37/1, 41/1). Read the stitch before this note wins any disagreement —
  the stitch is authoritative.
- Design stitches (37/1, 41/1) end in a **written proposal Bob ratifies**,
  then tie with `decisions.md`. Do not implement past an unratified design.
- Verification: headless Playwright + simfleet per CLAUDE.md's "Testing
  without hardware" (venv `~/.venvs/bopos`; copy the newest tied
  `verify_*.py` as template). New checks for shared surfaces go into
  `tests/`, not new tied guards (Bob's 2026-07-23 testing ruling).
- Anything wire-visible in 41 is an OSC-contract amendment — propose the
  delta in the design, don't land it unratified.
- Test rig for 37/41 hardware checks: Finn Jet (fleet-node) + Ciro Toast
  (standalone) — see the `finn-ciro-test-rig` memory and 37/1's rig note.

## Not included in this commit

`bopos.devices` (modified) and `dashboard/shows/` (untracked) predate this
session — they look like artifacts of Bob's patching session (device store
churn + saved show documents). Left for Bob to commit or discard
deliberately; `bopos.devices` was separately flagged stale (old MACs) as a
cleanup candidate.
