# 08-remove-traffic-count-copy

Remove the visible `shown` / `seen` traffic-count copy from the Monitor's
Incoming and Outgoing tab rows. Preserve traffic buffering, filtering, pause,
clear, and rendering behavior.

## Verification

- The Monitor markup no longer exposes the traffic-count outputs.
- No visible `shown` or `seen` copy remains in `monitor.js`.
- JavaScript syntax and the focused Monitor frame browser verifier pass.

## Outcome

Complete. Incoming and Outgoing retain their bounded traffic buffers and
rendering behavior without showing count copy in either tab row.
