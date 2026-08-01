# Decisions — 2-control-column-component

## Component boundary

`window.ControlColumn.create({host, ...})` now owns everything whose lifetime
must be independent for N columns:

- its `ControlSurface` and `TargetPicker` instances;
- preset capture previews, the pending preview key, and the last apply report;
- the open/closed state of per-seat device command disclosures; and
- host-relative references to the picker, cards, and live status output.

The facilitator host retains the websocket, installation snapshot, master,
mute, fleet commands, venue/status furniture, and the document-wide
`interacting` flag. The instructions describe that flag as page state in the
detailed boundary and explain why: every column must freeze while an operator
is manipulating any one of them. The column receives getter/setter adapters for
that shared guard.

The existing document is still the iframe and still instantiates exactly one
column. `full` is a constructor option, replacing the column's reads of the
page-global `embedded` flag. No layout or visible behavior changed.

## Root scoping

The current `document.body` is the component host. All column queries are
relative to that host; card binding is relative to the column's cards element.
This preserves today's DOM while giving `3-iframe-retirement` and `4-n-columns`
a component that can be mounted under a narrower root without changing its
internals.

`ControlSurface` now remembers its most recently bound root per instance. All
three fade-animation queries use that root instead of `document`, so N
instances do not walk or write one another's fades. Passing the same root into
`bindPresets` also keeps identical `scope:id` preset keys inside their own
column.

No component CSS was needed. `control-column` is registered with the ownership
guard so later column-owned appearance has an explicit owner.
