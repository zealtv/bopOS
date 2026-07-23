# 32b-asset-slot-package-import

Fix the dashboard startup regression introduced by the shared asset-slot
module. `dashboard/server.py` imports `python.identity` as a package module,
while device scripts import `identity` directly with `python/` on `sys.path`;
the sibling `asset_slots` import must work in both modes.

Add a living regression test that imports `python.identity` in a fresh Python
process with only the repository root importable. Verify dashboard argument
startup, the focused tests, and `./run.sh` startup without leaving a server
running.
