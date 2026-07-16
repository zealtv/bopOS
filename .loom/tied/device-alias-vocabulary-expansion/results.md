# Results — device alias vocabulary expansion

## Outcome

- Expanded the curated vocabulary from 64 to 128 global given names and from
  64 to 128 character-word surnames: **16,384** base combinations.
- Introduced generator v2 with its own pinned SHA-256 salt and candidate
  vectors while retaining an explicit v1 compatibility path.
- Existing registry entries remain byte-for-byte stable. A generated v1 entry
  is already reset, so Reset no longer renames it merely because v2 exists.
  Custom aliases created after this change reset into v2 as expected.
- Kept every token unique within its list, ASCII alphabetic, 2–12 characters,
  and selected for short English pronunciation.

## Verification

```text
PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python \
  .loom/threads/device-alias-vocabulary-expansion.stitching/verify_alias_vocabulary_v2.py
# 8/8 passed

PYTHONPYCACHEPREFIX=/tmp/bopos-pycache ~/.venvs/bopos/bin/python -m py_compile \
  dashboard/device_aliases.py dashboard/state.py \
  .loom/threads/device-alias-vocabulary-expansion.stitching/verify_alias_vocabulary_v2.py
# passed

git diff --check
# passed
```

The focused suite verifies both 128-entry lists, token constraints, every
legacy v1 vector, pinned v2 vectors, collision probing, complete traversal of
all 16,384 pairs, and restart/Reset preservation of Niko Cloud plus its mute
intent.

The tied v1 registry verifier now stops at its literal 64-entry assertion; that
expectation is intentionally superseded by this expansion. Its pinned v1
vectors are retained and exercised explicitly by the new verifier. The newer
alias UI backend regression passed its seven current Rename/Reset/projection
checks before reaching an unrelated identity-helper assertion superseded by
the later alias-only presentation sweep.

No `.pd` file or device runtime protocol changed.
