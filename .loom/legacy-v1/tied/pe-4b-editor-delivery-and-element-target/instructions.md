# pe-4b-editor-delivery-and-element-target

Follow up Bob's live PE-4 review:

- Prove and correct point/cue delivery from the running patch editor. The
  observed UI/backend split comes from static files being served by the
  pre-PE-4 dashboard process; restart the local dashboard after verification
  so both halves run the same revision.
- Add an edit-session point target toggle for element 0 or element 1. Keep
  authored geometry on the normal `/pt` path and make targeting private to
  the managed edit relay. Switching target must release held values on the
  old element and replay held points to the new element.
- Preserve the target across explicit restart/relaunch within an edit session,
  reset it to element 0 for a new session, and never persist it.
- Extend the PE-4 capture-socket verifier to assert cue delivery and both
  element targets. Do not edit `.pd` files.
