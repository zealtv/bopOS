# What would need a ruling before this becomes a thread

Nothing here is queued. This is the list of things that are **Bob's to decide**
rather than an implementer's to choose, collected so that picking this up later
starts from a known set of gates instead of rediscovering them.

Ordered by how much else depends on the answer.

## 1. Does a node get to say "I don't do that", and how?

The seam law lets a *patch* be small for free (`flexible-trigger-surface.md`
§1). Two things it does not cover:

- **Fetch tier.** A node that converges patch manifests over the network but
  expects media to arrive on an SD card is making a framework-level statement.
  The dashboard's convergence model currently has `absent/current/stale/
  unknown/extra` for assets and a patch badge for patches; a sideloaded node
  would sit permanently in a state that means something different from what it
  says.
- **`shutdown`.** Deep sleep is a one-way trip on a venue network. Reply `err`,
  or redefine the verb, or declare the node cannot do it.

§2's declared-facts table is the existing shape for this, and §14 already ruled
out the alternative (*"a capability broadcast/registry — pull via `/os/report` +
manifest instead"*). So the mechanism is probably a fact in `/os/report`, not a
new plane. **But adding a fact that the dashboard must branch on is close to the
line §14 draws**, and whether it crosses it is Bob's call, not an
implementer's.

This is the gate that would need to clear first, because a great deal of
dashboard behaviour hangs off it.

## 2. WiFi or PoE?

`hardware-sketch.md` argues these are different products, not a detail:

- WiFi is cheaper, has no cable, and inherits the broadcast-reliability risk
  that `feasibility.md` §5 calls the thing that could kill the idea.
- PoE is one cable for power and network, removes the broadcast risk entirely,
  and gives better sync — at the cost of an SPI Ethernet chip, since the S3 has
  no EMAC.

Deciding late means building the wrong board. Deciding early is nearly free.

## 3. Is the element convention ratified, or left to each instrument?

§3.2 deliberately says element meanings are *"patch convention, not framework
semantics"*, and that is correct. But if several S3 instruments exist, a shared
convention — say `(variant, gain, rate)` — is the difference between a fleet you
can author for and a set of one-offs.

The right home for that is a **starter-kit convention**, the way
`pd/bopos.pd` and `patches/demo-sc` are reference consumers rather than contract
text. Ratifying it into the contract would violate the ownership split the
contract just got right. Worth saying out loud so nobody helpfully "fixes" it
later by promoting it.

## 4. What does `engine-alive` mean on a node with no separate engine?

§6 calls "box up, engine crashed" vs "box gone" one of the two mid-show failures
an artist must tell apart. On an S3 the two collapse. Reporting the audio task's
watchdog keeps the bit meaningful, but it is a **redefinition of a
safety-relevant field**, and redefinitions of those belong to Bob.

Related, smaller: the heartbeat's `version` is a git shorthand today and would
become a firmware version string. `framework-version-management` is unbuilt, so
this can be decided when that thread is — but it should know there are two
kinds before it designs currentness.

## 5. Where does this sit against the horizon refactor?

`.notes/horizon-architecture-refactor.md` sets Bob's ordering explicitly: i2c
first (`59-i2c-inventory`, gated on `0a-io-design-review`), then
`62-split-elements`, then the refactor proper — *"which gets no thread until
`0a` and `62/1` have ruled, because those two rulings are most of its input."*

An S3 node is a third input to the same refactor, and arguably the clarifying
one, since it is the case where "engine" is not a process at all. The question
is whether it should be **written into the horizon note as a third force now**
(cheap, keeps the direction visible) or **left out until the first two have
ruled** (keeps the note honest about what is actually being planned).

Recommendation, weakly held: a single line in the horizon note pointing here,
nothing more. The note is explicitly *"a marker, not a plan"* and this is a
marker-sized fact.

## 6. Three bench measurements that should precede any of the above

Restated from `hardware-sketch.md` because they are cheap and they gate
everything:

1. Reliable broadcast reception with `esp_wifi_set_ps(WIFI_PS_NONE)` under a
   `/pt`-rate stream.
2. Box-to-box jitter on a scheduled fire against a shared clock — **measured
   against two Pis doing the same thing**, which has itself never been measured
   (`44-event-plane/5-pd-adoption` was tied on a local Pd test; its
   `verification.md` records that two-device forward-sync timing, *the thing
   cues existed for*, is unmeasured on hardware).
3. Voice count from PSRAM before the mixer or I2S underruns.

None needs the contract implemented. If (1) fails, nothing else matters.

And a free side-effect worth noting: **doing (2) properly would close a real
outstanding gap in the existing Pi fleet**, whether or not an S3 node is ever
built.
