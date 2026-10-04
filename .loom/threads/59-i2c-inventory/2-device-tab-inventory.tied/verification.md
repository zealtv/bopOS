# Device IO inventory verification — 2026-10-04

Worktree: `/Users/bob/repos/bopOS/.worktrees/59-2-device-tab`.
Branch: `stitch/59-2-device-tab`. Scope: Device-tab UI and tests only.

The IO card uses the existing `report.io`, `io_scan` request, scan receipts
and unsolicited IO errors. It distinguishes no bus, not scanned and scanned
empty; sorts hexadecimal addresses; marks kernel claims; and offers tentative
matches at the shipped ADS1x15, LIS3DH and MPR121 default addresses. Module
rows display name, type, address, state and the bridge's error reason. Missing
is handled generically until 59/3 supplies ownership/optionality information.

Scan is available in Performance and disabled while pending or offline.
Timeout preserves the last observed inventory and successful scan time.
IO updates remain visible while another Device form retains focus. Names
and reported text are escaped. No IO writer, Re-init or Monitor control is
added. Re-init lacks an admin mechanism in this checkout; current values are
absent from the IO object and depend on the future stream/panel work.

## Verification

- `./tools/run-tests.sh fast`: **484 passed**, exit 0.
- `./tools/run-tests.sh browser`: **all 31 journeys passed**, exit 0.
- New journey `tests/verify_device_io_inventory.py`: real dashboard/simfleet
  processes, three bus states, unknown report status, sorted/claimed addresses,
  tentative hints, running/errored/missing modules, Performance scan,
  pending/timeout/offline behavior, error updates with focus preserved,
  exact-UID routing and escaped module names.
- `node --check` passed for `device-io.js` and `dashboard.js`.
- `git diff --check` passed. No `.pd` edits or node/bridge/server changes.
- `BOPOS_DEVICE_IO_SCREENSHOT=<task scratchpad>` saves 1440/420px captures
  in light and dark themes. All four captures were visually inspected; the
  card fits the viewport and clears the fixed Monitor dock. Warning text
  uses the theme's readable warm text with the existing amber warning glyph.
- Logs: task scratchpad `fast-59-2.log`, `browser-59-2.log`.

An initial journey's recovery query collided with an existing pending report
after a deliberate timeout. Recovery now uses an attributed scan receipt.
No production backend changes were needed.

## Proposed operator wording for Bob's approval

- `IO`; `Modules` (also the module-list accessible label).
- `Scan`; `Scanning…`.
- `No bus`; `Not scanned yet`; `Bus is empty`.
- `{N} address`; `{N} addresses`; `I2C bus 1`.
- `Refresh the report to load IO status.`
- `Last scanned: {local date/time}`; `Last scanned: never`;
  `Last scanned: time unavailable`.
- `Kernel claimed (UU)`.
- `ADS1x15?`; `LIS3DH?`; `MPR121?`.
- `Address hints are tentative.`
- `Bus addresses` (address-list accessible label).
- `No modules reported.`; `Module status unavailable.`
- `Scan timed out. Try again.`
- `Last IO error: {module name} · {reason}`.
- Module status words reused verbatim: `running`, `errored`, `missing`;
  fallback `unknown`. Reported module names, types and ratified error reasons
  are displayed as data. The existing `⚠` mark and `·` separator are reused.

No blocking questions. Bob's approval of this wording remains pending.
Re-init and optional/required distinctions need the 59/3 mechanism/schema;
Monitor controls and values remain later panel work. No physical Pi, I2C
chip, real audio path or iPad was exercised. No push, merge or loom lifecycle
commands are part of this implementation.

## Follow-up 59/2b — main checkout, 2026-10-04

Optional/required absence is now distinguished using manifest declarations.
Assigned devices expose `io_modules` received through the existing `/os/params`
response, associated with the observed active patch. Otherwise the card uses
the host catalog manifest for the reported active patch (needed for unassigned
devices, whose selector-addressed `/os/params` cannot be queried). A declaration
must match module name, type and address before its optional flag applies.
Optional absence reads `missing (optional)` in neutral text without a warning;
required or undeclared absence retains the warning. Errored modules retain
their warning regardless of optionality. A new/legacy manifest clears old flags;
flags associated with another active patch are not used.

- Fast suite: PASS, 498 tests.
- Browser suite: PASS, all 31 journeys, including log destination and Performance.
- Extended Device IO journey: PASS, optional/required styling, unassigned host
  manifest fallback and rejection of stale patch metadata. Repeated after the
  final change to capture screenshots.
- All four refreshed `device-io[-dark]-{1440,420}.png` screenshots were visually
  inspected. Neutral optional status and amber required/error status remain
  legible and fit the card in both themes and widths.
- JavaScript syntax and diff whitespace checks: PASS.
- New operator string: `missing (optional)`.

Re-init remains unimplemented: the follow-up brief explicitly requires stopping
before a new admin verb or reply. No existing exact-device command routes a
per-module create; `io-write` addresses a peripheral and rejects reserved
management names, is locked in Performance, and cannot mean Re-init. A matching
declared `/io/create` is intentionally a no-op, so even forwarding that message
would not reinitialize a running instance. The proposed wire addition is in
scratchpad `report-59-2b.md`, awaiting ratification. No new wire tokens, no commit,
and no loom lifecycle commands were added. Physical I2C behavior remains pending.
