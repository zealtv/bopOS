# dashboard-9-ui-review

The broader dashboard UI review Bob called for (2026-07-13, in
`dashboard-5-position-precision`), now fed by his composer-experience brain
dump (`.lore/items/2026-07-13-composer-experience-brain-dump`). Concrete
fixes and interaction changes that need no ratification — judged together so
layout, legibility, and interaction design stay coherent.

Children in order: `ui-0` sidebar fixes, `ui-1` page layout pass, `ui-2`
spatial map pass, `ui-3` position precision (absorbed from dashboard-5,
deliberately last). Each ships its own Playwright `verify_*.py` (copy the
newest tied dashboard verify; venv + gotchas in CLAUDE.md).

Out of scope here (design gates elsewhere): patch/asset buttons and naming
(`patch-asset-sync`), simulate toggle / listener-puck visibility / forget
device (`dashboard-8-identity-sim-design`). If a child collides with one of
those, do the part that doesn't pre-empt the design and note the rest.
