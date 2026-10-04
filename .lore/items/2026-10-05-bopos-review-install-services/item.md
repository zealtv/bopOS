# bopOS code review addendum: install and services, October 2026

Review of the installers, lifecycle scripts, systemd units and sudoers helpers at `26a8aac`: five software-confirmed repair findings (a root USB unit runs a pi-writable script; engine launch masks failures; node services unsupervised; stale PID kills; USB unmount ownership) and one cleanup.

## Source

Codex review for loom stitch `74-review-remaining/3-review-install-and-services`,
2026-10-05, checked and routed by Claude. Addendum to
`2026-10-03-bopos-code-review-2026-10`. Findings became `67-repair-pass`
children 17–19. No Pi adoption was run; hardware claims stay pending.

## Tags

- code-review
- security
- systemd
- install
- lifecycle
