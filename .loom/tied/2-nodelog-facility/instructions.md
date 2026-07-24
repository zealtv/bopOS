# 2-nodelog-facility

The shared append-only log facility plus its engine wire. Ratified design:
`../1-logging-seed-design` (tied) — `proposal.md` + `decisions.md` are the
authority; this stitch implements, it does not re-decide.

## Build

- **`python/nodelog.py`** — `append(stream, values)`:
  - node-stamps at call time, ISO-8601 local with offset
    (`2026-07-24T14:03:22.512+01:00`);
  - one plain-text TSV line: `timestamp<TAB>stream<TAB>values…` (values
    space-joined, as received);
  - stream names validated `[A-Za-z0-9_-]+` (same rule as report names,
    `python/bopos.py:1969`); invalid → logged warning, dropped, never fatal;
  - per-stream daily files `<stream>-YYYY-MM-DD.log`; defensive 50 MB
    per-file cap (`-2` suffix continuation);
  - append + flush per entry, no per-line fsync (SD wear); fsync on close
    and destination change;
  - destination resolution: this stitch writes to the internal default
    (`~/bopos-logs/`) only; the internal/usb choice and per-write effective
    resolution land in `4-log-destination-config`. Keep the resolution
    seam (a `destination_dir()` hook) so 4 slots in without reshaping.
- **`/log <stream> <values…>`** engine-sent handler on localhost 7770 in
  `bopos.py`, alongside `/store`/`/report`/`/admin` (bopos.py:2050–2054).
  Fire-and-forget, no reply.
- **Contract amendment** — additive §4.2 term + §15 changelog row (v1.12),
  wording per the ratified proposal.
- **simfleet parity** — sim nodes accept `/log` on their engine-request
  port (new protocol features land in the simulator in the same stitch).
- **Tests** — durable shared surface ⇒ living `tests/` file (not a tied
  guard): stamp format, TSV shape, daily-file naming, invalid-stream drop,
  append-only behaviour across calls.

## Out of scope here

Destination config/envelope/heartbeat/Device tab (stitch 4), USB automount
(stitch 3), the `[bopos]` `to-bopos-log` PD edit (Bob's —
`.notes/pd-edits-for-bob.md`).
