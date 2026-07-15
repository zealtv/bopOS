# Asset scale and 2.4 GHz transfer-time reference

Measured pack size (Belief System 1.15 GB), 2.4 GHz throughput assumptions, a pack-size × fleet-size wall-time table and chart, node hashing cost, and the resulting revision of the fleet-distribution scale premise.

## Source

Planning conversation with Bob on 2026-07-15: Bob measured the Belief System
asset folder at 1.15 GB and expects most packs well under 5 GB, superseding
the 10–50 GB premise in `2026-07-15-asset-management-direction` for planning
defaults. Estimates computed from Pi Zero 2 W radio/CPU characteristics;
`content/make_chart.py` regenerates `content/transfer-times.svg`.

## Related

- `.lore/items/2026-07-15-asset-management-direction`
- `.loom/threads/ui-tabs/tabs-3-next-sweep/11-assets-device-workflow/`
- `.loom/threads/asset-fleet-distribution/`
- `python/identity.py`, `python/fetcher.py`

## Tags

- assets
- distribution
- reference
- measurements
- planning
