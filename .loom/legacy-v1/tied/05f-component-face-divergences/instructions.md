# 05f-component-face-divergences

The ten rules `05d`'s guard found and allowlisted rather than fixed. Both groups
are the same category — a component's face defined per-surface — but they need
opposite treatments, and one needs Bob.

`ALLOWED` in `tests/test_css_component_ownership.py` names every rule; the guard
turns red the moment one of them is deleted without the entry going too, and
`test_allowlist_entries_still_apply` turns red if an entry outlives its rule. So
this stitch cannot half-land.

## 1. `PrecisionField`'s face lives in four places (8 rules)

| where | width | notes |
|---|---|---|
| `style.css:331` (`.params .precise-input`) | 70px | `--accent-cyan` border |
| `facilitator.css:84` (`.live-param .precise-input`) | 72px | `--accent-cyan` border, 14px |
| `control-panel.css:162` | — | border colour + radius |
| `control-panel.css:366` | 100% | box-sizing, height, padding |

Three widths for one control, and **two of them paint a cyan border that the
ratified palette reserves for modulation** — `05b`/`05c`'s `decisions.md` and
design-language §5 both have cyan meaning "something is driving this." A static
precision field is not modulated, so those borders are wrong on the current
palette, not merely duplicated.

`05` already ratified the answer: `PrecisionField` delegates its face to
`ValueBox`, 58px, `--input`, `--radius-small`. So the fix is to delete these and
let `value-box.css` own it.

**The catch that kept it out of `05d`:** `PrecisionField.attach` has call sites
in `dashboard.js` (the Monitor dock's globals) as well as in the panel, so
deleting the surface rules changes appearance *outside* the panel too. That is
an appearance change and wants the `cascade_probe.py` treatment from
`.loom/tied/05c-drawer-component-ownership/` — measure every host, record the
before/after, and expect deliberate non-zero diffs where the cyan goes away.

## 2. The ∿ glyph diverges from its own design language (2 rules)

`control-panel.css:1585` overrides the shared `.live-param-mod` inside
`.show-param-generator-row`: `border:0`, `border-radius:0`,
`background:transparent`, monospace 15px — a bare glyph.

The panel's own rule at `:194` is design-language §5's **"Always an 18px circle,
exempt from the momentary/latching radii,"** with a border, `--input` background
and an 18px circle.

Both cannot be right. This is **not duplication to consolidate — it is a
contradiction to resolve**, and it is Bob's call, not a refactor:

- If §5's "always" holds, the Show inspector adopts the circle and these two
  rules are deleted.
- If the inspector's bare glyph is right, §5 gains a named second treatment and
  the override moves onto the component as a documented variant (a modifier
  class the component emits), not a host-scoped override.

Do not pick by inspection of which looks better in a screenshot; the ∿ is the
modulation affordance across three surfaces and §5 was ratified deliberately.
Mark `.waiting` on Bob if he is not in the session.

## Sequencing

No hard dependency on `06`–`09`, but group 1 gets easier after `05e` (one drawer
stylesheet already proves the component-stylesheet pattern for a second time),
and group 2 is worth putting in front of Bob whenever he next reviews the panel.
