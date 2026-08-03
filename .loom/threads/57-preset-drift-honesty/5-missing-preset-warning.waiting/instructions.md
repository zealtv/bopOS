# 5-missing-preset-warning

**`.waiting` on Bob's ruling.** One question, and it is a scope question, not a
technical one.

## The gap

A show step referencing a **deleted or corrupt** preset produces **no warning
at all** today. `show_reference_warnings` only compares fingerprints; it never
looks for the preset file. At playback the failure lands in `log.warning`
(`dashboard/server.py:1760-1764`) and the step **silently does nothing** — the
worst possible time to find out, and no cue anywhere before it.

`preset_store.list` already retains invalid entries with an `error`
(`preset_store.py:369-377`), so the store has the information; the show path
just never asks.

## Why it is parked rather than bundled

`1-resolution-authority` reads preset bodies, so detecting this becomes nearly
free once it lands: `presets[slug]` absent or `error` set →
`missing_preset`, `severity: "warn"`, collected per (patch, slug) like its
siblings.

But it **adds a warning** during a pass whose whole purpose is removing false
ones, and Bob's standing instruction is *"I want to fix and simplify things
before making them more complicated."* Adding it on the implementer's own
authority would be exactly the drift that instruction exists to prevent.

## The question for Bob

Should a Show step pointing at a preset that no longer exists say so in the
Show tab, or is the silent playback skip acceptable?

Arguments both ways, briefly:

* **For:** it is a genuine broken-show condition, it is the only one of the
  four warn-level codes that reports something *unrecoverable*, and finding out
  at playback is finding out too late.
* **Against:** it is one more line in a panel this thread just spent four
  stitches emptying, and a deleted preset is arguably visible enough from the
  inspector dropdown, where the slug will not resolve.

If ruled in, this is a small stitch: one code, one branch in
`show_reference_warnings`, one pin in `tests/test_show_model.py`, and one
fixture in `tests/test_preset_application.py` that deletes a saved preset out
from under a reference. It should follow `1`, and it needs nothing else.
