# Progress

2026-07-27 — Complete. Bob's four review calls on the shipped kinds.

## 1. Pulse instead of an invented cue

One rule now decides it, in `paramControl`: a control **tracks** its
generator's value only if it is the numeric row *and* either the fade (which
the rAF animator samples every frame) or a marker-bearing LFO/loop (whose
marker paints the exact position). Everything else — every toggle, every
enum, and the LFO shapes the runtime cannot know (sample+hold, drift) —
gets `auto-pulse` on the row: a 1.4s cyan breath on the control's own ring.
The 50%-duty toggle flash from stitch 6 is gone.

The pulse is anchored the way the marker is. Without that it restarted on
every heartbeat re-render and never reached its own peak. The anchor is the
**wall clock**, not each generator's elapsed time, so every pulsing row on
the panel breathes together rather than beating against its neighbours — the
pulse means "a generator owns this", not "here is its phase". The period is
emitted from JS onto the row (`--pulse-period`) so the module and the
stylesheet cannot disagree about it. `prefers-reduced-motion` gets a steady
ring.

## 2. The number box under a generator

**Architectural, and ratified.** An LFO's and a loop's position are painted
by a CSS animation (design-language §10: "CSS animation for periodic shapes,
rAF for fades — the shipping mechanism"), so no JavaScript holds the value
between heartbeats; the box was showing the last heartbeat's number beside a
marker that had moved on. Per Bob it now shows the mixed dots in the
modulation ink. A **fade keeps its number** — the rAF animator writes it
every frame, so it is honest.

## 3. The toggle

A PD toggle box: a square latching button the height of the row, marked `✕`
when on, with the parameter name beside it. It sits in the value-box column,
so a toggle row and a numeric row start their names at the same x. The enum
row already had this shape; the two now read as one grammar.

## 4. `label` — the string kind

Kept, and its role clarified rather than invented: `type: "s"` is in the
ratified kind table (`control-panel-design.md` §2 — "text box, no ∿, `/p/*`
string, no automation") and predates this thread; the fixture param happens
to be *named* `label`, which is what made it look like a new UI type. What
was genuinely wrong is the height: the row was 44px because the hosts size
their own text fields for tablet chrome. It is now `--row-h` like every
other kind, with the name to its left. Removing the kind is a one-line
change if Bob wants it gone — flagged, not assumed.

## Verification

- `tools/run-tests.sh browser` — all twelve green.
- `tools/run-tests.sh fast` — 184 tests, one failure: the standing red
  `45-device-enabled-replay-red`.
- New living checks in `verify_control_surface_component.py`: the square
  ✕-marked box with its label beside it, the one-row-tall string row, and a
  four-way pulse matrix (LFO box shows dots but does not pulse; fade keeps
  its number and does not pulse; toggle and enum pulse with
  `live-param-pulse`).
- Fixed a real flake while in here: `verify_live_param_kinds.py` used
  `focus()` + `keyboard.press()`, and a heartbeat re-render between the two
  swallowed the keystroke — that was the file's one intermittent failure in
  the tier. `locator.press()` re-checks actionability. Four consecutive
  green runs after.
- Re-shot the panel dark/light, unified/mixed, plus two pulse frames half a
  period apart.

The now-superseded "toggle flashes its live value" line in the tied
`design-language.md` §6 carries an inline supersession note pointing here, so
nobody re-implements the retired flash from the ratified document.
