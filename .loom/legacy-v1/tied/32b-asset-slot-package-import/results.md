# Asset-slot package-import hotfix

## Cause

`dashboard/server.py` imports `identity` as `python.identity`, but
`python/identity.py` imported its new sibling as top-level `asset_slots`.
Device scripts put `python/` itself on `sys.path`; dashboard package imports do
not. The result was `ModuleNotFoundError: No module named 'asset_slots'` before
dashboard startup.

## Fix

`identity.py` now uses a relative sibling import when it has package context
and retains the top-level import for direct device-script execution.

## Verification

- Fresh-process `from python import identity` regression: passed.
- `tests.test_asset_slot_context`: 8/8 passed.
- `dashboard/server.py --help`: passed.
- Python compilation and `git diff --check`: passed.
- Real `./run.sh` startup on temporary HTTP/OSC ports reached
  `Application startup complete` and shut down cleanly with Ctrl-C.

The first live-start attempt reached application startup but the sandbox
blocked its UDP bind with `PermissionError`; the approved unsandboxed retry
passed. No production/default port was used for the live check.
