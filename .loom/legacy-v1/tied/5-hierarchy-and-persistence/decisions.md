# 5-hierarchy-and-persistence — decisions and evidence

Authority: the tied `2-control-panel-design` stitch — `design-language.md` §9
(hierarchy accordions), §4 (the 12px drawer indent, reused here), and the
`.branch` rules in `mockup-control-panel.html`.

## What shipped

`dashboard/static/js/control-surface.js`:

- A nested address is now a **`<details class="live-param-branch">`** with a
  `<summary>` disclosure row and its children in a
  `.live-param-branch-kids` wrapper, replacing the always-open
  `<section>` + `<h3>`. `data-param-branch` is unchanged, so existing
  selectors that reach *through* a branch still resolve.
- **`<details>` does the showing and hiding.** The toggle handler writes the
  outcome and nothing else — no `requestRender`, no re-render on a collapse.
  This is the same idiom the facilitator already uses for
  `details[data-command-uid]`.
- **Collapsed state lives in `localStorage`** under
  `bopos.control.collapsed-branches` (a JSON array of keys), read once per
  `paramTree` render and written on toggle. Absent means open, so a fresh
  browser, a cleared store and a storage-denied context all land on today's
  always-open panel.

`dashboard/static/css/control-panel.css` §14 carries the ratified chrome:
`▸` / `▾` drawn as the summary's own `::before` (both the default list marker
and the `-webkit-details-marker` are suppressed, so the glyph is ours on every
engine), children at `margin-left:12px`.

## Calls made inside the ratified design

1. **The key is `scope:branch/path`, with no target id.** The instruction says
   "keyed by scope + branch path" and that is also the behaviour that makes
   sense: the Control tab renders one card per Seat off one manifest, so
   collapsing `reverb` on a Seat card collapses it on every Seat card. The
   operator is pruning the manifest, not one card. Scope is still in the key,
   so pruning the All view does not prune the Device panel.
2. **localStorage, not module state, even though `openDrawers` is module
   state.** Drawer state is deliberately ephemeral; a pruned tree is meant to
   survive a reload. It also has to cross the iframe boundary — the Control
   surface is an iframe and the Device panel is the parent document, and
   storage is the only channel they share (CLAUDE.md gotcha 15).
3. **Re-opening deletes the key rather than storing `open`.** The store only
   ever holds pruning, so it cannot accumulate entries for branches the
   operator has restored, and a manifest that loses a branch leaves no
   residue.
4. **The base stylesheets keep a branch rule.** `style.css` and
   `facilitator.css` were rewritten to `> summary` / `.live-param-branch-kids`
   rather than deleted, so the tree still reads as a hierarchy if
   `control-panel.css` is ever not loaded. Their indent moved from
   `padding-left` to `margin-left` so the panel rule *overrides* it instead of
   stacking with it — the old facilitator narrow-width `padding-left:9px`
   override would otherwise have summed to 21px, so it is gone. The 12px
   indent is now the ratified value at every width.
5. **The left rule is retired.** The shipping chrome drew a 1px `--line`
   border down the left of a branch; the design's indent-only treatment
   replaces it (mockup `.branch > .kids` has no border).

## Verification

`tools/run-tests.sh browser` — **12/12 pass**.

New living checks in `tests/verify_control_surface_component.py`, section (f):
a branch is a `<details>` open by default with the `▾` glyph and 12px child
indent; clicking the summary collapses it and swaps the glyph to `▸`; the
collapse survives a **heartbeat re-render** (proved by stamping the node and
waiting for its replacement) and a **reload**; the stored key is exactly
`["seat:filter"]`; re-opening restores the children and empties the store.
`PARITY_JS` gained a `data-branch-key` normalization for the same reason it
already normalizes `data-gen-key` — the key embeds the scope.
`tests/verify_manifest_param_visibility.py` moved its branch assertion from
`h3` to `> summary`.

Screenshots: `control-tab-{dark,light}.png` (open),
`control-tab-collapsed-{dark,light}.png`, plus the carried-over drawer and
device-panel shots, captured with `shoot_accordion.py`.

## Not verified here

- `tools/run-tests.sh fast` has **one failure that predates this stitch**:
  `test_device_control_routing.test_reappearing_physical_device_replays_persistent_enabled_state`.
  Reproduced on a stashed clean tree. Note for the record: `4-row-regrind`
  recorded it as passing when the module runs alone — it now **fails
  standalone too**, so it has got worse independently of this work. Nothing
  here touches that path; it wants its own stitch.
- Touch feel of the summary as a hit target on the standalone facilitator is a
  hardware/tablet judgment call, not claimed verified.
