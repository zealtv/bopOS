# decisions — 3-python-floor

- **`from __future__ import annotations`, not `Optional[...]`.** One line,
  covers every annotation in the module including the next one written, and
  changes no runtime behaviour. Rewriting three annotations would have fixed
  the three and left the trap armed.
- **The floor is 3.9, and that is a measurement, not a preference.** Under a
  real 3.9.6 venv: the whole `fast` suite passes (324 tests), `audition.py`
  imports and runs, and a real editor supervisor launches through
  `Dashboard.launch_supervisor` and is still alive after 4s. So the honest
  change to `install-dashboard.sh` is to **check** a floor it can meet, not to
  enforce the "3.11+" it printed. **Open for Bob:** if 3.11 is the intended
  floor, raise it deliberately — the evidence says the code does not need it,
  and no other reason for the number is recorded anywhere.
- **The installer now checks instead of asserting.** The old text was worse
  than no text: it named a version, verified only that `python3` existed, and
  so converted a wrong interpreter into a silent misconfiguration that
  surfaced days later as an unexplained supervisor death.
- **The guard is a source check, deliberately.** An interpreter check would
  need a second Python in CI, and the failure only exists on the interpreter
  CI is not running. `tests/test_python_floor.py` walks the AST for annotations
  that really are evaluated at runtime — module level and class level (they
  land in `__annotations__`) and function signatures (evaluated at `def` time)
  — and ignores annotations inside function bodies, which are never evaluated.
  Ordinary bitwise `|` in a default is not an annotation and is not flagged.
- **Two assertions, not one.** The general sweep passes the moment someone
  deletes the union; a second test pins `tools/audition.py` — the module the
  dashboard actually spawns — as deferring annotations, so the deferral
  survives the union that motivated it.
- **`dashboard/preset_application.py` and `preset_store.py` already carry the
  future import**, so the idiom was in the codebase; `audition.py` was simply
  missed. That is why this is a guard and not a note.
