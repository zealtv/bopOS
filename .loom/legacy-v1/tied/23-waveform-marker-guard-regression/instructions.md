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

**Superseded by the 2026-07-21 findings below** — at the time of writing, every
other tied suite was believed to pass: `02-inspector-sidebar`,
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

## More red guards on `main` (found 2026-07-21, later the same day)

This stitch was written believing the waveform marker was the *only* red guard.
It is not. Threads `21-theme-cyan-tint` and `22-listener-range-ux` each turned
up further pre-existing failures on `main` while re-running tied suites. They
are unrelated to each other and to the waveform marker; this stitch is now the
collection point for all of them, so **treat the list as four independent
investigations, not one**.

Confirmed pre-existing (each verified by stashing the in-flight work, so none is
caused by the thread that found it):

1. **The waveform marker** — the original, above. Still unsettled.
2. **`verify_bop_palette` / `verify_theme`, two assertions** — found by
   `21-theme-cyan-tint` and **already repaired in place** on the way past
   (see `.loom/tied/21-theme-cyan-tint/`): a literal `rgb(30,138,132)` that
   never matched the actual `#147772`, and Show pill colour trios written
   against dark that `theme-1`'s system-preference following left reading
   light. Recorded here for the pattern, not as outstanding work — both were
   guard mechanics, not runtime defects. **The lesson is the one worth
   keeping: a guard asserting a literal colour that never matched means it was
   passing for the wrong reason, or not being run.**
3. **`07-seats-workspace`, three failures** — found by
   `22-listener-range-ux/02`. Reported as `dashboard.js` text scrapes plus an
   `osc_bridge` binding issue. **Not yet investigated at all** — this is the
   real outstanding item alongside the waveform marker, and a binding failure
   is the sort of thing that is a genuine runtime defect rather than a stale
   assertion. Start here if you only have appetite for one.

## The broader question

Four red guards across three suites, all pre-existing, all found incidentally by
threads that happened to re-run neighbouring suites — that suggests tied guards
are not being run routinely, and are rotting quietly between the sessions that
touch their area. Worth deciding whether a periodic full sweep of `.loom/tied/*/
verify_*.py` belongs in the workflow, and saying so to Bob. Do not build that
sweep as part of this stitch without raising it first.

## Notes

- The harness declines to execute scripts under `.loom/tied/`. Copy the guard
  into your stitch directory and run the copy — the repo-by-marker root
  lookup survives the move, and it also spares the tied screenshots from
  being regenerated.
- Run everything from `~/.venvs/bopos/bin/python`; see `CLAUDE.md`
  "Dashboard browser tests" for the Playwright gotcha list.
