---
name: patch-editor-and-ui-tabs-decisions
description: "Bob's 2026-07-14 rulings — patch editor launches PD with GUI, paper tab-IA before the live UI review, cues become a manifest field"
metadata: 
  node_type: memory
  type: project
  originSessionId: c18c7ad9-d5f2-4425-bdbd-dc573f1c3cb6
---

Staging session 2026-07-14: Bob proposed a composer-helper **patch editor
tab** (host patch list → generated param UI over loopback, open-in-PD,
UI-driven manifest param editing, points/cues mini spatial setup) and a
**tabbed dashboard IA** (overview / spatial / fleet management / patch
editor). Three rulings he made explicitly:

1. **The editor launches PD itself, with the GUI**, via the managed-audition
   run-context path — not a hand-opened-PD port convention.
2. **Paper IA first, hands-on review after**: ratify a written tab map
   (tabs-0), build the skeleton (tabs-1), then hold the interactive UI review
   inside the real tabs (tabs-2). He wants deliberate checkpoints, not agents
   going "hell for leather".
3. **Cues become declarable in `bopos.patch.json`** — optional additive
   `"cues": []`, a v1.3→v1.4 amendment; wording ratified in pe-0.

pe-0 was drafted and ratified the same day
(`.lore/items/2026-07-14-patch-editor-design-ratified/`). Further rulings:
sim and edit are mutually exclusive supervisor modes; v1.4 carries cues
only (single-object §4.2 amendment gets its own later revision); New patch
writes a stub `main.pd` copied verbatim from a file Bob will provide;
editor points are session-only; master is the editor's only global.

**Why:** these are pre-ratifications — later design stitches must not
re-open them as questions, only refine details.

**How to apply:** goal stitches `fleet-patch`, `ui-tabs`, `patch-editor`
carry the full context; the pe-0 walkthrough is also the live
composer-workflow context [[bopos-single-object-idea]] was waiting for.
Ordering lives in CLAUDE.md. Related: [[samples-thread-needs-dialogue]].
