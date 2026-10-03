# Dead-code sweep — verification

2026-10-03. Software only; no devices contacted and no `.pd` files edited.

## Deletion evidence

Before editing, searched `dashboard/`, `python/`, `tools/` and `tests/` for
all candidate names, and inspected frontend sends including computed names.

- Removed WebSocket handlers `switch_patch`, `sync_distribution`, `set_points`,
  `list_venues`, `save_show_as`, the `restart_edit` alias, and `set_param`.
  None has a sender in the current frontend or living tests. Computed sends
  in `show.js` are step transport or add-step/add-divider messages;
  control-host/facilitator command callbacks send `action`, and spatial
  authoring sends individual `set_point`/`clear_point` messages. The frontend
  sends `relaunch_edit`, so that handler remains. Supported distribution is
  `send_distribution`; its Git-target refusal remains unchanged.
- Living tests' `set_param` references call/mock `OSCBridge.set_param`, not
  the WebSocket handler. Keep that bridge API and its tests; no test migration
  to another WebSocket verb was needed. The supported UI path already sends
  `set_live_param` through the manifest-aware handler.
- `active_param_identities`, `device_elements`, `Device.wire_id` and
  `Device.match_id` had only their definitions in current sources/tests;
  removed those definitions. `_current_patch_fingerprint` was already absent.
- Before deleting `bash/update.sh` and `bash/checkout.sh`, searched docs,
  installers, systemd units, dashboard, bash, Python, tests and root README
  for both basenames (therefore including absolute on-device paths) and their
  `BOPOS_UPDATE_RESULT` / `BOPOS_CHECKOUT_RESULT` result markers. Only the
  scripts themselves, the `bash/provision.sh` hint, `docs/INSTALL.md` manual
  check description and `python/io/README.md` dependency claim matched.
  No executable caller or result parser remains. Node provisioning callbacks
  call `converge_framework()` directly; installer invokes `provision.sh` and
  units invoke `start.sh`/`stop.sh`, not the removed scripts. Updated the three
  stale references. Repeating the search after deletion returns no matches
  in those current surfaces. Historical loom/lore references are retained.
- Removed per-Seat `patch` forwarding in add/update handlers because
  `clean_seat` drops it already. Simplified the short-argument fetch error:
  inside `len(args) < 2`, the second argument can never exist, so the slot
  was and remains the empty string.
- Removed unused imports/global declarations, placeholder-free f-string
  prefixes and the unused manifest import's path bootstrap. The I/O template's
  example-only command/args declarations are now comments beside their example
  consumers. The old loop-variable shadowing items are no longer present;
  existing meaningful parameter-identity locals remain. Updated simfleet's
  stale protocol docstring to point to the current contract and reference.

The searches used:

```sh
rg -n 'switch_patch|sync_distribution|set_points|list_venues|save_show_as|restart_edit|set_param|active_param_identities|_current_patch_fingerprint|device_elements|wire_id|match_id|admin_request' dashboard python tools tests --glob '!*.pd'
rg -n 'ws.send\((type|kind)|sendCommand' dashboard/static/js
rg -n 'update[.]sh|checkout[.]sh|BOPOS_UPDATE_RESULT|BOPOS_CHECKOUT_RESULT' docs install-device.sh install-dashboard.sh systemd dashboard bash tests python README.md --glob '!*.pd'
```

## Boundaries

Stitch 68 remains `.waiting` and untouched. Retained all Git patch-route
handlers, inventory fields, UI, refusals, script and simulator behavior.
`simfleet.admin_request` and its `ADMIN_ACTIONS` are deliberately retained:
the method contains the `update-patch` surface reserved for 68, even though
current-source search found no callers. This exception follows the user's
boundary over the checklist's proposed deletion.

Compared ASTs against HEAD for node Git callbacks, patch selection and fetch
worker; dashboard Git lookup/convergence helpers; and simfleet admin/request
and inventory methods. They are unchanged. Compared the exact `add_patch`,
`pull_patch` and `set_editor_point_element` WebSocket branches: unchanged.
Also compared whole files for `pull_active_patch.sh`, `osc_bridge.py`,
`audition.py`, `dashboard.js` and `index.html`: unchanged.

The element 0/1 handler and UI remain intact. The one-paragraph recommendation
in `element-recommendation.md` prefers N and describes the alternative of
documenting an explicit two-output audition limit; implementation awaits Bob.

## Checks

- `~/.venvs/bopos/bin/python -m pyflakes dashboard/ python/ tools/` — clean,
  exit 0, no diagnostics.
- Compiled all eight changed Python files with the working venv and
  `PYTHONPYCACHEPREFIX=/tmp/bopos-dead-code-pycache` — pass.
- `bash -n bash/provision.sh` — pass.
- `git diff --check` — pass.
- `./tools/run-tests.sh all` — pass: **362 fast tests and all 23 browser
  journeys**, exit 0. Log: `/tmp/bopos-dead-code-tests.log`. The first sandboxed
  attempt could not use localhost sockets or Chromium; the complete rerun
  with the required access passed both tiers.

Hardware, audible behavior and touch-device adoption are not claimed.
