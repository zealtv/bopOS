# 5-inspector

Context-sensitive inspector for the focused step or message, including the
OSC message builder. Requires stitch 4.

Scope:

- Inspector panel bound to the stitch-4 focus state; empty-state hint when
  nothing is focused.
- **Step inspector:** alias; duration as h/m/s fields (stored seconds);
  play n times; then-actions as an editable list (add/remove; each row picks
  one action from the vocabulary; `goto` offers a picker of steps by
  alias/uid); forward-sync toggle. Edits persist via the stitch-2 WS surface
  and reflect in the table summaries.
- **Message inspector / builder:** alias; **target selector** (all / group /
  seat — reuse existing selector idioms from live controls); then a guided
  payload picker: manifest-declared **parameters** (including nested
  addresses, with typed value entry honoring declared ranges), **cues**
  (manifest-declared cue picker), **points** (`/pt` static point set for
  now), plus a raw-address escape hatch with typed args. Show the resulting
  wire-form message read-only so what will be sent is never a mystery.
  Decomposed curves and point-motion authoring are explicitly out of scope
  (future residents noted in the design note).
- Adding a message to the focused step from the inspector (new-message
  button on a focused step); message pills update live.
- Respect PD float precision and 0-indexing laws in everything constructed.

Verify: `verify_show_inspector.py`, Playwright. Cover: focus step → edit
duration/plays/then-actions/sync and see them persist across reload; add a
then-action with goto via picker; focus message → build a param message via
pickers and a cue message, confirm wire-form preview; trigger the step and
assert simfleet receives the built messages.
