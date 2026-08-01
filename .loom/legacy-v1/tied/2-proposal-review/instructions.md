# 2-proposal-review

Review the ratified preset design in detail, before any of it is built. Bob
placed this stitch deliberately (2026-07-28): a second agent reads the
proposal against the actual code and reports back. Bob runs this stitch
himself ahead of the implementation stitches.

**Subject:** `.loom/tied/1-preset-architecture-design/proposal.md`, with
`decisions.md` beside it for what Bob ratified. Thread context is
`41-preset-primitive/instructions.md`.

## What this review is

An adversarial read for **defects, omissions, and unbudgeted cost** — not a
second design. The proposal is ratified; the job is to find where it is wrong,
under-specified, or more expensive than it claims, while there is still no
code to throw away.

## What is settled and not up for re-litigation

The ratified rulings in `decisions.md` (F1 `presets/` excluded from the
fingerprint, F2 `morph` over the mix function, F3 capture-as-step omits
un-preset targets, F4 stored provenance + derived dirtiness) and the earlier
rulings listed at the top of the proposal (patch-folder storage, hard
takeover, presets don't capture events, venue presets retire, collections are
show steps, groups by name, `{name, fingerprint}` drift).

**One exception:** if a ratified ruling turns out to be *unimplementable* or
to have a consequence nobody costed, say so plainly and show the evidence.
That is the most valuable thing this review can produce. Don't work around it
quietly.

## The load-bearing claims — verify each against the code

Each of these is falsifiable. Check them; don't take the proposal's word.

1. **"Apply is free."** `osc_bridge.set_param` already accepts a full argument
   list (`dashboard/osc_bridge.py:426`), so a generator preset entry replays
   with no new send path. Does that hold for *every* captured kind — enum,
   toggle, `text` (a string through `set_param`?), and a nested identity?
2. **The `presets/` exclusion is safe.** It changes `python/identity.py`'s
   walk, which both host and node use. Trace every consumer: distribution
   manifest, fingerprint, HTTP file serving, prune-to-manifest convergence on
   the node, the asset hash cache. Does a node that already holds a `presets/`
   directory (git-managed patch, or one fetched before the change) behave?
   Does prune delete it, keep it, or crash?
3. **The schema fingerprint is stable.** Does the proposed field set
   (identity, kind, min, max, options count) actually round-trip through
   `python/manifest.py`'s load/save, including derived `min`/`max` for toggle
   and enum? Does a manifest reorder — now drag-reorderable, thread
   `8-manifest-reorder` — change it? It must not.
4. **`morph` fits §3.3.** Read the grammar section and the parser
   (`python/` param grammar + `dashboard/static/js/paramspec.js`). Is `morph`
   unambiguous against existing forms, given that segment lists are bare
   numbers and options trail? Does the kind-coercion rule produce a defined
   argument vector for every kind pair the manifest allows, including
   `loop`/segment-list sources the proposal says less about than LFOs?
5. **Capture is honest.** The capture table in §1 reads from durable seat
   params plus the automation table (`osc_bridge.py:439`). Is a mid-fade
   destination really already stored (`_store_fade_destination`)? Is there a
   window where the dashboard's value and the node's differ, and does capture
   silently record the wrong one?
6. **Derived dirtiness is cheap and correct.** Per-render comparison over a
   card's params, at UI precision. Check it against the heartbeat re-render
   path — the same path `46-control-surface-probe-race` and
   `47-live-param-kinds-flake` live on. Does it add work to a hot path, or a
   new source of flapping state?

## Also look for

- **Gaps between the layers.** A pinned device runs its own patch
  (`live_scope_patch`); does the preset list follow correctly on every
  surface, including the standalone facilitator and the patch editor's
  seat-0 audition instance?
- **Failure and edge behaviour** the proposal doesn't state: a preset naming
  an identity that now belongs to a *different* patch; two dashboards saving
  the same preset name; a preset file that is malformed or hand-edited; an
  empty preset; apply to a target with no online device.
- **The show reference.** `/preset/<patch>/<name>` is a pseudo-address that
  never reaches the wire. Does that break anything that assumes a show message
  is literal OSC — the Monitor, the pill taxonomy, playback, undo,
  copy/paste, or `dashboard/shows/*.json` round-tripping?
- **Whether the stitch decomposition in §11 is the right one.** It is a
  sketch precisely so this review can reshape it. Name a better split if you
  see one, with the dependency reasoning.

## Deliverable

`review.md` in this stitch directory:

- **Findings**, most serious first. Each one: the claim, the evidence
  (file:line), what breaks, and a recommendation. Separate *defects* from
  *under-specified* from *cost concerns* — they need different responses.
- **Verified**: the load-bearing claims that checked out, stated briefly, so
  the implementation stitches can lean on them.
- **Open questions for Bob**, if any — kept short and each with a
  recommendation, in the house style.

Do not implement anything. Do not edit the proposal — findings go in
`review.md`, and Bob decides what changes.
