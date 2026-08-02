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
* **The fade case is not an ordering problem** and probably cannot be solved by
  ordering. A param message that lands on top of an in-flight fade for the same
  identity has to either cancel the fade for that identity or lose. Decide
  which, and say so; the §3.3 generator-slot grammar already has a `stop` form
  worth looking at first.
* Whether a step should be *allowed* to hold both a reference and a param
  message for the same identity, or whether the inspector should refuse it.
  Bob's stated workflow says allow.

## Verify

A living browser or engine-level guard that authors a step with a reference
plus a param message for the same identity, plays it, and asserts the param
value survives. Fail it against the current tree first — pre-fix it should show
the preset's value, not the authored one. Cover the `duration_ms` case
separately; it may need a different answer.
