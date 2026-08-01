# 04-reports-tab

Build the ratified demand-driven inspection surface for values patches send to
PD's `to-bopos-report` bus.

## Outcome

- Add a Monitor **Reports** tab with an assigned physical Device/Seat target
  picker, report-name input, and Request action.
- Send one `/<id>/os/probe <name>` request; do not poll or subscribe.
- Render the latest typed `/os/probe <id> <name> <values…>` response with
  device identity and receipt time. Retain only session history.
- Unknown names time out explicitly. Unassigned Devices are visible but
  unavailable with a terse explanation because v1 probe addressing is
  Seat/id-based.
- The raw request and reply still appear in Outgoing and Incoming.
- Explain in the UI that patch report values are latest-value, node-memory
  inspection and clear on node restart.

Do not add reports to the Device `/os/report` JSON or create a telemetry
subscription. This stitch uses the ratified OSC contract as-is.

## Verify

Add living browser-free coverage for probe routing/typed response handling
under `tests/` if a shared backend surface changes. Playwright against the real
server + simfleet must retain a named value, request it, render its types, show
the raw traffic in both streams, and exercise unknown/unassigned states.
