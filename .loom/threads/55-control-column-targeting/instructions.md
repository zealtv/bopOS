# 55-control-column-targeting

Bob's 2026-08-02 review of the shipped N-column Control tab
(`08-control-tab-columns`, tied 2026-07-31). Three reports and a stated
workflow:

> when selecting multiple targets (ie two groups, or a group and a seat) i can
> see additional control panels below the first, but the column is not
> scrollable so i can't access them. however - shouldn't it remain as a single
> control panel, that is targeting all seats from it's target picker?

> when i select a preset in either column, it effects all columns.

> workflow here should be - make some columns, target some groups, apply some
> presets (possibly creating them from this tab), then click capture step.

## What I measured before writing this (2026-08-02)

Real dashboard + simfleet, 6 seats in 3 groups, Chromium at 1440 × 900.
The scratch harness is `repro-columns.py` beside this file.

**Report 1 — the scroll. CONFIRMED, and it is worse than reported.**

| | 3 group targets, 8 params | 1 group target, 40 params |
|---|---|---|
| `#control-column-host` height | 710 | 710 |
| `.control-column` height | 710 (clamped ✓) | 710 (clamped ✓) |
| `.control-column-cards` clientHeight | 1370 | 1408 |
| `.control-column-cards` scrollHeight | 1370 | 1408 |
| **scrollable** | **false** | **false** |

The second column is the one that matters: **one card, one target, and it still
does not scroll.** So this is not a multi-target defect. The Control column has
never scrolled vertically in its life; multi-target is just the first content
tall enough to make it obvious. `css/control-column.css:36-42` claims the
opposite in a comment ("keeps the head in view while a forty-row manifest
scrolls under it") — that comment describes an intention that did not ship.

Cause and fix are both measured; see `1-column-scroll`.

**Report 2 — presets across columns. NOT REPRODUCED as described, and I think
I know what was actually seen.**

With column 1 → `Front` (g0) and column 2 → `Back` (g1), saving and applying a
preset from column 1 left column 2 reading `— none —`. The apply path is
correctly scoped end to end: `applyPreset` sends `{scope, id}`
(`control-host.js:135`), `apply_preset` resolves through
`live_param_target` (`server.py:2043`), and the displayed value comes from
per-seat `applied_preset` provenance (`control-surface.js:284`), not from any
shared client state. `presetReport` is filtered to a column whose member set
matches the report's targets exactly (`control-column.js:142`).

But an earlier run of the same harness — where I had failed to actually change
either column's target — reproduced Bob's sentence exactly. **`addColumn()`
defaults a new column to `["all"]`** (`control-host.js:210`). So a tab with
some columns aimed at groups and any column still on its default All shows the
applied preset in every All column, correctly, and looks exactly like a leak.

That is a real usability defect even though it is not a correctness one, and it
may be the whole of report 2. It is also entangled with report 1's design
question — hence one thread, not two. **Confirm with Bob what the columns were
aimed at before treating this as a bug**; if it was overlap, the fix is about
what a new column should default to and how a card says whose target it
answers, not about scoping.

## Children

* **`1-column-scroll`** — the defect. Claimable now, independent of everything
  below, and true whichever way the design question goes: a single card taller
  than the viewport must scroll.
* **`2-multi-target-model`** — `.waiting` on Bob. One control panel driving a
  multi-target selection, versus today's card-per-target. This is a reversal of
  a shipped `08` decision, so it needs his ruling, and the capture-step
  workflow he described is part of the same question.
