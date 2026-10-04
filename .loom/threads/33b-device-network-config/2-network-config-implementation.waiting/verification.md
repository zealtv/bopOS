# Wi-Fi configuration — software verification

2026-10-04. Scope follows Claude's brief: slices 2–6 and the testable parts
of slice 1. Slice 0 and the network-manager backend remain blocked on Bob
having a Pi up. No hardware, radio, profile-write or switchover claim is made.

## Implementation

- `python/wifi_config.py`: strict complete-list validation, public-state
  projection, helper status and stdin apply interface. ISO country codes
  come from the local public-domain IANA `iso3166.tab` (2025-07-01).
- `systemd/bopos-set-wifi`: executable, argument-less stdin request or
  `--status`; backend seam currently returns unavailable. Provisioning installs
  its validator root-owned in `/usr/local/lib/bopos`. Narrow sudoers and the
  already-installed authorization check cover both helper forms.
- `python/bopos.py`: exact-UID Wi-Fi dispatch, terminal receipt and redacted
  report. Request arguments and helper stderr are never logged. No node
  config or store writes.
- `dashboard/state.py`: ordered country/SSID/hidden/enabled metadata in
  `project.json`; venue snapshots and loads leave fleet Wi-Fi out.
- `dashboard/wifi_secrets.py`, `server.py`: host secrets and pending per-device
  secret changes at **`<data-dir>/state/wifi-secrets.json`**, mode 0600, atomic
  replacement. Default path is `dashboard/state/wifi-secrets.json`, newly
  gitignored. Pending flags survive restart and clear on an applied receipt;
  unreadable data is preserved and saving blocked. No secrets in public state.
- `dashboard/osc_bridge.py`: per-device full-list sends and bounded receipt
  timeout; outbound request console redaction, incoming Wi-Fi report/receipt
  projection. Passphrases travel only for missing or changed secrets.
- `dashboard/static/index.html`, `js/dashboard.js`, `js/wifi-networks.js`,
  `css/wifi-networks.css`: Devices panel, ordering, hidden/enabled flags,
  masked passphrase input, country, active-network warning, confirmation,
  chips, unmanaged SSID adoption. Uses the proposed warning with the reviewer's (Claude's) r2 count fix
  and pluralisation correction; the rest of the sentence stays verbatim.
  No enabled network disables Send. Host secrets never return to
  the browser; only SSID secret-presence flags do.
- `tools/simfleet.py`: full-list/keep-secret behavior, adoption, redacted report
  and receipts; stores secret-presence booleans, never passphrases.
- `docs/OSC-CONTRACT.md`, `OSC-REFERENCE.md`, `INSTALL.md`,
  `python/osc_contract.py`, glean `osc-contract`: v1.20 amendment and installation/
  workshop trust notes. Legacy facilitator `installation.json` text remains
  untouched (now OSC-CONTRACT line 859 after the additive section).
- Added `tests/test_wifi_config.py` and `tests/verify_wifi_networks.py`.
  No compatibility layer or backend guess was introduced. No commit or loom
  lifecycle operation performed; unrelated existing changes left alone.

## Gates

- `./tools/run-tests.sh fast`: 403 tests pass (run between slices and after
  the final behavior changes). Includes all 12 Wi-Fi tests.
- `~/.venvs/bopos/bin/python tests/test_wifi_config.py`: 12 pass. Covers every
  request rejection, keep-secret, missing secret, helper phases, an actual
  fake-helper executable with argument-less stdin, node receipt/report,
  console/public/file/log/simulator redaction, 0600 file mode, timeout chips,
  persistent offline secret changes, confirmation gating/distinct-network counts, malformed
  observations, and corrupt-secret-file preservation.
- `~/.venvs/bopos/bin/python tests/verify_wifi_networks.py`: pass, no browser
  errors. Real dashboard with two physical-protocol peers: edit two networks,
  country/hidden flags, exact proposed warning before either send, confirmation,
  in-sync chips, reorder with null PSKs, disable active with warning and fallback,
  unmanaged adoption, no-enabled Send block. Incoming WS traffic, public state,
  all fixture files except the private secret file, and dashboard logs exclude
  the generated passphrase. `rg --hidden --no-ignore` of the whole repository
  also finds none; its pattern is supplied on stdin.
- `~/.venvs/bopos/bin/python tests/verify_log_destination.py`: all five checks
  pass, zero failures — adjacent Devices-tab regression.
- `~/.venvs/bopos/bin/python tests/test_project_storage.py`: eight pass. Direct
  state imports establish the repository path before loading the shared validator;
  discovery's shared import path must not hide a standalone-tool regression.
- `node --check` for both changed/new JS files; `bash -n` for install/provision;
  `git diff --check`: pass.

## Screenshots

Saved to the requested scratchpad, visually inspected:

- `/private/tmp/claude-502/-Users-bob-repos-bopOS/eb6fbb68-c7f7-4a02-aeed-7744c61ade65/scratchpad/wifi-panel.png`
- `/private/tmp/claude-502/-Users-bob-repos-bopOS/eb6fbb68-c7f7-4a02-aeed-7744c61ade65/scratchpad/wifi-warning.png`

## Still requires Bob's Pi

Inspect the supported OS/network manager/interface, implement the marked seam
with owned profiles, adoption, root-only secrets and activation after the
receipt. Validate sudoers on the Pi, then rehearse both-AP workshop switchover,
disable testing, and show-network fallback; record hardware and framework
revision. Bob still reviews the proposed warning in the running app.

## Review r2 — three UI corrections

- `dashboard/server.py` counts distinct SSIDs whose PSK is sent, rather than
  packet copies. One network sent to two devices counts as one; two networks
  sent to two devices count as two, even with the same passphrase value.
- `dashboard/static/js/wifi-networks.js` uses `1 passphrase` / `2 passphrases`;
  the remaining warning sentence is unchanged.
- `dashboard/static/js/dashboard.js` puts unmanaged SSIDs and the adoption
  button inside a shared device-card wrapper. The primary selection button
  and adoption button remain siblings, avoiding invalid nested buttons.
  `css/wifi-networks.css` carries the card background/selection/exception tone
  across both lines.
- `dashboard/static/index.html` labels the add-row control `+ Add network`;
  its capitalization override preserves that exact label.
- Requested gates rerun: `test_wifi_config.py` 12 pass; fast suite 403 pass;
  `verify_wifi_networks.py` pass, zero browser errors. The journey now asserts
  both singular and plural warnings, the exact add label, and that adoption
  controls sit inside each card without nested buttons. Redaction/file-mode/
  repository passphrase checks still pass. Both JavaScript syntax checks and
  `git diff --check` pass.
- Both screenshots above refreshed and visually inspected: `wifi-warning.png`
  now shows **2 passphrases** for two networks sent to two devices;
  `wifi-panel.png` shows unmanaged SSIDs inside their cards and the new add label.
