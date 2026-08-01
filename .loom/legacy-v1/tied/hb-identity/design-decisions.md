# hb-identity — design decisions (2026-07-07)

Decisions made before delegating the build. Contract: `docs/OSC-CONTRACT.md`
§5–§6 (also §4 transport discipline, §12 float rule). Governing rule stays §1:
*a node never crashes or falls silent for lacking hardware.*

## 1. How helper.py hears the LAN (the load-bearing choice)

`/os/pong`, and any future request/reply, must be **unicast to the requester**
(§4). Today LAN commands reach helper only via PD's localhost forward
(6660 → `route helper` → 7770), which destroys the source address. And `/os/mute`
is a transport-level kill *below patch logic* (§6) — it must work when PD is
wedged or dead, so it cannot depend on PD forwarding at all.

**Decision: helper.py co-binds 6660** (SO_REUSEADDR + SO_REUSEPORT) next to PD's
`netreceive -u -b 6660` and handles the v1 os-plane verbs directly off the LAN
socket, seeing true source addresses. Dash→fleet traffic is broadcast by
contract (§4 port table), and UDP broadcast datagrams are delivered to **every**
socket bound to the port — PD keeps seeing everything it sees today; zero PD
changes, zero port changes.

Verified empirically on Linux (scratchpad `reuse_test.py`, 2026-07-07): both
bind orders succeed with PD-style REUSEADDR-only + helper-style
REUSEADDR+REUSEPORT (PD's x_net.c sets SO_REUSEADDR), and a broadcast datagram
is delivered to both sockets with the sender's address intact. Same kernel
semantics on Pi OS. Caveat documented: a *unicast* datagram to 6660 reaches only
one of the two sockets — fine, the contract makes dash→fleet broadcast-only.
This is also the mechanism the audition rig's port-sharing spike needs, so it
de-risks that stitch.

Degrade: if the 6660 bind fails (exotic PD build without REUSEADDR), log loudly
and retry every 30 s; heartbeat (a pure sender) is unaffected.

The 6660 listener handles **only** proper v1 grammar `/<selector>/os/<member>`
(selector `all` | `<id>`; id −1 while unassigned, §5). Members this stitch:
`ping`, `identify`, `mute`. Everything else stays with PD → 7770 exactly as
today; `assign-persistence` and later stitches extend the member set.

## 2. Heartbeat

- Daemon thread in helper.py; wire address is the registered shorthand **`/hb`**
  (§3 — it's the highest-rate framework message; canonical `/os/hb` stays valid
  for receivers, senders use the short form).
- Args per §6: `uid`(s) `id`(i) `version`(s) `engine-alive`(i) `[rssi]`(i) —
  uid/version are strings (§12), rssi **omitted** (not nulled) when unavailable.
- Sent on its own UDP socket, SO_BROADCAST, to `HB_TARGET:5550`
  (default `255.255.255.255`; config override for loopback dev rigs).
- Cadence: 10 s assigned, 2 s while `id == -1` (§5 — the fast heartbeat *is*
  discovery; no hello family). Re-evaluated every beat so assignment flips the
  rate immediately.

## 3. Identity resolution

- **uid**: pinned token in `$BOPOS_DIR/state/uid` (optional; nothing writes it
  automatically this stitch — the §10 store lands in assign-persistence and may
  pin it) → `argv[1]` MAC when present and not `unknown` → self-discovered
  primary-interface MAC (same ladder as start.sh: default-route iface → first
  non-lo iface up → first non-lo iface; read `/sys/class/net/*/address`) →
  per-boot `uuid4`. On deployed Pis this lands on uid == MAC (§13 guarantee).
- **id**: boot resolution per §5 minus the persisted half (next stitch):
  `bopos.devices` seed matched by uid → **−1**, never silence. The existing
  `/config` handler now also updates helper's live id (it previously only told
  PD), so the heartbeat acks a re-config without restart.
- **version**: `git -C $BOPOS_DIR rev-parse --short HEAD` at startup, `unknown`
  when not a checkout (live image). A string end-to-end; matches §7's
  `/os/rev <sha>` convergence story. Cached — every version change today goes
  through a reboot.

## 4. engine-alive

`run/pd.pid` (written by start-engine.sh since node-contract-fixes) →
`/proc/<pid>/comm` starts with `pd`; stale/missing pidfile falls back to a
cheap `/proc/*/comm` scan. Engine name hardcoded `pd` this stitch;
patch-manifest generalizes it from `bopos.patch.json`.

## 5. rssi

`sys_wireless.read_wireless` gains `iface=None` → first interface listed in
`/proc/net/wireless` (the wireless interface is not necessarily the *primary*
interface, and wlan0-hardcoding is banned by §5). Returns `(None, None)` → arg
absent. `HB_RSSI=0` in node config disables entirely (wired installs).

