# 20-remote-hold-cancel

**Status:** ready · **high**
**Goal:** a Remote reboot/shutdown/update hold never sends unless the
operator is still holding when it completes.

Evidence: `lore:2026-10-05-bopos-review-frontend` F1 (`reproduce_frontend.py` key `detached_hold`).
`control-column.js bindCommandButton` starts a 1,200 ms timer on pointerdown;
a card re-render replaces the button via `innerHTML` without cancelling it, so
the release lands on the new node and the old timer fires. Track the pending
hold at component level; cancel it on re-render/destroy and on any
release/cancel. Don't freeze rendering to dodge it.

Done when: a browser regression (render mid-hold, release early → nothing
sent; hold through → sent once) fails before and passes after; fast and the
Remote/Control journeys green.
