# Decisions

## Authored order is completion order

`ShowEngine` awaits a preset reference's dashboard-owned application task before
emitting the next message in the step. This makes authored order the effective
wire order for mixed preset references and OSC messages. A step's duration timer
is armed after its ordered message emission completes, so a slow preset apply
delays that step's timer rather than allowing later messages to overtake it.

## Fade takeover mirrors the displaced live slot

When a fade omits an explicit origin, the dashboard evaluates any displaced
fade, loop, or LFO at the new message's `sent_at` time. It falls back to the
durable scalar only when there is no evaluable automation entry. This matches
`GeneratorEngine.apply`; free-LFO phase remains the accepted dashboard estimate.

No wire, node, or Pure Data change is required.
