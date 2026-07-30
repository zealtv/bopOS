# Ground truth — the N-column Control tab (08/1)

Everything below is read off the shipping code on `main` at 2026-07-31, with
file:line citations. Experts: **do not take the framing in the stitch
instructions on faith over this file.** Where the instructions and this file
disagree, this file was checked against the source and the instructions were
not. Two of the instruction's own premises turn out to be wrong; §6 says which.

---

## 1. What the Control tab is today

`index.html:30-32` — the whole tab is one iframe:

```html
<section id="tab-control" …>
  <iframe id="dashboard-live-view" src="/facilitator?embedded=1"></iframe>
</section>
```

So the Control tab *is* `facilitator.html` with `?embedded=1`
(`facilitator.js:3-4` sets `body.embedded`). One document, one target picker,
one stack of cards. `style.css:44` gives the iframe
`height:58vh;min-height:520px;border:1px solid var(--line);background:var(--bg)`
— the design-language §12 violation the parent stitch retires.

`embedded` is load-bearing beyond layout. It gates three things:

| gate | line | effect |
|---|---|---|
| full manifest | `facilitator.js:125-127` | embedded shows every declaration; standalone filters to `dashboard === true` |
| preset row | `facilitator.js:200-205` | presets exist **only** embedded — an iPad applies nothing |
| capture-as-step | `facilitator.js:292` | `renderShowCapture()` returns immediately when not embedded |

After `3-iframe-retirement` there is no `embedded` flag on the Control side —
the Control tab is the parent document and `/facilitator` is Remote. These three
gates need a new discriminator, and that is `3`'s problem, not this stitch's.
Named here so the design does not silently assume it.

## 2. The one picker, and what a selection produces

`facilitator.js:101-112`:

```js
const targetPicker = window.TargetPicker.create({
  host: $("#target-picker-host"),
  id: "control",
  storageKey: "bopos.target.control",
  followFocusSeat: true,
  …
  onChange: () => { renderCards(); $("#cards").scrollTop = 0; },
});
```

A selection is an ordered list of wire selectors: `["all"]`, or a mixture of
`g<id>` group selectors and bare `<seat id>` strings (`target-picker.js:52-71`).
`all` is exclusive with everything (`toggle()`, line 63).

`renderCards()` (`facilitator.js:331-345`) maps that selection to cards:

- `all` (or empty) → **one** All card over every seat.
- otherwise → **one card per selected entry** (`selection.map(selectedCard)`),
  a group card per group and a seat card per seat.

**This matters for the whole stitch.** The tab already renders N cards from one
picker. Bob's N columns are therefore not "N cards where there was one" — they
are **N independently-targeted card lists**, each of which may itself hold
several cards. A column is a *panel with its own picker*, not a card.

Cards stack vertically (`facilitator.css:27`, `main{display:grid;gap:14px}`),
with a two-up rule only in the standalone landscape case
(`facilitator.css:71`).

### Per-host selection, shared focus seat

`target-picker.js:236-247` — selection persists under the host's own
`storageKey`. The comment names this stitch as the reason. One thing stays
global: `FOCUS_SEAT_KEY = "bopos.selected-seat"` (`target-picker.js:28`), which
the Seats tab writes and any `followFocusSeat` picker adopts **when it moves,
not on load** (`adoptFocusSeat`, lines 289-299: it compares against
`lastFocusSeat` and returns early when unchanged).

Note the mechanism: today the adoption arrives cross-document as a `storage`
event (`target-picker.js:365-367`). `storage` **does not fire in the document
that wrote the value.** Once the iframe is retired and Control lives in the same
document as the Seats tab, that listener stops firing for same-document writes.
`3-iframe-retirement` has to replace it with a direct call. Consequence for this
stitch: whatever rule you pick for focus-seat with N columns, the delivery
mechanism is being rewritten anyway, so do not pick a rule to preserve the
current plumbing.

## 3. The panel's measured floor

`control-panel.css:145-149`:

```css
/* The 320px drawer is an instrument face, not a responsive form. Its fixed
   width plus the shared card padding defines the smallest useful panel.
   Narrow viewports scroll this intact face instead of rearranging it. */
min-width:calc(320px + 2 * var(--pad-panel));
```

That is the `06` ruling: the generator drawer never reflows, parameter rows are
atomic (`06`, `06b`), and the card minimum was measured against a 360px phone.
A column narrower than ~340px is not a design option — the panel scrolls
horizontally instead of rearranging.

Budget at the three mockup widths, `.tab-panel{max-width:1400px}`
(`style.css:44`) and `padding:12px 16px`:

| viewport | usable | columns at 340px + 16px gutter |
|---|---|---|
| 1280 | ~1248 | 3 |
| 1680 | 1368 (capped) | 3 |
| 2560 | 1368 (capped) | 3 |

**The 1400px cap is the real constraint, not the panel floor.** At 2560 the tab
uses barely half the screen. Whether N columns raise or drop that cap is a
design call this stitch owes an answer on; nobody else owns `.tab-panel`.

## 4. Presets — provenance is per seat, not per view

`41-preset-primitive`, ratified (`.loom/tied/1-preset-architecture-design/decisions.md`):

- **F4** — `applied_preset` stores `{patch, name}` **on the seat**, cleared only
  by recalling another preset or choosing none. Dirtiness is **derived at
  render** (`preset_application.preset_dirty`, `dashboard/preset_application.py:264`),
  never stored.
- **F3** — capture-as-step captures only targets that *have* a preset applied;
  the button states the count before committing.

`control-surface.js:276-286` derives a row's provenance from its members:

