# 2-served-bytes

Count the bytes the dashboard's distribution file server sends to each
client IP, and expose them to the rest of the dashboard.

## Do

- `DistributionStaticFiles` (`dashboard/server.py`, mounted at `/assets` and
  `/patches`) subclasses Starlette `StaticFiles`. Wrap its ASGI `send` (for
  example by overriding `__call__(scope, receive, send)`) to add
  `len(body)` from each `http.response.body` message to a counter keyed by
  `scope["client"][0]`, with a last-activity time. Count range responses
  (the Pi resumes `.part` files with `Range`) as what was actually sent.
- Also count manifest requests (`/assets/{slot}/.manifest.json`) as activity
  (a time, not bytes), so the Pi's first contact registers.
- Keep it to a small object, e.g. `ServedBytes` with `reset(ip)`,
  `snapshot(ip) -> {bytes, last_at}`, owned by the `Dashboard` and handed to
  the app factory. The queue (`3-`) reads it; nothing is broadcast to
  browsers from here.
- Don't slow down serving: a dict update per chunk is fine; no locks across
  awaits.

## Verify

Unit tests with the Starlette test client or `httpx`: a full GET and a
`Range` GET count the right bytes under the client IP; manifest hits update
the activity time; a 404 for a dotfile counts nothing.
