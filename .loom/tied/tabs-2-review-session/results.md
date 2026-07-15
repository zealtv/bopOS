# tabs-2 review results

Bob reviewed the real tab skeleton and supplied a concrete composition and
installation-day workflow. An independent senior UX/UI reviewer specialising
in interactive installations then reviewed those observations, the ratified IA,
screenshots and implementation.

The durable review is lore-kept at
`.lore/items/2026-07-15-dashboard-tabs-hands-on-expert-review/` and includes:

- `bob-observations.md`
- `expert-review.md`
- `code-diagnosis.md`
- `next-sweep-proposal.md`

## Main conclusions

- The global execution targets are **Live fleet / Simulation / Patch edit**.
- Simulate belongs in the global header; remove Seats' `Edit this patch`.
- Seats owns logical places and every seat property. Devices owns physical
  boxes and their administration. Binding is one relationship with map-first
  and device-first entry.
- Patches chooses/deploys the sole desired fleet patch; Devices observes drift
  and repairs an exception with one button. Assets should follow this pattern.
- Dashboard cards identify bound controls by seat because presets are seat-keyed.
- Unique administration of unbound boxes needs a small UID-targeting design;
  current `all | seat ID` selectors cannot distinguish multiple ID -1 nodes.

## Confirmed implementation defects

- late virtual `device_update` payloads can resurrect cleared simulation cards;
- binding intentionally copies hostname into a default seat name;
- `patch_switch` can remain true forever when `/os/rev` is lost;
- mixed `renderDetail()` causes seat/device noun leakage;
- seat ID is not editable/reindexed;
- unbound detail omits normal administration;
- Dashboard falls back to uid/MAC instead of resolving the seat;
- production points are excluded from durable venue state; Bob subsequently
  confirmed this is intentional, so the proposed persistence follow-up was
  dropped.

## Follow-up

Created the ordered `ui-tabs/tabs-3-next-sweep` parent. Bob accepted the sweep
except for venue point persistence, which was dropped. Thirteen children remain:
`01-simulation-transition-coherence` is the sole loose end and later work waits
on its predecessor or explicit design gate.

No implementation or `.pd` file changed during tabs-2.
