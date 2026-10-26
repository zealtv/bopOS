# Manager review 1 — 7-osc-input-port

Solid work: the pure `translate`, the ramp with an injected clock, the rule set and the two-node
simfleet check all match the ratified proposal. One change before landing:

1. **Coalesce the state broadcasts the input triggers (must fix).** `OSCInput.note()` and the
   parameter path each call `queue_broadcast('state')` per datagram. The dashboard's own
   controls do that per human gesture, but an outside app can stream: qtable automating a
   parameter at 30–60 Hz, or any LAN sender spraying undeclared addresses, would push a full
   `state` snapshot to every browser 30–60 times a second. Throttle the input's state
   broadcasts to at most ~10 Hz with a trailing flush (one pending broadcast at a time; the last
   change always reaches the UI). Keep the device sends themselves unthrottled. `save_debounced`
   is already fine. Add a test: a burst of N rejections or parameter writes inside one window
   queues one state broadcast, and a final one follows after the window.

Then `git merge main`, rerun the fast suite, update `worker-result.md` (keep READY FOR REVIEW at
the top) and end with `WORKER DONE`. No need to rerun the full browser tier unless you touch UI.
