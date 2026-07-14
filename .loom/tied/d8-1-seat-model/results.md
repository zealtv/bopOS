# d8-1 results

The dashboard now persists schema 1 seats separately from the runtime device
roster. Seat CRUD/bind/unbind/forget surfaces, venue auto-rebind, preset params,
heartbeat assignment replay, selectors, sync, and the seed export all consume
the bound seat. Old device-shaped state is deliberately ignored.

Verification:

- `~/.venvs/bopos/bin/python verify_d8_seat_model.py` — 9/9 passed.
- `python -m py_compile dashboard/state.py dashboard/server.py
  dashboard/osc_bridge.py` — passed.
- Browser restructuring is owned by d8-3; this stitch verifies the ws/state
  seam directly.
