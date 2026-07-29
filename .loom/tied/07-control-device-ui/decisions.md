# Decisions — 07-control-device-ui

Date: 2026-07-29. Worked in parallel with `08-editor-save-recall`; the two
share one server-side preset surface and one row component, so several notes
below are referenced by that stitch's `decisions.md` rather than repeated.

## The row is the designed slot, made live

`7-preset-slot` shipped the anatomy inert. Nothing about it was redesigned:
patch name, dropdown, `new`/`save`/`del`, in the same place between the panel
head and the parameter rows. What changed is that the controls do something and
the visually-hidden "presets are not built yet" note is gone.

## Superseded — the facilitator loses the row entirely

Bob's Q4 ruling for `41-preset-primitive` is that the standalone
facilitator/iPad surface carries **no preset affordance at all** — removed, not
inert. This **supersedes decision 1 of the tied stitch
`desktop-ui-overhaul/01-control-panel/7-preset-slot`** ("the row is per panel,
not per privileged card"). The two hosts share one `liveCard()`, so the row is
now gated on `embedded`: the Control tab iframe renders it, the standalone page
does not. Same reasoning as `04-event-fire-affordance` — an iPad fires, it does
not configure.

Two living guards pinned the shipped inertness and were updated in place with
an inline note, per CLAUDE.md's interim supersession rule:

- `tests/verify_control_tab.py` — "every preset control is inert" and "each
  inert control explains that presets are future work" became "the preset row
  is live, not a placeholder";
- `tests/verify_device_control_panel.py` — the same `live == 0` clause.

## What the browser is allowed to know (C3)

Preset **bodies** never reach a client. Three things do:

- `preset_catalog`, a per-patch listing of `{slug, name, saved, schema,
  revision, valid, error, drift}`. It is parked on the runtime state dict so
  every `state` broadcast carries it — a partial broadcast must not momentarily
  empty every dropdown — and is absent from `durable()`, like automation.
- per-target `applied_preset` + derived `preset_dirty`, already published by 06.
- the apply report, broadcast as `preset_applied`.

`drift` is derived server-side by comparing the stored schema fingerprint to
the patch's current one, so a row can warn *before* an apply instead of only
reporting dropped entries afterwards.

## Apply broadcasts state as well as the report

06's atomicity note says "one persist + one broadcast per apply". The persist is
still one. The broadcast is now two messages: the ordinary `state` publication
every live write makes, then the additive `preset_applied` report. Without the
first, a card learns its provenance but never the values that were just written
— there is no periodic full-state broadcast to fall back on. The report says
what the apply *did*; `state` is how a surface renders the result. 06's living
test was updated to assert the pair, with the reason inline.

## Save is a preview, then a compare-and-swap

`preview_preset_capture` answers with exactly what a save would store —
canonical values, and the identities omitted because the target's Seats
disagree. The drawer lists both: a tick per capturable identity (all ticked by
default — capture-everything) and the omitted set stated plainly. That is F8:
a silent sparse omission surprises on the next apply, so it is stated *before*
the write.

`save_patch_preset` re-captures server-side rather than trusting the browser's
preview, filters to the ticked identities, and writes through the 05 store's
revision token. A stale token is refused with a refresh-and-retry message, and
the file is untouched.

Capture happens before the revision check, so a target with nothing agreed
fails with "nothing to save" rather than a conflict. That ordering is
deliberate: there is no document to compare-and-swap until one has been
captured.

## Offline

Applying stays legal offline — the values are dashboard state, and
`replay_live_params` sends them when the node returns. Capturing from a device
you cannot hear is refused (F8): the Device panel's `new`/`save`/`del` disable
while the device is offline, the dropdown does not. The Control tab's Seat card
follows the same rule.

## Reports and mixed

The report renders as one compact line with a `<details>` disclosure — never a
modal. It carries per-verdict drift detail and the skipped-target list. A
report is matched to the row whose concrete targets it covers **exactly**: the
broadcast carries no card key and any client's apply produces one.

A card whose targets carry different presets shows the panel's existing mixed
idiom — the dotted `·····` placeholder, with "mixed" in the accessible name.
Derived dirtiness renders as the `Dawn *` asterisk on the option itself.

## Verification

`tests/verify_preset_control_surface.py` (new) covers apply from the dropdown,
provenance, the derived asterisk after a nudge, the mixed card, the save
round-trip with include/exclude and the omitted-as-mixed marking, the stale
revision refusal, delete, the absent facilitator row, and the offline save
gate. `tools/run-tests.sh fast` and `browser` are green.

One pre-existing defect was fixed in passing because the new fixture trips it:
`facilitator.js` `deviceForSeat()` threw on an All card in a venue with no
Seats.
