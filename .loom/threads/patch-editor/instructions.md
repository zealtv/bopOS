# patch-editor

**Goal:** a composer-helper patch-editing mode in the dashboard (its own tab,
reserved by `ui-tabs`): list host patches under `patches/`, select one to get
a generated parameter interface that sends over localhost to the patch being
edited, open the patch in its engine's editor, and add/edit manifest params
from the UI so `bopos.patch.json` never needs hand-editing. Points (and cues)
get a small dedicated spatial setup for preview.

Decisions already made with Bob (2026-07-14):

- **The editor launches PD itself, with the GUI** — same run-context launch
  path the managed audition rig uses, ports wired automatically. "Open in PD"
  = launch; no hand-opened-PD port convention.
- **Cues become declarable in the manifest** — an optional additive
  `"cues": []` list (v1.3→v1.4 amendment); the editor renders a fire button
  per declared cue. Bob ratifies the exact wording via pe-0.
- Independent at the UI level, **shared infrastructure underneath**: build as
  a mode over the managed-audition machinery (N=1 engine, real localhost
  surface, existing `/pt` proximity computation), not a parallel stack. Like
  the listener puck, editor-only traffic is private loopback state, outside
  the fleet OSC contract.

Constraints:

- Never edit `.pd` files (house rule). The editor *launches* PD; PD authoring
  is Bob's.
- Manifest editing is host-file editing — no runtime param introspection on
  the wire (contract exclusion stands).
- A param added mid-session isn't validated until engine start: pe-0 decides
  restart-on-save vs a localhost-only dev-mode relay.
- The parked single-object seam idea (memory `bopos-single-object-idea`: merge
  [bopos]+[bopos.out~]) should be examined in this thread's design work — the
  editor walkthrough is the live composer-workflow context it was waiting for.

Ordering: design (pe-0) may be drafted alongside `ui-tabs`; implementation
lands in the Patch editor tab after tabs-1. Before
`patch-workflow-friction` — the composer guide should teach this workflow.
