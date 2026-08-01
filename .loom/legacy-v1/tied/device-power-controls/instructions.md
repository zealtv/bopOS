# device-power-controls

Restore dashboard `/os/reboot` and `/os/shutdown` on persistent Pi nodes after
the framework helper moved from root to the unprivileged `pi` account. Keep the
helper unprivileged and grant only the two exact systemd power commands through
a repo-managed sudoers rule. The callbacks must use non-interactive sudo so an
installation mistake fails immediately instead of waiting for a password.

Provide a small one-time installer, focused callback/policy verification, and
hardware proof on bop000. Authorization for both exact commands may be checked
non-destructively; reboot can be exercised live with Bob present, while
shutdown remains authorization-tested unless Bob explicitly arranges physical
power recovery.
