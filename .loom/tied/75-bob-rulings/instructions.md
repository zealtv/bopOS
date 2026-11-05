# 75-bob-rulings

**Status:** waiting on Bob · collected 2026-10-03 while working the repair queue
**Goal:** one place for everything from that session that needs Bob's review,
ruling or hands on hardware. Agents: don't work this stitch; it's Bob's.

Bob, 2026-10-03: *"anything that needs my ruling put in stitches for me to
follow up on after this session"* — then *"make it a single stitch for review
and ruling"*. Each item points at where the evidence lives; the stitches named
stay where they are. When an item is ruled, record the ruling in the stitch it
points at (resume that stitch if it's waiting), then move it to Ruled here.
Tie this when Open and Hardware checks are empty.

## Open


## Ruled 2026-10-04

5. IO error vocabulary — **adopted** in the ratified IO design
   (`59-i2c-inventory/0a-io-design-review.tied/proposal.md` §1): `no-bus`,
   `create-failed`, `invalid-arguments`, `unknown-command`, `write-failed`;
   reserved name `bridge`; relayed as `/os/io-error`. Built in `59/1`.

## Ruled 2026-10-03

1. OS upgrade in the installer — **yes, remove it** →
   `67-repair-pass/9-installer-no-os-upgrade`.
2. "Mute all" honesty — **yes** → `67-repair-pass/7-mute-all-honesty`.
3. Load-failure notice — **tint the background** →
   `67-repair-pass/8-load-notice-tint`.
4. Git patch route amendment — **approved** →
   `68-remove-git-patch-route/ruling.md`, phase 2.
6. Contract 1.18 wording — read to Bob. He clarified that "do whatever is
   cleanest" was spot advice for that question, not a standing ruling
   (recorded in glean `decision-gates`).
7. Patch editor elements 0/1 — **keep two**: devices have one or two elements
   for now; more are possible but not soon → document it,
   `67-repair-pass/11-editor-element-limit`.
8. Engine `/id` — **int, as long as Pd is happy** →
   `67-repair-pass/10-engine-id-int` (Pd check first; lands in 68's 1.19).

## Hardware checks

Moved to `76-bob-review` (hardware checks 16–19) on 2026-11-05, so Bob's
outstanding hands-on checks sit in one list. This stitch was tied then: Open
was already empty.
