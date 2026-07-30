# 05c-drawer-component-ownership

Anchor the generator drawer's styles to the drawer, not to the three places it
is mounted.

`04-generator-drawer-component` made the drawer a component in JS. Its CSS did
not follow: **68** rules in `control-panel.css` are scoped to
`:is(.live-card,.device-control,.show-inspector-section)`, and essentially all
of them name the drawer's own classes:

    .live-param-gen* 15 · .live-gen-* 53

The drawer emits its own root — `<div class="live-param-gen">`
(`param-generator.js:303`) — so every one of those rules could anchor on the
component and instead anchors on its current hosts.

**This is a latent bug with a scheduled trigger date, not tidiness.** `06`
mounts the drawer in the patch editor; `08` puts control panels in N columns.
A mount point outside those three containers loses all 68 rules at once — an
unstyled drawer, not a slightly-off one. `05b` was the same defect at
one-declaration scale (spinner suppression living on `.live-gen-num` inside the
same `:is()` list); this is it at structural scale.

Work:

- Re-anchor the drawer's rules to `.live-param-gen` (or the drawer's own class
  where the rule is about a descendant), dropping the host `:is()` prefix.
- Where a rule turns out to be genuinely host-dependent rather than drawer
  rules-in-the-wrong-place, **leave it and say which and why** in
  `decisions.md`. The count above is an upper bound on what should move, not a
  target to hit.
- Watch specificity. `:is(...) .live-gen-x` and `.live-param-gen .live-gen-x`
  do not weigh the same, and `control-panel.css` has neighbouring rules that
  may currently depend on losing or winning against these. Where a cascade
  order changes, that is a real change to inspect, not a mechanical one.
- Prefer moving the block wholesale to its own component stylesheet
  (`css/param-generator.css`) if that falls out cleanly —
  `css/value-box.css` is the precedent and is currently the only stylesheet in
  the app anchored on a component rather than a surface. If it does not fall
  out cleanly, keep it in `control-panel.css` and say so; the anchoring is the
  point, the file split is not.
- Both documents must load whatever is added: `index.html` and
  `facilitator.html` have different base stylesheets, which is why
  `value-box.css` exists at all.

Verification is the existing coverage: `verify_generator_drawer.py` and
`verify_show_generator_drawer.py` both exercise the drawer in two different
hosts, plus `tools/run-tests.sh browser` whole. A screenshot pair (Control tab
and Show inspector, before and after) is worth taking here because a cascade
slip is visual, not behavioral — the harness is `shoot.py` in
`.loom/tied/02-token-promotion/`, and note the bug that stitch found: it writes
`bopos.theme` while `theme.js` reads `bopos-theme`, so fix the key or expect
light panels in dark shots.

Not this stitch: the guard that prevents recurrence (`05d`), and any change to
the drawer's design, geometry, or markup.
