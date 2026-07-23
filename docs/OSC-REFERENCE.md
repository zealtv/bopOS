# OSC quick reference

Every OSC message a bopOS node speaks, senders and receivers both, with the
complete address, argument types, port, and what to expect back. This is a
**quick reference for constructing messages by hand** — with a bare OSC
client (`oscsend`, TouchOSC, a Python one-liner) and no dashboard in front of
you. [`docs/OSC-CONTRACT.md`](OSC-CONTRACT.md) is the **normative** spec;
where this page and the contract disagree, the contract wins. See also
[`docs/PORTS.md`](PORTS.md) for the one-page port map.

**Requested by Bob, 2026-07-17:** "If I need to, for example, mute a device
and I don't have the dashboard in front of me, I need to be able to look at
that list and understand the message that I need to construct to send a mute
message and which port I need to send it to." This page is that list.

## How to read the tables

- **address** — the literal OSC address, with `<selector>` where one is
  legal. `all` = every node; a bare non-negative integer = one Seat's `id`;
  `g<n>` = every node currently in group `n` (e.g. `g0`). Assignment and the
  two exact-UID envelopes below are exceptions — their address is always the
  literal `all`, never a numeric selector.
- **args** — in wire order, typed. `s` = string, `i` = 32-bit int, `f` =
  32-bit float. Anything documented as a string here MUST be sent as a
  string even if it looks numeric (git shorthands, uids, nanosecond
  timestamps) — bopOS never puts a value needing more than 32-bit float
  precision on the wire as a float (contract §12).
- **port** — where to send it. LAN traffic (6660/5550) reaches any node on
  the installation network; the four localhost ports (6661/6662/7770/8880)
  are internal to one running node and unreachable from another computer.
- **reply** — what comes back, and on which port. "—" means no reply is
  sent; resend if you're not sure it landed (every fleet command is
  full-state and idempotent, so resending is always safe).

## 1. Commands you send to the fleet (LAN, port 6660)

`bopos.py` is the only thing on a node that binds 6660 — it is broadcast-only
UDP, so anything you send here reaches every node on the network and each
node decides for itself whether the address/selector/uid matches it. Replies
come back **unicast** to your sender port on **5550**, except where noted.

### Identity, liveness, debug

| address | args | what it does | reply (port) |
|---|---|---|---|
| `/all/os/ping <token>` | `token` any type | liveness probe, echoed back | `/os/pong <token> <uid:s>` (5550) |
| `/<selector>/os/report` | — | ask for the static-facts JSON | `/os/report <json:s>` (5550) |
| `/<selector>/os/identify` | — | the box chirps/flashes (locate on install day) | — |
| `/all/os/identify <uid:s>` | `uid` | compatibility alias for exact-uid identify; only the matching node flashes | — |
| `/<selector>/os/probe <what:s>` | `what` | one-shot pull of a retained value (`id`, `uid`, `version`, `update_model`, or anything a patch has `/report`-ed) | `/os/probe <id:i> <what:s> <values…>` (5550); unknown `what` gets no reply |

### Safety mute

| address | args | what it does | reply (port) |
|---|---|---|---|
| `/all/os/mute <0\|1>` | `0` or `1`, int | session fleet-safety overlay — a transport-level kill, spam-safe | — |
| `/all/os/to <uid:s> mute <0\|1>` | `uid`, `0`/`1` int | persists **that physical box's** mute intent (survives the fleet overlay clearing) | `/os/mute <uid:s> <device-muted:i> <effective-muted:i>` (5550) |

Effective mute is the OR of the two layers. If you only have `oscsend` and
need silence *now*, `/all/os/mute 1` is the fastest single message and hits
every node on the network.

### Exact-UID administration envelope (v1.5)

One node, addressed by its stable `uid` (on a Pi, `uid == MAC`), not a
numeric Seat id — useful for a box that isn't assigned yet, or when you want
to be certain you're hitting exactly one physical device:

```
/all/os/to <uid:s> <verb:s> [args…]
```

