# Expert response — Simplicity guard / feature-questioner

## 1. Lens & altitude

I am the seat that asks "does this need to be in the protocol at all?" My altitude is
deliberately one level below the rest of the council: not "what is the complete
vocabulary of a spatial-AV platform," but "what is the smallest vocabulary that serves
the deployments that exist and the two Bob has explicitly named." bopOS works today at
2–12 devices with six ports and a handful of messages. My job is to make sure the
contract we ratify is still something Bob can hold in his head at midnight, and that the
deployed Kite Choir and Plants fleets migrate on a namespace alias, not a flag day.

The reason I go low: every message family, port, and manifest key this council mints is
carried forever by the person who didn't propose it. Platform-agnosticism, capability
broadcast, and port consolidation are all elegant at whiteboard altitude and expensive at
Pi-Zero-at-a-show altitude. Someone has to price them honestly. That's me.

## 2. Problem reframing

The seed says "design the OSC contract as a first-class spec." The trap is reading
"first-class spec" as "big spec." The current contract is *already* 90% right (review §4):
two external ports, broadcast, per-device routing inside the engine. The work is not to
invent vocabulary — it's to (a) **write down what already works**, (b) **rename one
namespace**, (c) **move the heartbeat into Python with identity**, and (d) **stop the
dashboard hardcoding three sliders**. Everything else on the mandate list is either a
settled decision, a convention, or a feature that hasn't earned protocol surface yet.

Bob's reframing (platform-agnostic, Pi-primary) is right but its cost is mine to police:
agnosticism must be achieved by *removing assumptions* (MAC-as-identity, I2C-required,
PD-required), never by *adding abstraction layers* the Pi pays for daily.

## 3. Proposed design

### Minimal responsibility statement (A)
> **bopOS gets an identified device onto the network, keeps it reporting itself alive,
> ships it code/assets/admin commands, and relays timed control to whatever engine it
> runs. Everything that comes out of the speakers — or the LEDs, printer, monitor — is the
> patch's.**

Framework owns: identity, liveness, admin, file/asset distribution, cue *transport*, k/v
persistence, and the I2C bridge. Patch owns: output semantics and its own parameter
namespace. Dashboard owns: control-plane state, spatial math, scene authoring. Engine
owns: audio/DSP and native human-interface IO.

### The first-class vocabulary — and the two families that are secretly one
Framework namespace is **`/os/*`** (rename of `/helper/*`, one release aliased) plus
**`/io/*`**, the heartbeat, and the reserved `/sync/*` `/cue` (settled). My simplifications:

- **`/system/*` folds into `/os/*`.** `/system/rssi|id|ip|uptime|rev|patch|info` and
  `/helper/*` are secretly one family: both are the framework talking *about/to* the
  device. They live in two processes for historical reasons; conceptually there is one
  framework namespace, `/os/*`, with introspection verbs (`/os/info`) and control verbs
  (`/os/update`). Code can stay split across helper.py/io; the *contract* has one prefix.
- **`/aloha` folds into `/hb`.** Once the heartbeat carries identity
  (`/hb <id> <version> [rssi]`), "announce yourself" is just "emit a heartbeat now."
  Keep one payload shape; the announce-request only triggers an immediate `/hb`. Don't
  ship two message shapes for one concept.

### The NOT-first-class list (B) — with reasons
- **Patch parameters (`/gain`/`/gain2`/`/backing`)** — patch-local, declared by the patch
  (settled). Namespace `/p/*` or patch-declared.
- **Capability broadcast** — rejected as a family (see G).
- **Spatial falloff / `/point` semantics** — the *cue transport* is framework; the falloff
  math is dashboard-computed first (review §6A, zero Pi-side change) and sends ordinary
  patch-param messages. Don't mint a spatial message family until the Pi-computed path
  (§6B) is actually needed at scale.
- **Scene / sequencing language** — dashboard/app concern, not wire protocol.
- **Video-mask** — dashboard layer, not framework.
- **A discovery handshake** — the identity-carrying heartbeat *is* discovery. No separate
  enroll/handshake family.
