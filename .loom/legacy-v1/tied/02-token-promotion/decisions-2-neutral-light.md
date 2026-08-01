# Addendum — the app-wide light panels go neutral grey

2026-07-30, after the tie. `decisions.md` recorded the purple-tinted light
panel scale as **held for a Bob-facing pass**. Bob looked at the before/after
pair and ruled: *"I'd like to try the grey neutrals on the panels."* So the
hold is lifted and the app-wide light theme is now the mockup's neutral scale.

Authority stays `control-panel.css`'s `--cp-*` light column (sampled from
`mockup.png`). `style.css` and `facilitator.css` light columns — both the
`@media (prefers-color-scheme: light)` block and the `:root[data-theme=light]`
block in each file — map onto it:

| token | was (purple-tinted) | now |
|---|---|---|
| `--bg` | `#f8f0fc` | unchanged — **the ground is the only pink** |
| `--panel` | `#fff` | `#f8f9fa` |
| `--surface-bar`, `--surface-alt` | `#e9e4ef`, `#e4eff2` | `#e9ecef` |
| `--panel-soft`, `--panel-strong` | `#f0edf4`, `#eee9f3` | `#f1f3f5` |
| `--canvas`, `--canvas-alt` | `#ece8f1`, `#e3dfea` | `#f1f3f5`, `#e9ecef` |
| `--input`, `--control` | `#fbfafe`, `#e5e0ea` | `#ffffff` |
| `--input-alt`, `--hover` | `#f0edf4`, `#ddd7e4` | `#f1f3f5` |
| `--subpanel`, `--selected`, `--deep` | `#f5f2f8`, `#d8d1e3`, `#fff` | `#e9ecef` |
| `--row` | `#f8f6fa` | `#f8f9fa` |
| `--line`, `--group-line`, `--subpanel-line` | `#918698`, `#9b91a5`, `#aaa0b4` | `#ced4da` |
| `--control-line`, `--strong-line` | `#82798c`, `#8b8197` | `#495057` |
| `--text`, `--muted-strong` | `#27222d`, `#4f4756` | `#212529`, `#343a40` |
| `--dim` | `#625b69` | `#6c757d` — see below |
| `--offline-mark` | `#706878` | `#adb5bd` |
| `--console` / `--console-text` | `#27232c` / `#f1edf5` | `#212529` / `#f8f9fa` |
| `--status-neutral-*` | lavender bg/border/text | `#e9ecef` / `#495057` / `#343a40` |

Three calls inside that sweep:

1. **`--deep` inverted its relationship deliberately.** It was `#fff` — the
   *lightest* value in a light theme — but in dark it is `#0f1418`, darker than
   `--panel`. It names a recessed surface (the execution-mode switch's trough),
   so it is now `#e9ecef`: recessed below the panel, the same direction dark
   already had.

2. **`--dim` is `#6c757d` app-wide, not the panel's `#868e96`.** The panel's
   value is ratified and stays. But app-wide `--dim` paints small uppercase
   labels on `#f8f9fa`, where `#868e96` lands near 3:1 — under the thread's
   standing accessibility constraint. `#6c757d` is the next step of the same
   grey ramp at ~4.6:1. A deliberate one-token divergence, not drift.

3. **Nothing else moved.** Purple `--accent*` (ratified), the cyan inks, status
   green/amber/red, and the Show message pills' eight-colour set are untouched.

**The cyan is explicitly closed, not carried.** Bob, same session: the mockup
cyan-fill delta was my note, not his ask — *"I don't want to change the
highlights. Leave `--mod-fill` as it is for now."* `--mod-fill` stays
`rgba(7,152,188,.20)` in light. Stop listing it as an open question.

Verified: `fast` 250 OK, `browser` 17/17 PASS. Light-theme evidence retained as
`neutral-*.png` (every tab at 1280 and 1680, the Monitor dock, the Remote view
and the All card) — compare against `after-*light.png` for the greys alone,
since the metrics are identical between those two sets.
