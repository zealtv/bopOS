# 16-file-fetch-walk

**Status:** ready
**Goal:** `file:` fetch copies exactly what the canonical identity walk
fingerprints.

Evidence: `lore:2026-10-05-bopos-review-core-libs` F9. `fetcher._file_fetch` follows source symlinks that
`identity.directory_manifest` skips, copying bytes from outside the source tree
and reporting success with mismatched fingerprints. Use the canonical walk
(as HTTP distribution already does). Done when: source file/dir symlink tests
fail before and pass after; existing destination-guard and rollback tests pass.
