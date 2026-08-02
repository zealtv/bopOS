# 6-remote-card-flow

Follow-up from Bob's screenshot review of `5-left-packed-flex-cards`:

> the cards don't seem to flex - they stay the same width as i change the width
> of the page. and on the remote page they are all in a single column - they
> should distribute like the control tab

## Cause

Control's card shells are direct children of its flex host. Remote instead has
one derived `ControlColumn`, whose shell and `.control-column-cards` region use
`display: contents`. Depending on the browser, the nested contents chain is not
giving the Remote live cards a dependable wrapping flex formatting context;
the screenshot shows the result as one 560px column.

## Scope

- Make Remote's `.control-column-cards` region an explicit wrapping, left-packed
  flex container.
- Keep the shared `.target-card` 340–560px sizing from stitch 5.
- Neutralize Remote's outer derived shell and let it span the host; it is
  structure, not another painted target card.
- Preserve Control's direct-card layout and the Remote sticky audio bar.

## Verify

- Extend the browser-free CSS contract to require Remote's actual cards region
  to be a flex container.
- Extend the focused browser measurement to check that region and card widths.
- Run `./tools/run-tests.sh fast`; attempt the focused browser journey and
  record any sandbox boundary honestly.
