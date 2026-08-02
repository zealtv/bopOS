# 53-ui-niggles

Nine small, independently shippable UI corrections from Bob's 2026-08-02
review of the shipped app. None is a design gate; each is a ratified change
with a stated outcome.

Bob's words, verbatim, so a later reader can check the stitches against the
ask rather than against my paraphrase:

> the theme button can be a bit smaller so it has some vertical padding when
> the view is wide

> in the inspector in the show tab. when i click generator, the value box
> remains (fine), but if i set the phase of an lfo, for example, the value box
> disappears. there is the affordance of clicking the value button - but that
> is confusing and the disappearance is unexpected. instead - the parameter
> should display a parameter slider (the same component as in the control
> panel), with the same behaviour as the control panel. visible automation
> where possible. clicking and dragging the slider or number box sets to static
> value. if automation is messy from a ui/ux perspective, simply have the
> generator icon remain blue is enough to indicate the generator is active.
> choose whichever approach is cleanest.

> The asterix isn't visible on a preset name when it has been modified if the
> name is too long. put the asterix at the start. move new, save, and delete
> into the dropdown, at the top, with icons, separated from presets by a
> divider. lose the edit button.

## Children

1. `1-theme-control-height` — the header's theme `<select>` is exactly as tall
   as the header. Smallest of the three; do it first.
2. `2-show-inspector-param-row` — the Show inspector's parameter builder loses
   its value field the moment a generator is chosen. Mount the shared
   `ControlSurface` row instead. The largest of the three, and the one with a
   judgment call inside it (Bob named the acceptable fallback).
3. `3-preset-dropdown-menu` — the preset row's dirty marker is invisible on a
   long name, and `new`/`save`/`del` sit behind an `edit` disclosure that Bob
   wants gone. This one changes a shipped component that four surfaces mount;
   read its stitch before assuming it is small.
4. `4-card-strokes-and-remote-bar` — follow-up on the new target cards: make
   group identity independent of Seats-map visibility, cap card tracks, and
   keep Remote's master/mute controls visible as one responsive live bar.
5. `5-left-packed-flex-cards` — review follow-up: left-pack cards and let them
   flex between 340px and 560px without spreading sparse rows apart.
6. `6-remote-card-flow` — screenshot follow-up: give Remote's nested cards
   region the same explicit wrapping flex flow as Control.
7. `7-remote-host-selector` — correct stitch 6's selector to Remote's actual
   same-element host/component structure.
8. `8-remove-control-width-lock` — reset the retired 342px direct-child flex
   rule that prevents Control cards from growing.
9. `9-equal-card-tracks` — use equal tracks so incomplete final rows retain the
   same card width as every preceding row.

The first three touch different files and can be worked in any order; their
stated order is by size. The last six followed Bob's reviews of the
subsequently shipped cards work.

## Standing constraints for all three

* **`tests/test_css_component_ownership.py`** (browser-free, in `fast`): rules
  belong to the component's own root, not to the surfaces it is mounted in. Its
  allowlist is deliberately **empty** — do not add to it.
* **One metric layer.** `--row-h`, `--gap`, `--radius-*`, `--pad-control`,
  `--pad-panel`, `--header-h`, all at `:root` in `css/control-panel.css`, the
  one stylesheet both documents load. `--chrome-*` is gone; do not reintroduce
  a third layer or a bare pixel where a token exists.
* **Design-language §12** (`tests/verify_ground_and_card.py`): `--bg` is the
  workspace ground and shows only as gutter between cards.
* Pre-tie: `tools/run-tests.sh fast` and the relevant `browser` journeys.
