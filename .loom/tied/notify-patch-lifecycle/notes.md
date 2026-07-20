# patch lifecycle notification completion notes

`pull_active_patch_callback` and valid `switch_patch_callback` operations now
send `/notify updatepatch` to the current engine before pull/stop/swap work.
Both paths intentionally share the ratified `updatepatch` symbol. The existing
identify, updatebopos, checkout, restart-engine, shutdown, and reboot symbols
are unchanged.

## Verification

Passed 2026-07-20:

```text
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python -m py_compile \
  python/bopos.py \
  .loom/threads/notify-patch-lifecycle.stitching/verify_notify_patch_lifecycle.py
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/threads/notify-patch-lifecycle.stitching/verify_notify_patch_lifecycle.py
git diff --check
```

The browser-free verifier passed three checks with an isolated patch tree and
instrumented engine/command boundaries: active pull notified before its
lifecycle script, patch switch notified before `stop-engine.sh`, and all six
existing symbols remained alongside exactly two `updatepatch` call sites.

No `.pd` file was edited. `.notes/pd-edits-for-bob.md` now records that the
reference `bopos-notify` route should recognize bare `updatepatch`. No hardware
or audible test was performed. Bob's untracked `dashboard/shows/` working
material was untouched.