| verb | args | what it does | reply (port) |
|---|---|---|---|
| `mute` | `<0\|1:i>` | see Safety mute above | `/os/mute` (5550) |
| `hostname` | `<name:s>` | applies one validated lowercase hostname (1–63 chars, alnum + internal hyphens) | `/os/hostname <uid:s> <name:s> <ok\|err:s>` (5550) |
| `identify` | — | chirp/flash | — |
| `report` | — | static-facts JSON | `/os/report <json:s>` (5550) |
| `reboot` | — | reboot the node | bare `/os/rev <sha:s> <model:s> <uid:s>` (5550), sent before the box goes down |
| `shutdown` | — | power off | bare `/os/rev …` (5550), sent before power-off |
| `restart-engine` | — | stop/relaunch just the engine, not the OS | bare `/os/rev …` (5550) |
| `updatebopos` | — | converge the bopOS framework (git pull + reboot on a persistent host) | `/os/rev … <status:s> <phase:s>` (5550) — status/phase set; success is sent before the reboot request, a rejected reboot sends a second `err reboot` |
| `unassign` | — | idempotently revoke: id → `-1`, positions cleared, group membership cleared, hostname retained | `/id -1` to its own engine + an immediate heartbeat (5550) as the revocation confirmation |

Any other verb (`patch`, `checkout`, `addpatch`, `pullpatch`, `droppatch`,
`dropassets`, patch parameters, probes, storage, distribution) is **not**
reachable through this envelope by design (contract §3) — use the
selector-addressed form below instead. Every listed verb above except
`mute`/`hostname` takes **zero** arguments; sending any triggers a silent
reject (no reply, no effect).

### Seat-group membership (v1.5)

```
/all/os/groups <uid:s> <group-id:i>...
```

Replaces the node's complete group membership (an empty tail clears it).
IDs must be unique non-negative int32s. Reply: `/os/groups <uid:s>
<sorted-group-id:i>...` (5550) on success; a mismatch, invalid/duplicate ID,
or persistence failure changes nothing and gets **no** reply.

### Assignment

```
/all/os/assign <uid:s> <id:i> <name:s> [x:f y:f]×N
```

Literal `all` only — never a numeric or group selector, even one that
happens to match. Sets the node's Seat id, hostname, and 0-indexed element
positions (one `x y` pair per element, pair order = element index).
Idempotent full-state. No direct reply; the node's next heartbeat carries
the new id as the ack.

### Lifecycle and provisioning (generic selector)

These take `all`, a numeric Seat id, or `g<n>` — not just `all` — so you can
target one Seat, one group, or the whole fleet:

```
/<selector>/os/<verb> [args…]
```

| verb | args | what it does | reply (port) |
|---|---|---|---|
| `reboot` | — | reboot | `/os/rev <sha:s> <model:s> <uid:s>` (5550) sent *before* the box goes down |
| `shutdown` | — | power off | same `/os/rev` shape, sent before power-off |
| `restart-engine` | — | stop/relaunch the engine only | `/os/rev …` (5550) |
| `updatebopos` | — | converge the bopOS framework (`/os/update` has no alias — removed) | `/os/rev … <status:s> <phase:s>` (5550) — this verb *does* set status/phase; success is sent before a reboot is requested, and a rejected reboot sends a second `err reboot` |
| `checkout` | `<branch:s>` | checkout a branch, then converge | `/os/rev … <status:s> <phase:s>` (5550) — status/phase set |
| `patch` | `<name:s>` | stop engine, switch active patch, relaunch — never reboots | `/os/rev … <status:s> <phase:s>` (5550) — status/phase set; phases: `invalid-name`, `not-found`, `stop-failed`, `write-failed`, `start-failed`, `restore-failed`, `ok switched` |
| `addpatch` | `<user:s> <repo:s>` | `git clone` `https://github.com/<user>/<repo>.git` into `patches/` | `/addpatch <repo:s>` to the engine (localhost) **and** `/os/rev … <status:s> <phase:s>` (5550); phases: `invalid-args`, `invalid-name`, `not-found`, `remove-failed`, `clone-failed`, `ok cloned` |
| `pullpatch` | — | `git pull` the active patch in place (this is what the engine-sent `/admin update-patch` also triggers, §3 below) | `/os/rev … <status:s> <phase:s>` (5550); success is sent before the reboot request (contract sec 7); phases: `active-patch`, `not-found`, `pull-failed`, `timeout`, `exception`, `ok pulled` |
| `droppatch` | `<name:s>` | remove an installed, inactive patch (refuses the active one) | `/os/rev … <status:s> <phase:s>` (5550); phases: `invalid-name`, `active-patch`, `remove-failed`, `ok dropped` |
| `dropassets` | `<slot:s>` | remove an installed asset slot | `/os/rev … <status:s> <phase:s>` (5550); phases: `invalid-name`, `remove-failed`, `ok dropped` |
| `mute` | `<0\|1:i>` | same as `/all/os/mute` above, but selector-generic | — |

