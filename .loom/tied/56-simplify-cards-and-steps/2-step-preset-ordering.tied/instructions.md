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
* **The fade take-over is a SEPARATE defect, and a smaller one than it looked.**
  Bob ruled it across two messages on 2026-08-02:

  > it cancels the fade - if it lands via a preset with interpolation,
  > interpolation starts where the fade left off

  > if a "from" value isn't specified, the parameter should head to it's new
  > destination from where ever that parameter happens to be - either a static
  > value, mid-lfo, or mid-fade.

  **The node already does exactly this, and always has.** `GeneratorEngine.apply`
  (`python/paramgen.py:188-212`) evaluates the live position of whatever slot is
  running and uses it as the origin:

  ```python
  current = self._current_locked(identity, now)
  ...
  elif spec.kind in ("fade", "loop"):
      start = spec.start if spec.start is not None else current
  ```

  `_current_locked` evaluates the running slot at `now`, so a constant, an
  in-flight fade and a mid-cycle LFO all answer correctly. `stop` freezes to the
  same `current`. Cancellation is likewise already shipped: a static `set`
  installs a `constant` slot and displaces the generator.

  **So there is nothing to change on the node, on the wire, or in PD.** Bob,
  correcting an assumption made earlier in this session: *"the pd side of bopos
  doesn't do anything to do with ramps. that's all python. bopos~.pd just
  receives precomputed osc parameters."* Interpolation is node-side Python;
  `[bopos~]` receives precomputed values. **Do not open a `.pd` question here.**

  **The defect is the DASHBOARD MIRROR only.** `record_param_for` is documented
  as *"Update dashboard mirrors without sending"* (`osc_bridge.py:435`), so its
  `from` never reaches the wire — it is what the dashboard *draws*. It reads a
  stale durable value instead of the live position:

  | parameter is… | mirror's `from` | node's origin | mirror correct? |
  |---|---|---|---|
  | at a static value | the static value | same | ✓ |
  | mid-fade | previous fade's DESTINATION | live position | ✗ jumps ahead |
  | mid-lfo / mid-loop | value from BEFORE the generator | live position | ✗ jumps back |

  Mid-fade is wrong because `_store_fade_destination` (`osc_bridge.py:523-527`)
  writes the destination into durable `params[identity]` at fade start; mid-LFO
  is wrong because periodic generators never write durable values at all.

  The fix is to compute the live position the way the node does.
  `_generator_value` (`preset_application.py:196-203`) already does it —
  `python/paramgen.py`'s `_current_locked` is the reference implementation, and
  the two should agree. **It is not cosmetic**: `capture_params` captures FROM
  the mirror and `preset_dirty` compares against it, so a preset saved mid-fade
  currently stores the wrong value.

  **Ruled acceptable — do not engineer around it.** A *free* LFO's node phase is
  "intentionally unknowable" to the dashboard, so the mirror's origin for that
  one case stays an estimate. Bob: *"i don't care - that variation is expected
  and musically useful."*

  **Periodic generators keep their own take-over semantics.** A non-free LFO is
  phase-locked to leader monotonic time (`osc_bridge.py:458-465`) so the fleet
  stays in step; it does not resume from a predecessor's value, and must not be
  made to. Value-continuity applies to a fade's ORIGIN, not to an LFO's phase.
  Two semantics, both deliberate — do not unify them.
* Whether a step should be *allowed* to hold both a reference and a param
  message for the same identity, or whether the inspector should refuse it.
  Bob's stated workflow says allow.

## Verify

A living browser or engine-level guard that authors a step with a reference
plus a param message for the same identity, plays it, and asserts the param
value survives. Fail it against the current tree first — pre-fix it should show
the preset's value, not the authored one.

For the mirror half, assert the dashboard's computed origin against
`GeneratorEngine`'s for the same spec and elapsed time, in all three take-over
cases. That is browser-free and pins the two implementations together, which
matters because they are now required to agree and live in different trees.
