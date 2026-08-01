# 08-generator-drawer

Give every numeric control on the shared surface a `value ▸ gen` mode switch that
opens an inline drawer hosting the generator builder.

**Authority:** `.loom/tied/3-generator-affordance-design/decisions.md` (Bob,
2026-07-25). Bob's stated priority — this lands **ahead of** thread 41 (presets).

**Depends on:** `07-control-surface-component` (the drawer is built once, inside
the component).

## Ratified shape — the three rulings

1. **Drawer, not popover — in every host.** No dense-aggregate variant. One
   affordance, one implementation, no host-conditional behaviour.
2. **Mixed aggregate uses the existing pattern.** Never disabled. Disagreement is
   *indicated* the way the surface already indicates mixed values
   (`state.mixed` / `state.automationMixed`, the `mixed` class, the `auto·mixed`
   readout — reuse them). Any adjustment, value or generator, **sets all
   members**; after it, the aggregate is no longer mixed. **Do not branch on
   `mode === 'gen'`** — that is the defect this ruling exists to prevent.
3. **Stop lives inside the drawer.** The switch stays strictly two-state.
   "Which authoring mode" and "is it running" are independent axes.

## The builder already exists — extract, don't rewrite

`dashboard/static/js/show.js` has the ratified `automation-2` builder:

- `renderParamBuilder` (~648) — the generator `<select>`
  (`value / fade / loop / lfo / stop`) plus `renderParamGeneratorFields`.
- `renderParamPreview` (~682) — the ratified waveform preview, including the
  "random — not previewable" case for `sh`/`drift`.
- compilation to the §3.2 wire grammar via `window.ParamSpec`.

Extract those into something the control surface can host. The Show inspector
must keep working through the same extracted code — two copies of the builder is
the failure mode here.

**Known trap (CLAUDE.md gotcha 10):** changing the generator `<select>`
write-through persists new args onto the focused message. Any test uses one
fixture per generator kind rather than switching kinds in-test.

## Wire

The drawer compiles to the existing `/p/*` §3.2 grammar — no contract change.
Stop emits the ratified stop form; what the value settles to on stop is the
grammar's business, already settled, not this stitch's.

The live path sends `set_live_param`; automation currently arrives through the
Show/OSC path. Establish how a drawer-authored generator reaches the wire from
the control surface, and record the choice in `decisions.md` — this is the one
genuinely open implementation question in the stitch.

## Verification

`tests/` (thread-27 policy). Cover at minimum: the mode switch renders per
numeric row and not on strings/booleans; the drawer compiles to the expected
wire args; stop is inside the drawer; a mixed aggregate is **not** disabled and a
generator commit sets all members.
