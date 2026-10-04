# Core libraries review addendum — 2026-10-05

Reviewed main at `c2b2526a2bf0ed1de3e9e2291344e07e080fb524`. All ten scoped modules were read in full, with their callers, existing tests, and relevant OSC contract sections. Ten findings are confirmed by bounded software reproductions; one structural finding is labelled *likely*. Highest priorities are safe manifest CLI quoting, preventing store-key data loss, and bounding automation work. Runtime code was not changed. No hardware, audio engine, or browser verification is claimed.

The earlier review's fetch destination guards hold for the tested traversal and existing-symlink cases. The new fetch finding concerns **source** file symlinks and differing canonical walks. `sync_node.py`, `groups.py`, and `relay.py` produced no additional actionable findings from this review; their shared parsing/address boundaries are already useful abstractions. Host motion sanitization and node point decoding have different responsibilities, so they should not be mechanically merged.

## Reproduction and test evidence

Run from the repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 ~/.venvs/bopos/bin/python .loom/threads/74-review-remaining/1-review-core-libs.stitching/reproduce.py
TMPDIR=/tmp ./tools/run-tests.sh fast
```

`reproduce.py` labels F1–F10 and asserts observed defects. It starts no engines or sockets, uses deterministic generator advancement without worker threads, and writes fixtures only inside its own `/tmp` temporary directory. F1 executes only the generated assignments in a scratch shell, creating a harmless marker there; it does not execute the actual launcher. The enormous event allocation in F6 is calculated, **not attempted**. Output is retained in `reproduction.log`.

Fast suite: **550 tests, OK**, 12.184 seconds, retained in `fast-tests.log`. The first sandboxed run had three boot-test failures due to `/dev/fd/63: Operation not permitted`; the approved rerun outside the sandbox passed. No browser tier was needed for a review with no runtime changes.

## F1 — Manifest CLI interpolates shell syntax into launcher assignments

- **File:line:** `python/manifest.py:376`, `python/manifest.py:377`; consumer `bash/start-engine.sh:51` (`eval "$MANIFEST_OUTPUT"`).
- **Severity:** High.
- **Status:** **CONFIRMED** — F1 in `reproduce.py`.
- The validator accepts arbitrary non-empty engine strings and entrypoint filenames containing apostrophes. The CLI encloses them in literal single quotes without escaping embedded quotes. An accepted engine `pd'; printf ...; #` executes a scratch marker command when evaluated. Ordinary filenames with an apostrophe also break launch. Patch packages already contain executable code (`start.sh` and their engine), so this is not a claim of privilege escalation from an otherwise untrusted patch boundary; it is a broken data-to-shell boundary in the shared manifest CLI.
- **Suggested route:** repair child. Quote each emitted shell value correctly (or replace the eval handoff), preserving accepted filename values and engine selection. Verify apostrophes, spaces, newlines, and shell metacharacters without launching audio.

## F2 — Malformed manifests raise instead of returning validation errors

- **File:line:** `python/manifest.py:168`, `python/manifest.py:122`, `python/manifest.py:212`.
- **Severity:** Medium.
- **Status:** **CONFIRMED** — F2 in `reproduce.py`.
- JSON `kind: []` raises `TypeError` at dictionary membership; a NUL-bearing entrypoint raises `ValueError` during filesystem inspection; a numeric default `10**400` raises `OverflowError` at `math.isfinite`. These violate the loader's documented `(manifest, error)` result, and bypass callers expecting an invalid-manifest receipt rather than an exception. The dashboard editor and patch catalog use this same validator. The exact downstream failure depends on each caller's exception handling; the reproduction establishes the shared boundary failure.
- **Suggested route:** repair child. Validate types before lookup/filesystem use and contain conversion errors, with malformed JSON value tests that assert a normal rejection and no manifest replacement.

## F3 — Accepted numeric declarations can exceed their OSC scalar representation

