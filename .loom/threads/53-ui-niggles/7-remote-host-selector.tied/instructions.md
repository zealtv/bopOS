# 7-remote-host-selector

Correction from Bob's second screenshot review of Remote card flow.

## Measured cause

The live server is serving the new rules, so this is not a stale asset. The
selector introduced by stitch 6 assumes this structure:

```text
#control-column-host > .control-column-derived > .control-column-cards
```

Remote actually passes `#control-column-host` itself to
`ControlColumn.create`, which adds the component classes to that same element:

```text
#control-column-host.control-column-derived > .control-column-cards
```

Both stitch-6 selectors therefore match nothing. The shared `.target-card`
560px ceiling remains on the whole host, exactly matching the screenshot.

## Scope

- Correct the Remote selectors to the real same-element structure.
- Neutralize the structural host's card face and width cap.
- Make its direct cards region the wrapping flex container.
- Update the browser-free contract to assert the real DOM-selector relation.
- Run fast and attempt the focused browser journey before tying.
