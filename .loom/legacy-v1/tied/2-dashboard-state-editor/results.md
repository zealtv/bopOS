# Verification record — dashboard state/editor

Date: 2026-07-16 (Australia/Melbourne)

## Outcome

- Dashboard defaults, Seat/device mirrors, individual and `/all` writes,
  reconnect catch-up, durable state, presets, and edit-session values now use
  `manifest.qualify_param()` identities.
- Same-patch schema staging retains unchanged qualified identities, defaults
  additions, and prunes removals. Patch-name changes retain the existing full
  reset behavior.
- Preset loads fail closed to identities declared by the staged manifest;
  historical entries remain inert and are never emitted.
- The manifest editor authors `path` as slash-separated text and serializes it
  as an array. `path` and legacy presentation-only `group` cannot be authored
  simultaneously; conversion requires clearing the existing field first.
- Path/name changes are remove-plus-add operations with exact `/p/...` route
  warnings. The edit-session UI renders a nested tree and binds duplicate leaf
  names by their complete identity.
- No facilitator/Dashboard promoted-control surface, Group selector/membership
  behavior, or `.pd` file was changed.

## Focused backend verification

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/threads/parameter-addresses/param-address-1-implementation.tending/2-dashboard-state-editor.stitching/verify_param_dashboard_backend.py
```

Result: **13 passed, 0 failed**. Coverage includes flat/nested defaults,
duplicate leaves in distinct branches, individual and `/all` state/OSC writes,
unbound/offline Seat state, preset save/load filtering, durable reload,
reconnect catch-up, same-patch retain/default/prune behavior, move warnings,
editor value retention/defaulting, and nested edit sends.

## Focused real-dashboard Playwright verification

Run outside the sandbox because Chromium and the real dashboard/audition relay
bind localhost HTTP and UDP ports:

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/threads/parameter-addresses/param-address-1-implementation.tending/2-dashboard-state-editor.stitching/verify_param_dashboard_browser.py
```

Result: **12 passed, 0 failed**. Coverage includes slash-text/array round-trip,
path/group exclusivity and explicit conversion, nested tree branches,
duplicate-leaf control binding through the real OSC relay, path update/create/
delete CRUD, exact old-identity confirmations/warnings, remove-plus-add control
rebinding, and browser page errors.

## Adjacent regressions and static checks

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/tied/fp-3b-patch-param-reset/verify_fp3b_param_reset.py
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/tied/pe-3-manifest-editor/verify_pe3_backend.py
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python -m py_compile \
  dashboard/state.py dashboard/osc_bridge.py dashboard/server.py
node --check dashboard/static/js/dashboard.js
git diff --check
```

Results:

- Fleet parameter reset: **9 passed, 0 failed**, including flat same-name
  preservation, patch-name reset, no-default omission, and Revert behavior.
- Existing manifest-editor backend: **12 passed, 0 failed**.
- Python compile, JavaScript syntax, and whitespace checks: **passed**.

The historical PE-3 browser verifier was also attempted twice. Its subprocess
completed without exposing stdout in this environment, so no pass count is
claimed. Its backend half passed, and the stitch-local real-dashboard verifier
exercises the current editor with both nested and legacy-group declarations.

## Unverified boundaries

- No installation LAN, physical node, touch device, or audible engine/Pure Data
  route was tested.
- The existing `.notes/pd-edits-for-bob.md` nested-route gate remains Bob-owned;
  this child requires no `.pd` change.
- Promoted live controls and the All/Group/Seat target matrix remain reserved
  for `12-dashboard-live-controls`; Group matching/membership remains reserved
  for the Seat-group implementation.
