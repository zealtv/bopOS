# d8-2 results

The dashboard manages `audition.py` as a simulation mode: every seat gets a
virtual audition node, command traffic switches to loopback, real bindings are
preserved but not driven, and teardown restores the performance target and
reaps all virtual rows. The sidebar exposes the mode and occupancy; the listener
puck renders only while simulation is active. Instance count remains uncapped
per Bob's deferral.

- `verify_d8_simulation.py` — 9/9 passed with a real two-node no-audio audition
  child on isolated ports, including teardown and restart persistence.
- Python compilation and `node --check` for both dashboard JS files passed.
