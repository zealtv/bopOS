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

7. **Patch editor: elements 0/1 only.** In Patch Edit, the Point preview
   section has a fieldset "send point values to: ○ element 0 ○ element 1"
   (`index.html`, `#editor-point-target`). The audition engine sends each
   point's computed value as `/pt <point> <element> <value>` to the chosen
   element only; the server (`set_editor_point_element`) and audition
   (`set_editor_element`) both reject anything but 0 or 1. So a patch whose
   elements 2+ respond to points can't be previewed for them. Recommendation:
   allow N (a number field instead of two radios). Asked for clarification
   2026-10-03. Evidence:
   `.loom/threads/70-dead-code-sweep/1-dead-code.tied/element-recommendation.md`.
5. **IO error vocabulary** — in the IO design gate
   (`59-i2c-inventory/0a-io-design-review`, decision 1). No separate ruling.

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
8. Engine `/id` — **int, as long as Pd is happy** →
   `67-repair-pass/10-engine-id-int` (Pd check first; lands in 68's 1.19).

## Hardware checks (Bob's hands; software halves are done)

Device-agnostic (Bob, 2026-10-03): Finn Jet and Ciro Toast are out of date and
will be updated first. Use any current bopOS device unless a check needs
specific hardware, and record which device and framework revision.

- **Wrong-address peripheral** → error, not zeros. Needs a device with an
  LIS3DH. `67-repair-pass/3-io-bridge-hardening.waiting`.
- **Invalid manifest**: write one with the retired `type` grammar, confirm the
  device stays visible, push a good patch, confirm it recovers. Any device.
  `58-patch-push-workflow/4-invalid-manifest-lockout.waiting`.
- **Device disable / mute all**: disable from the Device page, then mute all;
  is it actually silent? Most telling on a card with no hardware mixer (e.g.
  HiFiBerry). `67-repair-pass/2-device-enabled-honesty.waiting` and
  `7-mute-all-honesty`.
- **Package versions**: run the read-only comparison command in
  `docs/INSTALL.md` on a device; compare against `constraints.txt`.
