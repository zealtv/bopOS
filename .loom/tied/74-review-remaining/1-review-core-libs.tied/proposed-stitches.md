# Proposed stitches — review 74-1

Proposals only; no loom mutations performed. Each block is an intention for Claude to route. F6 and F5 should be coordinated because bounded scheduling and complete crossings share implementation, but they address distinct acceptance criteria.

## quote-manifest-cli-values

- **Parent thread:** `67-repair-pass`
- **Goal:** Keep validated engine and entrypoint values as literal data through the launcher handoff (F1).
- **Done when:** Apostrophes, whitespace, and shell syntax round-trip without executing injected commands; legitimate filenames still launch through the handoff; existing manifest/boot tests pass.

## reject-malformed-manifest-values

- **Parent thread:** `67-repair-pass`
- **Goal:** Return ordinary invalid-manifest errors for malformed values instead of conversion/type exceptions (F2).
- **Done when:** List/object kinds, NUL paths, huge JSON integers and malformed numeric fields return `(None, error)`; failed writes retain the original manifest; editor/catalog callers handle the result normally.

## enforce-scalar-wire-representability

- **Parent thread:** `67-repair-pass`
- **Goal:** Prevent accepted declarations and numeric generator values from producing unencodable OSC scalars (F3).
- **Done when:** float32 overflow and signed-int32 overflow are rejected before sending; intermediate calculations remain wireable; integration checks use the real serializers; existing floor semantics and ratified scalar tags are preserved. Any new public limits go through the existing decision gate.

## preserve-explicit-start-loops

- **Parent thread:** `67-repair-pass`
- **Goal:** Replay the explicit-start three-element loop form as required by contract §3.3 (F4).
- **Done when:** Float and integer explicit-start loops complete multiple cycles with the intended start snap; one-/two-element loop forms retain their documented ignored-loop behavior.

## preserve-integer-generator-crossings

- **Parent thread:** `67-repair-pass`
- **Goal:** Emit every required integer crossing in order across segment reversals, loop wraps, and delayed ticks (F5).
- **Done when:** Deterministic advancement covers multiple segments/cycles within a tick and exact loop endpoints without lost or duplicated crossings; LFO turning points are covered; output work stays bounded in coordination with the scheduling repair.

## bound-generator-scheduling-work

- **Parent thread:** `67-repair-pass`
- **Goal:** Reject non-finite converted durations and compute automation lazily instead of allocating work proportional to full duration or an unchecked crossing range (F6).
- **Done when:** Huge string durations fail as grammar errors, long finite fades start with bounded memory/time, integer slots allocate no unused float event list, and a large crossing jump cannot monopolize a handler or scheduler. Existing trajectory/crossing behavior passes deterministic tests; any public-limit decision is ratified before implementation.

## harden-point-input-boundaries

- **Parent thread:** `67-repair-pass`
- **Goal:** Reject malformed point authoring and OSC frames before exceptions, unsafe conversions, or state mutation (F7).
- **Done when:** Malformed falloffs/motion collections, infinities, oversized IDs and fractional frame counts fail closed; a rejected atomic frame preserves prior points; valid host motion and sparse/frame/clear traffic retain their current behavior.

## isolate-store-temporary-files

- **Parent thread:** `67-repair-pass`
- **Goal:** Preserve independent valid keys and safe write ordering by eliminating the shared `<key>.tmp` scratch destination (F8).
- **Done when:** Writing/deleting `assignment` never alters `assignment.tmp`; concurrent same-key writes each use private scratch files; failed replacement preserves prior values; ephemeral and persistent APIs still agree.

## share-canonical-file-fetch-walk

- **Parent thread:** `67-repair-pass`
- **Goal:** Align `file:` convergence with the canonical identity and HTTP distribution namespace (F9).
- **Done when:** Source file/directory symlinks are excluded without following outside targets; dot/part exclusions match identity; fetched distributable bytes have the source fingerprint; existing destination traversal/symlink and patch rollback tests pass.

## stop-completed-point-path-traffic

- **Parent thread:** `67-repair-pass`
- **Goal:** Stop 25 Hz point traffic once a non-looping path has delivered its final endpoint (F10).
- **Done when:** A deterministic loop test observes a final endpoint then silence, while looping paths/orbits/bounces continue; newly edited motion resumes correctly and static hold remains intact.

## split-manifest-schema-validation

- **Parent thread:** `69-complexity`
- **Goal:** Make the independent manifest schemas readable behind the existing single validation API (F11).
- **Done when:** Entry/parameter/event/IO checks have focused private helpers; the redundant post-copy dict check is removed; normalization, rejection behavior and atomic-write results are preserved; the repair tests and fast suite pass. Perform after the manifest behavior repairs.
