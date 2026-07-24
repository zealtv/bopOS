# 42-node-logging

**SEED.** A general logging facility for bopOS: an **append-only, timestamped
log** on the node, with a **destination settable from the Device tab**, and —
folded in here per Bob — **USB-drive auto-mount** so a stick is a first-class log
target.

This is a *seed*, not a spec. Bob planted it because he can already see several
places that will need to log data. The design is not ratified; the goal starts
with a design/scoping stitch (`1-logging-seed-design`).

**Activated 2026-07-24:** Bob set this **medium priority** — "logging I need to
get done." Renumbered `35`→`42` so the queue serves it after
`40-precision-param-input`; the design stitch is un-waited and workable. The
proposal still ends in Bob ratification before implementation.

Bob, 2026-07-23: "I can see multiple instances where I'm going to need to log
data. So I think we're going to need a log function in bopOS that does an
append-only timestamped log, and I want to be able to set the destination for
that log from within the Device tab. … Looking forward, I'm going to want [the
install] to auto-mount USB drives because that's likely going to be one of the
places we log to most often. So that can go into the logging seed loom item."

## The seed, captured

- **Log function:** append-only, timestamped, a shared facility multiple bopOS
  subsystems can write to (not one bespoke log per feature).
- **Destination configurable from the Device tab:** local path, or a mounted USB
  drive, or elsewhere. Device-tab UI = a Bob gate when it comes to that.
- **USB auto-mount:** the node auto-mounts inserted USB drives; a stick is
  expected to be the most common log destination. The *mechanism* (udev/systemd
  automount) is set up by the install/provisioning flow — see
  `31-install-oneliner` — but the **design of it lives here**, per Bob.

## Open questions for `1-logging-seed-design`

- What writes to it, and at what rate? (Rate drives rotation/format choices.)
- Format: line-oriented text vs structured (jsonl)? Rotation/size limits?
- Absolute time on the node is fine (this is not PD — keep epoch time out of PD,
  but the node's own log can hold real timestamps).
- How the destination is chosen and persisted; behaviour when the USB target is
  absent/unmounted (fall back to local, buffer, drop?).
- The USB auto-mount mechanism and where it's installed (provisioning vs
  runtime), and how logging discovers the mount.
- Any Dashboard visibility (is the log surfaced/queryable, or write-only)?

Don't implement past the ratified seed design.
