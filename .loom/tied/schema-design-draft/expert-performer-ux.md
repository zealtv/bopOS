# Expert response — Performer / Artist Workflow lens

## 1. Lens & altitude

I judge every schema decision by what it costs the artist in the room: minutes from
flight case to first sound, what breaks at soundcheck, what you see when a box dies
during a show, and how a composer (with an agent beside them) authors behaviour across
50 devices the next morning. My altitude is **the four rehearsal scenarios, message by
message** — install day, soundcheck, mid-show failure, composition session. That is the
only altitude where a schema stops being a spec and becomes an instrument. I carry the
Belief System lesson as a hard bias: *ceremony and instability kill art.* Every message
family below earns its place by removing a step from one of those four moments, or it
doesn't ship.

## 2. Problem reframing

The current contract fails the artist at exactly one seam: **the dashboard cannot build
correct controls for a patch it has never seen.** It hardcodes gain/gain2/backing
because the patch is mute about itself. That is the difference between an instrument (you
plug it in, it tells you what knobs it has) and a config exercise (you edit the dashboard
to match the patch). Fixing declaration (D) is therefore the whole game — it retroactively
solves capability (G) and the assign flow, because all three are the same act: *a device
announcing what it is and what it can do, without pre-registration.*

## 3. Proposed design

### D — Patch parameter declaration (the decisive call)

**The patch ships a static manifest; the framework reads it; the dashboard auto-builds
from it. The engine never has to introspect itself.** Next to `bopos.config`, a patch
carries `bopos.params` — one line per parameter:

```
gain    float 0 1 0.75  "Volume"
cutoff  float 20 12000 800 "Filter" log
mode    enum  rain|wind|still  rain "Texture"
```

helper.py reads it at boot and, on request (`/os/describe`), broadcasts one message per
param:

```
/os/param <mac> gain float 0 1 0.75 "Volume"
```

Parameter *values* travel in a dedicated **`/p/` namespace**: `/<id>/p/gain 0.75`. The
engine's OSC-in routes `/p/*` however it likes — PD, SC, and OF all just see
`/p/gain 0.75`. gain/gain2/backing become three declared params, not framework verbs.

Why a file, not a runtime engine query: a manifest works identically for PD (no
introspection), SuperCollider, openFrameworks, and a live-boot x86 box. It's diffable,
git-friendly, agent-writable (an AI composing a patch writes `bopos.params` in the same
breath), and it **fails loud** — no manifest, no auto-controls, and the dashboard says
so plainly instead of guessing. The dashboard's detail panel stops being hand-authored;
it renders whatever the selected device declared. That single change turns the dashboard
into an instrument for *any* patch.

### The install hour — identity & assignment, message by message

Walk in, 50 boxes in cases, nothing pre-registered. Today that's a CSV-editing evening.
The workflow I want:

1. Power on. No `bopos.devices` row → device takes **id −1 (unset)** and heartbeats
   `/hb <mac> -1 <version> <engine> <caps...>` (see G). It appears in the dashboard's
   **Unassigned** pool keyed by MAC.
2. **Locate it physically** — the primitive the current system utterly lacks. Tap a row;
   dashboard sends `/os/identify <mac>`. That box *chirps and flashes* (reuses the aloha
   feedback sound; lights its LED/OLED if present). "Which physical box is this MAC?" is
   answered in one tap. This is the highest-leverage new message on install day.
3. **Assign** — `/os/assign <mac> <id> <name>`. helper.py on the matching device
   persists its own identity locally (the persistence store already ratified), sets
   hostname, tells the engine its id. No pre-registered CSV. `bopos.devices` degrades to
   an *export/cache*, not a prerequisite — which is also what makes an x86 live-boot box
   a first-class citizen (C): identity is assigned, never assumed from a MAC table.
4. **Place** — drag the node on the spatial map → `/os/pos <mac> <x> <y> [x2 y2]`,
   persisted both sides. Positions were already first-class; this just lets you set them
   from the floor instead of a spreadsheet.

Fifty devices: fifty taps to chirp-and-name, dragging as you go. Under an hour, no
terminal, no reflashing. That is the install-day payoff of remote assignment Bob endorsed.

### G — Capability broadcast: accept as announce metadata, reject as a query protocol

Bob wants concrete uses. Mine, all real:
- *"Show me which devices have screens"* — route a text/lyric cue only to OLED nodes.
- *"Which nodes can play this cue?"* — a patch needs an accelerometer; only place it on
  nodes that have one; grey out the rest.
- *Mixed fleet* — some Pis with I2C, some x86 boxes with none, some with audio-in.

