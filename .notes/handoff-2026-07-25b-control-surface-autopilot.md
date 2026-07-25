# Handoff — thread 37 complete: control surface, generators, Control tab (2026-07-25)

Second autopilot session of the day. Bob ratified the four control-surface
designs with feedback, confirmed the hardware test passed, and asked for the
whole implementation sequence in one session. **All of it shipped.**

## State of play

**Thread 37 is complete and tied — eleven stitches.** The loom has **no loose
ends**; everything remaining is `.waiting` on Bob.

An operator can now target a patch to one device independently of the fleet
*and* interact with that device: per-device live controls on the Device tab,
generators authorable from any numeric row, a renamed **Control** tab with a
reusable target filter, and a "Set patch…" hand-off from a device to the
pre-scoped Patches picker.

## Bob's rulings, and the two that changed the design

Recorded in `decisions.md` in each tied design stitch (`.loom/tied/3`–`6`), and
the proposal HTML was corrected to match rather than left contradicting them.

| Gate | Ruling |
|---|---|
| Generator | drawer everywhere (no popover variant); mixed aggregates use the **existing** pattern with no `mode === 'gen'` branch; stop **inside** the drawer |
| Placement | collapsed by default; offline = disabled showing last values; one code path; **device actions move up** below diagnostics |
| Control tab | Dashboard → Control; seat filter as a **reusable component**; cues at top (provisional); presets follow the filter |
| Hand-off | ordinary Seat for standalone devices; tab switch, one picker |

**Two corrections, not approvals:**

1. **Deployment stays on the Patch tab.** Only the *Dashboard* tab becomes
   Control, and Control hosts no picker. Proposals 02 and 04 both assumed a
   Control-tab picker.
2. **"Pinned" stays patch-only.** A seat-bound standalone device gets an
   ordinary Seat and no new vocabulary. (This was a collision Bob's note would
   have introduced against shipped `patch_pinned` code.)

## Commits on `main` (not pushed — Bob's call)

- `448b5dc` — ratifications, corrected artifact, five stitch instructions.
- `a53ff0d` — **07** extract `control-surface.js`.
- `5efbd7c` — **08** generator drawer + `param-generator.js` + `set_live_automation`.
- `213092d` — **09** Device-tab control panel + per-device schema.
- `491f8e8` — **10** Control rename + `seat-filter.js` + scoped presets.
- `1f44883` — **11** Set patch… hand-off.

## Architecture worth knowing

- The live surface was **inside `facilitator.js`**, which the Control tab embeds
  by **iframe**. It is now `control-surface.js`, hosted by both pages. The
  component never touches the wire — the host's `send` callback does, which is
  the seam that lets one renderer serve fleet fanout and a single device.
- `param-generator.js` is the automation-2 builder extracted from `show.js`;
  the Show inspector delegates to it. Its tied guard passes 9/9 unchanged.
- A **pinned device** carries its own `live_controls` (its patch's promoted
  params) on the device payload from `public_device` — *not* `public_state`,
  because `device_update` broadcasts carry one device.
- Cross-document state between the parent page and the iframe is **shared
  `localStorage` plus the `storage` event**. That is what "the global selected
  seat" means in practice.

## New durable tests (all in `tests/`, per thread-27 policy)

| File | Checks |
|---|---|
| `verify_control_surface_component.py` | 11 |
| `verify_generator_drawer.py` | 38 (whole scenario run twice: agreeing and mixed seats) |
| `verify_device_control_panel.py` | 12 |
| `verify_control_tab.py` | 15 |
| `verify_set_patch_handoff.py` | 14 |

Full suite green at wind-down, including `verify_device_patch_targeting`
(14/14), `verify_live_param_checkbox`, `verify_precision_param_input`, all 14
`tests/test_*.py`, and the tied guards `automation-2-show-builder-gui` (9/9)
and `automation-5-waveform-marker` (19/19) run from copies.

## Bugs the verifiers caught (worth the tests existing)

1. **Label-swallowed clicks** — the value/gen switch sits inside the row's
   `<label>`, so clicking "gen" also toggled the labelled checkbox.
   `preventDefault()`.
2. **Wrong broadcast seam** — a pinned device's schema published from
   `public_state` never reached the client.
3. **Temporal dead zone** — refreshing the preset shelf from `activateTab`
   touched `presetNames` before its `let`, so opening straight onto Control
   threw and killed the whole script.
4. **Shadowed global** — the hand-off crumb's handler, written inside
   `renderFleetPatch`, resolved `select` to the local `<select>` element rather
   than `select(uid)`, so "back" silently did nothing.

## Left for Bob / other threads

- **`41-preset-primitive`** — its blocker is gone: the generator affordance now
  exists. Stitch 10 fixed only the *scoping rule* and reserved the shelf; what a
  preset captures, how it loads, and generator interpolation are still 41's.
- **`27-tied-guard-rot`** — still awaiting Bob's fresh session.
- **Cue placement** — "let's try cues up the top" is provisional by Bob's own
  framing. The strip is self-contained so it can move.
- **Seats-detail overflow** — the Device panel gives per-device controls a home,
  which was the substantive fix. Whether anything in the Seats inspector is now
  redundant is a UX call, not a silent deletion.
- **Hardware:** none of this session's five stitches has been exercised on a
  real Pi. The wire paths are simfleet-verified (including a real generator
  engine ticking), but audible behaviour and PD-side response to
  `set_live_automation` remain a rig check.

## Known flake, not ours

`verify_live_param_checkbox.py` failed its slider check once in four runs. The
test focuses the slider and presses a key, but `focus()` does not set the
`interacting` render guard — only `pointerdown` does — so a heartbeat re-render
between focus and keypress destroys the target element. Pre-existing; left
alone rather than fixed opportunistically.

## Protected worktree items left untouched

`dashboard/shows/test.json` and
`.notes/handoff-2026-07-24-control-surface-presets.md` were **not** staged in
any commit — every commit staged explicit paths.
