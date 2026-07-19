# Codex implementation spec — p5 inspector defaults

Implement the already-ratified requirements in `instructions.md`. Design is
settled; do not broaden scope.

## Model invariant

- Canonical `then_actions` is never empty. Normalize a missing or empty list to
  `[{'type': 'stop'}]` in `dashboard/show_model.py` wherever a step enters or
  changes the model: loaded documents, new steps, and step updates.
- Existing non-empty lists retain their order and meaning.
- This is authoring-surface truth-telling only; do not change playback-engine
  semantics.

## Step inspector

- Always render at least the canonical stop row.
- Row index 0 has no Remove button. Later rows retain Remove and can be removed,
  returning to the single non-removable first row.
- Remove the stale "No rows means stop" hint.

## Message target disclosure

- Replace the permanently expanded target block with a native, accessible
  disclosure (`details`/`summary` is preferred).
- Its closed summary must visibly include `Target` and the existing terse wire
  selector (`all`, `3+7+g1`, etc.). The existing All/group/Seat picker lives in
  the disclosed body and editing behavior is unchanged.
- Existing/saved messages default closed, including messages whose canonical
  target is `all`.
- A message created through the inspector's Add message button defaults open on
  its first render. A pasted message is not "fresh" for this purpose and
  defaults closed. Preserve open/closed state across ordinary Show re-renders
  while that same message remains focused.
- `/cue` and `/pt` keep the current greyed/disabled picker behavior.

## Verification and records

- Add stitch-local `verify_show_inspector_defaults.py`, using the current
  Playwright house pattern and repo-by-marker lookup. It must prove every item
  required by `instructions.md`, including saved normalization on disk and
  target edits after expansion.
- Add `worklog.md` with files changed, exact checks attempted/results, any tied
  verifier amendments, and honest sandbox limitations.
- Amend older tied verifies only if their expectations genuinely moved, and log
  every amendment.
- Run browser-free model checks and `node --check dashboard/static/js/show.js`.
  Attempt the focused Playwright verify; if socket sandboxing blocks it, report
  that honestly instead of weakening the test.

## Workspace boundary

- Do not touch `.loom` state or any stitch outside this claimed p5 directory.
- Never edit `.pd` files.
- Do not touch or add `dashboard/shows/`; it is Bob's local untracked data.
- Do not commit or tie the stitch.

When done, summarize what changed, how you verified it, and anything you could
not verify in `codex-result.md` inside this p5 stitch directory.
