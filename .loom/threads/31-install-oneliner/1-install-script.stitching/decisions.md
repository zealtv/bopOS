# Decisions

## Explicit installer names

Bob chose the house terminology and explicit entry points:

- `install-dashboard.sh` — laptop Dashboard environment
- `install-device.sh` — Raspberry Pi device installation

There is no overloaded `install.sh` and no environment inference.

## GitHub delivery

Until separate hosting exists, the copy-paste command uses the raw
`zealtv/bopOS` `main` URL. The cloned framework also comes from that GitHub
repository. This keeps the first delivery model visible and replaceable.

## Existing-checkout behavior

First installation clones recursively. A rerun fast-forwards the current
checkout and refreshes submodules; it does not use `bash/update.sh`, because
that runtime convergence script deliberately runs `git restore .` and would
make a first-time installer unexpectedly destructive to a working checkout.
Privileged setup is composed through `bash/provision.sh`, which in turn composes
`install-power-control.sh`.

## Device config and boot

Provisioning copies `bopos.config.example` only when `bopos.config` is absent.
The reference defaults are the hardware-verified DigiAMP+/Digital pair, and
later user or Device-tab edits are preserved.

The repository-owned `rc.local` boot entry is replaced by `bopos.service`.
Provisioning only retires `/etc/rc.local` when it byte-matches the known legacy
bopOS file, saves a recoverable `/etc/rc.local.bopos-legacy` backup, and leaves
site-owned variants alone. The systemd start is restartable on failure.

The old fixed 15-second delay is replaced by a bounded wait for the configured
ALSA card in `start-engine.sh`. A failed start cleans up the partial stack so
systemd can retry without duplicate framework processes.

## Locale

Device installation defaults to `en_AU.UTF-8`, with `BOPOS_LOCALE` as an
explicit override. Package bootstrap runs under the guaranteed `C` locale;
after the `locales` package is present, Raspberry Pi's supported noninteractive
locale command generates the requested locale. `update-locale` sets `LANG` and
removes stale `LC_ALL`/`LANGUAGE` globals rather than pinning the process-wide
override. The systemd service reads `/etc/default/locale`.

## Deferred

USB auto-mount remains a hook for `35-node-logging`; this stitch does not guess
its mount policy.
