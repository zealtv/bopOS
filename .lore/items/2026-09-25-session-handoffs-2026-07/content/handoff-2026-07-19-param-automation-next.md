# Handoff — 2026-07-19: parameter automation GUI next

## Start here

The next implementation stitch is exactly:

```sh
./.loom/loom.sh claim automation-2-show-builder-gui
```

Do not claim automation-3 or automation-4 alongside it. Work one stitch,
verify, tie, commit, and pause. Before claiming, read `CLAUDE.md`, this handoff,
and `.loom/threads/16-param-automation/automation-2-show-builder-gui/instructions.md`.

At handoff there are no Loom claims. Bob's untracked `dashboard/shows/` is the
only worktree item and must remain untouched/un-staged.

## Landed authority and implementation

- `automation-0-design-ratification` — commit `1e7082e`: Bob's ratified design
  is in `.lore/items/2026-07-19-param-automation-design-ratified/`; the wire
  grammar is OSC contract v1.8 §3.2.
- `automation-1-engine-and-parity` — commit `9a9e875`: shared parser and
  generator engine in `python/paramgen.py`, numeric-param integration in
  `python/bopos.py`, and simfleet parity in `tools/simfleet.py`.
- `15-show-polish` and its post-close transport spot fixes are tied. The latest
  implementation commit is `7162943`; do not reintroduce per-step
  `forward_sync`, message edit/copy buttons, Stop-all/count UI, full-DOM
  countdown renders, or stepped progress.

The parent automation instructions have been corrected: the grammar is
ratified, automation-0/1 are complete, and automation-2 is next.

## Settled grammar — do not re-derive

One last-message-wins generator slot exists per manifest-declared numeric
`/p/*` identity:

```text
x                              constant
x duration                     fade current → x
x y duration                   explicit x → y fade
a duration b duration ...      multi-segment fade
loop a duration b duration ... looping segment list
stop                           freeze current output
lfo shape min max period [p:n] [f] [c:n]
```

- Durations are bare milliseconds or strings such as `250ms`, `10s`, `1.5m`,
  `2h`; no beats/bars reach the wire.
- Shapes: `sine`, `tri`, `saw`, `square`, `sh`, `drift`.
- Dashboard output uses canonical short options `c:`, `p:`, `f`; the parser
  also accepts `curve:`, `phase:`, `free`.
- Options trail, keywords lead. Phase is 0..1. Phase/free are LFO-only; curve
  is invalid on a constant; odd segment lists reject.
- A true loop requires at least two destination/duration pairs. The existing
  parser intentionally treats a short one-pair `loop` as a normal fade.
- Only `f`/`i` declarations automate. String params stay plain set-only; the
  proposed string/mixed-array manifest kind still has no name or wire plane.
- Musical time, per-segment curves, square duty, and audio-rate modulation are
  deferred. Never edit engines or `.pd` patches for the GUI stitch.

## automation-2 implementation seam

The Show message schema already persists ordered typed OSC args, and Show
playback already forwards them unchanged. Build a compiler/editor in
`dashboard/static/js/show.js`, not a second server-side generator model.

Primary functions:

- `renderParamBuilder` — current constant-only parameter inspector.
- the message-editor `change` handler — currently writes one value arg.
- `typedArg` — preserves numeric declaration typing and OSC strings.
- `wirePreview` — must show the exact compiled canonical args.
- `manifestFromStagedPatch` — source of qualified declaration type/range.

The UI needs constant / fade / loop / LFO / stop modes; editable segment rows;
duration-unit fields; one curve exponent; LFO shape/min/max/period/phase/free;
and an honest round-trip parser for existing message args. Focusing or
re-rendering a message must not rewrite it. Invalid/hand-authored forms need an
honest raw fallback rather than silent coercion. String declarations expose
only constant mode.

Follow the landed p5/p6 inspector density and keyboard rulings. Preserve the
p7 target picker semantics and the `7162943` selective-render/CSS-progress
behavior.

## Verification runway

First confirm the engine baseline:

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/tied/automation-1-engine-and-parity/verify_param_automation.py
```

Automation-2 needs a focused real-dashboard + simfleet Playwright verifier
that authors every generator kind, checks the exact typed/canonical wire form
in the outgoing console or simfleet receipt, reloads/re-focuses to prove
round-trip state, and covers string-param fail-closed behavior plus browser
errors. Start from:

- `.loom/tied/p3-global-transport-and-cue-lead/verify_show_transport.py`
- `.loom/tied/p5-inspector-defaults/verify_show_inspector_defaults.py`

Required adjacent regressions:

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/tied/show-transport-spot-fixes/verify_show_transport_spot_fixes.py
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/tied/6-message-editing/verify_show_editing.py
```

Use `node --check dashboard/static/js/show.js` and `git diff --check` too.
Browser verifies bind random loopback ports and may require sandbox escalation.
They can regenerate tracked screenshots; restore those artifacts unless the
stitch intentionally changes and reviews them.

## After automation-2

1. `automation-3-animated-takeover`: locally simulate sent generators on every
   promoted-control surface with zero added OSC traffic; touch sends one plain
   value and freezes at the taken-over constant.
2. `automation-4-waveform-ux-gate`: write the app-wide waveform UX proposal,
   mark the stitch waiting, and stop for Bob's ratification before implementing
   waveform visualisation.
3. Resume the host-loom `patch-workflow-friction` docs/starter-kit close-out
   only after thread 16, so it documents the finished system.

Long-standing hardware and `scene-sequencing` co-design waits are unchanged.
