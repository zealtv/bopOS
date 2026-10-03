# Verification matrix

Verification is proportional to the stitch. Durable regression tests live
under `tests/`; each completed stitch also retains its focused commands,
results, and honest boundaries under `.loom/tied/<stitch>/`.

Use `~/.venvs/bopos/bin/python` for project verifies. Dependency and Chromium
setup is documented in `.glean/findings/verification.md` and `dashboard/README.md`. Set
`PYTHONPYCACHEPREFIX=/tmp/bopos-pycache` for compile/import checks launched from
stitch directories so generated `__pycache__` folders do not appear to Loom as
unresolved child stitches. Focused verifier scripts should also set
`sys.dont_write_bytecode = True` before importing repository modules.

## Stable software tiers

### Automatic gates

Run `./tools/install-hooks.sh` once in each clone (also run by
`./install-dashboard.sh`). It sets the local `core.hooksPath` to the versioned
`tools/hooks`; Git then runs `tools/run-tests.sh fast` before every commit,
including agent commits, and refuses the commit if tests fail or cannot run.
Existing hook configurations are reported rather than overwritten. Hooks
check the working tree; keep staged changes and tested files in sync.
Use `BOPOS_PYTHON=/path/to/python git commit ...` for a custom venv. The fast
tier also needs Node.js on PATH for JavaScript model checks.

[Software tests](https://github.com/zealtv/bopOS/actions/workflows/tests.yml)
runs fast tests on pushes and PRs. The browser job runs independently on PRs,
daily at 17:23 UTC, and via **Run workflow**. GitHub schedules run from the
default branch once the workflow is pushed there; a local commit alone does
not activate the cadence. Both jobs also run on the scheduled/manual events.
Failures make the job red; the browser job publishes its per-file summary and
retains `browser.log` for 14 days. No failure is marked `continue-on-error`.

CI uses Python 3.11 and pinned `requirements-dev.txt`, Node.js for fast
tests, and the pinned Playwright browser with its Linux dependencies for browser
tests. Runtime and dev files load root `constraints.txt`; see [INSTALL.md](INSTALL.md#python-dependency-pins) for provenance and deliberate pin updates. The living journeys construct temporary patch/asset/state fixtures or
use static components; none needs the local gitignored patch library or Pd.
All `tests/verify_*.py` run; retired feature journeys are removed with their
features, while shared control and automation coverage remains.

GitHub Actions was chosen over a laptop scheduler so runs survive a sleeping
or offline laptop and share their results in the repository. See GitHub's
[schedule documentation](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)
(runs may be delayed; public-repo schedules can be disabled after 60 days
without activity) and Playwright's
[CI setup](https://playwright.dev/python/docs/ci).

Run the repository entry point from any working directory:

```sh
# Default pre-tie check: all browser-free living tests.
./tools/run-tests.sh
./tools/run-tests.sh fast

# Slower Playwright/integration journeys, one fresh process per surface.
./tools/run-tests.sh browser

# Both tiers; browser tests still all run if fast or an earlier browser fails.
./tools/run-tests.sh all
```

Set `BOPOS_PYTHON=/path/to/python` to override the documented venv. The runner
sets `PYTHONDONTWRITEBYTECODE=1`, discovers only living files under `tests/`,
and prints a per-file browser summary. It never executes `.loom/tied/`.

`./tools/run-tests.sh fast` is the routine pre-tie command. Also run the
focused test for the changed surface and the browser tier when the matrix below
calls for it. Software tiers do not include hardware, Pure Data, audible,
real-LAN, or iPad adoption checks.

| Change area | Minimum local verification | Stronger / integration verification | Hardware boundary |
|---|---|---|---|
| Python module or helper logic | Run the focused living `test_*.py` or `verify_*.py` associated with the feature; compile every touched Python file with `python -m py_compile <files>` | Run `./tools/run-tests.sh fast`; add the durable property to the owning living module if no focused test exists | Report hardware as unverified unless run on a real node |
| OSC contract or node protocol | Add or update a browser-free `test_*.py`; exercise the real helper where practical | Run the real dashboard and `tools/simfleet.py` on non-default ports; protocol changes must land in simfleet in the same stitch | Confirm broadcast, audio-engine delivery, or peripheral behavior on the rig when required |
| Dashboard backend / WebSocket state | Browser-free verify against the real `dashboard/server.py` and simfleet | Run the relevant Playwright dashboard regression | Verify discovery and control on the installation LAN before calling rig adoption complete |
| Dashboard or facilitator UI | Focused Playwright `verify_*.py` using the newest tied browser verify as the template | Run adjacent UI regressions, especially facilitator, spatial, patch-management, and meter surfaces affected by the change | Check iPad/touch interaction when the behavior is facilitator-facing |
| Clock sync and cue timing | `tests/test_sync_protocol.py` or a narrower living sync test for the changed layer | `tools/sync_measure.py --devices 5 --sync-skew-ms 40` | `tools/sync_measure.py --mode hardware --cues 8`; software spread is only a floor |
| Spatial terms / point decomposition | `tests/test_pointfield.py` | Real dashboard + simfleet; recompute expected falloff from sniffed point frames | Audible confirmation awaits the documented PD receiver edits and a rig |
| Pure Data integration | Do not edit `.pd`; add the edit to loom `64-pd-edits-owed` with exact live spellings and expected behavior | Verify the Python/dashboard/simfleet side independently | Bob performs the PD edit and audible rig verification |
| Bash, boot, audio-board, or peripheral work | Static review plus the narrowest safe local check | Laptop rig where applicable | Follow `docs/HARDWARE.md`; record board, OS, command, result, and limitations |
| Documentation or contract-only change | Check links, commands, terminology, and consistency with `AGENTS.md` and `.glean/findings/` | If normative, inspect affected implementation and stitch instructions for drift | None unless the documentation asserts hardware behavior |

## Routine commands

```sh
# Stable pre-tie software check
./tools/run-tests.sh fast

# Current work state; do not claim a stitch merely to inspect it
./.loom/loom.sh status

# Manual dashboard smoke test, terminals 1 and 2
~/.venvs/bopos/bin/python dashboard/server.py
~/.venvs/bopos/bin/python tools/simfleet.py --devices 5

# Current protocol and point regressions
~/.venvs/bopos/bin/python tests/test_protocol_primitives.py
~/.venvs/bopos/bin/python tests/test_pointfield.py

# Software clock-sync measurement
~/.venvs/bopos/bin/python tools/sync_measure.py --devices 5 --sync-skew-ms 40
```

## Stitch completion record

Before tying a stitch, retain inside its directory:

1. A focused verification script when behavior changed.
2. The exact commands run and pass/fail counts.
3. Relevant regression results.
4. An honest statement of anything not tested, especially hardware, macOS,
   browser/touch, audio, or pending PD work.

Run `./tools/run-tests.sh fast` before tying. Run `browser` or `all` when the
change reaches a browser surface; a fast pass is not evidence for browser
behavior.

Test scripts must locate the repository by a marker or imported module path.
Tying moves their directory, so fixed `../..` assumptions are invalid.
