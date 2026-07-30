# 02-component-unification

Unify the desktop application around a small set of reusable components, then
extract the coherent design language from them.

Authorized by Bob's 2026-07-30 session (lore
`2026-07-30-ui-unification-braindump`). Supersedes the dropped
`02-app-wide-rollout-design`, which had the order backwards: it would have
ratified a token system top-down before the second consumer of each pattern
existed. Bob's ruling is components first — identify, design one at a time,
integrate into every consumer, and let the language fall out of what shipped.

## The standard

Bob's Excalidraw mockup is the north star: *"the closer we can match it the
better."* The mockup is recorded at
`.lore/items/2026-07-27-control-panel-ui-and-architecture-braindump/`, with
`content/mockup-fidelity-notes.md` naming the parts later rulings superseded —
read it before matching the image pixel-for-pixel, or you will reintroduce
retired features (per-event `sync` buttons, per-element event labels).

The ratified design language is `.loom/tied/2-control-panel-design/`:
`design-language.md`, `control-panel-design.md`, and the living prototype
`mockup-control-panel.html`. Where prose and prototype disagree, the prototype
as last reviewed by Bob wins.

This is **desktop software**. Professional density: icons in toolbars, compact
controls, minimal padding. Touch-sized controls are a mobile concern; where
mobile needs different treatment, it gets a metric override (the shipping
`@media (pointer:coarse) { --row-h: 34px }` is the pattern), not a parallel
layout. The standalone facilitator keeps its tablet-first constraints.

## The evidence base

`.notes/component-inventory-2026-07.md` — Stage A, complete. Ranked ledger of
components, current divergence, consumers, and the dependency sequence the
children below follow. Its headline finding: the app has two disjoint token
layers (`--chrome-*` at 32px/12px in `style.css`, `--row-h`/`--gap` at
24px/6px in `control-panel.css`) with zero files using both, and the rollout is
promotion of the second over the first rather than invention of a third.

## Children, in dependency order

1. `01-component-inventory` — done, tied on delivery.
2. `02-token-promotion` — widen the `--cp-*` layer past `.live-card` /
   `.device-control`; retire `--chrome-*`.
3. `03-chrome-reclamation` — dead heading text, toolbar icon buttons, the
   standalone-view link into the tab bar. Cheap, independent, visible.
4. `04-generator-drawer-component` — lift the drawer chrome out of
   `control-surface.js`; the Show inspector adopts it.
5. `05-value-box-component` — one 58px precision numeric entry everywhere.
   `05b-value-box-spinner-suppression` — follow-up from Bob's review: the
   component face now owns spinner suppression, which had been living on the
   generator drawer's surface-scoped rule alone.
   `05c-drawer-component-ownership` (tied) then `05d-component-ownership-guard`
   then `05e-drawer-base-layer-consolidation` — the
   generalized form of the same defect. The drawer's 68 rules are still scoped
   to the three containers it is mounted in rather than to its own root, so `06`
   and `08` would silently unstyle it at a new mount point; then a browser-free
   guard makes the next instance a test failure. Four instances inside this
   thread is the argument for a check rather than a fourth restatement of the
   principle. `05c` shipped with zero rendered change in all three real hosts
   (`cascade_probe.py`, 27 computed properties × every drawer element) and
   turned up two things the later children need: **a host can also be a
   component root** (`.live-card`/`.device-control` are the control panel's own
   roots as well as the drawer's hosts, so `05d` cannot classify by container
   name without ~40 false positives), and **the drawer has two duplicated base
   layers** in `style.css` and `facilitator.css`, which is a DRY defect rather
   than an ownership one and became `05e`.
6. `06-control-panel-reflow-and-editor` — atomic parameter rows, non-reflowing
   drawer, and the patch editor adopts the shared panel.
7. `07-target-selector-component` — **done, tied 2026-07-30.** One picker, two
   domains (seats/groups and devices), `js/target-picker.js` +
   `css/target-picker.css`; `seat-filter.js` deleted. Selection is per host, the
   focus Seat stays shared — see its `decisions.md`, which `08` depends on.
8. `08-control-tab-columns` — **design gate.** N control-panel columns with
   per-column targets. Carries the load-bearing iframe question.
9. `09-patches-deploy-row` — patch, target, actions on one line.

## Constraints

The system works today and must keep working. Prefer small ordered changes over
rewrites. Each component stitch integrates into **every** consumer before it
ties — a component with one adopter is how the app got two token systems in the
first place. Pre-tie checks are `tools/run-tests.sh fast|browser`; the two
known-red tests (`45-device-enabled-replay-red`, `47-live-param-kinds-flake`)
are pre-existing and not this thread's to fix.

Accessibility remains a constraint throughout: labels, focus order, and
`aria-pressed`/`role` semantics survive the density pass. `design-language.md`
§8 deliberately keys the latching-button radius off `button[aria-pressed]` so
semantics and appearance cannot drift apart — keep that discipline.
