# 07-target-selector-component — decisions

Calls made while shipping the unified picker. Bob's two rulings from 2026-07-30
are the frame; everything below is either a consequence of them or a judgment
this stitch had to make.

## 1. Shared vs per-host selection — the question the stitch asked explicitly

**Per host, except the focus Seat, which stays shared.**

The instructions required an explicit answer. `SeatFilter` kept two keys: a
shared `bopos.selected-seat` and a per-view `bopos.target-filter-mode`. The new
picker keeps that shape rather than collapsing it:

- The **multi-select selection is per host** (`bopos.target.<host>`). This is
  forced by the next stitch: `08-control-tab-columns` gives each column its own
  target, and one shared multi-selection cannot express N different ones.
- The **focus Seat stays one key** (`TargetPicker.FOCUS_SEAT_KEY`), because the
  documented workflow depends on it: choose a Seat on the Seats tab, open
  Control, land on that Seat. A picker opts in with `followFocusSeat`.

The mechanism is "adopt on change, not on load": the picker records the focus
Seat it last saw and replaces its selection only when that value *moves*. So a
cold load restores the host's own selection (an operator who left Control on All
finds All), while a Seat chosen on the Seats tab during the session still moves
Control — which is the case the shared key existed for. Across the iframe
boundary it arrives as a `storage` event; the heartbeat render is the fallback.

## 2. Same disclosure, two selection models

`multiple: false` is not a second component. Devices are single-select because
the Assets workflow is single-device by design (thread 11b) and a deploy pin
targets one device — so a device choice **replaces** rather than accumulates.
Everything else is shared: chrome, chips, `aria-pressed`, terse state, pruning.

One consequence, decided while looking at the shipped shot: a single-select
picker has **no summary row**. The row exists to remove entries from a mixture,
and with one choice it duplicated the terse state. The pressed chip is the
statement.

## 3. Group selectors differ by domain, on purpose

The Show inspector emits `group:<name>` (portable — a Show travels between
venues; ratified in the entity-architecture review) and the Control surface
emits `g<id>` (live — nothing is persisted into a portable document, and an id
cannot be ambiguous when two groups share a name). The component takes
`groupSelector: "name" | "id"` and carries the other form as the chip's alias, so
a chip lights up for either spelling. That is the same alias mechanism that
already let an older Show document's `g7` match the named chip.

## 4. Selection chrome is purple, and chips are near-square

Design-language §1: cyan means modulation first, selection second; **purple is
the structural accent for focus and selection**. A chosen target is not a
modulated one, so `.target-chip.on` keeps the shipped `--accent` border +
`--selected` face + inset ring, and does **not** take §8's `--mod-fill` latching
face. §8's *shape* does apply — a chip holds state, so it is
`--radius-toggle` (1px), retiring the 15px pill the Show picker had. Chip height
is `--row-h`, down from a hardcoded 32/44px.

Both are pinned in `verify_target_picker.py` so a later stitch cannot quietly
repaint selection cyan.

## 5. The summary label is not uppercase

Design-language §3: "No uppercase transforms in the new language (existing
uppercase labels are repainted during rollout, not imitated)." The Show
inspector's picker summary *was* uppercase with letter-spacing, matching its
sibling field labels. A new component must not imitate that, so the picker reads
`Target  all` in mixed case, visibly different from the `PAYLOAD MODE` labels
beside it until the app-wide repaint reaches them. Deliberate, and directionally
correct rather than locally consistent.

## 6. Label and terse state sit together at the left

The Show original used `justify-content:space-between` to push the terse readout
to the right edge. That is invisible in a 380px sidebar and reads as **two
unrelated labels** once the same component spans a 1280px Control bar — the first
shipped screenshot showed exactly that, with the `▸` marker stranded at the far
left. Grouped left (`Target  all`) reads correctly at every width, so the
component takes that and the Show inspector changes with it.

## 7. Pruning moved into the component

`selectedAssetDevice` used to answer "did the chosen device go away" by mutating
a module variable mid-render. The picker prunes selectors with no chip at render
time — falling back to All, or to the first non-disabled chip where there is no
All — so hosts read a selection that is already valid. That is what let the
Assets host drop its `assetTarget` variable entirely.

Ordering consequence, worth stating because it bit once: `renderAssets` must call
`assetPicker.render()` **before** it reads the chosen device, since pruning is
part of rendering.

**A disabled chip is not a selectable one.** The first version pruned only
selectors with no chip at all, which silently changed shipped behaviour: a device
that went offline while it was the Assets target stayed selected, and the tab fell
to "choose an eligible target" instead of advancing to the next eligible device
the way the `<select>` did. Pruning now skips disabled chips, so the shipped
auto-advance is preserved by the component rather than lost with the host code
that used to do it. Caught by reading the diff, not by a test — hence the new
assertion for it.

## 8. Capture-as-step reduces a mixable selection to a coarse scope

The server's capture vocabulary is `all` / `groups` / one `seat`
(`41-preset-primitive`, ratified). A mixable selection has to reduce to it, and
the reduction lives in `presetScope()`: one Seat and nothing else is that Seat;
anything involving a group is `groups`; All, or several Seats, is the whole
venue. Widening the server's vocabulary was the alternative and is not this
stitch's call.

## 9. The Remote (facilitator) collapse, measured

Per Bob's *"let's let facilitator collapse"*, the five `.target-filter*` rules
died with no attempt to preserve their values, and `49-remote-ipad-restyle` asks
each collapse to **measure** its own tap-target cost rather than inherit the
alarm or `05e`'s reassurance. `touch_probe.py` measured it under iPad-portrait
coarse-pointer emulation:

| retired | declared | replacement (measured) |
|---|---|---|
| `.target-filter button` | `min-height:44px`, `font-size:14px` | 34px tall (`--row-h` coarse), ~42px hit with the `::after` pad, 12px type |
| `.target-filter-seat select` | `min-height:44px`, `min-width:140px` | a row of 32px-wide numeric Seat chips |

So unlike `05e`, this collapse **does** shrink interactive controls: 44 → 34
visible, and a 140px dropdown became 32px chips. The result is recorded in `49`.
