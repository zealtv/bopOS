# friction-0-docs

**.waiting (2026-07-13, gate updated same day):** Bob's composer-experience
brain dump (`.lore/items/2026-07-13-composer-experience-brain-dump`) makes
this doc a first-class deliverable — "how to create a patch, what you need
running locally, step by step how to get it onto a device, in a beautifully
laid out, very simple, clearly labelled markdown file". The model is now
**ratified** (`.loom/tied/dist-0-proposal/` — proposal + ratification); this
doc must be walked against the real Send flow on simfleet, so resume once
`patch-asset-sync/dist-2` and `dist-3` are tied. Content rulings from Bob (2026-07-13): the main flow
is git-free (folder in `patches/`, copy a demo, edit, Send); **git gets its
own section, "advanced workflow with git"** — not a prerequisite anywhere
else. The network-recipe checklist below is not gated; it can split out if
the wait drags.

The documentation half of lowering the musician barrier (parent has context).
Written for a musician, not an agent — plain language, checklists, no jargon.

- [ ] "Bring a patch" path end-to-end: who makes the repo, who presses what,
      from `main.pd` on a laptop to sound on a Pi via the dashboard
      (dashboard-4 patch management is built — write against it, walk the flow
      on simfleet while writing so the doc matches reality).
- [ ] Network setup recipe: the travel-router pattern (documented
      SSID/password convention) so "get the Pis on WiFi" is a checklist, not
      an adventure.
- [ ] Decide placement (`docs/` for durable, likely) and link from README.

DECISION (Bob, don't build): the parent's "dashboard zip upload to bypass
GitHub" idea — if writing the doc reveals the git path is genuinely too steep
for workshops, write a short proposal instead of building; surface via
gremlin.
