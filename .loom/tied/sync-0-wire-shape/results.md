# sync-0 verify results

Wire shape pinned in `docs/OSC-CONTRACT.md §3.1`, rationale in `wire-shape.md`,
simulator support in `tools/simfleet.py`, browser-free socket verify in
`verify_sync.py`.

## Run recipe

```sh
# deps (pure socket test -- no Playwright/dashboard needed):
pip install python-osc
python3 verify_sync.py      # from this stitch dir; locates the repo by marker
```

## Output (stable across 3 runs, 2026-07-09)

```
[PASS] heartbeats seen from both devices
[PASS] a pong per device
[PASS] pongs well-formed (seq+leaderTime echoed, uid=mac, ns int)
[PASS] cue fired on both devices
[PASS] devices fired coherently (skew cancelled)
[PASS] fired at the intended instant

sync-0 wire-shape checks passed
```

The last two checks are the substance: two sim devices given random ±40 ms
fake clock skews, handed the leader-computed `/<id>/sync/offset`, both fire one
broadcast `/cue` within 20 ms of each other and 25 ms of the intended instant —
the skew is genuinely cancelled by the offset. (An earlier verify bug that
computed the offset one drain-window too late failed "fired at the intended
instant" by ~1001 ms, confirming that check has teeth.)

## Manual smoke (optional)

```sh
python3 tools/simfleet.py --devices 3 --sync-skew-ms 30 --sync-jitter-ms 2
# then, as the leader, send /sync/ping to 6660 and watch /sync/pong on 5550;
# push /<id>/sync/offset, send /cue <id> <sharedTimeNs> and watch the fires log.
```

## For the next stitches

- `sync-1-leader`: the dashboard backend implements the leader side — ping loop
  (500±100 ms), pong collection, `oneWay/offset` smoothing, per-device
  `/<id>/sync/offset` push. simfleet is the fleet under test.
- `sync-2-helper-cue`: helper.py implements the node side — answer ping, slew
  toward the pushed offset, convert `/cue` to a local monotonic deadline, fire
  bare `/cue <cueId>` to PD on 7770.
- `sync-3-jitter-harness`: the honest measurement (GPIO/click on N nodes,
  recorded together). simfleet's `fire_mono` logging is the software analogue.
