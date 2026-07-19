# p4-step-list-scrollbox — worklog

2026-07-19, autopilot session. Implementation delegated to GPT 5.5 (codex)
against `codex-spec.md`; results in `codex-report.md`.

- `.show-rows-box` wraps only the rows: 480 px default (~14 compact
  rows), 160 px minimum, internal scroll, native `resize:vertical` for
  desktop plus a full-width 10 px pointer-capture drag handle for touch.
  Height and scrollTop live in module variables and are re-applied
  across every rebuild; renders are gated during a drag (one pending
  render applies on pointerup) so the captured handle is never replaced
  mid-drag; hidden-tab zero-height measurements are ignored so startup
  broadcasts can't erase the default.
- Add bar (and handle) sit outside the box — y-position independent of
  step count; a one-shot pending-add flag scrolls only the newly created
  step into view, so later renders never yank the list.
- Console first-paint: investigation found the panels already started
  closed with the right heights; the demonstrable defect was blank
  summary counters until first traffic. Startup now closes both panels
  and renders once, deterministically showing "0 shown · 0 seen".
- No tied amendments needed; regenerated screenshots restored by codex.

Verification (orchestrator-run): `verify_show_scrollbox.py` 12/12 PASS
at 768×1024 touch; tied 5b and 6b re-run green. Codex ran the full
ten-suite acceptance green (its report). CSS reviewed — the diff's
`!important`s are the pre-existing `.show-check` block, untouched.