- **A telemetry/log-streaming family** — heartbeat + on-request `/os/info` is enough;
  don't build a logging protocol for a fleet you debug over SSH.

### Cheapest parameter declaration (D): a manifest file, not an announce protocol
The patch declares its parameters (name, range, default, maybe `/p/<name>` address) in a
**file that ships in the patch repo** — extend the existing `bopos.config`, or a small
sibling `patch.json`. The dashboard obtains it via **one request/reply verb reusing the
exact `/system/info` pattern**: `/os/params` → device replies `/os/params <blob>` with the
declared params. That is the whole mechanism.

Rejected: an **OSC announce/push protocol** where the engine enumerates its own params at
runtime and pushes them. PD does runtime introspection badly, everything is a 32-bit
float, ordering is fragile, and it duplicates a file that already exists. Rejected too:
**convention-only** (`/p/*` names with no metadata) — it gives you routing but not the
ranges/defaults a slider needs. A declared file is the source of truth; one reply verb
delivers it. No new family, no floats-as-schema.

### Port ruling (E) — keep-and-document; honest per-option cost
**Ruling: keep all six ports, document them as the contract, change only the namespace
(`/helper`→`/os`).** The two *external* ports (5550 listen / 6660 send) are the real public
contract and they are fine. The four localhost ports are one device's *internal plumbing*
— they don't need designing, they need documenting.

- **Option 1 — keep + document (chosen).** Cost: ~zero. Fleets: only the settled
  one-release namespace alias. Muscle memory, DASHBOARD.pd, every `bopos.devices`, all
  intact. Engine-side change: `bopos.osc.pd` route line for `/helper`→`/os`.
- **Option 2 — consolidate to one port per side + namespace demux.** Elegance is real; the
  cost is carried by whoever didn't propose it. The four localhost ports give you *process
  isolation* — a helper crash doesn't touch the io socket. Merging them forces a demux
  layer and re-tangles the exact process independence the "heartbeat-into-Python" decision
  was trying to *increase*. Migration needs a synchronized PD+Python+config change on every
  deployed Pi in one shot. You spend real flag-day risk on plumbing nobody outside the Pi
  can see. Reject now; revisit only if a concrete need appears.
- **Option 3 — renumber to a "coherent" scheme (555x…).** Pure cost, zero benefit: breaks
  every deployed config and Bob's fingers for aesthetics. Reject outright.

The only defensible follow-up is giving the localhost ports symbolic names in
`bopos.config` so they aren't magic numbers in three files — a refactor, not a protocol
change, and it can wait.

### Capability broadcast (G): rejected, with its 90% substitute
Bob hasn't needed it; I hold the line. No device should unsolicitedly broadcast a
capability manifest — at 50–100 devices that's also chatter you don't want. **Capabilities
are a property of the running patch, and the dashboard already learns them two cheaper
ways:** (1) device facts from `/os/info` (rssi/ip/rev/**patch name**/uptime — already
built), and (2) the patch manifest the dashboard fetches for parameter declaration (D),
which already lists the params, peripherals, and assets that patch expects. The patch name
*is* the capability signal. If a genuinely concrete question arrives later ("which devices
have an OLED?"), it is a `/os/*` **query-reply**, not a broadcast family. Cheapest 90%:
`/os/info` + patch manifest. Zero new machinery.

### Platform agnosticism (C) & IO boundary (F), minimally
- Identity is an **opaque stable string** keyed in `bopos.devices`; MAC is the default
  *provider*, not the definition. A live-image x86 box uses machine-id/hostname. RSSI and
  I2C are **optional** — absent, not error. That's the whole agnosticism change: delete
  assumptions from wording, don't add layers.
- IO boundary rule: **framework owns bus/offboard IO the engine can't reach (`/io` = I2C,
  the entire framework-IO surface); the engine owns IO it has native objects for (MIDI,
  keyboard, mouse, audio-in).** Don't pre-mint `/gpio` `/midi` `/serial`; when a real
  peripheral needs one, route it through the existing `/io` registry pattern.

