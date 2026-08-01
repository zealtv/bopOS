# Codex report — p2 exclusive playback and progress

## Changes

1. **Exclusive playback:** `ShowEngine._begin()` now stops every other uid in
   `self.playback` through `_stop_step()` before installing the requested uid.
   This applies to manual starts and every then-action path, and includes paused
   steps. Restarting the same uid still cancels and replaces its own timer.

2. **Armed snapshot uid:** `snapshot()` now returns
   `{"steps": <unchanged map>, "armed": <uid or null>}`. `armed` is recomputed
   from the current document on every snapshot and is non-null only with exactly
   one active step and exactly one deterministic then-action. It resolves
   `next_step`, `previous_step`, `next_section`, `previous_section`, valid
   `goto`, and `play_again`. Empty actions, explicit stop, missing goto targets,
   random `any_in_section` / `other_in_section` actions, and multiple actions
   expose `null`; randomness is never pre-resolved.

3. **Progress fill:** each playing or paused row with a positive duration and a
   finite remaining time renders a `.show-step-progress` layer whose clamped
   width is `1 - remaining / duration_s`. The existing 500 ms render tick grows
   it while playing; paused remaining time freezes it. CSS positions the layer
   behind row content with a subtle green tint and an amber paused tint, without
   changing layout.

4. **Armed pulse:** rows matching `playback.armed` receive
   `.show-step-armed`. A 1.8 s border-colour keyframe pulse provides the ready
   indication without changing layout or replacing the active row's inset
   playing/paused accent.

## Tied-verifier amendments

`.loom/tied/3-playback-engine/verify_show_engine.py` was amended minimally:

- The initial full-payload assertion now expects the additive `"armed": None`.
- The old “both playing” precondition for `stop_all_steps` now asserts that only
  the latest-started step is playing before stop-all clears it.
- Its older `bind(("127.0.0.1", 0))` allocator was rejected by the managed
  environment before product code ran. It now uses the current house pattern of
  explicitly selected random loopback ports, matching the newer Show verifiers.

The compact-row and target-picker verifiers refreshed their tracked screenshots
while running; those two generated changes were restored because screenshots
were outside this stitch's authorized file list.

## Verification

Static checks:

- `git diff --check` — pass.
- `PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python -m py_compile dashboard/show_engine.py .loom/threads/15-show-polish/p2-exclusive-playback-and-progress.stitching/verify_show_exclusive.py .loom/tied/3-playback-engine/verify_show_engine.py` — pass.

Required acceptance commands:

- `~/.venvs/bopos/bin/python .loom/threads/15-show-polish/p2-exclusive-playback-and-progress.stitching/verify_show_exclusive.py` — pass, 9 checks, 0 failures.
- `~/.venvs/bopos/bin/python .loom/tied/3-playback-engine/verify_show_engine.py` — pass, 32 checks, “All checks passed.”
- `~/.venvs/bopos/bin/python .loom/tied/p1-zero-value-and-transport-bugs/verify_show_polish_bugs.py` — pass, 6 checks, 0 failures.
- `~/.venvs/bopos/bin/python .loom/tied/4-tab-ui/verify_show_tab.py` — pass, 8 checks, 0 failures.
- `~/.venvs/bopos/bin/python .loom/tied/5-inspector/verify_show_inspector.py` — pass, 9 checks, 0 failures.
- `~/.venvs/bopos/bin/python .loom/tied/5b-compact-rows/verify_show_compact.py` — pass, 12 checks, 0 failures.
- `~/.venvs/bopos/bin/python .loom/tied/5c-target-model-and-picker/verify_show_targets.py` — pass, 10 checks, 0 failures.
- `~/.venvs/bopos/bin/python .loom/tied/6-message-editing/verify_show_editing.py` — pass, 18 checks, 0 failures.
- `~/.venvs/bopos/bin/python .loom/tied/6b-show-management/verify_show_management.py` — exit 0 (this invocation emitted no captured check lines).

The focused verifier's first development run found that its first paused-width
sample occurred during the optimistic-client to authoritative-server pause
handoff. The verifier was corrected to settle that broadcast before taking its
two frozen samples; the required final run passed all checks. Two combined-suite
launch attempts also encountered transient managed-sandbox loopback allocation
denials before product code ran; each exact verifier was rerun individually and
passed as recorded above.

## Not done / boundaries

- No `.pd` files, show schema, or existing `show_playback.steps` fields were
  changed.
- No Loom claim, status, tie, or other state command was run.
- No hardware, iPad/touch, or physical-audio verification was performed; the UI
  checks used headless Chromium against the real dashboard server and simfleet.
- No commit was made.
