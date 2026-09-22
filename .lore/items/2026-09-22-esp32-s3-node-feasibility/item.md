# ESP32-S3 as a restricted bopOS node — feasibility exploration

Whether a cheap microcontroller node running only the trigger layer can be a legal bopOS citizen, what it would cost to build, and what hardware and OSC-surface design would make it flexible enough to be worth deploying.

## Source

Chat session 2026-09-22. Bob's question: *"i am wondering about future possible
devices for bopOS to interface with — wondering what the feasibility of a esp32
s3 node is. possibly with samples on a usb flash drive or sd card. and a
restricted feature set (ie only the trigger layer and associated osc parsing)."*
Then: *"the other side is hardware — we'd still need an audio amp and power. but
would be good to think about how to make something like this that could be small,
cheap, and flexible (ie define the right osc address and behaviour so it can
perform flexibly. the trigger layer is pretty close to that)."*

Analysis is Claude's, read against the ratified contract at `docs/OSC-CONTRACT.md`
v1.17 and the node source in `python/` as of commit `ecded85`.

## Outcome

**Nothing is ratified and nothing is queued.** Bob's own framing: *"it's a later
thing but something we might explore."* Ordering is deliberate — the horizon
refactor (`.notes/horizon-architecture-refactor.md`) has engine agnosticism
half-built and `sclang` has never once launched under the framework, so this sits
behind that, not beside it.

Read `content/feasibility.md` first. The hardware sketch and the flexibility
design are `content/hardware-sketch.md` and
`content/flexible-trigger-surface.md`; what would need a Bob ruling before any of
it becomes a thread is `content/open-questions.md`.

## Provenance of claims

Two kinds of claim live in this item and they are marked throughout:

- **Measured from the repo** — file paths, line counts, contract sections. These
  were read in-session and are checkable.
- **Asserted from general knowledge** — every ESP32-S3 hardware figure (RAM,
  PSRAM bandwidth, SD throughput, part prices, power draw). **None of it was
  measured**, no S3 was in the room, and prices move. Treat all of it as a
  starting point for a bench test, not as evidence.

## Tags

bopos, esp32, esp32-s3, node, hardware, trigger-layer, event-plane, engine-agnosticism, feasibility, exploration, horizon
