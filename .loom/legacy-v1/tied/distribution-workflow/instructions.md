# distribution-workflow

Make patch development converge cleanly in both managed simulation and the
real fleet.

- In Simulate mode, treat every valid host patch as already installed; do not
  offer byte distribution to loopback audition nodes.
- Support one fleet-wide simulated patch selection and restart the managed
  audition engines into that host patch.
- Make simulated patch inventory and lifecycle receipts honest so the UI cannot
  remain indefinitely in an invented queued state.
- Prevent real-device sends from advertising a loopback-only HTTP source; give
  the operator an actionable error/configuration path instead.
- Preserve real-node semantics: sending an inactive host-mirrored patch installs
  it without stopping audio; overwriting the active patch stops, fetches, and
  restarts before the terminal receipt.
- Add focused dashboard/simulator verification and retain results here. Do not
  edit any `.pd` file.
