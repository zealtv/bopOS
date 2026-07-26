# version-0-currentness-design

Design the remaining framework-currentness model and UX for Devices.

Verified current baseline (2026-07-26):

- the dashboard publishes and displays its `host_version`;
- heartbeat `version` and report `git_rev`, `contract_version`, and
  `update_model` are retained and visible;
- per-device and fleet **Update bopOS** actions already exist;
- `/os/rev` retains status/phase, and `updatebopos-unattended` proved
  noninteractive convergence, success-before-reboot receipts, reappearance,
  and active-patch preservation on a real persistent node.

Do not redesign those shipped mechanisms. Define what desired framework state
means: whether the dashboard host checkout is sufficient, how branch/release
intent is represented, and whether equality alone can distinguish stale from
diverged or requires ancestry/release metadata. Specify current, stale,
unknown, and diverged classifications; where compact per-device and fleet
summaries live; how actions select only appropriate persistent nodes; and how
ephemeral nodes are explained without implying they can persist an update.
Reuse the existing confirmation, receipt, reboot, and reappearance behavior.
Do not conflate framework revision with patch fingerprint or OSC contract
version.

Deliver a short proposal and implementation split, lore-keep it, and return to
waiting for Bob's ratification.
