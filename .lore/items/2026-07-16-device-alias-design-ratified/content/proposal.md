# Physical device aliases

**Status: ratified by Bob on 2026-07-16.**

## Decision

A physical bopOS computer receives a memorable host-side alias such as
`Freda Sparks`. The alias names the box, not its current role:

```text
Freda Sparks sits in Seat 0.
```

The four identity layers remain distinct:

| Layer | Meaning | Mutability |
|---|---|---|
| UID | Opaque physical identity and registry key | Immutable |
| Device alias | Human identity for the physical box | Durable, editable |
| Hostname | Node-reported technical/runtime fact | Node-managed |
| Seat name/ID | Logical position in the piece | Independently authored |

An alias is presentation data. It is never copied into a Seat name, sent as an
assignment name, used as an OSC selector, or written to the node hostname.
There is no wire-contract amendment.

Virtual and simulated devices do not enter the physical-device registry.

## Global host registry

The dashboard host owns a durable registry keyed by full UID, separate from the
runtime device roster:

```json
{
  "device_registry": {
    "2c:cf:67:b3:0a:58": {
      "alias": "Freda Sparks",
      "source": "generated",
      "generator": 1
    }
  }
}
```

The registry is global across venues. It survives dashboard and node restarts,
keeps aliases available for bound offline UIDs, and is retained unchanged when
a venue loads. Venue snapshots do not own or overwrite it.

Only registry state is durable. Hostname, IP, health, version and observed
content remain runtime facts in `devices[uid]`.

On first observation of a physical UID—or when loading an older bound UID with
no registry entry—the host allocates and atomically saves a generated alias.

## Naming system

`Freda Sparks` is the canonical seed and tone reference:

- `Freda` is entry zero of the given-name list;
- `Sparks` is entry zero of the character-surname list;
- documentation and golden examples use the complete pair;
- it is not hard-coded to the first discovered device. A device receives it
  only when the deterministic allocator selects that available pair, or when
  an operator assigns it deliberately.

Generator version 1 uses two pinned curated lists and SHA-256 of the normalized
UID plus a probe number. A candidate is `given[index] + " " + character[index]`.
If another UID already owns that alias case-insensitively, the allocator probes
again until it finds a free pair. The resolved alias is persisted immediately,
so discovery order, restarts and later list revisions never rename an existing
box. A future list revision increments `generator`; it does not rewrite old
entries.

The initial implementation should use at least 64 words in each list (4,096
pairs). Deterministic probing, rather than an audible numeric suffix, resolves
collisions. Exhaustion fails visibly and does not invent an unsafe name.

### Given-name list brief

The project is global. The list should draw evenly from different regions and
language traditions while optimizing for use in an English-speaking install
crew:

- ASCII letters only; no accents, apostrophes, hyphens or punctuation;
- one word, normally 3–7 letters;
- short and readily pronounceable in English;
- avoid near-homophones within the list;
- avoid names strongly dominated by one country or one gender presentation;
- avoid titles, religious figures, politicians and novelty spellings.

Tone examples: `Freda`, `Amina`, `Anya`, `Asha`, `Diego`, `Hana`, `Imani`,
`Juno`, `Lila`, `Luca`, `Mina`, `Niko`, `Omar`, `Priya`, `Remy`, `Sora`,
`Talia`, `Zuri`. These examples guide curation; the implementation list still
needs duplicate, pronunciation and combination review as a complete set.

### Character-surname list brief

The second word is not an ordinary family name. It is a vivid, pop-star-style
character word that makes the alias easy to remember and call across a room:

- ASCII letters only; no punctuation or digits;
- one word, normally 3–8 letters;
- a concrete or evocative non-name word;
- easy to pronounce, hear and type in English;
- energetic without being violent, sexual, political, insulting or culturally
  appropriative;
- avoid pairs that accidentally form a real celebrity, brand, slur or loaded
  phrase.

Tone examples: `Sparks`, `Bloom`, `Comet`, `Echo`, `Halo`, `Neon`, `Orbit`,
`Pepper`, `Prism`, `Rocket`, `Tempo`, `Velvet`. `Sparks` is the list anchor.

List acceptance includes reviewing the full Cartesian set with automated
deny-list checks and a human pass over likely awkward combinations. The lists
are product copy and ship under focused tests, not as an unreviewed name
generator dependency.

## Editing and uniqueness

The Devices workspace provides Rename and Reset alias actions. Generated and
custom aliases share one case-insensitive uniqueness namespace.

- Rename is host-only and does not interrupt the node.
- Input is trimmed and internal whitespace is collapsed.
- Custom aliases use exactly two ASCII alphabetic words separated by one
  space, with the same short, pronounceable intent as generated aliases.
- A duplicate is rejected with the existing owner's alias and UID tail; the
  backend is authoritative even if two browsers edit concurrently.
- Reset releases the current alias and deterministically allocates the first
  available generated pair for that UID.
- Alias updates are atomic and broadcast as full state so every surface
  converges together.

## Forget semantics

**Forget genuinely forgets.** For an unbound physical device it removes the
runtime observation and its durable registry entry in one confirmed operation.
If the alias was customized, confirmation explicitly says the custom alias will
be lost. A later heartbeat creates a new registry entry through the normal
deterministic allocator; it may receive a different pair if collision ownership
has changed.

Bound devices cannot be forgotten until they are unassigned, preserving the
single Seat binding authority.

## Display hierarchy

Use one shared alias resolver/formatter across dashboard surfaces:

- **Devices list:** alias primary; hostname, UID tail and Seat secondary.
- **Device detail:** alias heading; hostname, full copyable UID, IP, version and
  health as technical facts.
- **Seat assignment picker:** alias first, then hostname/UID tail and online
  state.
- **Assets target and device-scoped confirmations:** alias first.
- **Bound Dashboard card:** Seat name/ID remains primary; alias is secondary.
- **Unbound physical device:** alias is primary.
- **Remembered offline binding:** resolve alias from the registry even without
  a runtime device row.

Full UID remains available for copying anywhere ambiguity matters. Duplicate
hostnames are harmless because they are never the primary human identity.

## Required implementation coverage

The implementation follow-up must prove:

1. the UID-to-candidate algorithm and pinned generator vectors;
2. collision probing without renaming the existing owner;
3. restart, offline binding and cross-venue persistence;
4. custom validation, case-insensitive collision rejection and concurrent-edit
   authority;
5. Reset and genuine Forget semantics;
6. no alias-to-Seat, hostname, node state or OSC leakage;
7. no virtual/simulated registry pollution;
8. consistent identity hierarchy in Devices, Seats, Assets and Dashboard;
9. accessible Rename/Reset controls and narrow touch layout;
10. complete word-list linting plus human review of the shipped list pair.

The follow-up should land before or with any Live Controls target picker that
would otherwise introduce another hostname-first device label.
