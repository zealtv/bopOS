# Decision (Bob, 2026-10-28)

Bob asked for the simplest option and whether a wire change was needed. I
laid out four options:
- **A:** a queue over the existing `/os/fetch`, with device-level progress
  only.
- **B:** A plus the dashboard counting the bytes its file server sends to
  each device's IP.
- **C:** the contract amendment in `proposal.md` (KiB done/total from the
  Pi).
- **D:** the dashboard pushing files to the Pis.

**Bob chose B.** There's no wire change and no Pi change. The contract
amendment in `proposal.md` §2a is **not adopted**; keep it on file in case
exact percentages for updates are wanted later. The rest of the proposal
stands: the single queue, one device at a time, the one-off operation,
unicast fetch, the All chip and the send panel. With B, the progress bar
shows "MB sent" plus an exact percentage only when the slot is absent on the
device.

Open questions defaulted in the build stitches; Bob can overrule them:
- Cancel only drops waiting jobs (the running transfer finishes).
- Remove stays single-device.

Build: thread `82-fleet-asset-send` (not queued, per Bob).
