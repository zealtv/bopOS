# Decisions

## The guard asks about ownership, not about container names

`tests/test_css_component_ownership.py`, browser-free, in `fast`. A component
registry maps class-name prefixes to components, resolved by **longest prefix**
so `.live-param-gen` (drawer) is not swallowed by `.live-param` (panel). For each
selector, the **innermost identified component owns the rule**; any different
component further left is merely hosting it, and styling across that boundary
fails.

`05c`'s finding drove this: `.live-card` and `.device-control` host the drawer
*and* are the control panel's own roots, so ~40 legitimate rules name them. An
earlier draft required the ancestor to be a component *root*; that was dropped
because ownership already answers the question, and requiring root-ness let
`facilitator.css:84` (`.live-param .precise-input`) through.

## Reading right to left, not from the last compound

Keying the subject off the final compound selector alone missed **15 of `05c`'s
68 rules**, because most drawer subjects are bare elements —
`:is(hosts) .live-param-gen input` is a drawer rule whose subject is an `input`.
Scanning every compound right-to-left and taking the innermost owned class fixes
it. Detection went 51/68 → **66/68**, the remaining two being positioning-only
and therefore correctly permitted.

## Two bugs found by testing against the real defect, not a paraphrase

The first working version reported the reverted `05c` file as **clean**. Two
causes, both of which a hand-written fixture hid:

1. **Comma-splitting broke `:is()`.** Splitting the selector list on every comma
   turned `:is(.live-card,.device-control,.show-inspector-section) .live-gen-num`
   into fragments whose host was `.show-inspector-section`.
2. **That host was unregistered**, so the fragment resolved to no component.

My self-test used a two-host paraphrase ending in `.device-control` — registered
— so it passed while reality did not. `split_selector_list` now respects
parentheses, `.show-inspector-section` is registered, and the self-test asserts
the **verbatim** shipped selector. The general lesson is worth keeping: *a guard
verified only against its own fixtures is not verified.* Reverting the real
commit is the check that counts.

## Property allowlist, not a comment opt-out

A surface may **position** what it hosts (margin, order, grid/flex placement,
inset, z-index — `POSITIONING`). It may not restyle it. An inline-comment escape
hatch was considered and rejected: it gets used the first time the guard is
inconvenient, which is the failure mode the guard exists to prevent. A property
list is bounded and reviewable.

## Ten pre-existing violations: allowlisted with an owner, not suppressed

Fixing them means changing appearance, which a guard stitch has no business
doing. Each entry names `05f-component-face-divergences`, and
`test_allowlist_entries_still_apply` fails if an entry outlives its rule, so the
allowlist cannot rot into a permanent suppression.

- **8 rules — `PrecisionField`'s face in four files** at three widths
  (100%/72px/70px), two of them painting an `--accent-cyan` border that the
  ratified palette reserves for modulation. Not just duplication: those borders
  are *wrong* on the current palette.
- **2 rules — the ∿ glyph.** Not duplication at all. The Show inspector
  overrides the shared `.live-param-mod` to a borderless transparent monospace
  glyph, while design-language §5 says it is "always an 18px circle." That is a
  contradiction in the ratified language and Bob's to resolve, so `05f` carries
  it as a question rather than a refactor.

Finding these was the guard paying for itself before it had run twice — neither
was known when `05d` was written.

## Known limitations, stated rather than discovered later

- **Runtime-attached classes are invisible.** `PrecisionField` adds `.value-box`
  in JS, so `.live-card .live-param output` reads as a bare-element subject. The
  guard sees source text only.
- **Unregistered surfaces are invisible.** A new container styling a component
  passes until someone adds it to `COMPONENTS`. This is why the registry carries
  a comment telling the next author to give a new component a distinguishing
  prefix — a component whose classes cannot be told apart from its host's is
  precisely the defect being guarded.
- Not a CSS parser. Hand-rolled block walk over the subset this app writes.
