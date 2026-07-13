# friction-1-starter-kit

**Rewritten 2026-07-13** after the patch-asset-sync ratification
(`.loom/tied/dist-0-proposal/`): the starter kit **is the demo patches**
(`patches/demo-pd`, `patches/demo-sc`) — there is no separate template repo
and no `templates/` directory (Q6 superseded the 2026-07-08 "template lives
in `templates/`" ruling). `bopos.config` (patch-level) is retired; a patch
is a folder with a valid `bopos.patch.json` (entrypoint manifest-named;
`role`/meter died with the 2026-07-12 engine-boundary ratification — do not
reintroduce them here). Engine-boundary is ratified; the demos must teach
the accepted seam (provided terms §4.1, engine surface §4.2, run context).

Scope once dist-4 lands the demos:

- [ ] **Demo polish as teaching material**: each demo's README written for a
      musician — what every file is, how params/facilitator promotion work,
      how the provided terms arrive (master, `/pt`, `/cue`, run context) —
      link friction-0's composer doc, don't duplicate it.
- [ ] **The `main.pd` skeleton is Bob's** (agents never write PD): write a
      precise spec of what `demo-pd`'s patch must demonstrate (consume
      bopos-context, declare manifest params, read `BOPOS_ASSETS`), put it
      in `.notes/pd-edits-for-bob.md`, then mark `.waiting` on Bob.
- [ ] Verify: copy-a-demo → rename → Send patch → runs, walked on simfleet
      and recorded here.

Blocked by `dist-4-demos` (which is itself deferred by Bob) — this stitch
waits.
