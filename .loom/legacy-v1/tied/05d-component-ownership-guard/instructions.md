# 05d-component-ownership-guard

Make "a rule is living on a surface instead of on the component" a test failure
rather than something Bob notices by eye.

Three instances got past careful review inside this thread alone: the
`--chrome-*` / `--row-h` token split (`02`), the three Seats rules that silently
widened numeric fields to 64/80/88px (`05`), and spinner suppression scoped to
the drawer (`05b`). `05c` is the fourth and largest.

**A written rule will not catch the fifth.** The principle was already stated,
in a comment, directly above the offending rule — `control-panel.css` argued
that "browser arrows in one of them and not the others is exactly the
incoherence this pass closes" and then shipped that suppression scoped to three
hosts anyway. Restating it in `design-language.md` is worth doing (see below)
but is the *least* valuable of the available moves.

Work:

- Add a source-level check to `tests/` — browser-free, so it runs in
  `tools/run-tests.sh fast`. It scans the app's CSS and fails when one selector
  names **both** a host container and a component class.
- Host containers today: `.live-card`, `.device-control`, `#device-control`,
  `.show-inspector-section`. Component classes are the ones a component's own
  JS emits. Derive the lists explicitly and in one place in the test, with a
  comment saying how to extend them, because the next component will need to be
  added by hand.
- **Allow positioning.** A surface legitimately places a component: margin,
  grid/flex placement, `order`, `align-self`. Allow a narrow **property**
  allowlist rather than an inline-comment escape hatch, so exceptions stay
  visible and bounded — a comment opt-out would be used the moment the guard is
  inconvenient, which is the failure mode this whole stitch exists to prevent.
- Fail with a message that names the file, the selector, and the offending
  property, and states the fix ("anchor on the component's own root"). A guard
  whose output does not say what to do gets suppressed.
- **Do not add stylelint.** A new dependency and config file to express one
  project-specific rule the repo can state in ~20 lines of Python. The two
  source-level assertions at the end of `tests/verify_value_box_component.py`
  are the pattern to generalize.

Sequencing: after `05c`, because the guard is red until the drawer's 68 rules
are re-anchored. If `05c` decides some rules are legitimately host-scoped, this
stitch either allowlists them explicitly or the guard is wrong — reconcile in
`decisions.md`, do not weaken the check silently.

Then, and only then, state the rule in prose: a component owns everything about
its own appearance, including resets and suppressions; a surface may position a
component but never restyle it. That line belongs in the design language `02`
extracts at the end of the thread, alongside the structural convention
`value-box.css` demonstrates — one stylesheet per component, selectors anchored
on the component's own root.

Also carry forward the observability note from `05b`, which is the same class of
lesson about guards: a native shadow-DOM control's *absence* is observable
headlessly by neither DOM nor pixel probe, so assert the declaration. It
belongs with CLAUDE.md's Playwright gotcha 11.
