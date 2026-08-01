# 09-patches-deploy-row — decisions

## The open question: `<select>`, not `TargetPicker`

The stitch recorded Bob as unsure the picker was the right object here and asked
for evidence rather than a forced component. **Keep the `<select>`s.** Measured
in the real running app (`probe_target_object.py`), against the Assets tab's
device-domain picker — the component's only existing device consumer, and so
the honest comparison:

| object | height at rest |
| --- | --- |
| `#patch-target` `<select>` | **37px** |
| device-domain `TargetPicker`, closed | **51px** |

Four reasons, in order of weight:

1. **It cannot sit in the line this stitch exists to make.** The deliverable is
   one row of controls. 51px against 37px means the picker sets the row height
   on its own and the two selects and the buttons float inside it.
2. **It is a `<details>`, so it grows in place when used.** A control that
   pushes the buttons down when opened is structurally at odds with "patch, the
   target, and the buttons all in a single line."
3. **Its distinguishing capability is unused.** The picker earns its size by
   handling multi-select and mixtures. This target is exactly one of: the whole
   fleet, or one online seat-bound device — `multiple:false` with an `all`,
   which is a `<select>` with extra chrome.
4. **The Assets picker is there for a reason this row does not share.** It shows
   every discovered device including ineligible ones, each wearing the reason it
   cannot be chosen. The deploy target lists only deployable devices; there are
   no reasons to display.

**The honest cost:** two different device-targeting UIs in one app. Recorded
rather than argued away. It is the smaller cost, and it is the distinction Bob
himself drew when `07` was designed — *"here we're targeting devices rather than
seats. So perhaps a device picker and a seat picker are two different things."*
If a later pass wants one device-targeting object everywhere, the picker will
need a compact single-line mode, and that is a design change to the component,
not something to smuggle in here.

## The layout

`.fleet-patch-choice` is deleted — it existed only to stack the two selects.
The row is now three grid columns: patch, target, actions.

**Capped at 260px and left-aligned rather than stretched.** The first version
filled the panel and gave two 486px selects to hold the word `alpha`. The
deciding evidence is in the same tab: `.editor-launch`, directly below, is
already a left-aligned row of content-sized controls with trailing space. A
stretched deploy row was the odd one out in its own panel, and this thread is
explicitly about less wasted space.

Result: **74px → 37px**, and the panel reads as a toolbar.

Below 760px the three stack full-width exactly as before; one line is a desktop
affordance and the existing breakpoint already said so.

## The sweep

The stitch also asked to sweep the tab for the same class of stacking. Done by
measurement, not by reading markup: every container in `#tab-patches` whose own
height exceeds its tallest control (which is what "the controls are on separate
lines" actually means).

Only `#fleet-patch-panel` and `#manifest-editor` remain, and both are *panels* —
a heading, a control row, a summary — which are supposed to be multi-row.
**The deploy row was the only offender of this class in the tab.**

Worth noting the first version of that sweep used distinct `top` values and
reported five false positives including the fixed row itself: the buttons are
shorter than the selects and centred against them, so equal tops is the wrong
test and flags a correct layout. The guard below avoids the same trap.

## The guard

Two assertions added to `tests/verify_device_patch_targeting.py`, the living
journey that already drives this surface, rather than a new file.

They measure "the row is no taller than its tallest control" plus a shared
vertical centre. Confirmed to fail on the pre-change tree with the exact
numbers — `{'height': 74, 'tallest': 37, 'centreSpread': 43}` — which is also a
compact record of what the defect was.

## Verification

See `verification.md`.
