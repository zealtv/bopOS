# 3-link-recovery-design

On 2026-10-23, Bria Fox logged `Network is unreachable` for 2 minutes and did
nothing about it; only a power cycle brought her back. Even with power save
off, should bopOS nudge a dead link (e.g. bounce wlan0 or restart
NetworkManager after N minutes unreachable), or leave that to the OS?

This is a design question, so propose before building (glean
`decision-gates`). Wait for `2-pi-power-save-check`: if power save off plus
the OS's own reconnect survives an access-point restart, this may be
unnecessary.
