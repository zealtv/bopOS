# 19-node-process-ownership

**Status:** ready · propose the model first if it changes units
**Goal:** one owner for each node process: startup failures and later crashes
are seen and handled, and stop kills only what we started.

Evidence: `lore:2026-10-05-bopos-review-install-services` B4, B5, D1.

- **B4 (high).** `start.sh` backgrounds the daemon and IO bridge and returns
  0 even when both exit at once; `bopos.service` is a oneshot with
  `RemainAfterExit=yes`, so `Restart=on-failure` never sees their crashes.
- **B5.** `stop-engine.sh`/`stop.sh` kill any live PID found in `run/`
  (persisted across boots); the `pkill` fallback is name-wide.
- **D1.** `systemd/bopos-helper.service` (unused, would duplicate the daemon)
  and `bash/restart.sh` (broad sudo, no callers). Delete them if the chosen
  model doesn't use them — prefer removing to adding.

Prefer letting systemd own the processes (simple services, cgroup kill) over
more PID bookkeeping. If that changes units or boot order, write a short
proposal in this directory and stop for Bob before building it. Preserve
invalid-manifest boot connectivity. Done when: fixture tests fail before and
pass after; fast green; Pi adoption on Bob's hardware list.