But I **reject a standalone capability *query* protocol** as speculative machinery. The
dashboard already needs the boot announce; fold capabilities into it as a flat tag list:
`caps = {engine tags declared in bopos.config} ∪ {live io peripherals from io/scan}`.
So the heartbeat/hello carries `screen accel audio-in leds`. No round-trip, no new
socket, no registry — capability is just *the announce, richer*. That gives Bob every
use case at near-zero cost and nothing to maintain.

### Creative namespaces, pressure-tested against rehearsal

- **`/cue <cueId> <relative-deadline>`** — discrete triggers only. Re-running a cue must
  be idempotent: fire it again, it fires again. Deadlines are *relative* ("fire in 843
  ms"), computed by Python from the synced clock, never absolute time into the engine
  (the 32-bit float wall). Keep `/cue` dumb and re-triggerable.
- **Crossfading scenes is NOT a `/cue` job.** Scenes live in the dashboard; a crossfade
  is just param automation — the backend emits `/p/*` streams over the fade. Don't
  overload `/cue` with envelopes; discrete vs continuous stay cleanly separated. This is
  the anti-Ableton-instability move: the fade is deterministic backend math, not a
  fragile sequencer chain.
- **The panic button must be framework, not patch.** "Silence All" mid-show cannot
  depend on a misbehaving patch honouring `/p/gain 0`. So I carve out exactly one
  framework output control: **`/os/mute <0|1>`**, enforced by helper.py at the
  soundcard/JACK level (amixer), *below* patch logic. Muting the transport is not output
  *semantics* (which Bob rules patch-side) — it's the trustworthy kill switch a
  performer needs when one box goes feral. Ultimate escalation is targeted
  engine-restart (the ratified process-management fix), not `pkill python`.
- **`/point <x> <y> <radius>`** — reserve for Pi-computed spatial falloff at scale, but
  ship dashboard-computed per-device `/p/gain` first (§6 A→B). The moving point is the
  Belief technique; the namespace is reserved now so B is a drop-in later.

## 4. How it fits the existing system

**Changes:** heartbeat carries `<mac> <id> <version> <engine> <caps>` from helper.py
(already ratified, +engine/caps); new `/os/identify`, `/os/assign`, `/os/pos`,
`/os/describe`/`/os/param`, `/os/mute`; `/p/` replaces bare gain/gain2/backing; patches
gain a `bopos.params` file. **Stays:** broadcast-with-route-by-id transport, the
`installation.json` model, positions-as-first-class, the whole dashboard stack.
**Migration:** `bopos.devices` still loads as a seed, so deployed Kite Choir / Plants
fleets keep working; bare `/gain` is aliased to `/p/gain` for one release; a patch with
no `bopos.params` falls back to today's three sliders with a visible "undeclared" badge.
Nothing dies on upgrade day.

## 5. Why it's right (against the values)

The Belief System failed on *instability and ceremony*. Every call here removes ceremony
(assign from the floor, no CSV; auto-built controls, no dashboard editing) or removes
instability (relative-time cues; deterministic backend crossfades; a transport-level
panic button that can't be defeated by a bad patch). It's the *smallest* vocabulary that
works: one manifest file solves declaration, capability rides the announce we already
send, and I explicitly rejected two tempting-but-speculative systems (a capability query
protocol, an envelope-carrying cue). Agent-assisted composition gets a clean substrate —
an AI writes `bopos.params` and `/p/*` streams as plain text.

## 6. Tradeoffs, risks, not-solving

- A static manifest can drift from the patch's real params. Accepted: fail-loud badge
  when a `/p/*` value hits an undeclared name; the file is cheap to keep honest.
- `/os/mute` at the soundcard assumes a controllable mixer; on an x86 box that's a
  different call. It degrades to engine-restart. Fine — the *guarantee* holds, the
  mechanism varies.
- I'm **not** solving the scene-scripting language, video-mask, or sync internals — only
  the namespaces they plug into (`/cue`, `/point`, `/p/`, `/sync`).
- `/os/identify`'s feedback needs *some* output (beep/LED); a truly silent, screenless
  node can't self-announce physically. Rare; note it, don't over-engineer.

## 7. Smallest first step

Ship **`/os/identify <mac>`** and the **`bopos.params` → `/os/param`** pair. Identify
proves the assign-from-the-floor workflow with one tap and one chirp; the manifest turns
the dashboard into an any-patch instrument. Both are additive, both are testable on
`simfleet` today, and between them they retire the CSV evening and the three hardcoded
sliders — the two biggest artist-facing frictions in the current contract.
