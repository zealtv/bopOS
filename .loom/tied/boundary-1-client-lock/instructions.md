# boundary-1-client-lock

Make the shared helper-to-engine OSC client safe before expanding relay use.

- Add one lock covering every `client.send()` path shared by the LAN listener,
  cue scheduler, configuration/persistence handlers, and other threads.
- Add a focused concurrency regression/soak test for simultaneous cue and LAN
  delivery; confirm messages remain decodable and no send is lost or corrupt.
- Preserve current wire behavior. Do not add the council's rejected
  `/helper/*` compatibility alias.
- Follow `docs/VERIFICATION.md` and record results in this stitch.
- Never edit `.pd` files.
