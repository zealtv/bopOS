# Seven-character host version — results

The Dashboard host now asks Git for the conventional seven-character checkout
abbreviation, matching the spelling used in operator conversation and device
version reports. Git may still lengthen the value if seven characters are ever
ambiguous.

## Verification

Passed on 2026-07-16:

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/tied/20-host-version-shorthand/verify_host_version_shorthand.py
# 3/3

PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/tied/13-diagnostic-density/verify_diagnostic_density.py
# 17/17

PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python -m py_compile \
  dashboard/server.py \
  .loom/tied/20-host-version-shorthand/verify_host_version_shorthand.py
git diff --check
```

The focused check compared the Dashboard helper with the real checkout's
`git rev-parse --short=7 HEAD`, asserted the exact Git invocation, and retained
graceful fallback outside a checkout. The existing real Dashboard + simfleet +
Chromium regression confirmed the value remains beside the wordmark. No
hardware or `.pd` behavior was involved.