`/os/rev`'s full shape is `<sha:s> <model:s> <uid:s> [<status:s>
<phase:s>]` — the contract marks status/phase optional (v1.6). As of the
2026-07-17 outcome-receipts revision, every verb in this table sets
status/phase on both success and failure, so `/os/rev` alone tells you
whether the operation landed. Older nodes running framework builds before
this revision may still send the bare three-field form for `patch`,
`addpatch`, `pullpatch`, `droppatch`, and `dropassets` — if you see a bare
reply from one of those five verbs, that's an old node, not a refusal.

An ephemeral (live-image) node answers every provisioning verb here with an
honest no-op `/os/rev` (no filesystem write) rather than pretending to
persist.

### Patch and asset distribution, params, storage

```
/<selector>/os/<verb> [args…]
```

| verb | args | what it does | reply (port) |
|---|---|---|---|
| `params` | — | the active patch's raw `bopos.patch.json` | `/os/params <json:s>` (5550) |
| `patches` | — | installed-patch inventory: `{name, active, git, manifest, fingerprint?}` | `/os/patches <json:s>` (5550) |
| `assets` | — | installed asset-slot inventory: `{name, fingerprint, files, bytes}` | `/os/assets <json:s>` (5550) |
| `fetch` | `<source-uri:s> <slot:s>` (or `patch:<name>` as the slot) | pull an asset slot or a host-mirrored patch by diff (`http:`/`file:` schemes) | `/os/fetch-progress <slot:s> <queued\|fetching:s>` while pending, then `/os/fetched <slot:s> <ok\|err:s>` (5550) |
| `store` | `<key:s> <values…>` | write to the node's persistence store | — |
| `load` | `<key:s>` | read from the node's persistence store | `/os/load <key:s> <values…>` (5550) |

### Patch parameters, master, and spatial points

These are **provided terms and patch-owned values**, relayed selector-
stripped straight to the engine — bopos.py never interprets them:

| address | args | what it does | reply (port) |
|---|---|---|---|
| `/<selector>/p/<segment>[/<segment>...]` | patch-declared, see `bopos.patch.json` | drives one patch parameter (nested paths join with `/`, e.g. `instrument/marimba/gain`) | — |
| `/<selector>/os/master <0..1:f>` | one float | the framework's one universal output-stage term | — |
| `/pt <count:i> (<id:i> <x:f> <y:f> <r:f> <f:i>)×count` | one frame, all points, atomic | full-state spatial point frame; no selector — always fleet-wide | — |
| `/pt <id:i> <x:f> <y:f> <r:f> <f:i>` | one point | sparse single-point update (5 args = the shorthand form) | — |
| `/pt/clear <id:i>` | one id | releases a point (fades to hold=0) | — |

`f` in a point tuple is the falloff enum: `0` linear, `1` smooth, `2` gauss.

### Sync and cue plane

Framework-owned, no selector — always fleet-wide:

| address | args | direction | reply (port) |
|---|---|---|---|
| `/sync/ping <seq:i> <leaderTimeNs:s>` | leader → fleet | broadcast, 6660 | `/sync/pong <seq:i> <leaderTimeNs:s> <uid:s> <deviceTimeNs:s>` (5550) |
| `/<id>/sync/offset <offsetNs:s>` | leader → one node | unicast, 6660 | — |
| `/cue <cueId:s> <sharedTimeNs:s>` | leader → fleet | broadcast, 6660 | — (relayed to the engine at the local deadline as bare `/cue <cueId>`) |

## 2. What comes back on 5550 (fleet → controller)

You don't send these — they're what to expect listening on 5550 after
sending the commands above, or unprompted (heartbeats):

| address | args | when |
|---|---|---|
| `/hb <uid:s> <id:i> <version:s> <engine-alive:i> [rssi:i]` | — | every 10 s (2 s while unassigned); the sole liveness signal |
| `/os/pong <token> <uid:s>` | echoes the ping's type | reply to `/os/ping` |
| `/os/report <json:s>` | — | reply to `report` |
| `/os/probe <id:i> <what:s> <values…>` | — | reply to `probe` |
| `/os/mute <uid:s> <device-muted:i> <effective-muted:i>` | — | reply to the exact-uid `mute` verb |
| `/os/hostname <uid:s> <name:s> <ok\|err:s>` | — | reply to the exact-uid `hostname` verb |
| `/os/groups <uid:s> <group-id:i>...` | sorted | reply to `/all/os/groups` |
| `/os/rev <sha:s> <model:s> <uid:s> [<status:s> <phase:s>]` | — | reply to every lifecycle/provisioning verb (`patches`/`assets` are queries, they reply with their listing instead); `reboot`/`shutdown`/`restart-engine` send the bare three-field form (nothing to report before the box goes away), every other verb sets status/phase |
| `/os/load <key:s> <values…>` | — | reply to `load` |
| `/os/params <json:s>` | — | reply to `params` |
| `/os/patches <json:s>` | — | reply to `patches` |
| `/os/assets <json:s>` | — | reply to `assets` |
| `/os/fetch-progress <slot:s> <queued\|fetching:s>` | — | while a `fetch` is pending |
| `/os/fetched <slot:s> <ok\|err:s>` | — | terminal reply to `fetch` |
| `/sync/pong <seq:i> <leaderTimeNs:s> <uid:s> <deviceTimeNs:s>` | — | reply to `/sync/ping` |

## 3. The engine surface (localhost, one node at a time)

These never leave one Pi — they're for patch and engine authors, not a
fleet-wide OSC client. `/id`, `/os/master`, `/p/*`, `/pt`, `/cue`, and
`/notify` arrive on the **engine's** port (6661 in production, or the
audition port set by `BOPOS_ENGINE_PORT`); `/config`, `/store`, `/load`,
`/report`, `/admin` are sent **by the engine to bopos.py** on **7770**.

### bopos.py → engine (6661)

| address | args | when |
|---|---|---|
| `/id <n:i>` | resolved Seat id | on assignment, and after `/config` |
| `/os/master <0..1:f>` | the master term | on change, and on catch-up when a device (re)appears |
| `/p/<segment>[/<segment>...] <values…>` | patch-declared | whenever a matching `/p/*` command arrives |
| `/pt <point:i> <element:i> <value:f>` | one shaped scalar per point × element | ~20–30 Hz while moving |
| `/cue <id:s>` | bare cue id, no time | at the synced local deadline |
| `/notify <event:s>` | `identify`, `checkout`, `updatebopos`, `shutdown`, `reboot`, `restart-engine` | on the matching admin action (`pullpatch`/`update-patch` does **not** notify — it just re-syncs the patch in place) |

**Launch-delivered run context** (never over OSC — `-send` for PD at
process start, environment variables for other engines): `seed`, `run-id`,
`patch`, `assets`, and — additive, v1.7 — `version` and `patch-fingerprint`.
PD gets `bopos-context version <string>` / `bopos-context patch-fingerprint
<string>`; other engines get `BOPOS_VERSION` / `BOPOS_PATCH_FINGERPRINT`.
`patch-fingerprint` is the literal string `unknown` when it can't be
resolved without blocking launch on a hash.

In v1.9, `assets` is the ordered list of absolute installed asset-slot paths:
PD gets `bopos-context assets <absolute-path...>` and other engines get the
same list as a JSON array in `BOPOS_ASSETS`. The list may be empty and is
refreshed on the next engine start after a slot is added or removed.

### Engine → bopos.py (7770)

| address | args | what it does | reply |
|---|---|---|---|
| `/config` | — | ask for identity; retry until `/id` arrives | `/id <n>` (6661) |
| `/store <key:s> <values…>` | — | persistence write | — |
| `/load <key:s>` | — | persistence read | `/load <key:s> <values…>` (6661) |
| `/report <name:s> <values…>` | — | retain a typed value for `/os/probe` to pull later | — |
| `/admin <action:s>` | `action` ∈ `update-patch`, `update-bopos`, `shutdown`, `reboot` | **v1.7, additive.** A patch running on the Pi asks bopos.py for the same node-lifecycle action the LAN `/os/*` verbs already provide — routes to the identical implementation (`pullpatch`/`updatebopos`/`shutdown`/`reboot`). No selector, no reply to the engine (these are terminal or restart the engine anyway); `/os/rev` outcome receipts still flow to the LAN model where a real requester exists. An unknown or missing action logs a warning and is otherwise ignored — never fatal. |

The PD-side bus that would let a real `[bopos]`-using patch send `/admin` is
not wired yet (`pd/bopos.pd` — Bob's `.pd` edit, not an agent's); other
engines can send it directly over the localhost socket today.

## 4. Worked examples

Using [`oscsend`](https://liblo.sourceforge.net/) (part of `liblo-tools`;
`brew install liblo` / `apt install liblo-tools`). Replace
`10.0.0.5`/`02:53:49:4d:00:01` with your dashboard-machine broadcast address
and the target node's real `uid`.

**Mute one physical device**, dashboard or not in front of you:

```sh
oscsend 10.0.0.5 6660 /all/os/to ssi "02:53:49:4d:00:01" mute 1
```

Un-mute the same box: swap the trailing `1` for `0`. Kill the whole room
instead: `oscsend 10.0.0.5 6660 /all/os/mute i 1` (no uid needed — it's a
fleet broadcast).

**Reboot one Seat by its assigned id** (Seat 7 here) instead of by uid:

```sh
oscsend 10.0.0.5 6660 /7/os/reboot
```

Or the same box addressed by uid through the admin envelope:

```sh
oscsend 10.0.0.5 6660 /all/os/to ss "02:53:49:4d:00:01" reboot
```

**Update the active patch** (git-pull it in place, no engine restart
notification) on group 0's boxes:

```sh
oscsend 10.0.0.5 6660 /g0/os/pullpatch
```

**Switch which patch is active** fleet-wide, then watch for convergence:

```sh
oscsend 10.0.0.5 6660 /all/os/patch s demo-pd
# listen on 5550 for: /os/rev <sha> <model> <uid> <status> <phase>
# e.g. "ok switched" on success, "not-found" if demo-pd isn't installed
```

**A raw Python one-liner** (no `liblo` needed) for the same mute, using the
`pyOSC3` module this repo already vendors:

```python
import pyOSC3
msg = pyOSC3.OSCMessage("/all/os/to")
msg.append("02:53:49:4d:00:01"); msg.append("mute"); msg.append(1)
client = pyOSC3.OSCClient(); client.connect(("10.0.0.5", 6660)); client.send(msg)
```

## Verified against

Every row above was cross-checked against `docs/OSC-CONTRACT.md` and the
actual handler tables in `python/bopos.py` — `handle_lan_datagram`,
`dispatch_uid_admin`/`UID_ADMIN_VERBS`, `dispatch_admin_verb`/
`LIFECYCLE_VERBS`/`PROVISION_VERBS`, and the 7770 callback map
(`ENGINE_ADMIN_VERBS` plus `/config`/`/store`/`/load`/`/report`), plus a live
run against `tools/simfleet.py` (mute and report). See
`.loom/tied/4-osc-quickref/notes.md` for the original cross-check log that
found the gap this doc now describes as fixed: through the 2026-07-17
outcome-receipts revision, `addpatch`, `pullpatch`, `droppatch`,
`dropassets`, and `patch` always replied with a **bare** `/os/rev` even on
refusal or failure — the contract's `[<status> <phase>]` was optional, and
only `updatebopos`/`checkout` populated it. See
`.loom/tied/rev-outcome-receipts/notes.md` for that fix.
