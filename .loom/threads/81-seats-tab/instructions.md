# 81-seats-tab

**Goal:** two Seats-tab fixes Bob raised on 2026-10-27 while live-testing the
KC fleet: the UNPLACED tray loses Seats off its right edge, and the map
cannot show which device sits in which Seat.

Both touch `dashboard/static/js/spatial.js` (the Seats map) and its rules in
`dashboard/static/css/style.css`. They don't depend on each other.
