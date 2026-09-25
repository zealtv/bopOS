# 49-remote-ipad-restyle

**Status:** parked · needs a real iPad (Playwright's `pointer:coarse` isn't a
finger)
**Goal:** restyle the Remote view for iPad touch in one deliberate pass, against
the finished component set.

Bob, 2026-07-30: *"let's let facilitator collapse — we will restyle remote for
iPad as a standalone pass."*

## Background

During UI unification the facilitator's bespoke touch metrics were allowed to
collapse onto the shared components rather than being defended one rule at a
time. Touch devices still get the shared coarse-pointer override (`--row-h` =
34px), just not the old 44px tuning.

Remote is now one `ControlColumn` between a header and footer, and
`facilitator.css` is down to page furniture. So this is a **coarse-pointer
override layer on `control-column.css` + `control-panel.css`** (both documents
load them), plus Remote's own header/footer.

## What actually shrank (measured per collapse)

| component | stitch | delta on Remote |
|---|---|---|
| generator drawer | `05e` | nothing visible |
| target picker | `07` | tabs 44px → 34px chips (12px type); seat `<select>` → **32px-wide** Seat chips |
| card chrome | `08/3` | page gutter 22 → 12px; card padding/radius gone; head 44 → 24px; **`Send all` 88×44 → 54×24** |

Parameter rows were unaffected throughout.

*(Since then `56` retired multi-select for one-target-per-card, so re-measure
before trusting the target-picker row.)*

## Do

- One `@media (pointer:coarse)` metric override layer — a metric override, not a
  parallel layout.
- Tap-target size decided once, as a number with a reason. Start with the three
  smallest: 32px Seat chips, dense 34px roster chips, the `Send all` button.
- Verify on the actual iPad.
