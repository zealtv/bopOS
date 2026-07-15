# 04-venue-point-persistence

Reconcile production point persistence with the accepted venue/composition
workflow. Currently points are runtime-only and omitted by `durable()`. Confirm
the desired persistence boundary with Bob, then implement installation/venue
save-load, migration and wire reassertion if ratified. Editor scratch points
remain session-only.
