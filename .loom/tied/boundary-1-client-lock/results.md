# boundary-1-client-lock results

## Change

`python/helper.py` now routes all 15 helper-to-engine `OSCClient.send()` call
sites through `send_to_engine()`. One module-level lock serializes each OSC
datagram without widening the critical section to point batches, lifecycle
operations, or unrelated UDP reply sockets. Wire addresses, values, error
handling, and call ordering within each caller are unchanged. No `/helper/*`
alias was added.

## Verification

Commands used the documented `~/.venvs/bopos` environment. `pyOSC3==1.2` was
installed there because it was initially missing.

```sh
~/.venvs/bopos/bin/python -m py_compile python/helper.py \
  .loom/threads/engine-boundary-design/boundary-6-contract-v12-and-renames/boundary-5-launch-context-and-topology/boundary-4-pd-edit-wave/boundary-3-framework-slimdown/boundary-2-pd-parallel-relay/boundary-1-client-lock.stitching/verify_client_lock.py
```

PASS (no output).

```sh
~/.venvs/bopos/bin/python \
  .loom/threads/engine-boundary-design/boundary-6-contract-v12-and-renames/boundary-5-launch-context-and-topology/boundary-4-pd-edit-wave/boundary-3-framework-slimdown/boundary-2-pd-parallel-relay/boundary-1-client-lock.stitching/verify_client_lock.py
```

PASS: four simultaneous cue/LAN workers sent 2,000 unique messages through a
deliberately slow recording client. Maximum concurrent `client.send()` calls
was one; all 2,000 messages were retained, decoded, and matched their original
address and value.

```sh
~/.venvs/bopos/bin/python .loom/tied/sync-2-helper-cue/verify_sync_helper.py
```

PASS: 15 checks covering offset slew, cue policy, sync pong, and real-helper
loopback cue delivery.

```sh
~/.venvs/bopos/bin/python .loom/tied/seam-3-points-node-side/verify_points_node_side.py
```

PASS: 17 checks covering assignment, point decomposition, sparse updates,
clear/release, frame cadence, master catch-up, and absence of tracebacks.

`rg -n "client\\.send\\(" python/helper.py` leaves exactly one occurrence, inside
the locked wrapper.

## Boundaries

This was a browser-free, hardware-free localhost verification on macOS. It did
not run an audio engine, a production node, or a real installation LAN. No Pure
Data file was edited.
