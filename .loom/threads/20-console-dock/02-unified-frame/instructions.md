# 02-unified-frame

The shippable slice of Bob's actual complaint: "I'd like the terminals to
collapse and expand together, so they're essentially one window."

**Do not start before `01-dock-design` is tied** — this builds the frame the
design names, and redoing the container twice is the waste this ordering exists
to avoid.

## Outcome

- The outgoing and incoming OSC consoles become **one** frame with one collapse
  control and one header, the two streams selected by tabs within it.
- Collapse/expand is a single action affecting both. State persists per the
  design's persistence ruling.
- The frame carries the tab strip the later children extend — don't hard-code
  "two tabs".
- Preserved from the shipped consoles: per-view client-side filtering, the
  message counts, bounded scrollback, and the DOM living outside `#show-root`
  so the high-rate stream never re-renders the show table.
- Existing tied verify suites that touch the consoles must still pass —
  update their selectors in this stitch if the markup moves, and say so.

## Verify

Playwright per `CLAUDE.md`: drive the real `dashboard/server.py` +
`tools/simfleet.py`, assert one collapse control toggles both streams, tab
switching shows the right stream, filtering still narrows each stream
independently, and — the performance property — that show-table DOM nodes are
not replaced while OSC traffic flows. Note gotcha 8: elements inside a
non-active tab panel resolve but never become *visible*; wait with
`state="attached"`.
