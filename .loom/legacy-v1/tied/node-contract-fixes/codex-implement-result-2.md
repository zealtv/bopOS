Implemented all three deltas:

- Graceful I2C degradation and `/io/error` replies.
- Dynamic identity/path discovery in `start.sh`.
- PID-based targeted process management and engine restart support.
- Added executable `start-engine.sh` and `stop-engine.sh`.
- Added simfleet `restart-engine` handling.
- Added `run/` to `.gitignore`.
- No `.pd` files touched.

Verification passed:

- `bash -n` on all six shell scripts.
- `py_compile` on all four Python files.
- Clean-environment `sys_i2c` degradation test.
- Simfleet restart scheduling/state smoke test.
- Executable permission checks and `git diff --check`.

Runtime testing of `helper.py` and `io/main.py` was not possible without pyOSC3, as expected. Unrelated existing Loom worktree changes were left untouched.