# dist-3 results

The dashboard now completes the OSC v1.3 distribution workflow:

- serves safe manifests and static content from repository `patches/` and
  `assets/`, with file counts, sizes, modified times, and host fingerprints;
- sends one folder or Sync all to the selected node or every online node;
- consumes queued/fetching/terminal receipts and records the exact successful
  host fingerprint, so later host edits render stale after Refresh;
- lists installed patches from `/os/patches`, distinguishes Git-managed
  patches, filters Git targets from mirror sends, and exposes Pull only for an
  active Git patch;
- confirm-gates active-patch sends and patch/asset removal, with patch switch,
  `droppatch`, and `dropassets` controls;
- removes getsamples and the typed patch switch, and uses Update bopOS /
  `updatebopos` in technical and facilitator surfaces.

Safety and reliability details: catalog hashing runs off the asyncio loop;
hidden, partial, and symlinked source files cannot be served; query replies use
source-IP attribution with an ordered simfleet fallback; lost patch queries
expire for retry; one fetch generation per node/slot prevents coalesced replies
from certifying the wrong host bytes. A timed-out fetch remains an explicit
non-retryable tombstone until dashboard restart because v1.3 receipts have no
request ID.

## Verification

Passed on 2026-07-14:

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/threads/patch-asset-sync/dist-3-dashboard-send.stitching/verify_dist3_dashboard_send.py

PYTHONPYCACHEPREFIX=/tmp/bopos-pycache PYTHONPATH=python:python/io \
  ~/.venvs/bopos/bin/python \
  .loom/tied/dist-2-node-side/verify_dist2_node_side.py

PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/tied/ui-0-sidebar-fixes/verify_ui0_sidebar.py
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/tied/ui-1-layout-pass/verify_ui1_layout.py
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/tied/ui-3-position-precision/verify_ui3_positions.py

PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python -m py_compile \
  dashboard/server.py dashboard/osc_bridge.py dashboard/state.py \
  .loom/threads/patch-asset-sync/dist-3-dashboard-send.stitching/verify_dist3_dashboard_send.py
node --check dashboard/static/js/dashboard.js
node --check dashboard/static/js/facilitator.js
git diff --check
```

The focused real-server + real-simfleet + Playwright suite passes every check,
including a two-device mixed Git/mirrored all-target case. Evidence screenshot:
`dist3-dashboard-send.png`.

The older fetch-landing suite retains its documented single stale failure: its
coalescing assertion stops at the two new progress packets. All HTTP/diff/prune/
Range/file/simulator checks before and after that assertion pass; dist-2 and the
focused suite cover terminal receipt handling. The old role-removal browser
verifier also expects obsolete `gain` names while the current demo declares
`gain0`/`gain1`; its manifest checks pass before that stale selector times out.

Not verified: real Pi/LAN transfer, engine stop/restart and audible continuity,
iPad/touch interaction, or installation hardware. No `.pd` file was edited.
