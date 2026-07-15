# Asset management design record

## Status

Product direction accepted by Bob on 2026-07-15. This record does not by
itself ratify a new OSC wire term; the minimal device-asset observation shape
remains the first actionable design/contract step.

## Context from prior installations

Belief System used one canonical top-level asset folder containing many folders
of audio samples. The structure was looser than a BOP sample pack, but shared
the useful folder-first property. Real operations included:

- adding files to an existing collection;
- editing or removing files within it;
- publishing a holistically processed replacement generation;
- installing old and new generations side by side, changing the patch to use
  the new generation, retaining the old generation for rollback, and removing
  it later to reclaim constrained device storage.

Pure Data and dormant SuperCollider support mean audio and text are the
immediate asset types. Future engines such as openFrameworks may introduce
images, video, fonts, models, and other data, so the transport must not encode
an audio-only taxonomy.

## Accepted content model

The top-level directory beneath `assets/` remains the independently deployable
asset slot:

```text
assets/
  belief-system-000/
    voices/
    textures/
    field-recordings/
  belief-system-001/
    voices/
    textures/
    field-recordings/
```

Names and generation suffixes are entirely operator-defined. bopOS treats each
entry as a folder; it does not parse `000`, infer a family, or impose semantic
versioning. Everything below the top level is an opaque, arbitrary hierarchy
owned by the project. A slot may contain one media kind or a coherent mixture.

Choose slot boundaries operationally: files that must deploy, activate, roll
back, and be removed together share a slot. Independently managed content uses
separate slots. An optional semantic manifest may be considered when a real
consumer needs labels, collections, licensing, or media facts, but it is not a
transport prerequisite.

Two authoring operations are intentionally distinct:

1. **Revise a slot in place.** Add, edit, or remove files and converge the same
   operational folder name to a new content fingerprint.
2. **Publish a new generation.** Create another operator-named folder when a
   change is holistic or needs a reliable rollback. Install both, switch the
   patch, retain the old slot through a confidence period, then remove it
   explicitly.

A prior fingerprint without retained prior bytes is not a rollback mechanism.

## First implementation: one device at a time

Fleet-wide desired assets and coordinated rollout are deferred. The immediate
Assets workflow manages one online, assigned physical device at a time:

- show the host asset catalog with slot name, file count, bytes, modified time,
  and canonical content fingerprint;
- select exactly one device and one host slot;
- send a missing slot or update an existing slot using the existing convergent
  fetch operation;
- show honest queued, fetching, succeeded, and failed feedback;
- explicitly remove an installed slot from that device;
- distinguish observed installed content from a transfer receipt and do not
  claim durable convergence from dashboard-session memory;
- remove asset selection and fleet-wide send/sync controls from Devices and
  place the single-device operation in Assets.

Sending a new side-by-side slot need not stop the running engine. Updating a
slot used by the active patch can expose partial live changes under the current
in-place fetcher, so the first UI must warn rather than silently promise safety.
Automatic stop/fetch/restart is not part of the first implementation: a
dashboard-owned sequence could strand an engine if the dashboard or transfer
fails. Proper node-owned staging and activation belongs to the deferred
hardening work.

The first implementation needs a minimal, additive device asset inventory so
the dashboard can distinguish absent, current, stale, and extra slots after a
restart. The exact wire response is a decision gate; the likely shape parallels
patch inventory and reports installed slot names plus canonical fingerprints.

## Existing transport retained

The ratified `/os/fetch` HTTP path already provides a useful data plane:

- a canonical manifest of relative paths, sizes, and SHA-256 hashes;
- per-file comparison and skipping of matching content;
- HTTP Range resume into `.part` files;
- verification before per-file replacement;
- pruning of files absent from the source manifest.

The canonical directory-manifest fingerprint remains the asset identity. An
archive hash must not replace it: archive bytes may vary with ordering,
timestamps, or compressor implementation while extracting to equivalent
content.

## Deferred fleet-scale problem

The design must eventually support roughly 10–50 GB sent to tens of devices
over installation Wi-Fi. Ten GB to 50 receivers is 500 GB of receiver traffic;
packaging does not remove that airtime.

The agreed future direction is:

- freeze immutable deployment snapshots during a rollout;
- query device inventory, free bytes/inodes, capability, and engine state;
- stage a complete generation while the engine continues running;
- reuse verified unchanged files where practical;
- verify, then atomically activate a slot;
- restart the engine once after all required slot activations when hot reload is
  not explicitly supported;
- retain the previous generation for deliberate rollback and garbage
  collection;
- persist transfer journals and desired deployment state across dashboard and
  node restarts;
- begin with a canary, then use bounded configurable waves per access point;
- expose measured byte progress, rate, verification, activation, failure,
  rollback, pause, retry, and cleanup states;
- use wired origins/caches or physical USB/SD seeding for large initial loads;
- measure the real rig before considering chunk stores, peer-to-peer transfer,
  or reliable multicast.

One-device-at-a-time remains a valid conservative scheduler setting later, but
the fleet scheduler is explicitly outside the first implementation.

## Packaging decision

Do not make one ZIP or tar archive the ordinary synchronization unit. It reduces
request overhead but makes small edits invalidate a large object, weakens
incremental delivery, and may require space for the old generation, archive,
and extracted generation simultaneously. Already-compressed media often gains
little.

Archives remain useful as optional import/export or physical bulk-seeding
artifacts, and deterministic small-file packfiles may be evaluated if measured
request overhead warrants them. After any seed or extraction, the normal
directory manifest remains the verification authority.

rclone may help acquire host content or populate wired edge caches; rsync or
chunk hashes may help when measurements show frequent small edits inside very
large files. Neither replaces the initial node contract now.

## Explicit deferrals

The following are not part of the first Assets workspace:

- fleet-wide desired asset state;
- Sync All or all-device asset deployment;
- concurrency and per-access-point scheduling;
- automatic coordinated engine restarts;
- immutable snapshot serving and atomic slot activation;
- byte-level fleet progress and ETA;
- caches, physical seeding orchestration, P2P, multicast, or content-addressed
  chunk storage.

These requirements are retained on a separate waiting Loom thread so the
single-device workflow does not accidentally grow into a bulk-distribution
project.
