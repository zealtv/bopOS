# d8-3 results

The dashboard now starts from authored seats rather than discovered hardware.
Empty-room clicks add the next free 0-indexed seat; inline names and map drags
update durable seat state. Composer binding works from either a seat or an
unbound device, fresh seats adopt reported hostnames, swaps preserve seat data,
and venue loads report both automatic rebounds and bindings still waiting for a
device. The ordered sidebar separates occupancy-badged seats, unbound devices,
forget controls, and simulation.

- `verify_d8_binding_ux.py` — 10/10 passed with the real dashboard, managed
  no-audio audition mode, Chromium, and a three-node simfleet on isolated ports.
- Adjacent d8-1 seat-model and d8-2 simulation regressions passed 9/9 each.
- Python compilation, `node --check` for both dashboard JS files, and
  `git diff --check` passed.
- No hardware, iPad/touch, or audible engine verification was performed.
