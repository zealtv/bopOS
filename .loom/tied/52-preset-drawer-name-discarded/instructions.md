# 52-preset-drawer-name-discarded

**A preset name typed into the save drawer is discarded by the next heartbeat
re-render.** Operator-facing, and reproducible 3 times out of 3.

## Reproduce

`probe_drawer_typing.py`, kept here. It opens the Control tab's preset save
drawer, types `Dawn`, waits ~3 s with a 0.5 s-heartbeat simfleet running, and
reads the field back:

```
  typed into the field: 'Dawn'
  focus right after fill: INPUT/preset-name
  still there after ~3s of heartbeats: ''
  input node was replaced: True
  VERDICT: DISCARDED by re-render
```

Focus is *in the field* and the node is replaced anyway.

## Why it matters beyond the annoyance

It is the cause of the remaining browser-suite red. `verify_preset_control_surface.py`
fails at its **first** assertion, `wait_catalog(page, 1)` after
`save_from_row(...)`, in full-suite runs 0, 4 and 5 (it passed 2 and 3, and
passes standalone and 4/4 under concurrency). The chain is exact: `fill` writes
the name → a heartbeat re-render replaces the input and resets it to the stored
`""` → `commit`'s handler reads `name === ""` and bails without sending →
`preset_catalog` never gains an entry → the wait times out.

So the "flaky preset journey" that threads `47` and `50` have both circled is,
at least in part, this defect. `50` fixed a genuine host-scoping bug in the same
journey's helper; it was not the whole story.

## What is already known — and what is contradicted

`control-surface.js:487-488` *intends* to prevent exactly this:

```js
// Editing a name or ticking boxes must survive the heartbeat, the same
// guard the generator drawer and precision field use.
drawer.onfocusin = () => context.setInteracting?.(true);
drawer.onfocusout = () => context.setInteracting?.(false);
```

The guard is wired end to end — `control-column.js:125` passes `setInteracting`
into the surface context, `control-host.js:110-111` implements both halves, and
`control-column.js:354` consults `isInteracting()` before rebuilding the cards.
**It does not hold, and why is not yet established.**

Two hypotheses were tested and neither explains it:

* **Gotcha 16 (the handler is bound after the node exists).** Waiting for
  `drawer.onfocusin` before typing changed the result from 0/3 surviving to
  1/3 — a real effect, not the cause.
* **The `interacting` flag never being set.** One instrumented run (a temporary
  `window.__probeInteracting` in `control-host.js`, since reverted) read
  `interacting === false` immediately after focus — but that same run was the
  one that *survived*, so it is not a clean datapoint and must be redone.

Note `control-surface.js:356` also has no write-through: the field is emitted as
`value="${esc(name)}"` from the `openSaveDrawers` entry, and nothing puts what
was typed back into it. So even a correctly-held render guard only defers the
loss to the first render that does happen — a second, independent defect in the
same few lines.

## Where to start

Instrument the *sequence*, not the end state: log every `setInteracting` call
and every `renderCards` entry with a timestamp, and find the render that runs
while focus is in the drawer. `focusout` fires when the focused node is removed,
so the log must distinguish the render that caused the loss from the
`setInteracting(false)` that follows it — reading only the final state cannot,
which is what made the two hypotheses above look plausible.

Then decide between:

1. making the guard actually hold (fixes typing, and the caret/focus loss with
   it), and
2. write-through on `oninput` into `openSaveDrawers` (makes the value survive
   any render at all, guard or no guard).

They are not alternatives — (2) without (1) still moves the caret to the end of
the field on every heartbeat, and (1) without (2) leaves the value at the mercy
of any render the guard does not cover. Both, probably, but establish the cause
before writing either.

Check the sibling surfaces while there: the same drawer is mounted on the Device
panel and in the patch editor, and `verify_preset_editor.py` drives the same
`fill` → `commit` sequence.

## Prior art

* `46-control-surface-probe-race`, `47-live-param-kinds-flake` — the same
  family; `47` widened this very guard to cover keyboard focus.
* `50-state-broadcast-argument` — fixed the host-scoping half of this journey's
  flakiness and recorded the run-by-run evidence.
* `51-control-column-first-render-flake` — found this while verifying its own
  fix; its `verification.md` has the run table.
