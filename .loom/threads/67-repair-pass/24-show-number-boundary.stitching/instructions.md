# 24-show-number-boundary

**Status:** ready · **high**
**Goal:** every show input fails closed at one boundary: show files, WS
edits and `set_live_automation`'s use of `clean_arg`.

Evidence: `lore:2026-10-05-bopos-review-show-model` F1, F2, F3, F8.

- **F1 (high).** `load_show` catches only `ValueError`; `1e999` or a 400-digit
  number raises `OverflowError`, so the dashboard won't start (open show) or
  every `state.public()` fails (any show in the project).
- **F2.** The same numbers in WS edits drop the client's socket.
- **F3.** `clean_arg` coerces (`1.9`→1, `"12"`→12) and never range-checks
  `i`; `2**31` goes out tagged `h`. Reject non-integral/out-of-int32 `i`,
  non-float32 `f` and numeric strings. Bob's only stored show has no such
  values (checked 2026-10-05), so strict rejection breaks nothing.
- **F8.** Addresses accept `/`, spaces, `#`, `//`; apply OSC address rules.

Done when: the F1/F2/F3/F8 cases now fail closed (damaged file loads
read-only, edit returns an error), a non-open bad show no longer breaks
snapshots, valid shows load unchanged; show tests and fast green.