```js
if (!members.length) return {preset: null, dirty: false, mixed: false};
… if (distinct.size > 1) return {preset: null, dirty: false, mixed: true};
return {preset: members[0].applied_preset || null,
        dirty: members.some(seat => !!seat.preset_dirty), mixed: false};
```

**So overlapping columns are not a state-consistency problem.** Two columns
showing the same seat read the same per-seat provenance and derive the same
verdict; an apply in one column changes seat state and the other column's next
render reflects it. There is no per-view copy to go stale. The only real
question is *perceptual*: the same fact rendered twice on one screen, and
whether an apply in column A visibly moving column B is legible or alarming.
That is a UX question, and a much smaller one than the instructions imply.

## 5. Capture-as-step — what the code actually does

This is the consult's subject, and the instructions materially misdescribe it.

**Client** (`facilitator.js:291-303`, `381-397`): `renderShowCapture()` appends
one `Capture as Show step` button to the picker host. On click, `presetScope()`
reduces the picker's selection to a coarse scope:

- `all` / empty → `{scope:"all"}`
- exactly one seat and nothing else → `{scope:"seat", id}`
- several seats, no group → `{scope:"all"}`
- anything involving a group → `{scope:"groups"}`

**Server** (`dashboard/server.py:1804-1889`). The received scope is used in
exactly one place — `_capture_show_seats` (line 1804), which turns it into a
**set of seats to consider**:

```python
if scope == "seat":   return [that seat]
if scope == "groups": return [every seat that is in any group]
return list(self.state.seats.values())        # "all"
```

Then `_captured_show_preset_messages` (line 1838) does the real work:

1. Group those seats **by their applied preset** `(patch, name)`.
2. For each distinct preset, call `preset_application.capture_target(members, …)`
   (`preset_application.py:246`), which returns the **most portable selector
   shape** for that exact seat set: `all` if it is every seat, else `group:<name>`
   if it exactly matches a group, else an explicit seat-id list.
3. Emit one `reference` message per preset, with those selectors as its target.

### The two consequences that reframe the question

**(a) The step's arrangement is reconstructed from per-seat provenance, not from
the picker.** The scope is a *filter*, not a shape. A capture at `scope:"all"`
already emits a multi-message step — "group Left gets `dusk`, group Right gets
`bloom`, seat 7 gets `solo`" — with portable `group:<name>` targets, exactly the
entity-review model. The instructions' claim that an all-column capture "either
reduces the union (losing the arrangement) or needs a widened server vocabulary"
is **false**: the arrangement survives the reduction because it was never
carried by the scope in the first place.

**(b) The scope filter is nearly inert.** `scope:"all"` and `scope:"groups"`
differ only in that `groups` drops seats belonging to no group — and a seat with
no group that has a preset applied is precisely a target an operator would be
surprised to lose. `scope:"seat"` is the only genuinely narrowing case. So
today's picker→scope reduction contributes almost nothing except a way to
silently drop targets.

Whatever this consult recommends, note that **the widened-server-vocabulary cost
the instructions warn about does not exist.** If the answer is "capture is
venue-wide", the change is *removing* an argument, not adding one.

### The preview handshake

`preview_show_preset_capture` → server replies `show_preset_capture_preview`
with `{applied, total, omitted, show_loaded}` → client
(`facilitator.js:247-265`) alerts if no show is loaded, alerts if
`applied === 0`, else `confirm()`s "N of M targets have a preset applied; the
other K will not be captured. Add this arrangement as a Show step?" and only
then sends `capture_show_preset_step`. Two blocking dialogs and a confirm, on a
surface an operator may be driving mid-show.

## 6. Corrections to the stitch instructions

1. **"an all-column capture either reduces the union … or needs a widened
   server vocabulary — which `41-preset-primitive` deliberately declined once."**
   Wrong, per §5(a). Arrangement lives in per-seat provenance and is rebuilt
   server-side. `41` declined to widen the vocabulary *because it did not need
   it*, not as a constraint being worked around.
2. **"the applied-preset marker and its derived dirtiness … when two columns'
   targets overlap"** is framed as a hard open question. Per §4 it is a rendering
   question only — derived state cannot diverge.

## 7. The five open questions, restated

1. **Column widths** — fixed at the ~340px floor, or resizable? And does
   `.tab-panel`'s 1400px cap survive on this tab?
2. **A column resolving to no seats** — an emptied group or a deleted seat.
   Today: `<p class="empty">No Seats</p>` (`facilitator.js:343`) and an
   `empty-group` card class (`facilitator.js:206`).
3. **Overlapping columns and the preset marker** — perceptual only (§4).
4. **`followFocusSeat` with N columns** — does a Seats-tab click move every
   column, one, or none? The per-column storage key follows from the answer.
5. **Capture-as-step ownership** — per column, or whole tab? The consult
   question. Read §5 before answering.

## 8. Fixed constraints — design within these, do not reopen

- N columns, each a control panel with its own pop-out target picker; simple
  add/remove, **minimum one** (Bob, 2026-07-30).
- Column layout persists in **localStorage**.
- §12 ground and card: columns are cards on the ground; `--bg` shows only as
  gutter *between* them, never inside a column's footprint.
- The panel's 320px drawer never reflows; rows are atomic.
- Design language: monospace, 12px base, `--row-h` 24px (34px coarse pointer),
  grayscale + purple (`--accent`, structure/selection) + cyan (`--mod`,
  modulation). Status green/amber/red for status semantics only.
  Full rulebook: `.loom/tied/2-control-panel-design/design-language.md`.
- The mockup north star is
  `.lore/items/2026-07-27-control-panel-ui-and-architecture-braindump/content/mockup.png`,
  qualified by `mockup-fidelity-notes.md` beside it — several mockup details
  were superseded by Bob's later rulings and must not be copied back in.
