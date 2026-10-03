# Node daemon tidy — verification

2026-10-03. Behaviour-preserving software cleanup; no hardware, audible or live
Pd verification claimed. No `.pd` files edited or devices contacted.

## Changes

- Removed eight redundant transport-error wrappers: identify, groups,
  assignment, unassignment, point delivery, provided-term relay, load reply
  and event fire. `send_to_engine` itself remains unchanged: it serializes
  sends, catches `OSError` / pyOSC3 `OSCError`, rate-limits its warning and
  reports delivery with a bool. Unexpected programming exceptions are not
  reclassified as transport failures.
- The ready-context path still checks that bool and returns False for retry.
  Best-effort traffic still attempts its sends without a new retry/buffering
  policy. `relay_provided_term` still returns True for a handled term when the
  engine is down; the LAN dispatcher ignores that return, and changing it to
  a delivery receipt would be a separate behavioural change. Point delivery
  still attempts each shaped element even when a send returns False.
- `notify_engine` constructs the same `/notify ,s <event>` message for
  identify, framework update, shutdown, reboot, checkout and engine restart.
  Notification order, arguments and lifecycle actions remain unchanged.
- One `FingerprintCacheWarmer` implements both inventory warmers. Each kind
  retains its own lock/thread, at most one active warm, daemon workers,
  best-effort `nice(10)`, cache loading before warming, and the same warning
  text. The public warm/initialise wrappers and their root defaults remain;
  fingerprint walking and persistence stay in the unchanged identity module.

## Boundaries and decisions

- `/id` stays float on assignment/unassignment and int on `/config` and
  ready replay. Contract §4.2 does not explicitly fix the tag; the reference
  guide's integer spelling alone does not authorize changing engine-visible
  packets. `id-type-proposal.md` records the contract/Pd inspection and an
  int32 recommendation for Bob. No new Pd edit is needed by that proposal,
  so `64-pd-edits-owed` is untouched.
- Import setup remains unchanged. `import-assessment.md` records why moving
  the server/state/callback/lifecycle globals needs a coordinated initializer
  and fixture change beyond this cheap tidy. Eleven living test modules
  currently import bopos; the existing fake constructors remain sufficient.
- Waiting stitch 68 and its Git patch-route surfaces stay untouched. In
  particular the clone-confirmation wrapper and switch/pull notification
  blocks remain for its Phase 2 rather than being refactored here.
- Compared ASTs against HEAD: `send_to_engine`, `deliver_engine_context`,
  `config_callback`, clone/pull/switch callbacks, fetch worker and exit handler
  are unchanged. Compared callback registration, atexit and `__main__` startup
  text: unchanged. Contract, Pd adapter, simfleet and audition files unchanged.
  The protocol modules imported by simfleet/audition were not modified.

## Verification

Added six focused tests to `tests/test_engine_ready_replay.py`: unchanged
notification tag/value and transport result; dropped-send handling for groups,
events, points, load and provided terms; current identity packets; independent
warm coalescing/restart; cache load before warm even on failure; and priority
failure fallback plus warm error containment. They use existing fake OSC
constructors, packet decoding and plain mocks, without live engine sockets or
timing sleeps.

```sh
~/.venvs/bopos/bin/python -B tests/test_engine_ready_replay.py
~/.venvs/bopos/bin/python -m pyflakes dashboard/ python/ tools/ tests/test_engine_ready_replay.py
PYTHONPYCACHEPREFIX=/tmp/bopos-node-daemon-tidy-pycache ~/.venvs/bopos/bin/python -m py_compile python/bopos.py tests/test_engine_ready_replay.py
./tools/run-tests.sh all
git diff --check
```

- Focused tests: **13 passed**.
- Pyflakes, compilation and whitespace checks: **pass**.
- Fast: **373 tests passed**.
- Browser: **all 23 journeys passed**. Both tiers completed successfully with
  the required localhost/Chromium access; log:
  `/tmp/bopos-node-daemon-tidy-tests.log`.

The prior accepted stitches provide the unchanged baseline (367 fast tests
after doc drift; all 23 browser journeys after the dead-code sweep). No queue
work beyond this stitch was claimed.
