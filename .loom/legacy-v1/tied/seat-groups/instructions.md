# seat-groups

This is just a brain dump for the moment but something that would be really useful is to be able to assign the seats into groups. Groups would resolve in the same way as ID and all. So for example, seat 0, seat 1, and seat 2 could all be put into group 1. If an OSC message was sent to `/g1/p/gain 0`, that message would decompose onto all of the seats in that group. This requires a little bit of fleshing out but hopefully it's a fairly simple implementation.

Bob clarified on 2026-07-15 that the selector is lowercase (`g1`, not `G1`)
and that the omitted `/p/` in the original example was a typo.

After ratifying the protocol/data proposal, Bob added a Seats-workspace UX
requirement: highlight the spatial distribution of a selected group at a
glance, explore showing multiple groups with multiple colours, and give
overlapping Seat memberships explicit UX-design attention before implementation.
