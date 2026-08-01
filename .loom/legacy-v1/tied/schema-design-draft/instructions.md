# schema-design-draft

**Do this first — it gates the whole thread and steers the dashboard.** Produce a
written OSC contract proposal for Bob to ratify. No implementation in this stitch.

Deliverable: a draft `docs/OSC-CONTRACT.md` (or a lore item if it's still argumentative)
covering, with explicit **DECISION:** markers wherever Bob must choose:

- **Namespace split:** framework (`/os/*`, `/io/*`, `/sync/*`, `/cue`) vs patch
  parameters. Propose how a patch *declares* its parameters (names, ranges, defaults)
  so the dashboard can discover them instead of hardcoding gain/gain2/backing — those
  three are patch-specific legacies, not framework.
- **Port rationalisation:** today's six ports (5550/6660/6661/6662/7770/8880) smell —
  quantity, arbitrary numbers, protocol shape. Propose at least two options (e.g.
  keep-but-document vs consolidate to one port per side with namespace routing), with
  the migration cost for deployed fleets spelled out per option.
- **`/echo` resolution:** it just echoes OSC back. Propose its replacement: move into
  helper.py as a liveness/latency probe (`/os/ping` → `/os/pong <t>`), plus deliberate
  debug/discoverability design (parameter listing, verbose reporting).
- **Heartbeat shape:** `/hb <mac> <id> <version> [rssi]` from helper.py (not PD), RSSI
  switchable via bopos.config.
- **Identity-set message** for dashboard-3's assign flow.
- **Constraints section:** PD 32-bit float rule; 64-bit values as strings/int-pairs;
  which messages are broadcast vs unicast and why.

Method: read `pd/bopos.osc.pd` routing, helper.py, io/main.py, DASHBOARD.pd docs, and
`.notes/dashboard-development-context.md` §3 so the draft matches deployed reality.

When the draft is ready: mark this stitch `.waiting`, surface it to Bob, fold his
rulings back in, keep the ratified decision record in `.lore/`, land the final spec at
`docs/OSC-CONTRACT.md`, then tie. Implementation happens in sibling stitches split
from the parent afterwards.
