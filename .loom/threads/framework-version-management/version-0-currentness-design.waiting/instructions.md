# version-0-currentness-design

Design framework-version currentness and update UX for Devices.

Survey the existing heartbeat `version`, `/os/report` `git-rev`,
`contract-version`, `update_model`, `/os/rev`, and `/os/updatebopos` flow. Define
which host/release fact is desired state; current/stale/unknown/diverged badges;
per-device and fleet update actions; confirmation, progress, reboot/reappearance
and failure semantics; and how persistent versus ephemeral update models differ.
Do not conflate framework version with patch content fingerprint or OSC contract
version.

Deliver a short proposal and implementation split, lore-keep it, and return to
waiting for Bob's ratification. Parked from the 2026-07-15 tabs-0 session until
Bob explicitly resumes it after the current UI-tabs runway.
