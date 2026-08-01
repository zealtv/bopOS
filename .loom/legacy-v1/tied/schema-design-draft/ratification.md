# Ratification — Bob's rulings on the council judgment

Date: 2026-07-07. Bob read all five expert designs and `judgment.md` and ruled.
This file is the authoritative delta on the judgment; `docs/OSC-CONTRACT.md` is the
merged result.

## Crux 1 — AMENDED: node-side persistence is required, not optional

Bob: installations exist **today** where devices run standalone — configured over
the network, then the network is taken down for the duration and machines boot and
run independently on persisted settings (state is currently persisted PD-side).
Dashboard-driven ID assignment is a UX boon he wants — **but assignments must
persist on the node.** A live-OS host may sacrifice persistence; that is adapted to
in that circumstance, not the design center.

Ruling as amended: the dashboard is the **assignment tool** (and keeps its
`uid → assignment` table for re-setup), but on persistent hosts `/os/assign` state
is **persisted node-side** via the framework persistence store. Standalone,
dashboard-less, network-less operation is a **first-class operating mode**. Boot
resolution order: local persisted assignment → `bopos.devices` seed → unassigned
(id −1, fast heartbeat). Ephemeral hosts re-hello and are re-assigned per boot.
The idempotent full-state control-plane law stands unchanged.

## Schema — NEW REQUIREMENT: short addresses

High OSC volume is expected on the wire. Addresses stay readable, but the contract
defines **optional registered shorthands** (canonical + short form, both permanently
valid), targeting first-letters where possible — e.g. `/point` ↔ `/pt`. Shorthands
are minted only for high-rate messages; patch parameter names under `/p/*` are the
patch's own to keep short.

## Crux 2 — RATIFIED, with a scope note

The plane grammar and manifest keystone stand. Note: **the dashboard's sequenced
scenes may emit arbitrary OSC** — including to non-bopOS devices integrated into a
dash-driven install. The contract governs what bopOS *nodes* speak; it does not
constrain the dashboard's emission surface or the scene language.

## Verbs

- **`/os/identify` — ratified.** Chirp-to-locate is what `/aloha` has effectively
  been used for so far; it is important.
- **`/os/mute` — ratified, elevated to safety-critical.** Stopping the system can be
  a safety issue. Mute must be **spam-safe**: broadcast, idempotent, repeatable at
  will, and it silences the system reliably below patch logic.

## Numbered DECISION items (judgment §5)

1. `engine-alive` heartbeat field + fast-heartbeat-when-unassigned — **yes** (engine-alive important; fast heartbeat could be helpful).
2. Manifest `bopos.patch.json`, JSON, one file — **yes**.
3. Framework-owned neutral assets root `~/bopOS/assets/<slot>/` — **yes**.
4. `/os/identify` — **yes**.
5. `/os/mute` — **yes**.
6. Dashboard as assignment source of truth — **amended per Crux 1 above**: dashboard
   assigns and remembers, node persists and runs standalone.
