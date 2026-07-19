# automation-2 notes — 2026-07-20

Implementation delegated to GPT 5.6 Sol via codex (`spec.md` is the settled
design; `codex-a2-result.md` summary retained in session scratch). Orchestrator
reviewed the diff, fixed the seam codex correctly flagged, and ran all
verification locally.

## What landed

- `dashboard/static/js/show.js`: `parseParamArgs` (mirrors
  `python/paramgen.py::parse_message`), generator-mode builder (value / fade /
  loop / lfo / stop), canonical short-option emission (`p:`/`f`/`c:` order),
  unit-suffixed duration strings, round-trip inference without rewrite-on-focus,
  labelled raw fallback for invalid forms, one-row-loop refusal, string params
  constant-only.
- `dashboard/static/css/style.css`: compact segment/LFO layout classes.
- **Spec correction found by the delegate:** Show playback only forwarded
  `args[0]` for `/p/*`. Fixed by the orchestrator:
  `dashboard/show_engine.py` now passes the full arg list and
  `dashboard/osc_bridge.py::set_param` accepts a list (scalar callers
  unchanged). The handoff's claim that playback already delivered args
  unchanged was wrong for `/p/*`.

## Verification (run by orchestrator, 2026-07-20)

- `node --check dashboard/static/js/show.js` — OK.
- `verify_show_param_builder.py` (this dir) — 27/27 PASS (real server +
  simfleet + headless Chromium). Two fixture bugs fixed during bring-up:
  string params cannot carry a string `default` (manifest validator allows
  numeric defaults only), and added segment rows default to `1s` so the test
  now selects `ms` explicitly.
- `.loom/tied/6-message-editing/verify_show_editing.py` — 0 failures.
- `.loom/tied/automation-1-engine-and-parity/verify_param_automation.py` —
  0 failures.
- `.loom/tied/show-transport-spot-fixes/verify_show_transport_spot_fixes.py` —
  1 pre-existing failure ("progress uses a continuous CSS animation") that
  reproduces identically on unmodified HEAD `96202eb` in this environment
  (3/3 runs; element handle detaches mid-measure). Not a regression of this
  stitch; left for investigation (see handoff).
- `git diff --check` — clean.
