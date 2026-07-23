# Handoff — device audio config complete; continue 33b → 34 → 27 → 20/25

This is the current launch note for a fresh session. It supersedes
`.notes/handoff-2026-07-23-autopilot-node-bug.md` for launch state and work
ordering. The dedicated guard-rot briefing remains useful when thread 27 is
reached, but its historical order is stale.

## Continued order — Bob's ruling

Work one loom stitch at a time in this order:

1. **Complete — 33: device audio configuration**
2. **33b — saved device networks**
3. **34 — fleet-patch global state**
4. **27 — tied-guard rot**
5. **20 / 25 — console dock and message-pill encoding**

Threads 20 and 25 are the final pair in this sequence; no precedence between
them was established here. Do not bring 27 forward ahead of 32–34, including
33b.

## Thread 32 — complete and tied

The `1-context-list-design` gate is ratified and tied. Bob accepted:

- every installed top-level asset slot in context;
- deterministic slot-name order with no precedence meaning;
- `bopos-context assets <absolute-path...>` for PD and JSON-array
  `BOPOS_ASSETS` for other engines;
- the intentional retirement of the old scalar-root meaning;
- **asset slot** as the one consistent term (no separate asset-pack concept).

The software side of `2-multi-pack-implementation` is complete and verified.
Bob also completed the `.pd` side, choosing direct
`[r bopos-context] -> [route patch assets]` consumption rather than a second
plural bus, and confirmed list lengths 0/1/2 for zero/one/two host slots.
Thread 32 is tied. Read:

- `.loom/tied/1-context-list-design/decisions.md`
- `.loom/tied/2-multi-pack-implementation/results.md`
- the top entry in `.notes/pd-edits-for-bob.md`

The 33 design and implementation stitches are tied. The next stitch is
`33b-device-network-config/1-network-config-design`; it is a Bob-ratified
design gate, and the ordered sweep remains one stitch at a time.

## Stitch 31 — complete and tied

`31-install-oneliner` and its `1-install-script` child are tied. The resulting
house terminology is explicit:

- `install-device.sh` — Raspberry Pi device
- `install-dashboard.sh` — laptop Dashboard host

The public device command is:

```sh
curl -fsSL https://raw.githubusercontent.com/zealtv/bopOS/main/install-device.sh | env LANG=C LC_ALL=C bash
```

It now:

- prepares and upgrades Raspberry Pi OS;
- expands the root partition and enables I2C;
- defaults to `en_AU.UTF-8`, with `BOPOS_LOCALE` override;
- clones or fast-forwards bopOS and recursive submodules;
- creates/reuses `~/venv` and installs device Python requirements;
- seeds `bopos.config` once with DigiAMP defaults;
- installs the narrow privileged helper/sudoers policy;
- installs and enables `bopos.service`;
- starts JACK safely under headless systemd with the required realtime and
  memlock limits;
- automatically reboots after a successful run.

Relevant commits:

- `0dbf2c7` — initial one-command device installer
- `26a2467` — headless JACK and systemd audio-limit fix
- `fa7bd53` — automatic installer reboot
- `0cc2ec8` — fresh-install report
- `e5d2b2d` — tied stitch 31

## Fresh-Pi verification

The installer was run from the public raw-GitHub URL on freshly flashed
`new-bop` (`pi`, Raspberry Pi OS Lite 64-bit, Debian Trixie, DigiAMP+).

Passed:

- complete first install;
- AU locale generation and warning-free fresh login;
- filesystem geometry check — the 7.4 GiB card already had a full 6.9 GiB root
  partition; the 6.8 GiB ext4 size is normal metadata overhead;
- recursive Git/submodule clone;
- config seeding and preservation;
- sudoers validation and systemd unit verification;
- cold boot with `bopos.service` active, `Result=success`, zero restarts;
- bopOS, I/O bridge, JACK, Pure Data, and `pd-watchdog` alive;
- expected JACK ports and UDP listeners;
- exact-device resume/mute on the DigiAMP while JACK/PD retained their PIDs;
- full public-installer rerun with no package/dependency changes, unchanged
  config SHA-256, automatic reboot, and one healthy boot stack afterward.

The complete record is:

`.lore/items/2026-07-23-fresh-device-install/`

The Pi's last checked checkout was clean at `fa7bd53`; it does not need the
lore/tie-only commits to run the installed system. At handoff it was reachable
at `192.168.0.102`, with the service active. Bob's authenticated tmux console is
pane `0:0.0`.

## Finding deliberately left for its owning work

The fresh boot exposed an unrelated legacy identity bug. The assignment loader
tries to rename `new-bop` to the invalid OS hostname `Seat 0` using three old
interactive `sudo` commands. All three fail, the host remains `new-bop`, and the
service continues normally. The newer exact-UID alias-derived hostname helper
is already provisioned. Reconcile/retire the old `set_hostname()` call in the
identity/alias work; do not hide it inside a later installer edit.

## Working tree / repository state

- `main` was pushed through `e5d2b2d` before this handoff note.
- Stitch 31 is tied; no stitch is claimed.
- `.lore` is valid: 34 items, zero invalid or partial items.
- Local checks for the installer pass: bash parsing, six living
  `tests/test_device_install.py` tests, and `git diff --check`.
- `shellcheck` was unavailable on both the development Mac and fresh Pi;
  `systemd-analyze verify` passed on the Pi.
- `dashboard/shows/` is unrelated, untracked, user-owned work. Leave it
  untouched and unstaged.

## What follows 33

- **33 is complete:** node-level `bopos.config` is the single source of audio
  truth; the Device tab offers detected cards plus rate/buffer/periods, while
  mixer selection remains node-side hardware policy; applying restarts
  transactionally and rolls back on JACK failure.
  Living tests pass 38/38 and the focused browser route journey passes 16/16.
  Real Pi/JACK, audible rollback/silence, and iPad/touch remain hardware gates.
- **33b** starts with `1-network-config-design`: manage an ordered set of saved
  SSIDs and write-only passphrases from the Device tab. The design must settle
  profile priority, secret handling, and safe switching/reconnect/recovery.
  Design requires Bob ratification.
- **34** starts with `1-menubar-fleet-patch-design`: define fleet-patch global
  state and its menu-bar convergence indicator. Design requires Bob
  ratification.
- **27** uses `.notes/handoff-guard-rot-briefing.md`, with its corrected
  two-tier ruling: promote durable contracts into living tests organized by
  code surface; retire authoring-only tied guards as recorded artifacts.
- **20 / 25** come last in this sequence.
