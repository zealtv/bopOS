# 3-wrong-key-lockout

**Status:** Bob's hands (a repro on a Pi). Added 2026-11-05 from the noor-dusk
soak (`lore:2026-11-05-ap-restart-soak-noor-dusk`, addendum).
**Goal:** know whether a node that meets its saved SSID with the wrong
passphrase gets stuck off Wi-Fi until power-cycled, and if so, stop a
dashboard push from stranding devices that way.

## Observed (kite-choir-brains session, 2026-11-05; unconfirmed)

For a few minutes a spare AP broadcast `<dev-ssid>` with a placeholder passphrase.
noor-dusk (Pi 3 A+, Trixie, NM 1.52.1, default `autoconnect-retries -1`,
`auth-retries -1`) then stayed off Wi-Fi for at least 4½ minutes after the AP
had the correct key, including ~5 min unbroken with the right key on air. A
phone joined in seconds. Only a power cycle brought noor-dusk back (in about a
minute). NM's usual failed-attempt block lifts after ~5 min, so this leans
towards a block that doesn't self-clear, e.g. no-secrets with no secret agent
on a headless node. The volatile journal was lost, so the cause is a guess.

## Why it matters here

A push from the Wi-Fi networks panel that leaves an AP and the devices with
mismatched passphrases could strand every device until someone power-cycles
it. That is the failure `33b`'s "safe apply, reconnect, rollback" constraint
exists to prevent.

## Next actions

1. Repro on a Pi **outside Performance mode** (Bob accepts losing logs during
   shows, because Performance mode avoids SD writes): broadcast the node's
   SSID with a wrong key for a few minutes, then the right key. Capture
   `journalctl -u NetworkManager` and `nmcli -f GENERAL,CONNECTION con show <profile>`
   before the power cycle. Record device, OS and framework (glean
   `hardware-claims`).
2. If it reproduces, propose a fix before building (glean `decision-gates`).
   Options named so far: provision `connection.autoconnect-retries 0` (retry
   forever) on bopOS-managed profiles, or a node-side nudge that re-activates
   the profile after N minutes unreachable (the idea dropped from
   `79/3-link-recovery-design`).
3. If it doesn't reproduce, record that and tie this stitch.
