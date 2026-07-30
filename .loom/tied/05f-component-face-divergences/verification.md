# Verification

Passed on 2026-07-30:

```text
./tools/run-tests.sh fast
Ran 255 tests — OK
  including tests.test_css_component_ownership with ALLOWED now EMPTY:
  all ten pre-existing violations discharged, none re-scoped

./tools/run-tests.sh browser
19/19 browser verifiers passed
  verify_precision_param_input.py — the living guard for this control
  verify_control_tab.py, verify_device_control_panel.py — the real panel rows
  verify_show_generator_drawer.py — now asserts §5's circle in the third host

python precision_probe.py --doc dashboard|facilitator  → precision-*.txt
```

## The ∿ ruling is now a test, not a note

`verify_show_generator_drawer.py` asserts `border-radius:50%`, 18×18 and a
non-zero border on the Show inspector's mod glyph — deliberately in the surface
where §5 had been untrue, not in the panel that owns the rule.

It **failed on first run** at `height:24px` and found a shipped defect: §6 set
`height` but not `min-height`, so the generic `button{min-height:var(--row-h)}`
made §5's circle an 18×24 oval in the control panel for as long as it has
shipped. Fixed in §6; the assertion now passes.

## Precision field deltas

`precision-dashboard.txt` / `precision-facilitator.txt`. Both `patch-editor` and
`bare-div` report **unchanged** in every state, which is the finding that matters:
two of the four duplicated definitions (70px and 72px) were already losing on
source order, so those surfaces already rendered the component's 58px face.

Live deltas are `padding: 0px 4px -> 0px 5px` in the panel rows, and the focus
ring going cyan → purple in the patch editor and Show inspector.

## Not verified

- **No screenshots.** Three changes are visible by design — the ∿ becoming a
  circle in the Show inspector, the focus ring going purple outside the panel,
  and 1px of padding in the panel rows. The suites prove geometry and ink
  numerically; they do not prove it *looks* right. Worth an eye on the Show
  inspector and Patches tab.
- **The probe's `width` column is not trustworthy** for the panel rows (its host
  template is not the real 58px grid — see `decisions.md`). Width is covered by
  the real-panel verifiers instead.
- No Firefox, no physical device, no iPad, no Pure Data, no audible checks. CSS
  and one test assertion only; no markup or JS behaviour changed.