- **File:line:** `python/manifest.py:210`, `python/paramgen.py:31`; node serializer `python/bopos.py:849`.
- **Severity:** Medium.
- **Status:** **CONFIRMED** — F3 in `reproduce.py`.
- A float default `1e100` and an int default `2147483648` both validate successfully, but cannot be packed as float32 and signed int32 respectively. The node explicitly serializes Python floats with OSC `f` and integers with OSC `i`. Finiteness in Python is insufficient for the actual wire. Plain numeric generator values also lack these checks. A declaration can thus be presented as valid while its initial value or generated output cannot be sent. This finding concerns representability; it does not propose an arbitrary six-digit validator or change the ratified wire types.
- **Suggested route:** repair child. Reject unwireable declarations/inputs and ensure intermediate outputs cannot become non-finite or unwireable. Exercise manifest, generator, and real serializers together, keeping valid floor semantics and existing scalar types.

## F4 — Explicit-start `loop` becomes a one-shot fade

- **File:line:** `python/paramgen.py:94`, `python/paramgen.py:143`.
- **Severity:** Medium.
- **Status:** **CONFIRMED** — F4 in `reproduce.py`.
- Contract §3.3 permits `loop <fade-form>` and ignores loop only for one- and two-element forms. Parsing `['loop', 0, 1, '1s']` returns `kind='fade'`, because the three-element branch never uses its `loop` argument. A looping ramp with an explicit start therefore completes once and becomes a constant; longer implicit-start loops do work.
- **Suggested route:** repair child. Retain looping for explicit-start forms and verify several cycles, integer and float output, and unchanged one-/two-element shorthand behavior.

## F5 — Integer generators skip crossings inside segments and at loop boundaries

- **File:line:** `python/paramgen.py:358`, `python/paramgen.py:367`, `python/paramgen.py:400`.
- **Severity:** Medium.
- **Status:** **CONFIRMED** — F5 in `reproduce.py`.
- An int fade from 0 to 2 in 10 ms, then back to 0 in 10 ms, advances at the normal 30 ms tick with **no output**: `_crossings` compares only the previous and current sampled values. The required `[1,2,1,0]` crossings vanish. In a 0→2→4 loop with 30 ms segments, advancing at the exact 60 ms boundary snaps to 0 before emitting the final segment; the reproduction observes `[[0]]` instead of the second segment's crossings and snap. LFO sampling has the same endpoint-only mechanism; rapidly turning oscillations can likewise hide movement within a tick (this extension was not separately reproduced). Contract §3.3 promises no missed integer crossings.
- **Suggested route:** repair child. Advance piecewise through boundaries between the previous and current times, preserving output order and snaps. Include reversal-within-one-tick, exact-boundary, and delayed-wakeup cases with bounded work.

## F6 — Durations escape finiteness checks and fades preallocate unbounded event lists

- **File:line:** `python/paramgen.py:48`, `python/paramgen.py:233`, `python/paramgen.py:242`, `python/paramgen.py:244`.
- **Severity:** High.
- **Status:** **CONFIRMED** — F6 in `reproduce.py`; process exhaustion is a *likely consequence*, deliberately not induced.
- A 400-digit decimal duration string with `s` parses into infinity and is accepted, then `apply` raises `OverflowError` converting it to nanoseconds. Even finite durations allocate one event per ~30 ms **at apply time**, while holding the generator condition lock. The bounded int example, 60 s, allocates 2,000 float event tuples despite never consuming that list in the integer advancement branch. A valid `1000000h` duration projects to 120 billion events. Large integer endpoint jumps also materialize the entire crossing range at once (`_crossings`). These operations can stall the OSC handler and other generator activity or exhaust memory.
- **Suggested route:** repair child. Check string durations after unit conversion; lazily compute float ticks and avoid unused int event lists; bound per-wakeup output work while preserving the crossing law. If a new public duration/range limit is needed, propose it for ratification rather than inventing one.

## F7 — Point boundaries can throw, accept unwireable IDs, or truncate frame counts

