# Session directives — 2026-07-27 (paraphrased from Bob's message)

1. **UI first, architecture review parallel/following.** The control-panel UI
   pass (from the mockup) is the initial priority. Like the dropped Show-tab
   chrome approach: define the control panel UI, get it looking really nice,
   then develop a strategy to push that language across the whole application.
   That rollout is a separate task from the architectural decisions.

2. **Architecture review before preset implementation.** Bob smells complexity
   around devices, seats, pinning, controls — and expects presets to
   exacerbate it. He wants to get clear on how these components relate and
   whether things can simplify. Specific concerns:
   - Shows will trigger patch loads mid-show and then sequence that patch's
     parameters, including presets — possibly different patches on different
     devices, or a fleet patch switched at a point in time (he's not opposed
     to that).
   - Avoid loopy dependencies among patches, patch presets, show files, and
     seat presets. A seat preset makes sense standalone (site-specific). A
     show references patches + manifests and targets seats; seat targeting
     might change show-to-show or seats might just be repositioned — so there
     are couplings show↔seats, show↔patches/presets to get right.
   - Method: first understand the system as it currently is, then think
     through workflows and their consequences. Ideal is **simplicity** —
     flexibility, and a system small enough to hold in one's mind.
   - Constraint: **the system currently works and must remain working.**
     Prefer small changes that keep things clean, flexible, ordered — not a
     rewrite.

3. **Ruling — Control tab shows the full manifest.** By default the Control
   tab must show *all* parameters in the manifest and allow value-setting and
   generator application on any of them. The manifest's `dashboard:` option
   changes meaning: it defines what appears on the **iPad facilitator view**
   (the simplified mixing/basic-controls surface), not what the Control tab
   shows.
