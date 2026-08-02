# 3-cross-column-preset-report

**A question for Bob, and nothing else.** The deliverable is one answer written
into `decisions.md`. Whatever work follows is laid out from that answer, not
from this stitch.

## The report

> when i select a preset in either column, it effects all columns.
> — Bob, 2026-08-02

## It did not reproduce (measured 2026-08-02)

Real dashboard + simfleet, 6 seats in 3 groups, Chromium 1440 × 900. Harness:
`repro-columns.py` in the parent stitch.

Column 1 → `Front` (g0), column 2 → `Back` (g1). Saved a preset from column 1,
then applied it there:

```
after applying 'Repro-One' in column 1
  column "Front"  →  preset: Repro One
  column "Back"   →  preset: — none —
```

The apply path is correctly scoped end to end, and there is no shared client
state to leak through:

* `applyPreset` sends `{scope, id}` — `control-host.js:135`;
* `apply_preset` resolves concrete seats via `live_param_target` —
  `server.py:2043`;
* the displayed value is derived from **per-seat** `applied_preset` provenance —
  `control-surface.js:284`;
* `presetReport` is filtered to a column whose member set matches the report's
  targets exactly — `control-column.js:142`.

## But an earlier run reproduced the sentence exactly

In a first pass I failed to actually change either column's target. Both were
therefore still on **`addColumn()`'s `["all"]` default**
(`control-host.js:210`), and applying a preset in one column showed it in both —
correctly, because both columns were pointed at every seat.

So the most likely explanation is **overlap, not leakage**: a tab with some
columns aimed at groups and any column still on its default All will show an
applied preset in every All column. Same for a group column and a seat column
whose seat is in that group.

## The question

**What were the columns aimed at when you saw this?**

* **If any of them were still on All** — this is not a scoping bug. It is two
  defects of legibility, and both are worth fixing:
  1. `addColumn()` defaults to every seat in the venue. If a column is an
     *arrangement* (`2-multi-target-model`), "everything" is probably the wrong
     thing for a new one to be.
  2. A card gives no indication that its state is answering a target other
     than its own column's — an All column showing `Repro One` because a
     *group* was set is truthful and unreadable at the same time.
* **If every column was aimed at a disjoint group or seat** — then I have not
  reproduced it and the measurement above is missing a condition. Say what the
  targets were, and whether the preset was applied from the dropdown or created
  with `new`/`save` first; those take different paths (`apply_preset` versus
  `save_patch_preset` followed by an apply) and I only exercised the second.

## Why it is not folded into `2-multi-target-model`

Because the answers diverge. If it is overlap, the fix is about defaults and
per-card legibility and can ship whatever Bob decides about aggregate panels.
If it is not overlap, there is a real scoping defect that must be found before
any of that surface is restructured on top of it.

Related, and the reason this thread exists at all:
`1-column-scroll` (a plain defect, claimable now) and
`2-multi-target-model` (Bob's other open question).