## 6. Node-level `bopos.config` (new, optional, gitignored)

`$BOPOS_DIR/bopos.config`, same shell-var `KEY=VALUE` syntax as the *patch*
level `bopos.config` that getsamples.sh already reads — same name, different
scope, per-node so it must not be committed (gitignored). Keys this stitch:
`HB_TARGET`, `HB_RSSI`, `MIXER_CONTROL`. Parsed leniently in Python (comments
and blank lines ignored); absent file = all defaults.

## 7. `/all/os/ping <token>` → `/os/pong <token> <uid>`

Pong is unicast to **(source-ip, 5550)** — the requester's listen port is the
known dash-side port; replying to the ephemeral source port would require the
requester to read replies off its send socket. Token echoed verbatim as-is.
Retires `/echo` (nothing removed here — `/echo` was PD-side and is on Bob's
edit list only if it exists; the contract just stops speaking it).

## 8. `/<sel>/os/identify`

- Accepts an **optional uid argument as a filter**: `/all/os/identify <uid>`
  chirps exactly one box even when everything is still id −1 (install-day case;
  contract-compatible superset — bare `/…/identify` behaves per §6).
- Actions, all degrade-silent, every one attempted: (1) OSC `/identify` to PD
  on 6661 — the chirp hook is Bob's PD edit, specced in `pd-edits-for-bob.md`;
  until it lands PD just forwards an inert report to 5550, which is itself a
  visible ack; (2) best-effort ACT-LED flash via `/sys/class/leds/` (usually
  root-only — try, give up quietly); (3) a log line.

## 9. `/all/os/mute <0|1>` (safety-critical, §6)

- Handled on the LAN socket so it works with PD dead (the whole point).
- mute 1: `amixer -q sset <ctl> mute` over candidates — `MIXER_CONTROL` from
  node config if set, else `Master`, `Digital` (DigiAMP/HiFiBerry), `PCM`,
  `Speaker`, `Headphone`; first success wins and is remembered. If none
  succeeds (no mixer): **degrade to engine-stop** (`stop-engine.sh`), flag
  `muted_via_stop`.
- mute 0: `amixer -q sset <ctl> unmute` (remembered control, else all
  candidates); if `muted_via_stop`, run `start-engine.sh` detached (same Popen
  pattern as `/restart-engine`) exactly once, then clear the flag.
- Spam-safety: mute 1 is **re-applied on every receipt** (never short-circuit
  on believed state — repeated sends must converge on silence, §6);
  stop-engine.sh is idempotent. The only guarded transition is the unmute
  engine-restart (start-engine.sh is not idempotent).
- Not hardware-verified: the right control name on a real DigiAMP rig needs a
  live Pi; candidates + config override are the hedge.

## 10. Serve-loop latency fix (drive-by, small)

The old main loop was `sleep(1); server.handle_request()` — up to a second of
added latency per command and requests queue behind the sleep. Replaced with
`server.timeout = 1.0` and no sleep (pyOSC3's server is a stdlib
`socketserver.UDPServer`; `handle_request()` honors `timeout`). Behavior
otherwise identical.

## 11. simfleet (protocol features land in the sim in the same stitch)

- `--protocol {legacy,v1}`, **default `v1`** (the state the dashboard develops
  against). `legacy` remains the pre-update fleet, byte-identical to before.
- v1 devices: contract `/hb` (2 s / 10 s by assignment, staggered), answer
  `/all/os/ping` with unicast pong to (src, 5550), `identify` (marks the TUI
  row so you can *see* the chirp), `mute` (state column). Legacy 6660 command
  handling (gain/echo/`helper …`) stays — PD's side of a real node doesn't
  change until Bob's edits.
- **`--legacy-reports` (default ON in v1)**: real updated Pis still emit the old
  PD `/rpt <id> hb`/`version`/`aloha` until Bob removes the emitters — the
  truthful wire has both. `--no-legacy-reports` previews the post-PD-edit
  fleet.
- `--unassigned N`: last N devices boot id −1 (uid still MAC, fast heartbeat) —
  assignment handling itself is next stitch.
- `--wired N`: last N devices heartbeat without rssi (dashboard must render the
  absent column, §1). Others random-walk −35…−80 dBm.
- v1 `version` is a string on the wire (fake short-sha style, bumps on
  `helper update` like the legacy counter did).

## Out of scope (parked where)

- `/os/assign`, persistence store, boot resolution's persisted half →
  `assign-persistence` (next).
- PD edits: identify chirp hook; removing PD's `/hb`/`/aloha` emitters →
  `pd-edits-for-bob.md` §2–§3.
- Engine name from manifest → `patch-manifest`.
- Hardware verification (real amixer control names, WLAN broadcast behavior,
  DigiAMP rig) → needs Bob or a live rig; listed in verification.md.
