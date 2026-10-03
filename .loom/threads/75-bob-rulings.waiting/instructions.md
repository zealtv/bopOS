# 75-bob-rulings

**Status:** waiting on Bob · collected 2026-10-03 while working the repair queue
**Goal:** one place for everything from that session that needs Bob's review,
ruling or hands on hardware. Agents: don't work this stitch; it's Bob's.

Bob, 2026-10-03: *"anything that needs my ruling put in stitches for me to
follow up on after this session"* — then *"make it a single stitch for review
and ruling"*. Each item points at where the evidence lives; the stitches named
stay where they are. When an item is ruled, record the ruling in the stitch it
points at (resume that stitch if it's waiting), then strike it here. Tie this
when the list is empty.

## Rulings

1. **OS upgrade in the device installer.** Recommendation: remove
   `apt-get upgrade -y` from `install-device.sh` (it can move JACK, Pd, kernel
   or drivers during an install); keep `apt-get update` and the named packages.
   See `.loom/tied/73-pinned-dependencies/os-upgrade-recommendation.md`.
   Ruling → new stitch to make the change, or no.
2. **"Mute all" honesty.** `set_mute` (`python/bopos.py`) sets `mute_all`
   before `enforce_mute`, so a failed mixer call leaves the report claiming
   output is off while sound continues — the same bug `67/2` just fixed for
   Device enabled. Ruling → stitch it as a repair, or leave it.
3. **Load-failure notice emphasis.** Built to option 2 (`55d769c`): plain
   text over a thin amber rule. Ruling → keep, or make it stronger (a
   "Warning" label, tinted background). Screenshots:
   `.loom/threads/67-repair-pass/6-load-failure-followups.tied/notice-*.png`.
4. **Git patch route amendment.** `68-remove-git-patch-route.waiting/proposal.md`
   (ready, `4d61e88`): contract §7/§15 text at v1.19, the removal list, and
   what push does to a device's existing git-cloned patch dir. Ruling →
   approve so phase 2 can land, or amend.
5. **IO error vocabulary** — already handed to the IO design gate
   (`59-i2c-inventory/0a-io-design-review`, decision 1). No separate ruling;
   listed so it isn't forgotten.
6. **Contract 1.18 wording (FYI).** The preset retirement's §15 entry was
   written by the agent under "do whatever is cleanest". Read it in
   `docs/OSC-CONTRACT.md` §15 if you want to confirm the text.

## Hardware checks (Bob's hands; software halves are done)

- **Finn Jet — LIS3DH wrong address** → error, not zeros.
  `67-repair-pass/3-io-bridge-hardening.waiting`.
- **Finn Jet / Ciro Toast — invalid manifest**: write one with the retired
  `type` grammar, confirm the device stays visible, push a good patch, confirm
  it recovers. `58-patch-push-workflow/4-invalid-manifest-lockout.waiting`.
- **Ciro Toast — Device disable**: disable from the Device page; is it
  actually silent? `67-repair-pass/2-device-enabled-honesty.waiting`.
- **Rig package versions**: run the read-only comparison command in
  `docs/INSTALL.md` on a device; compare against `constraints.txt`.
