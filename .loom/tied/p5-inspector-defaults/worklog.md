# p5 inspector defaults — worklog

## Shipped

- Canonicalized every missing/empty step `then_actions` list to one `stop`
  action on load, creation, and update.
- Rendered the first then-action as non-removable while keeping appended rows
  removable.
- Replaced the always-open target picker with a native disclosure carrying the
  terse wire selector in its summary. Existing and pasted messages default
  closed; a newly added message defaults open; state survives ordinary Show
  re-renders while the message remains focused.
- Added the p5 amendment to `.notes/show-tab-design-2026-07-18.md`.

## Verification

- `node --check dashboard/static/js/show.js` — pass.
- `PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python -m
  py_compile dashboard/show_model.py
  .loom/threads/15-show-polish/p5-inspector-defaults.stitching/verify_show_inspector_defaults.py`
  — pass.
- `git diff --check` — pass.
- `verify_show_inspector_defaults.py` — 19 checks, 0 failures. It drives the
  real dashboard in Chromium and covers model entry points, disk normalization,
  then-row authoring, disclosure defaults and persistence, target editing,
  pasted messages, and disabled cue/point targeting.
- `.loom/tied/2-model-and-persistence/verify_show_model.py` — pass, including
  real server/WebSocket persistence and restart.
- `.loom/tied/5-inspector/verify_show_inspector.py` — 9 checks, 0 failures.
- `.loom/tied/5c-target-model-and-picker/verify_show_targets.py` — 10 checks,
  0 failures after the expected amendment below.
- `.loom/tied/p4-step-list-scrollbox/verify_show_scrollbox.py` — 12 checks,
  0 failures.
- Visual taste pass: `inspector-defaults.png`; the expanded disclosure keeps
  the terse selector legible and the existing chip hierarchy intact at the
  touch viewport.

All browser/networked verifies were rerun outside the agent socket sandbox on
temporary loopback ports. No hardware, audible engine, or physical iPad run was
required for this authoring-only change.

## Tied verifier amendment

`5c-target-model-and-picker/verify_show_targets.py` now opens the p5 disclosure
before clicking its first Seat chip. No target-model or send-semantics assertion
changed.

## Delegation experiment

GPT-5.6 Luna max was tried for the whole bounded stitch, then GPT-5.6 Sol high
and medium for the one-file verifier. Each spent heavily on repository
orientation without producing an edit, so each was stopped at a bounded
checkpoint and the work was completed locally. For this repository, delegate
startup should use a distilled context/worktree or a task large enough to
amortize the mandatory orientation read.
