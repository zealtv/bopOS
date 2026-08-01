# 19-alias-hostname-action

Add an explicit selected-Device **Set hostname** action:

- Derive the target on the Dashboard host from the current two-word device
  alias: lowercase and hyphenated (`Finn Jet` → `finn-jet`). Do not accept an
  arbitrary hostname from the browser.
- Address the physical box by exact UID, independent of Seat assignment.
- Add an additive full-state hostname verb and terminal success/error receipt;
  update the selected Device's reported hostname only on success.
- Perform the privileged OS change through a narrow root-owned helper and
  `sudo -n` authorization installed by `provision.sh`; never prompt from the
  background helper.
- Add simfleet and audition parity. Verify derivation, exact UID isolation,
  persistence, receipt/error behavior, and UI pending/current/retry states.
- Do not edit `.pd` files. Record the one-time provisioning boundary honestly;
  routine Update bopOS intentionally cannot install root-owned policy.
