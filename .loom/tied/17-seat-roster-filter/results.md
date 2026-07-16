# Seat and Physical device roster containment — results

The Seats workspace now keeps its numeric roster inside a 432 px scrolling
region (about eight ordinary rows) and provides the same live name-prefix
filter used by the Group membership inspector. No-match and clear-filter states
are explicit without changing Seat selection, inline naming, heartbeat, or
patch badges.

The Physical devices roster uses the same bounded-scroll containment. Its
existing all/online/offline/bound/unbound dropdown remains the sole filter; no
name search was added.

## Verification

Passed on 2026-07-16:

```sh
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/tied/17-seat-roster-filter/verify_seat_roster_filter.py
# 9/9

node --check dashboard/static/js/dashboard.js
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python -m py_compile \
  .loom/tied/17-seat-roster-filter/verify_seat_roster_filter.py
git diff --check
```

The focused test launches the real Dashboard, 14-node simfleet, and touch-sized
Chromium. Visual evidence is `seat-roster-filter-ipad.png`. No `.pd` file
changed. Real iPad/Safari was not exercised.
