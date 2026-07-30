# Rulings from the 2026-07-30 session

Extracted from the braindump for implementers. Anything not listed here is
context, not a ruling.

## Process (supersedes the prior rollout order)

**Components first, design language extracted from them.** Identify reusable
components → design one at a time → integrate into the application → extract
the coherent style from what shipped. This reverses
`desktop-ui-overhaul/02-app-wide-rollout-design`, which would have ratified a
token/pattern system top-down before the second consumer of each pattern
existed. That stitch is dropped; `02-component-unification` replaces it.

Ordering named by Bob: the control panel is first, the target selector
probably second, and the pass should surface others.

## Standard

The 2026-07-27 Excalidraw mockup is the north star — "the closer we can match
it the better" — qualified by
`2026-07-27-control-panel-ui-and-architecture-braindump/content/mockup-fidelity-notes.md`,
which names the mockup details that later rulings superseded.

## Ratified layout and behaviour

1. **The control panel goes anywhere a patch is controlled**, with the same UI
   and the same features. Named consequence: the patch editor's hand-rolled
   parameter tree is retired in favour of the shared surface.
2. **The Show inspector uses the control panel** and the generator/modulation
   drawer where appropriate. The inspector is a narrow column, which is the
   shape those components were designed for.
3. **The Control tab becomes N columns**, each a control panel with its own
   pop-out target selector; add/remove columns; **minimum one**. The
   All/Groups/Seat radio row is retired.
4. **One target selector, mixable**: all, a selection of groups, a selection of
   seats, or a mixture. Seats and devices are **probably two different
   pickers** — same idea, different domain.
5. **The standalone-view link moves into the tab bar, right-aligned**, with a
   short name Bob has not yet chosen. The "Live control / Control" and
   "Single-device delivery / Assets" heading text is deleted outright; the
   pattern applies across tabs.
6. **Fleet patch deployment goes on one line**: patch, target, buttons. The
   target here selects devices. Bob is unsure the picker component is right
   for this spot.
7. **Parameter rows never wrap.** Number box, slider and modulation icon stay
   on one line as the parent narrows.
8. **The modulation pop-out never reflows.** It is a fixed interface, and its
   width may set the minimum width of the host — acceptable as long as the
   result is reasonable on a phone.
9. **Desktop design language.** Professional desktop software: icon buttons in
   toolbars, compact and minimal. Get away from big high-padding buttons.
   Styling mobile completely differently is explicitly fine.

## Left open for Bob

- The short name for the standalone-view tab (`Live` recommended;
  `Stage` / `Remote` / `Panel` offered).
- Whether the Control tab retires its iframe so N columns can live in the
  parent document.
- Where column layout persists (browser vs installation).
- Whether the app-wide light theme repaints from lavender to the control
  panel's pink.

---

## Second round — same session, answering the four open questions

1. **The standalone view is named `Remote`.** It becomes a right-aligned link
   in the primary tab bar. **The manifest tab's checkboxes are renamed to
   `Remote` too** — the flag is unchanged (it still gates only that view);
   only the terminology follows the name. Shipped in the 2026-07-30 groundwork
   commit: two `manifest-check` checkboxes (was "Facilitator") and the editor
   param badge (was "Dashboard").
2. **Retire the Control-tab iframe.** `/facilitator` stays as the standalone
   Remote view; `ControlSurface` is hosted directly in the parent document so
   the Control tab can hold N columns without cross-document coordination.
3. **Column layout persists in `localStorage`.** Bob: *"with a chip picker it
   should be easy to spin up whatever control panel targets one needs"* —
   cheap re-creation is why durable server-side layout isn't needed.
4. **App-wide light repaint: yes, but the pink is a GROUND, not a panel
   colour.** Bob: *"the pink is a little heavy on the control panel — notice
   how it's used in the Excalidraw mockup. It's a background that panels sit
   on, not the colour of panels themselves."*

   Sampled from `mockup.png`, the light scheme is a **neutral grey scale on a
   pale pink ground**:

   | role | value |
   |---|---|
   | page ground | `#f8f0fc` — the only pink |
   | panel body | `#f8f9fa` |
   | subpanel / drawer / manual slider fill | `#e9ecef` |
   | value boxes, troughs, button faces | `#ffffff` |
   | ink | `#1e1e1e` (shipped as `--text #212529`, `--control-line #495057`) |

   Shipped in the same commit. Cyan is unchanged — it was ratified 2026-07-27
   and Bob raised no objection. One measured delta noted but not acted on: the
   mockup's cyan fill `#99e9f2` is more saturated than `--mod-fill` renders
   over white.
