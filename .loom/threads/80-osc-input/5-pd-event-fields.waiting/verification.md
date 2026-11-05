# Headless Pd check — 2026-11-05 (software half only)

Ran by Claude Code on Bob's Mac at Bob's request (`76-bob-review` item 20).
**Pd 0.55-2 (macOS), `-nogui -nosound`**, loading `pd/bopos~.pd` unmodified
as an abstraction in a scratch harness that listens on a private port.
Datagrams built with pyOSC3 the same way `fire_event_to_engine`
(`python/bopos.py`) builds them. Harnesses, sender and raw logs are in
`headless-test/`. This was not the rig and not the Pi's Pd build: the
hardware claim (item 11) stays open.

## Path

`netreceive -u -b` → `oscparse` → `list trim` → `route id groups os audition`
→ (reject) `route p e pt notify` → `e`: `[list]` → `s bopos-event`.

## Observed at `r bopos-event`

| Sent | Arrived (atom types) |
| --- | --- |
| `/e/trig` (no fields) | `symbol trig` |
| `/e/trig 0.5f 7i "play"s` | `list trig 0.5 7 play`: s, f, f, s |
| `/e/trig "play"s` | `list trig play`: s, s |
| `/e/trig/play` (no fields) | `list trig play`: s, s (**identical to the row above**) |
| `/e/kite/trig "42"s` | `list kite trig 42`: s, s, **s** (text stays a symbol) |
| `/e/trig 16777216i` | float; `[== 16777216]` → 1 (exact; prints as `1.67772e+07`) |
| `/e/scene/3 1.0f` | `list scene 3 1`: s, **s**, f (numeric segment stays a symbol) |
| `/e/trig "a;b" "x,y" "$1" "{q}"` | all symbols, escaped `a\;b x\,y \$1 {q}` |

Patch-side idiom (as in `patches/kc-test/main.pd`):
`r bopos-event` → `list trim` → `route trig` gives `bang` for a zero-field
fire, `play` for the text field, and the float for the int. **Without
`list trim`, `route trig` matched nothing**, not even the zero-field fire.

## Readings

- Text and int fields pass through unchanged within Pd's types (ints become
  exact floats up to 2^24). **No `bopos~.pd` edit is owed for pass-through.**
- **Ambiguity:** a multi-segment identity and a text field look the same
  (`/e/trig "play"` ≡ `/e/trig/play`). New with 1.22 text fields; a design
  question for Bob, not a pass-through defect.
- `list trim` before `route` is required but appears undocumented for patch
  authors (no `bopos-event` mention in `docs/`).

## Cause of the `list trim` trap — 2026-11-05, same setup (`harness3.pd`)

The `[list]` between `route p e pt notify`'s `e` outlet and `s bopos-event`
causes it; the param path has no such object. `route`'s `e` outlet emits a message
whose selector is the identity (`do 1 2`); `[list]` turns it into a
`list`-selector message (`list do 1 2`, or `symbol do` with no fields). A
`[route do]` with symbol arguments matches selectors, so it never sees `do`.

| Path | Raw | `[route <name>]` straight off the receiver |
| --- | --- | --- |
| `/p/gain 0.5` → `bopos-param` (no `[list]`) | `gain 0.5` | `0.5` ✓ |
| `/e/do …` → `bopos-event` (via `[list]`) | `symbol do` / `list do 1 2` / `list do play` | nothing ✗ |
| same `/e/do …`, replica path without `[list]` | `do` / `do 1 2` / `do play` | `bang` / `1 2` / `play` ✓ |

`[list]` arrived in `7ce74d1` (2026-07-28). The same commit's template
(`patches/.templates/bopos-template.pd`) reads `r bopos-event → route do →
unpack f f f`, which by this test receives nothing. `kc-test` works because it
puts `list trim` first; `list trim` also passes the un-listed form through
unchanged, so removing `[list]` keeps those patches working.

## Rulings — Bob, 2026-11-05

- **Ambiguity: accept it (option a).** Patch authors avoid nested identities
  that collide with a shorter identity's text field; authoring note added to
  `docs/OSC-CONTRACT.md` §3.2 (no wire change).
- **`[list]` trap: fix at source.** Edit written up in `64-pd-edits-owed`
  for Bob; no docs workaround needed once it lands.
- Remaining here: Bob's rig check (`76` hardware item 11), ideally after the
  `64` edit so the template idiom is checked too.
