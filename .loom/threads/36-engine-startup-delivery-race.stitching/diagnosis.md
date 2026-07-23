# Diagnosis + fix — engine startup delivery race

## Root cause (confirmed by reading the code path)

`send_to_engine` (`python/bopos.py`) sends over a module-level pyOSC3 `OSCClient`
connected to `127.0.0.1:6661`. During the window between `bopos.py` binding the
LAN listener and Pure Data opening 6661 (and on any engine restart), that port
is closed, so `client.send` raises `ConnectionRefusedError` (Errno 111).

`ConnectionRefusedError` **is an `OSError`**. Several `send_to_engine` call sites
are wrapped (`apply_assign`, `relay_provided_term`, `send_groups_to_engine`) and
merely *lose* the data; but others are **unwrapped** — notably the `/p/*`
parameter path (`param_generator.apply` → emit → `send_to_engine`) and
`config_callback`. An unwrapped refusal raised inside `handle_lan_datagram`
propagated up to the listener loop:

```python
while True:
    try:
        datagram, source = sock.recvfrom(65535)
        handle_lan_datagram(datagram, source, sock, state)
    except OSError as error:                 # catches ConnectionRefusedError!
        print("WARNING: LAN OSC LISTENER FAILED; REBINDING:", error)
        sock.close(); break
```

The loop mistook the *engine* refusal for its own *listener* failure, closed the
LAN socket and rebound — repeatedly, for every provided term arriving during the
cold-start window. Net effect: the node stops processing Dashboard commands
(unresponsive in the Dashboard) while SSH, on a separate path, stays up. Exactly
the reported symptom, and it matches "three provided-term sends raised Errno 111."

## Which early terms can be lost

- Wrapped sends (`/id` on assign, `/groups`, `relay_provided_term`) were caught
  but **silently dropped** — engine never got them, no replay.
- Unwrapped sends (`/p/*` static/automation, `config_callback`) additionally
  **tore down the LAN listener** — the responsiveness failure.
- Transient cues/points are fire-and-forget and are *not* meant to be replayed.
- Running automation generators (fade/loop/lfo) are "forgotten by design across
  restarts" (parameter-automation ratification) — must not be buffered/replayed.

## Fix (readiness/replay boundary)

1. **`send_to_engine` swallows connection-level errors** (`except OSError` →
   log rate-limited, return `False`). No call site can leak a refusal into a LAN
   handler again; the listener stays up while the engine starts. *(This is the
   responsiveness fix — the actual "unresponsive" defect.)*
2. **`deliver_engine_context(state)`** redelivers durable authoritative state —
   `/id`, `/groups`, and the latest *static* value of each live param — once the
   engine is ready. Idempotent full-state; harmless on the normal launch path.
3. **`heartbeat_loop` fires it on the engine-alive `0 -> 1` transition**, reusing
   the existing `engine_alive()` computation (pid/JACK). No new polling thread.
4. **`record_static_param`** captures the latest `kind == "set"` value per param
   identity in the `/p/*` handler; a non-static spec (generator/stop) *clears*
   any stale static value so it is never replayed over live automation.

Delivers ID + groups + persistent live values after ready; does not buffer
transient cues/points; no automation replay. Meets the stitch's boundary.

## Verification

- **Browser-free node-protocol test:** `tests/test_engine_ready_replay.py`
  (imports real `bopos.py` with pyOSC3 faked, per `test_node_fetch_dispatch.py`).
  6 tests: send swallows ECONNREFUSED / reports success when up; the
  previously-unwrapped `config_callback` path no longer raises when the engine
  refuses; `deliver_engine_context` redelivers `/id` + `/groups`; a static param
  is recorded and replayed; a generator spec is not buffered.
  - `~/.venvs/bopos/bin/python -m unittest tests.test_engine_ready_replay -v` → **6 OK**
- **Regression:** full `tests/` suite → **50 OK** (was 44 + 6 new).
  - `~/.venvs/bopos/bin/python -m unittest discover -s tests -p "test_*.py"`

Note: simfleet is a protocol simulator (fake Pis), not a runner of real
`bopos.py`, so the engine-port race is not something simfleet models — the
browser-free test against the real node code is the right coverage vehicle here.

## Remaining — hardware adoption check (not claimed as done)

Final confirmation on a freshly-flashed Pi (the real cold cache / first fetch /
timeout cold-start) needs the rig — **Finn Jet** is the natural target (that is
where it was observed). The software fix removes the confirmed root cause and is
unit-proven; the on-Pi cold boot is an adoption check, per the project's
hardware-verification rule (cf. 33-device-audio-config's tie note).
