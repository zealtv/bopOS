# Worklog — 1-design-and-schema (2026-07-18)

Deliverable: `.notes/show-tab-design-2026-07-18.md` (369 lines). Drafted by a
Sonnet delegate against this stitch's checklist; reviewed in full by the
orchestrator (Fable) before tying.

Verification: note covers all four required sections — braindump↔brainstorm
comparison (incl. de-facto vs open §08 decisions), show-file schema with
worked example (storage `dashboard/shows/<name>.json`, venue-convention;
server-minted 8-hex uids; tagged then-actions with goto-by-uid), WS API
patterned on save_venue/fire_cue/add_seat conventions, and playback
semantics at implementable precision (state machine, shuffle-bag episode
rule, section derivation, edge cases, forward-sync = reuse fire_cue for
/cue only with immediate fallback, PD-float and 0-index laws respected).

Discoveries recorded in the note's closing section: stitch 3 needs explicit
per-section "play episode" bookkeeping for bag reset; stitch 5 should reuse
the live-controls target selector. Stitches 2–7 instructions checked — no
edits needed.
