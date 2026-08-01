# 02-editing-and-cross-surface-ui

Expose the durable registry through the dashboard without changing node state.

- Add authoritative Rename and Reset alias WebSocket operations with validation
  and concurrent duplicate rejection.
- Make unbound Forget delete both runtime observation and registry entry after
  explicit confirmation, including custom-alias loss copy.
- Use one shared alias-first identity formatter in Devices, Seat assignment,
  Assets targets and confirmations; keep Seat primary on bound Dashboard cards.
- Show hostname and UID tail as technical secondary facts and full UID where it
  can be copied.
- Keep virtual devices and venue loading outside registry mutation.
