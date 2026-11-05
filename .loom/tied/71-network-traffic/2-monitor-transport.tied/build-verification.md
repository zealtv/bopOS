# Monitor transport build verification — 2026-10-05

Built Bob's “OK all” ruling on branch `stitch/71-2-monitor`, from `68168d8`.
No OSC addresses/ports, Pd files, node poll cadence or sync routing changed.
Exact new wording/screenshots still go to Bob before tie; no loom command run.

## Software verification

- Fast suite: 533 passing tests, including 13 transport tests. A stalled writer
  is flooded with raw/sample traffic: queues remain capped, no extra tasks are
  created, a healthy writer continues, and deadline cleanup releases only the
  stalled connection's source consumer. Tests cover redaction/preview limits,
  100-device coalescing/enrichment, lane fairness, UID/group attribution without
  IP guessing, priority/snapshot limits, atomic selections, generation changes,
  and prepared tombstone invalidation without raw loss. Changing capture does
  not refill admission tokens. Invalid visual IO values drop whole bundles.
- Browser suite: all 33 `tests/verify_*.py` pass. The new production OSC/WS
  journey checks default class suppression/opt-in, structured versus local
  history filters, Pause/no backlog, dock/document hiding, both split panes,
  rejected replacement, visible drops/gaps, Clear, reconnect/stale generations,
  map cadence, consumed clock facts, Remote's bounded/expiring event buffer,
  and snapshot replay. Existing IO receipts/pending transitions remain ordered.
- `node --check` on `ws.js` and `monitor.js`; `git diff --check` pass.
- Original proposal evidence verifier still passes; its dated files were
  preserved. New `verify_build_measurement.py` validates final 50/100-node
  observations against exact per-peer counts/encoded bytes and batch bounds.

An initial Remote scroll check captured a detached card's zero rect; standalone
rerun and the complete rerun passed. The IO raw-WS verifier was updated to unwrap
telemetry, and administrative pending state explicitly uses the priority lane.
The obsolete per-pong sync-publication assertion was replaced with a check that
backend samples still converge without that unused WS stream.

## Loopback measurements

`measure_monitor.py`: default 12 s acquisition; each phase 3 s settling + 12 s
counting, simfleet heartbeat 10 s, real production OSC/WS, no Pd, compression off.
The after clients consume quiet Incoming/Outgoing, map and clock summaries.
Snapshots/inventory on connect are excluded. All runs' source hashes stayed
unchanged while running; final hashes include the new broker.

| Phase | Before 50 nodes: WS/s combined | After 50: WS/s combined | Before B/s per client | After B/s per client |
| --- | ---: | ---: | ---: | ---: |
| No clients, static | 0 | 0 | — | — |
| One client, static | 311.65 | 3.92 | 56,403 | 20,399 |
| One client, moving | 361.60 | 9.83 | 57,734 | 17,170 |
| Three clients, moving | 1,040.32 | 29.74 | 60,238 | 23,304–23,333 |

At 100 nodes: 3.92 WS/s static; 9.91 WS/s one moving client; 29.49 WS/s
combined for three moving clients. Bytes per client were 39,233 static,
31,406 one moving, and 43,387–43,403 with three moving clients. Both after
runs created zero publication tasks, delivered zero default high-rate raw lines,
reported zero transport drops, and stayed within 100 entries/32 KiB per envelope
and 10 frames/s/client (allowing counting-window boundary skew).

Committed summaries: `build-before-50.json`, `build-after-50.json`,
`build-after-100.json`. Full after observations/logs remain in scratchpad
`monitor-71-2-after/` and `monitor-71-2-100/`; the fresh before observations are
`monitor-71-2-before.jsonl`. The original proposal evidence remains unchanged.

## Visible wording for Bob

Controls: “Search retained lines: /p/* !/sync”, “Capture filters”, “Address
starts with”, “Exclude addresses”, “Device UIDs”, “All devices”, “Include raw
lines:”, “Sync”, “Heartbeats”, “Points”. Help explains that both panes share
filters, prefixes/UIDs are space-separated, and excluded traffic never enters
history. Summary: “Sync, heartbeats, points excluded.” / “All traffic classes
included.”; “Rates/s: sync N, heartbeats N, points N. N filtered · N unattributed”.
Loss: “⚠ N matching messages dropped · N previews shortened”; gap line
“N matching messages dropped”; shortened previews show omitted bytes/values.
Pause/start/filter/reconnect notes explicitly describe absent hidden/paused
history and unknown traffic during a lost connection. Clear resets local loss
baselines. System: “N / N with 3+ samples”, with “Refreshes each second while
this panel is visible”. These counts are not physical timing measurements.

Screenshots generated via `BOPOS_MONITOR_TRANSPORT_SCREENSHOT` in scratchpad:
`monitor-71-2-{1440,420}-{light,dark}.png`, plus `monitor-71-2-system.png`.
Inspected rendered screenshots; filters, rates, amber loss indicator and gap
line are legible at both widths/themes. Screenshots stabilize an injected
12-drop/2-shortened-preview fixture after actual live loss was verified.

## Remaining verification and integration

Bob reviews exact wording/screenshots before tie. Ten-minute browser heap/CPU,
ordinary laptop/tablet use, physical Wi-Fi and audio/module fidelity are pending;
this evidence establishes software frame/byte/queue behavior only. No Modules
panels were built. The broker's selected-module adapter shares 59/8's source,
keeps original values/timetags/order, and exposes explicit drop counters; 59/9
owns panel selection/visibility/transient rendering and pop-out UI.

The parallel 71/1 change owns sync routing. Keep its unicast offset routing
when merging; this branch only removes the per-pong WS publication/throttle and
changes the OSC tap path. Documentation/API/bounds: `docs/MONITOR-TRANSPORT.md`.
