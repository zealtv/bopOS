# Ruling — 2026-11-05

Bob, 2026-11-05 (walking `76-bob-review` item 17): **approve the systemd model
in `proposal.md`, with three amendments.**

Approved as proposed:

- `bopos.target` with `bopos.service`, `bopos-io.service` and
  `bopos-engine.service`; daemon and IO bridge `Restart=always`, engine
  `Restart=no`.
- The exact-match sudoers lines for `systemctl start|stop|restart` (and
  `--no-block restart`) of `bopos-engine.service`.
- The journal split and per-boot log rotation.
- Deleting PID files, `stop-engine.sh`, `pkill`, `bopos-helper.service` and
  the old broad-sudo `restart.sh`.

Amendments:

1. **No migration shim.** Instead, `provision.sh` writes a provision-level
   marker on the Pi, and the dashboard's **Update bopOS** refuses a Pi whose
   level is older than the incoming framework needs. The receipt tells the
   operator to run `bopos update` on the device. Bring the exact refusal
   wording back to Bob. This replaces INSTALL.md's "existing Pis need one
   manual `sudo provision.sh`" warnings and covers future root-owned changes.
2. **One front door for people: a `bopos` command.** A plain bash `case`
   script (about 60 lines, no options framework) that `provision.sh` installs
   at `/usr/local/bin/bopos`:
   - `bopos status`: the three units, engine alive, active patch, framework
     revision, last log lines;
   - `bopos start | stop | restart`: `systemctl … bopos.target`;
   - `bopos update`: pull with submodules, keep the active patch, run
     `provision.sh` when root-owned pieces changed, restart;
   - `bopos logs`: `journalctl -u 'bopos*' -b -f`;
   - bare `bopos` prints the list.
   If a subcommand grows, it calls a script rather than growing inline.
3. **Separate internal entry points from human ones.** What systemd's
   `ExecStart` runs gets internal names (e.g. under `bash/run/`) or calls
   Python directly; no file serves both systemd and a person.

Why (Bob): the refactors have lost some of the original bopOS/plants OS
simplicity. He used to run a simple `update.sh`, and wants easy commands to
start, stop, restart, update and check status. He found the arg-sniffing
`start.sh` shim likely to get messy.

Migration scale (Bob, 2026-11-05): 5 Kite Choir Pis running, plus a few
standalone projects; SSHing in to run `bopos update` on each is fine.
