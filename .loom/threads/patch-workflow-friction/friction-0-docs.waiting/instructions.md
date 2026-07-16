# friction-0-documentation-review

**.waiting only for the next-session boundary (2026-07-16):** claim this stitch
first in the next session. Its distribution prerequisites are tied and Bob has
explicitly selected the documentation review as the next work. Bob's composer
experience brain dump (`.lore/items/2026-07-13-composer-experience-brain-dump`) makes
this doc a first-class deliverable — "how to create a patch, what you need
running locally, step by step how to get it onto a device, in a beautifully
laid out, very simple, clearly labelled markdown file". The model is now
**ratified** (`.loom/tied/dist-0-proposal/` — proposal + ratification); this
doc must be walked against the real Send flow on simfleet;
`patch-asset-sync/dist-2` and `dist-3` are tied. Content rulings from Bob
(2026-07-13): the main flow
is git-free (folder in `patches/`, copy a demo, edit, Send); **git gets its
own section, "advanced workflow with git"** — not a prerequisite anywhere
else. The network-recipe checklist below is not gated; it can split out if
the wait drags.

**Scope revision (Bob, 2026-07-16):** this is now a complete
documentation review, not only a composer getting-started page. Preserve the
composer deliverable below, but first establish a clear documentation
architecture and reconcile the existing material with the finished system.

The README is the friendly front door. Write as if introducing bopOS to an
intelligent friend who is somewhat familiar with audio programming and may know
what Pure Data is, but is not assumed to be an audio expert or developer. It
should explain plainly what bopOS is, what problem it solves, how its pieces
work together, and where to go next. Move implementation detail, installation
commands, protocol facts, and operator reference out of the README rather than
making the introduction carry every audience.

Create or clearly identify three routes through the documentation:

- [ ] **Getting started:** the shortest path to seeing and understanding a
      working bopOS system, with prerequisites and clearly labelled next steps.
- [ ] **Composer guide:** the git-free create/edit/audition/deploy path for a
      musician, from a local patch to sound on the fleet through the finished
      Dashboard. Git belongs only in **Advanced workflow with Git**.
- [ ] **Technical documentation:** installation, architecture, runtime and
      engine boundaries, manifests, networking, OSC, hardware, verification,
      and operational reference. Split this across sensible durable documents;
      do not create one replacement dumping ground.

Audit the complete current documentation surface (`README.md`, `docs/`,
`dashboard/README.md`, `patches/README.md`, and linked durable guides) for stale
workflow, duplicated facts, broken hierarchy, unexplained jargon, and links
that strand a reader. Establish one obvious navigation map from the README and
avoid maintaining the same normative detail in several places.

Write for people, not agents: plain language, short labelled sections,
checklists where sequence matters, and no assumed terminal or Git fluency in
the introductory or composer paths.

- [ ] "Bring a patch" path end-to-end: who makes the repo, who presses what,
      from `main.pd` on a laptop to sound on a Pi via the dashboard
      (dashboard-4 patch management is built — write against it, walk the flow
      on simfleet while writing so the doc matches reality).
- [ ] Network setup recipe: the travel-router pattern (documented
      SSID/password convention) so "get the Pis on WiFi" is a checklist, not
      an adventure.
- [ ] Decide placement (`docs/` for durable, likely) and link from README.
- [ ] Walk every documented Dashboard label and action against the real current
      UI and simfleet while writing; record hardware-only claims honestly.

DECISION (Bob, don't build): the parent's "dashboard zip upload to bypass
GitHub" idea — if writing the doc reveals the git path is genuinely too steep
for workshops, write a short proposal instead of building; surface via
gremlin.
