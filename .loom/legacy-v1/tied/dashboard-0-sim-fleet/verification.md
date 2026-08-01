# Verification — 2026-07-07

Built `tools/simfleet.py` (codex-implement draft, then hand-corrected for
protocol fidelity; see below). All checks ran live on the laptop, loopback
UDP (`--target 127.0.0.1`), python-osc 1.10.2, Python 3.12.

## What was exercised (observed on a real 5550 listener)

- Heartbeats: `/rpt <id> hb` + `/rpt <id> version 0.0` pairs, staggered phases,
  correct interval; id 0 during the ~1 s boot window; boot announce
  `/rpt <id> aloha 1` at ~1.2 s.
- Routing: `/all gain 0.5` (arg-encoded) hit all devices; path-encoded
  `/2/gain2 0.7` hit only device 2 — both encodings flatten identically,
  matching PD's oscparse.
- `aloha` → `/rpt <id> aloha 1` reply.
- Echo gate: `echo 1` not self-echoed; subsequent payloads echoed as
  `/rpt <id> <payload…>`; `echo 0` echoed once as the gate closes (matches the
  PD send-order ambiguity resolution: gate state before processing).
- `helper reboot`: `helper-reply reboot`, silence ≈ boot-secs, return through
  id-0 window + announce.
- `helper update`: `helper-reply update`, updating → reboot cycle, version
  bumped on return.
- `helper shutdown`: `helper-reply shutdown`, then permanently silent.
- `--unresponsive 1`: device kept heartbeating, ignored every command.
- `--drop 0.5 --jitter-ms 200`: 29 of ~50 heartbeats arrived; inbound drop is
  per-device, so `/all` commands can partially apply (intentional).
- `--devices-file bopos.devices`: real rows loaded (including the duplicate
  id 1 of spool1/voice1, faithfully).
- TTY table renders and restores the cursor; non-TTY logs one line per
  state change/command.

## Divergences found in codex's draft and fixed by hand

- Boot announce (`loadbang → delay 1000 → aloha`) was missing (also missing
  from the first cut of wire-protocol-today.md — found on second PD read).
- Wire version defaulted to 1; real devices always report 0 (`value version`
  is never written — dead wiring, noted in ../osc-schema-contract/pd-edits-for-bob.md).
- `version <v>` command was implemented as a setter; on real devices it is a
  no-op (`s version` has no receiver).
- Inbound drop was all-or-nothing per datagram; made per-device.
- Report/match id asymmetry (reports 0 / matches −1 while unconfigured) was
  collapsed to 0/0; split into wire_id/match_id.

## Not verified

- **Hardware:** "an unmodified real Pi appears indistinguishably in the same
  dashboard" needs a live Pi or the real DASHBOARD.pd side by side — not
  claimed. Everything above is loopback against a python-osc listener that
  mimics DASHBOARD.pd's parse (`route rpt` → id → payload).
- Broadcast to 255.255.255.255 (default `--target`) across a real WLAN.
