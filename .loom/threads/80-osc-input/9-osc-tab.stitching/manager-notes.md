# Manager notes on the mockup — go ahead with Phase B

The mockup passes (Bob pre-approved it; the manager checked it against proposal §5).
`8-osc-tab-mockup` is tied and `9-osc-tab` is claimed; write Phase B files in this directory
(`9-osc-tab.stitching/`). `git merge main` first to pick up the loom moves.

1. **Clamps lose the cyan.** Glean `dashboard-vocabulary` reserves cyan for modulation
   ("something is driving this"). Show the `clamp` tag in neutral/muted ink; keep ⚠ amber for
   rejections.
2. Open questions, settled within scope: keep **newest-first**; keep the **`<target>`
   placeholder**; **no** per-row copy buttons; keep the **outgoing-interface IP** (and
   `--public-url` when given).
3. The journey (`tests/verify_osc_tab.py`) must cover: the reference generated from the fleet
   patch; switching to Patch Edit regenerates it from the edited patch (and the "Generated
   from" line follows); real UDP to the input port producing a rejection and a clamp that appear
   live without reload; the ambiguity flag; groups by name and `g<id>`; no page errors; phone
   width has no horizontal page scroll.
4. Run the full browser tier at the end, then write `worker-result.md` here and end with
   `WORKER DONE: <status>`.
