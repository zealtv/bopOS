# 2-step-preset-ordering

**BUG.** A step holding a preset reference *and* a `/p/*` param message applies
them in the wrong order, and the preset wins. So "fire a preset, then change a
couple of things" — the workflow Bob called natural and explicitly kept when he
removed capture — does not work.

Found by the systems consult, then **verified directly in the code**
(2026-08-02), not taken on the agent's word.

## The mechanism

`show_engine.py:146`:

```python
def _emit_messages(self, step):
    for message in step["messages"]:
        self._send_message(message)
```

The loop is synchronous, but the two message kinds leave it by different doors:

* a **`reference`** calls `self.apply_preset(...)` → `queue_show_preset`
  (`server.py:1694`), which is `self.spawn(...)` — it creates a task and
  **returns immediately**. Nothing has been sent yet.
* an **`osc`** message falls through to `resolve_targets` and sends
  **synchronously, in the same loop turn**.

So for an authored order of `[reference, /p/x]` the param goes out first, and
the preset lands afterwards and overwrites it.

**Authoring around it does not work.** Putting the param message second is
already the natural order and is what fails. And with a `duration_ms` on the
reference, the §3.3 fade keeps writing `/p/x` for the whole fade duration, so
no arrangement of a synchronous send survives it.

## Scope

This is **independent of capture** and survives `1-capture-retirement` — it is a
property of playback, not of how a step was authored. After R5, hand-authoring
is the *only* path, which is what promotes this from cosmetic to blocking.

## What to settle

* **Where the ordering guarantee lives.** The honest fix is probably that
  `_emit_messages` awaits a reference's application before continuing, so
  authored order is wire order. Check what that costs: `queue_show_preset`
  takes `supervisor_lock`, and `_emit_messages` is called from
  `show_engine.py:227` inside step start — a step that blocks on a slow apply
  may delay its own timer arm.
* **The fade case is not an ordering problem** and cannot be solved by
  ordering. **Bob ruled it 2026-08-02:**

  > it cancels the fade - if it lands via a preset with interpolation,
  > interpolation starts where the fade left off - which i assume is how lfos
  > and loops also behave?

  Three things were then verified in code, and the ruling lands differently
  against each:

  1. **Cancellation already ships.** A static value message pops the
     automation entry for that identity (`osc_bridge.py:482-489`). Nothing to
     build; the ruling ratifies existing behaviour.
  **Bob generalised the ruling, 2026-08-02:**

  > in the case of a fade taking over, if a "from" value isn't specified, the
  > parameter should head to it's new destination from where ever that
  > parameter happens to be - either a static value, mid-lfo, or mid-fade.

  This is broader than the mid-fade case below, and re-siting it makes the fix
  **smaller**, not larger. `record_param_for` is documented as *"Update
  dashboard mirrors without sending"* (`osc_bridge.py:435`), so the `from`
  discussed here is a **display guess and never reaches the wire** — the node
  receives whatever was authored, with no start when none was written. The
  defect is the dashboard's PICTURE of the fade, in all three of Bob's cases:

  | parameter is… | mirror's `from` today | correct? |
  |---|---|---|
  | at a static value | the static value | ✓ already right |
  | mid-fade | the previous fade's DESTINATION | ✗ jumps ahead |
  | mid-lfo / mid-loop | the value from BEFORE the generator started | ✗ jumps back |

  `_generator_value` (`preset_application.py:196-203`) already computes the
  live position for all three kinds; the mirror has to ask it instead of
  reading `prior`. No PD edit, no contract change — which **retires the
  "exact continuity is node-side" framing** recorded a message earlier in the
  same session, which wrongly treated the dashboard mirror as controlling.

  It is not cosmetic even so: `capture_params` captures FROM the mirror and
  `preset_dirty` compares against it, so a wrong take-over origin means a
  preset saved mid-fade stores the wrong value. One case stays inexact by
  design — a **free** LFO's node phase is "intentionally unknowable", so its
  estimate uses the authored phase. That is a display estimate, not a control
  error.

  **The open question is now Bob's and it is a PD one:** when `[bopos]`
  receives a fade with no start, does it ramp from its current output? If yes,
  the fleet already behaves as ruled and only the dashboard was lying. If it
  ramps from the last *received* value, the wire behaviour needs Bob's `.pd`
  edit too, and the dashboard fix alone would make the picture right while the
  sound stays wrong. **Ask before building** — the answer decides whether this
  is one change or two, and agents do not edit `.pd`.

  2. **"Starts where the fade left off" is the OPPOSITE of today's
     behaviour**, and this is the actual work.
     `_store_fade_destination` (`osc_bridge.py:523-527`) writes the fade's
     **destination** into the seat's durable `params[identity]` the moment the
     fade starts, and a new fade's origin is
     `spec.start if spec.start is not None else prior` where `prior` is that
     durable value (`osc_bridge.py:474`). So a fade taking over an in-flight
     fade starts from where its predecessor was *heading*: it jumps forward,
     then interpolates. **Open question for Bob, do not decide alone:** the
     dashboard can compute the live position (`_fade_value` already does,
     from `from` + segments + `sent_at`) and author an explicit `start`, but
     the NODE runs the interpolation, so a dashboard-authored origin is off by
     roughly the network latency and the take-over carries a small
     discontinuity. Exact continuity is node-side, which is PD and therefore
     Bob's. Put the two options to him with the size of the error measured, not
     estimated.
  3. **LFOs and loops do NOT behave this way, deliberately — Bob's assumption
     is the one part to drop.** A non-free LFO records `phase_at_send_ms` from
     **leader monotonic time** (`osc_bridge.py:458-465`) and `_lfo_value`
     derives position from that absolute clock; loops share the same path
     (`preset_application.py:196-203`). The point is fleet phase-lock — every
     device must sit at the same point in the cycle, so a periodic generator
     cannot continue from a predecessor's *value* without breaking sync. The
     code calls free-LFO node phase "intentionally unknowable."

  So the system carries **two** take-over semantics on purpose: fades are
  value-continuous, periodic generators are phase-locked. Do not unify them.
* Whether a step should be *allowed* to hold both a reference and a param
  message for the same identity, or whether the inspector should refuse it.
  Bob's stated workflow says allow.

## Verify

A living browser or engine-level guard that authors a step with a reference
plus a param message for the same identity, plays it, and asserts the param
value survives. Fail it against the current tree first — pre-fix it should show
the preset's value, not the authored one. Cover the `duration_ms` case
separately; it may need a different answer.
