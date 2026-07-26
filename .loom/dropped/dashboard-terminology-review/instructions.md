# dashboard-terminology-review

Holistically review the overlapping **Dashboard** and **facilitator**
terminology before renaming the Dashboard tab.

This is a Bob-gated design stitch, not authorization for implementation.
Inventory and reconcile at least:

- **Dashboard** as the name of the overall web application;
- **Dashboard** as the manual live-control tab beside Show;
- the patch-manifest `dashboard: true` promotion field and its public meaning;
- the `/facilitator` compatibility route, `facilitator.html/js/css`, embedded
  view, internal identifiers, documentation, and historical operator language;
- user-facing phrases such as “Open standalone dashboard”, “Dashboard cues”,
  live controls, promoted controls, and admin command promotion;
- migration and compatibility costs for manifests, URLs, saved state, tests,
  external tooling, and composer/operator documentation.

Produce a small terminology system rather than choosing a tab label in
isolation. Compare candidate names for the application, manual-control tab,
manifest capability, and compatibility surface; identify which terms are
public contracts versus safe internal cleanup; recommend a migration path; and
bring the decision back to Bob for ratification before changing code or docs.

Context: on 2026-07-20 Bob accepted the Show-first tab order but explicitly
kept **Dashboard** as the tab label pending this review.
