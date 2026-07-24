# 2-nodelog-facility — verification

Implemented per the ratified design (`.loom/tied/1-logging-seed-design/`).
This stitch lands the facility + wire only; destination config (stitch 4),
USB automount (stitch 3), and the `[bopos]` `to-bopos-log` PD edit (Bob's,
tracked in `.notes/pd-edits-for-bob.md`) are out of scope.

## What landed

- **`python/nodelog.py`** — `NodeLog.append(stream, values)` + module-level
  `nodelog.append/configure/close`:
  - node-stamps at call time, ISO-8601 local with offset, ms precision
    (`2026-07-24T14:03:22.512+01:00`);
  - one TSV line `timestamp<TAB>stream<TAB>values…` (values space-joined);
  - stream names validated `[A-Za-z0-9_-]+` (report rule); invalid → warned,
    dropped, never raised;
  - per-stream daily files `<stream>-YYYY-MM-DD.log`; 50 MB per-file cap with
    `-N` continuation;
  - append + flush per entry, no per-line fsync; fsync on stream close / day
    roll / cap trip / destination change / `close()`;
  - writes to the internal default `~/bopos-logs/` this stitch; the
    `destination_dir()` seam (static path **or** a callable re-evaluated per
    entry) is what stitch 4 slots into — a callable destination lets a hot USB
    switch take effect on the next write with no restart.
- **`/log <stream> <values…>`** engine handler (`log_callback`) registered on
  localhost 7770 in `bopos.py`, alongside `/store`/`/report`/`/admin`.
  Fire-and-forget, no reply. `exit_handler` now `nodelog.close()`s (fsync).
- **Contract amendment v1.12** — additive §4.2 `/log` term + §15 changelog row
  in `docs/OSC-CONTRACT.md`; mirrored in `docs/OSC-REFERENCE.md`
  (Engine → bopos.py table + the 7770 term list). Version header bumped
  1.11 → 1.12. The node's reported `contract_version` bumped in lockstep in
  `bopos.py`, `tools/simfleet.py`, `tools/audition.py` (the established
  per-amendment pattern).
- **simfleet parity** — `SimFleet.log_request(device, stream, values)` mirrors
  the real node (same stamp/validate/append contract), following the
  `admin_request` direct-call precedent (N sim devices share one process, so
  there is no private 7770 socket to bind; the method is what a verify harness
  drives). Records into `device.log_streams` for inspection.

## Verified (software)

`~/.venvs/bopos/bin/python -m unittest tests.test_nodelog -v` — 12 pass:

- stamp format (ISO-8601 local + offset + ms, regex);
- TSV shape (3 tab fields, values space-joined);
- daily-file naming (`<stream>-YYYY-MM-DD.log`, date matches stamp);
- invalid-stream drop (empty / space / dot / slash / `../` → no file);
- append-only across calls (3 appends → 3 lines, order preserved);
- streams are separate files; empty-values still stamps;
- file-cap roll to `-N` continuation;
- destination hook re-evaluated per entry (the stitch-4 seam);
- never raises on an unwritable destination;
- **bopos.py**: `/log` registered on the server + `log_callback` dispatches to
  `nodelog.append`, missing stream is a no-op (no raise);
- **simfleet**: `log_request` records valid streams, drops invalid.

Full non-browser suite green after the lockstep version bump:
`~/.venvs/bopos/bin/python -m unittest discover -s tests -p 'test_*.py'`
→ **63 pass**. Three pre-existing tests pinned the exact contract version
(`test_asset_slot_context`, `test_device_enabled`, `verify_device_control_modes`)
and were updated 1.11 → 1.12 in lockstep with the amendment.

## Not verified here (out of scope / needs Bob or hardware)

- The `[bopos]` `to-bopos-log` PD bus — Bob's `.pd` edit
  (`.notes/pd-edits-for-bob.md`). Until wired, a `/log` from PD is simply an
  unknown message on 7770; SC/other engines can send the wire directly today.
- Real on-Pi file writes / power-cut truncation behaviour — hardware adoption
  check (Ciro Toast). Software models per-entry flush; the truncated-last-line
  failure mode is by design.
