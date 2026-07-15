# Global execution target results

## Outcome

- The header now owns an authoritative three-way **Live fleet / Simulation /
  Patch edit** execution-target control and reasserts the server's actual target.
- Target changes are guarded at both the browser journey and WebSocket command
  boundary. Contextual editor launch/stop paths use the same confirmation rules.
- **Patch edit** navigates to Patches and focuses patch selection without
  guessing or launching a patch.
- Simulation uses the contextual Patches selection without changing the desired
  Live fleet patch.
- Seats retains compact simulation status while the former simulation toggle
  and **Edit this patch** controls are removed.

## Verification

Passed:

```sh
node --check dashboard/static/js/dashboard.js
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python -m py_compile dashboard/server.py .loom/threads/ui-tabs/tabs-3-next-sweep/05-global-execution-target.stitching/verify_execution_target.py
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python .loom/threads/ui-tabs/tabs-3-next-sweep/05-global-execution-target.stitching/verify_execution_target.py
```

Result: **17/17 passed** in headless Chromium against the real dashboard and
audition process. Coverage includes all three targets, guarded direct WebSocket
transitions, guarded UI journeys, Patch edit navigation without launch,
contextual Simulation selection, preservation of the desired Live fleet patch,
target/status reassertion, master/mute restoration, browser errors, and clean
shutdown.

Adjacent regressions passed:

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python .loom/tied/03-seat-identity-leaks/verify_seat_identity.py
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python .loom/tied/02-patch-switch-terminal-state/verify_patch_switch_terminal_ui.py
```

Results: **10/10 passed** and **5/5 passed**, respectively.

```sh
git diff --check
```

Result: passed. The retained browser screenshot was visually inspected at
1400px: the target group is compact and legible, and does not overlap the
online, mute, or connection controls.

## Review

A read-only review confirmed the overall control shape and identified missing
guards around Live-to-Simulation and Patch-edit exit/contextual paths. Those
guards and direct boundary tests were added before verification. The review
also prompted an explicit regression proving that contextual Simulation cannot
alter the desired Live fleet patch.

## Boundaries

Older tied UI tests that require the removed Seats `#simulate-toggle` and
`#edit-sim-patch` selectors are intentionally superseded by this stitch's
execution-target verifier. No `.pd` file changed. No physical hardware, audible
engine output, installation LAN, or iPad/touch browser was tested.
