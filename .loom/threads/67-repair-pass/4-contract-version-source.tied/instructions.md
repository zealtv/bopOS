# 4-contract-version-source

**Status:** ready · small
**Goal:** one source for the contract version every node reports.

`"contract_version": "1.16"` is hard-coded in `python/bopos.py`,
`tools/simfleet.py` and `tools/audition.py`; the contract is v1.17.

## Do

- One constant (e.g. in a small shared module the three already import), set
  to the current contract version.
- A test that it matches the `**Version x.y**` line in `docs/OSC-CONTRACT.md`,
  so the next amendment can't forget it.
