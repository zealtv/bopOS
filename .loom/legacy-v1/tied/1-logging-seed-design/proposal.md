# Proposal — bopOS node logging facility (42/1-logging-seed-design)

Status: **awaiting Bob's ratification.** Nothing here is implemented.
Wire-visible items are proposed OSC-contract amendments (additive), not landed.

## The anchor use case (Bob, 2026-07-24)

A standalone device (Ciro Toast pattern) runs a patch with i2c buttons and
line-out headphones. The patch must **time the interval between two button
presses** and append it to a **time/date-stamped, append-only log**. The log
destination is set from the **Device tab**. Third-party users retrieve logs
with no SSH and no dashboard: power off, pull the USB stick, copy files,
reinsert. Hence USB auto-mount. Bob expects this to be a **common pattern** —
"we are often requesting to log interactions of different kinds" — and the
standing workflow goal is: SSH only for install/custom config; everything
else (automount, destination selection) from the dash.

## 1. The facility

A shared node-side module, `python/nodelog.py`, owned by `bopos.py` (the
sole owner of node persistence and the engine surface). One facility, many
streams — not one bespoke logger per feature.

- **API (node-internal):** `nodelog.append(stream, values)` — stamps the
  entry at call time and appends one line. Any bopOS subsystem (bopos.py
  handlers, the io bridge, future features) calls it directly.
- **Streams:** a stream is a short name matching the existing report-name
  rule `[A-Za-z0-9_-]+` (bopos.py:1969). Streams need no declaration;
  first write creates the file.
- **Timestamping:** the **node** stamps every entry at receipt with local
  civil time, ISO-8601 with offset (`2026-07-24T14:03:22.512+01:00`).
  Absolute time never enters PD (house rule); PD only ever sends events or
  relative intervals.
- **Format — recommendation: line-oriented plain text, tab-separated:**

  ```
  2026-07-24T14:03:22.512+01:00	presses	1071.5
  ```

  `timestamp<TAB>stream<TAB>values…` (values space-joined, OSC-typed as
  received). Rationale: the primary consumer is a third party opening the
  file straight off a USB stick — plain text reads in anything, imports
  into a spreadsheet, and greps. jsonl was considered and rejected for v1:
  the values here are scalars/short tuples, and structure can be revisited
  if a caller ever needs nesting. (Alternative if you prefer: jsonl —
  `{"t": "...", "stream": "...", "values": [...]}` — machine-friendlier,
  worse for the pull-the-stick audience.)
- **Files and rotation — recommendation: one file per stream per day:**
  `<stream>-YYYY-MM-DD.log` (e.g. `presses-2026-07-24.log`). Daily files
  *are* the rotation — no rotation daemon, no size juggling, natural for
  a third party ("yesterday's file"). Interaction-rate logging (button
  presses) makes size limits a non-issue; a defensive per-file cap
  (e.g. 50 MB, then `-2` suffix) guards against a runaway caller.
- **Write discipline:** append + flush per entry, line-buffered. An
  append-only log's failure mode on power cut is at worst a truncated last
  line — acceptable, matches `store.py`'s "lose at most the key being
  written" philosophy. No fsync per line (SD-card wear); fsync on stream
  close and destination change.

## 2. The wire: engine-sent `/log` (contract §4.2 amendment, additive)

The patch is the first caller, so the engine surface grows one term,
alongside `/store` / `/report` / `/admin` on localhost 7770:

```
/log <stream> <values…>        append one entry to the named stream; the
                               node stamps it at receipt. No reply. Invalid
                               stream names are dropped with a logged
                               warning, never fatal.
```

- Mirrors `/report`'s validation and `/store`'s fire-and-forget shape.
- PD-side: a `to-bopos-log` bus consumed by `[bopos]` — **Bob's patch edit**
  (agents never touch `.pd`), same situation as the §4.2 note about
  `to-bopos-admin`. SC/other engines speak the wire directly.
- **The button-interval caller, concretely:** two supported idioms, patch
  author's choice —
  1. **PD computes the interval** (relative ms is safe in PD floats to ~6
     sig figs ≈ 100 s at ms precision) and sends
     `/log presses <interval-ms>`; or
  2. **PD forwards raw events** (`/log button <id> <state>`) and the node's
     timestamps make the interval derivable exactly, at any span, in
     post-processing.
  For Ciro's headphone piece, (1) is the direct answer; (2) is the
  precision-safe fallback if intervals can exceed ~100 s.

## 3. Destination: model, config surface, Device tab

- **Model:** the destination is a node-persisted **choice**, not a free
  path: `internal` (default — `~/bopos-logs/` on the SD card) or `usb`
  (the auto-mounted stick, logs under `<mount>/bopos-logs/`). Bounded
  choices follow the audio-config precedent (detected cards only, v1.11) —
  no operator-typed absolute paths to get wrong from the dash.
- **Persistence:** one key in `bopos.config` (`LOG_DESTINATION=internal|usb`),
  next to the audio keys — survives reboot, readable without the store.
- **Fallback when `usb` is chosen but no stick is mounted —
  recommendation: fall back to internal, visibly.** Entries are never
  dropped and never buffered in RAM (power-off is the *normal* end of a
  session in this workflow, so RAM buffers would lose exactly the data we
  care about). The heartbeat reports the effective state so the Dashboard
  can show "logging: usb (fallback → internal)". Migration of fallback
  files onto a later-inserted stick is **out of scope v1** (open question
  Q3).
