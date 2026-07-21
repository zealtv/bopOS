# 23-waveform-marker-guard-regression

The tied guard `.loom/tied/automation-5-waveform-marker/verify_waveform_marker.py`
**fails on `main`**, independently of any uncommitted work.

Observed 2026-07-21 (autopilot session, thread `19-show-chrome-fixes`), at
`2d69554` with the working tree clean:

```
playwright._impl._errors.TimeoutError: Page.wait_for_selector: Timeout 30000ms exceeded.
  - waiting for locator(".seat-card[data-live-id=\"0\"] label[data-param-path=\"fade\"] [data-auto-fade-progress]") to be visible
```

Confirmed twice — once by the stitch-04 delegate, once by the orchestrator
with `dashboard/static/css/style.css` stashed. It is a **Dashboard-tab
seat-card automation marker** selector, unrelated to the Show-tab chrome work
of threads 18 and 19, all of whose own suites are green.

Every other tied suite passes: `02-inspector-sidebar`,
`04-named-section-dividers`, `05-compact-chrome`,
`02-edit-bar-and-inline-step-name`, `03-responsive-osc-terminals`,
`01-inspector-toggle-overlap`, `02-step-and-divider-icons`,
`03-divider-rule-styling`, `04-lfo-period-field-width`,
`ap-1-fade-inspector-layout`, `automation-2-show-builder-gui`,
`automation-3-animated-takeover`.

## The question to settle

Either the runtime automation marker regressed after `automation-5` was tied
(a real defect — promoted live controls stop showing automation progress), or
the guard itself went stale (its fixture/timing assumption no longer holds).
Find out which before changing anything.

## Next action

Reproduce, then bisect the guard's failure back to the commit that changed
its behaviour (`git log --oneline` over `dashboard/static/js/` since
`automation-5` was tied is the short list). Then either fix the runtime
defect, or — if the guard is stale — repair the guard with an inline comment
naming what changed and why, the pattern used in
`.loom/tied/03-divider-rule-styling/decisions.md`.

## Notes

- The harness declines to execute scripts under `.loom/tied/`. Copy the guard
  into your stitch directory and run the copy — the repo-by-marker root
  lookup survives the move, and it also spares the tied screenshots from
  being regenerated.
- Run everything from `~/.venvs/bopos/bin/python`; see `CLAUDE.md`
  "Dashboard browser tests" for the Playwright gotcha list.
