# ap-3 part 2 spec — fades move the real slider (dashboard-side only)

Bob's ruling: for deterministic fades ("lines") the actual slider thumb
must travel. No wire changes; zero extra OSC sends.

## Where things stand

- `facilitator.js paramControl()` renders each numeric live param as
  `<output>` + `.live-param-range-wrap` containing optional
  `.live-param-fade-progress` + `.live-param-marker` + the range input.
- `automationModel()` already computes `elapsedMs`, `periodMs`, and the
  fade `target` from `ParamSpec.phaseAnchor(entry, parsed)`, where
  `entry.sent_at` anchors wall-clock elapsed. `catchupValue` (the
  seat's currently-known value) seeds loop sampling; fades may have
  `from: null` (start at current value) or explicit `from`.
- Cards are re-rendered wholesale (`innerHTML`) on heartbeat/state
  broadcasts, so any animator must tolerate node replacement at any
  frame: keep NO per-node state that matters; re-derive from data
  attributes each frame.
- Take-over: `beginTakeover()` sets `takingOver` on pointerdown for
  automated inputs and `.taking-over` on the label; user drag then sends
  one value and the bridge clears the generator. The animator must never
  fight the finger: skip any input whose label has `.taking-over` (or
  `:active` pointer capture) and stop entirely once `data-automated` is
  gone.

## Required behaviour

1. At render time (`paramControl`), when `model.parsed.mode === "fade"`,
   stamp the range input (or wrap) with:
   `data-fade-anchor` (epoch ms the generator started, i.e.
   `Date.now() - model.elapsedMs`), `data-fade-duration` (= periodMs),
   `data-fade-from` (explicit `parsed.from`, else the seat's current
   value at render), `data-fade-curve`, and `data-fade-segments`
   (JSON `[{value, ms}, …]`).
2. One module-level rAF loop (started when any fade attribute exists,
   stopped when none): each frame, for every stamped input not being
   touched, compute elapsed = now - anchor, walk the segments piecewise
   with the same ramp math the previews use
   (`fraction >= 1 ? 1 : ParamSpec.shapeFraction("saw", fraction, curve)`),
   set `input.value`, and mirror to the sibling `<output>` (same as the
   existing `oninput` mirror — do NOT dispatch events; programmatic set
   must not trigger `send()`).
3. On completion (elapsed ≥ duration): set the final value once, then
   perform the cleanup the old `[data-auto-fade-progress]`
   `onanimationend` handler did (design.md drops that element entirely):
   remove the label's `automated` class, the `.live-param-glyph` and
   `.live-param-marker` nodes, the input's `data-automated`, restore the
   plain `aria-label`, and sync the `<output>`. The loop drops the input
   from its set. Delete the now-dead `[data-auto-fade-progress]`
   forEach block in `bindCards`.
4. `prefers-reduced-motion: reduce`: no per-frame motion — update the
   value at most once per second and once at completion.
5. Aggregate (All/Group) fade rows behave the same (they render from the
   same `paramControl`).

## Acceptance

- A 10s fade visibly moves the thumb (sample `input.value` over time:
  monotonic toward target, reaches it within tolerance at the end).
- During the fade, dragging the slider still takes over exactly as
  before (one datagram, automation cleared) and the loop never
  overwrites the finger's value while pointer is down.
- No `/p/*` OSC traffic is produced by the animation itself.
- No console errors; heartbeat re-renders do not stall or duplicate the
  loop.
