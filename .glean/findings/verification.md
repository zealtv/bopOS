# Verify at the right level, and run tests from the venv

When checking a change, use `tools/run-tests.sh` from `~/.venvs/bopos` and pick the level from `docs/VERIFICATION.md`.

- `./tools/run-tests.sh fast` — routine pre-tie (browser-free). `browser` — Playwright journeys. `all` — both.
- Durable checks go into the code-surface-owned modules under `tests/`. `.loom/legacy-v1/tied/` guards are historical evidence, not a regression suite — don't sweep or repair them.
- Venv setup: `python3 -m venv ~/.venvs/bopos && ~/.venvs/bopos/bin/pip install -r dashboard/requirements.txt pyOSC3`; browser tests add `playwright` (+ `playwright install chromium --only-shell`) and pixel guards add `Pillow`.
- No hardware: `tools/simfleet.py` fakes N nodes. `--sim-no-engine --sim-audio-backend none` reaches real edit/simulate modes without Pd.
- Stitch scripts find the repo by walking up to `tools/simfleet.py`, never by `..` counts.
- Python floor is 3.9, measured (`tests/test_python_floor.py`).

## Triggers

- run-tests.sh
- simfleet
- venv
- playwright

## Associations

- [[playwright-gotchas]]
- [[hardware-claims]]
