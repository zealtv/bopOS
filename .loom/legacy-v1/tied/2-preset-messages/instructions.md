# 09/2-preset-messages

The `/preset/*` Show message family, riding the sibling foundation.
**Needs 09/1 tied.**

## The message

By reference (proposal §6): `address: /preset/<patch>/<name>`,
`args: [<dur>?] [c:<n>?]`, targets via the existing chips with named groups.
Its reference payload (09/1's mechanism) carries **both** fingerprints per
Bob's Q2 ruling: the patch `{name, fingerprint}` R2 requires (the cross-layer
content reference), and the schema fingerprint as the applicability check.
Drift on either is a derived, non-blocking warning in the Show tab and at
show load — never stored, never blocking.

## Expansion

The message never reaches the wire verbatim. At send time it expands through
the **06 application core** — patch-aware targeting, kind-aware timed apply
(duration → fades for floats/ints, t=0 sets for the rest; no morph exists),
report — via a **callback injected into `ShowEngine`** at construction
(`dashboard/server.py:124-167`, `dashboard/show_engine.py:48-53`). The
engine stays transport-only: it must never read patch files or resolve
groups itself. An explicit playback branch is mandatory — without one,
`/preset/...` falls through to raw OSC (`show_engine.py:141-161`). Monitor
honesty comes free: every expanded send passes the `_send_to` tap.

## Pills

One additive ninth category beside the ratified flat eight: `preset`, code
**`PRE`**. A preset message with a duration may take the modulation ink
(cyan = "something is driving this", per `04-event-fire-affordance`'s
widened meaning).

## Editor operations — atomic, one undo entry each

Both go through `apply_show_mutation` (`dashboard/server.py:1345-1372`):

- **Flatten-to-messages**: one preset message → N literal `/p/*` messages,
  an explicit escape hatch for hand-editing, never the default.
- **Capture-as-step** (Bob's ratified workflow; closes "collections start as
  show steps"): one Control-tab action stores the current target→preset
  arrangement as a new show step — one message per **distinct preset**,
  targeting the seats that carry it via the 06 projection (all / group by
  name with the lowest-id tie-break / seat list). **Targets with no preset
  applied are omitted, and the count is stated before committing** ("3 of 5
  targets have a preset applied; the other 2 will not be captured") — F3,
  ratified. The button lives on the Control tab's target-filter chrome, not
  in a per-card row; the capture itself is dirty-agnostic (the asterisk is a
  UI truth, not a capture rule).

## Verify and tie

Fast tests: expansion output (targets, timed/untimed, skip report),
reference drift warnings, flatten and capture-as-step as single undo
entries. Browser journeys: author a preset step, play it, watch the Monitor
show the expansion; capture-as-step end-to-end from the Control tab
(iframe gotcha 15). `tools/run-tests.sh fast` and `browser` green.