- **Hot insert/remove:** the facility checks the effective destination per
  entry-open (cheap mountpoint test, cached with invalidation on mount
  events); a stick inserted mid-run starts receiving new entries without a
  restart. Removal mid-run degrades to fallback on the next write.
- **OSC/admin surface (contract amendment, additive, mirrors v1.11
  audio-config):**

  ```
  /all/os/to <uid> log-config <json>
      → /os/log-config <uid> <ok|err> <json>
  ```

  `<json>` carries `{"destination": "internal"|"usb"}`. The receipt's JSON
  is the complete log state object (below). Exact-UID physical
  administration — this is device hardware policy, not Seat state.
- **Heartbeat:** the heartbeat's device object gains a `log` object:
  `{"destination": "usb", "effective": "internal", "usb_present": false}`
  (shape final at implementation; the point is configured vs effective vs
  media presence are all visible without SSH).
- **Device tab UI:** a small "Logging" block in the Device tab —
  destination selector (Internal / USB), effective-state indication, USB
  presence. **UI specifics remain a Bob gate at implementation review**,
  per the thread instructions; this proposal fixes only what the block
  must convey.
- **Dashboard visibility of log *content*: write-only v1.** No log
  browsing/tailing in the dash. The retrieval story is the USB stick (or
  SSH for us). A future Monitor-dock stream is possible but explicitly not
  in this scope.

## 4. USB auto-mount

- **Mechanism — recommendation: bopOS-owned udev rule + systemd mount
  template**, not `usbmount` (dead upstream) and not a desktop automounter
  (`udisks2` pulls a stack we don't need on Lite):
  - udev rule matches block partitions on USB (`ID_BUS=usb`), tags them,
    and starts a templated `bopos-usb@.service`;
  - the unit mounts the **first partition of the first stick** at the
    stable path **`/media/bopos-usb`** with filesystem auto-detection
    (vfat/exfat/ext4), `uid`/`gid` of the bopos user for FAT-family so the
    unprivileged node process can write, and `sync`-leaning options chosen
    for pull-without-eject safety (`flush` on vfat);
  - unmount on removal is handled by the same unit's stop path; a yanked
    stick is expected and safe by design (per-line flush + FAT `flush`
    option ⇒ at worst the truncated final line).
  - One stick at a time is the supported model (matches the workflow;
    multi-stick arbitration is complexity with no user).
- **Where installed:** provisioning. `install-device.sh` is already tied
  (thread 31), so this is **net-new install work — an implementation child
  of this thread** edits the install script (per the stitch note; not
  retrofitted into 31). Idempotent, unprivileged-runtime: the rule/unit are
  installed with sudo at install time; runtime needs no privilege.
- **How logging discovers the mount:** by the stable path —
  `os.path.ismount("/media/bopos-usb")`. No udev listening inside
  bopos.py.

## 5. First callers (enumerated)

1. **Ciro Toast button-interval piece** (the anchor): PD → `/log` via
   `to-bopos-log`.
2. **Interaction logging generally** — Bob: "we are often requesting to
   log interactions of different kinds." The stream model means each piece
   names its own streams without framework changes.
3. **The io bridge** (`python/io/main.py`) — sensor/button events can be
   logged node-side (direct `nodelog.append` call) when a piece wants raw
   interaction capture without patch plumbing. Not wired by default;
   available.
4. *(Candidate, not in scope)* framework events (patch switches, admin
   verbs) — the facility supports it, but nothing subscribes system events
   in v1.

## 6. What this deliberately excludes (v1)

- Log browsing/tailing in the Dashboard or Monitor dock.
- Fleet-wide log aggregation.
- Buffering/queueing when the destination is absent (fallback instead).
- Automatic migration of internal-fallback files onto a later stick.
- jsonl/structured entries (revisit when a caller needs it).
- Multi-stick support; choosing among partitions.

## Open questions for Bob

- **Q1 — format:** plain text TSV (recommended) or jsonl?
- **Q2 — file granularity:** per-stream daily files (recommended) or one
  continuous file per stream?
- **Q3 — fallback files:** when `usb` is configured but absent, entries go
  to internal. Is "they stay there; retrieve over SSH or by switching to
  internal-retrieval later" acceptable for v1, or do you want
  copy-on-insert catch-up designed in now?
- **Q4 — PD bus name:** `to-bopos-log` alongside `to-bopos-report` /
  `to-bopos-io` — the `[bopos]` edit is yours; naming ok?
- **Q5 — mount path/name:** `/media/bopos-usb` ok?
- **Q6 — interval encoding for Ciro:** happy with "patch author chooses
  idiom (interval vs raw events)", with raw events as the precision-safe
  form?

## Proposed implementation children (laid out after ratification)

1. `2-nodelog-facility` — `python/nodelog.py` + `/log` on 7770 + contract
   §4.2 amendment text + simfleet parity + `tests/` coverage (durable
   surface ⇒ living tests, per the 2026-07-23 testing ruling).
2. `3-usb-automount-install` — udev rule + systemd unit + idempotent
   `install-device.sh` step.
3. `4-log-destination-config` — `LOG_DESTINATION` persistence, `log-config`
   envelope + receipt, heartbeat `log` object, Device tab block (UI Bob
   gate), Dashboard + simfleet + `tests/` verify.
4. *(Bob)* `[bopos]` PD edit: `to-bopos-log` bus → noted in
   `.notes/pd-edits-for-bob.md`.
