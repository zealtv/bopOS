# 11-ground-and-card-audit

Sweep every tab for design-language **§12** (ground and card) and fix what the
named stitches did not already cover.

Bob's 2026-07-30 tab-by-tab review found three surfaces in three different
states, which is the signature of per-surface drift rather than a theme problem:

| surface | state | owner |
|---|---|---|
| Remote | **correct** — chrome, ground, card. The reference implementation | — |
| Show step list | rows sitting on ground, gaps showing pink | `05g` |
| Control tab | iframe painted `--bg` and bordered; panel "swimming in empty space" | `06` + `08` |

Bob's own summary of why Remote works: *"the pink defines the workspace from the
chrome."* That is the entire job of the ground. Anything more reads as unfinished.

## Work

Run this **last** in the thread, after `05g`, `06`, `07`, `08` and `09` have each
fixed the surface they own — otherwise this stitch collides with all of them.

- Grep first: `background:var(--bg)` anywhere outside `html`/`body`, and any rule
  with a `border`/`border-radius`/inset-shadow and no background. Those two
  patterns are the whole defect class.
- Walk every tab in both themes at 1280 and 1680: Show, Control, Seats, Devices,
  Patches, Assets, plus the Monitor dock and the Remote view. Squint. You should
  see chrome, then ground, then cards — never ground inside a card's footprint,
  never a control on ground.
- `.tab-panel` is `background:transparent` and that is **correct** — it is the
  ground's window. The fix is always to give the *content* a card, never to paint
  the panel.
- Where a surface is already right, leave it and say so; the point is a known
  state for every tab, not a diff on every file.

## Consider promoting the check

`05d`'s `tests/test_css_component_ownership.py` shows the shape of a cheap
browser-free CSS invariant. `background:var(--bg)` outside `html`/`body` is
mechanically detectable in the same way and would keep §12 from drifting back the
way component ownership did four times. Worth adding if the audit finds more than
one or two instances — if it finds none beyond the known three, a test guarding a
rule nobody breaks is not worth its maintenance.

Verification is screenshots, in both themes, since §12 is a visual invariant.
Record the "correct" surfaces too, so a later reviewer can tell audited-and-fine
from never-looked-at.
