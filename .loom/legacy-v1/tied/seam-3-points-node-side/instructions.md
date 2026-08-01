# seam-3-points-node-side

**GATED: requires `seam-1-contract-amendment` tied. Do not claim before.**

The S1 implementation — node-side point decomposition per the ratified seam
ruling (supersedes the reverted `spatial-0`; salvage from commit `0ce8821`).

- **Wire (LAN, 6660 broadcast):** frame form `/pt <n> <id x y r f>×n`
  (atomic, MTU-bounded, ~20–30 Hz while moving, silence = hold); sparse
  per-point form + `/pt/clear <id>` for authoring edits; `falloff` enum int
  (0=linear, 1=smooth, 2=gauss). Exact spellings per the seam-1 contract text.
- **`python/helper.py`:** parse `/pt`; shared falloff module (salvage
  `linear/smooth/gauss` from the reverted `dashboard/spatial.py` at
  `0ce8821`); compute proximity 0→1 per point **per assigned element
  position** (positions list from assign; one element today, loop anyway);
  deliver to the engine on 6661, routed-single-receiver flat args (lean:
  `/pt <pointId> <element> <v>` — final spelling from seam-1/Bob).
- **`dashboard/osc_bridge.py`:** point set state + broadcast loop (reuse the
  reverted `path`/`orbit` motion logic as the test driver); **catch-up**: send
  the current `/pt` frame (and master) unicast to a device on (re)appearance —
  piggyback the existing params catch-up.
- **`tools/simfleet.py`:** identical decomposition via the shared falloff
  module; log per-point values so the verify asserts
  `proximity == falloff(distance)` over a moving frame (node-computed, not
  dashboard-computed).
- Browser-free `verify_*.py` in this stitch dir (venv `~/.venvs/bopos`,
  repo-root-by-marker).
- PD receiver + `bopos.point` abstraction are Bob's (`.notes/pd-edits-for-bob.md`
  A6/B2) — do not block on them; simfleet is the test surface.

**UI direction from Bob (2026-07-11, seam-1 review):** when the dashboard
grows multi-element positioning (defining N elements per device and placing
them), render each element as a coloured dot carrying the device's number,
with colour keyed to **element index** fleet-wide (element 1 one colour on
every device, element 2 another, etc. — exact colours are a UX choice). Fold
this in during the multi-element implementation, not as a separate pass. See
`seam-1-contract-amendment/bob-review-2026-07-11.md` (tied).

After tying: re-scoped `spatial-audio/spatial-1` (author/move points UI) can
build on this.