- **File:line:** `dashboard/points.py:34`, `dashboard/points.py:119`, `dashboard/points.py:156`; `python/pointfield.py:62`, `python/pointfield.py:85`, `python/pointfield.py:94`.
- **Severity:** Medium.
- **Status:** **CONFIRMED** — F7 in `reproduce.py`.
- A dashboard point with `falloff: []` raises `TypeError` before fallback; path `points: 7` raises when iterated; infinite IDs raise `OverflowError` at both host and node boundaries. Infinite node falloff also raises at `int(float(...))`. The host accepts ID `2**31`, which cannot serialize as the int32 ID it emits. Finally `/pt 0.9` truncates its count to zero and is accepted as an empty full-state frame, clearing the point state instead of rejecting the malformed frame. Existing callers rely on these helpers to sanitize/reject input; the node frame mutation follows immediately from a successful parse.
- **Suggested route:** repair child. Make malformed host payloads and wire frames fail closed; check integral counts/IDs and output representation before conversion or mutation. Preserve the distinction between host motion authoring and node wire parsing.

## F8 — Writing one valid store key deletes another valid key

- **File:line:** `python/store.py:18`, `python/store.py:42`, `python/store.py:45`.
- **Severity:** High.
- **Status:** **CONFIRMED** — F8 in `reproduce.py`.
- `assignment.tmp` is a valid key. Put it with `['precious']`, then put `assignment` with `[7]`: the second put opens the first key's file as its temporary output and renames it away. `get('assignment.tmp')` now returns `[]`. This deterministically loses unrelated stored data without concurrent access or a crash. The same fixed temporary path also permits competing same-key writes to interfere (a likely additional consequence; no timing-dependent reproduction is claimed). The store is shared by engine requests, LAN requests, and assignment persistence.
- **Suggested route:** repair child. Use private unique temporary names outside the valid-key namespace and appropriate write ordering; verify suffix keys remain independent and failed writes preserve prior values. Keep the current key API.

## F9 — `file:` fetch follows source symlinks omitted by canonical identity

- **File:line:** `python/fetcher.py:173`, `python/fetcher.py:180`, `python/fetcher.py:191`; contrasting walk `python/identity.py:40`.
- **Severity:** Medium.
- **Status:** **CONFIRMED** — F9 in `reproduce.py`.
- A visible source file symlink to a file outside the source directory is absent from `identity.directory_manifest`, but `_file_fetch` hashes and copies its target into a regular destination file. Fetch reports success while source and destination fingerprints disagree. It also copies bytes outside the stated source tree. Destination traversal and existing-symlink checks do not prevent this source-side mismatch. The HTTP catalog walk already excludes these links.
- **Suggested route:** repair child. Use the canonical distributable walk for file-fetch, so dot/part/symlink exclusions and fingerprint identity match HTTP distribution. Add source file/directory symlink coverage alongside the already-passing destination guards.

## F10 — Completed non-looping paths keep broadcasting forever

- **File:line:** `dashboard/points.py:91`, `dashboard/points.py:98`; consumer `dashboard/osc_bridge.py:706`.
- **Severity:** Low.
- **Status:** **CONFIRMED** — F10 in `reproduce.py`, plus the live loop's unconditional use of that predicate.
- A one-second non-looping two-point path holds the same endpoint at elapsed 2 s and 100 s, but `is_dynamic` always returns true for a multi-point path. `points_loop` consequently sends full `/pt` and browser point frames at 25 Hz indefinitely. This contradicts its own “only while a point moves” behavior and contract §4.1's silence=hold design.
- **Suggested route:** repair child, separate from the point validation repair. Make activity time-aware and ensure one final endpoint frame is delivered before ticking stops; orbit, bounce, and looping paths must continue.

## F11 — Manifest validation still bundles several independent schemas

- **File:line:** `python/manifest.py:91`, `python/manifest.py:131`, `python/manifest.py:235`, `python/manifest.py:274`.
- **Severity:** Low (maintainability).
- **Status:** *likely* — static review, not a behavioral defect.
- `validate` combines engine/entrypoint safety, parameter identity/presentation/kinds/ranges, events, IO modules, and caps/slots in one function. Type and conversion gaps in F2/F3 are dispersed through it. There is also a provably redundant `isinstance(manifest, dict)` test immediately after `manifest = dict(candidate)` (`python/manifest.py:105`). The distinct schemas can be local private helpers while retaining one public shared validator; adding a second validator would worsen drift.
- **Suggested route:** 69 structure, after behavior repairs. Extract small schema validators and delete the redundant branch, preserving normalization, error ordering where relied upon, and callers' single boundary. No separate 70 stitch is justified for that one dead check.