### Distribution (H)
Generalize `getsamples` → **`/os/fetch <url>`**, media-agnostic, into a **landing location
the patch declares in its manifest** (`assets_dir`, default `patches/<active>/assets/`).
Keep the pull model; make the *source* pluggable (gdrive URL today, dashboard-served HTTP
tomorrow for the local-network case Bob wants) and the *destination* patch-declared. The
local-network want is a URL change plus a static file server on the dashboard — not a
fleet-sync protocol. Convention over protocol.

## 4. How it fits the existing system

**Stays (maximize this):** all six ports and their numbers; broadcast + route-by-id;
DASHBOARD.pd; `bopos.devices`; patches-as-git-repos; `/addpatch`/`/patch`/`/pullpatch`;
the `/io` peripheral registry; the `/system/info` request-reply *pattern* (reused for
`/os/params`). The remote-git-update loop — explicitly keep-don't-disturb — is untouched.

**Changes (small, mostly settled):** namespace `/helper`→`/os` (aliased one release);
heartbeat moves PD→helper.py and carries `<id> <version> [rssi]`; add two `/os` reply
verbs (`/os/info` already exists as `/system/*`; add `/os/params`); `getsamples`→`/os/fetch`
with a patch-declared landing dir; patch manifest gains a `params` block; targeted process
management replaces `pkill python` (settled). `bopos.devices` doc reworded MAC→stable-id.

**Fleet migration:** Kite Choir and Plants get the namespace alias for one release, a
heartbeat that now carries identity (dashboard keeps IP-correlation as fallback until
patches update), and a `params` block added to their patch repos when convenient. No flag
day. No port change. No re-flash.

## 5. Why it's right

Graded against the values: **performance stability > features** — I added no per-frame
message families, no unsolicited broadcast, no runtime schema enumeration on the
single-threaded Pi. **Smallest vocabulary that works** — one framework prefix (`/os/*`),
one heartbeat shape (absorbing `/aloha`), one reply verb for params, one fetch verb.
**Fail loud** — optional I2C/RSSI are absent-not-faked; identity lookup still hard-fails on
unknown id (kept). **Migration path** — everything deployed keeps running on an alias.

Complexity taxes I refused to pay: the **port-consolidation retrofit** (flag-day risk on
invisible plumbing); the **capability-broadcast family** (a protocol for a need Bob doesn't
have); the **params-over-OSC announce protocol** (runtime introspection PD is bad at,
duplicating a file); a **spatial/scene message family** (dashboard math doesn't need wire
surface yet); and **renumbered ports** (cost for aesthetics).

## 6. Tradeoffs, risks, what I'm NOT solving

- Keeping six ports means the "smell" Bob named is documented, not deodorized. I claim the
  smell is aesthetic and the ports are a *symptom of healthy process separation*. If the
  council later proves a concrete win from consolidation, my ruling loses — accepted.
- Manifest-file params mean the dashboard must fetch the manifest (one reply verb) rather
  than being pushed changes live. A patch that changes its own params at runtime isn't
  served. I judge that rare and not worth an announce protocol; revisit if it turns real.
- Folding `/system/*` into the `/os/*` *contract* while leaving the *code* split could
  confuse a reader. Doc must state clearly: one namespace, two processes behind it.
- Rejecting capability broadcast gives up automatic feature-driven UI. Substitute (patch
  manifest + `/os/info`) covers the known cases; a novel cross-device capability query
  would need the query-reply I deferred.
- Not solving: scene language, video-mask, clock-sync internals, Pi-computed spatial —
  correctly other seats' and other threads' work. I only guarded their *wire surface*.

## 7. Smallest first step

Write `docs/OSC-CONTRACT.md` documenting the **six ports exactly as they are** and the
**current** messages, with two edits landed in the same doc: the `/helper`→`/os` rename
(alias noted) and the `/hb <id> <version> [rssi]` shape. Nothing else changes yet. That
single document *is* the "first-class spec" — it turns the working system into the
contract, and every later decision (params, fetch, process mgmt) becomes a small, reviewed
diff against a written baseline instead of a redesign.
