# 🪺 nestlings

A tiny, file-based protocol for making a folder ready to receive material.

One script. One folder convention.

When you open `.nest/in/`, you are looking at the items available to be tended.
They may have arrived moments ago or be waiting for the next batch.

```
.nest/
  nestling.sh
  in/
  out/
  dropped/
  tend.md
```

## What a nest is for

A nest is the entrance and transport layer for a folder. A new repository can
begin with only `.nest/`: material can arrive before anyone knows whether it
will become evidence, memory, work, or nothing at all.

Items arrive in `in/`. A human, agent, or process tends them according to the
folder's local policy. Hatched items land in `out/`; dropped items land in
`dropped/` with a reason.

Nestlings owns safe intake, claiming, and disposition. It does not decide what
an item means, preserve project memory, plan work, or require a particular
agent runtime. Those choices belong to the tender and the folder. Other tools
may be selected as destinations when tending reveals a need for them, but they
are optional: a repository can remain useful with only its nest.

An item is one file or directory accepted into the nest. It may be an
unclassified piece of material, a shaped request, or material accompanied by a
note about what should happen. An item does not have to be a task.

To **tend** is to apply the folder's local policy to a claimed item. To
**hatch** is to complete that tending successfully by placing its result in
`out/`. Passing items through `in/`, `out/`, and `dropped/` leaves a simple
filesystem record of what happened.

## Start a repository with a nest

Create an empty folder, enter it, then stream the installer from upstream:

```sh
mkdir my-project
cd my-project
curl -fsSL https://raw.githubusercontent.com/zealtv/nestlings/main/install.sh | bash
```

The folder now contains only `.nest/`. Read and tailor `.nest/tend.md`; it is
the local routing policy and will not be overwritten by later installs.

If an agent instruction file is useful, its Nestlings pointer can be one line:

```markdown
For incoming material, read `.nest/tend.md` and inspect `.nest/in/`.
```

That pointer is optional and runtime-neutral. Project guidance belongs
elsewhere and can be added when the project has enough shape to need it.

Capture an establishment request as an ordinary envelope outside the nest:

```text
establish-repository/
  request.md
  attachments/
    brief.md
```

In `request.md`, state the desired outcome, which initial materials matter, and
that only justified project structures or tools should be added. Then ingest it:

```sh
./.nest/nestling.sh ingest establish-repository/
```

When tending the request, claim and read it before deciding what the repository
needs. Preserve or shape the initial material using the host policy. If a tool
such as Lore, Glean, Loom, or Groundhog is justified, run that tool's own
installer explicitly, inspect what it added, and use its own interface. The
Nestlings installer never selects or installs sibling tools.

Finish by hatching a short receipt that records what was established and where
the material went:

```text
# repository established

- retained the original brief at: path:<repo-relative-path>
- added: <independently installed structure or tool, or "nothing yet">
- next material belongs in: .nest/in/
```

Pass that receipt to `complete` as the result source. It lands in `out/`, while
the claimed establishment envelope is removed from `in/`:

```sh
./.nest/nestling.sh complete establish-repository <receipt-file> repository-established.md
```

The repository can remain a nest plus its initial material. More furniture is
an outcome of tending, not a prerequisite for capture.

## Capture now, tend later

Put a self-contained note directly in `in/` when prose is enough:

```text
.nest/in/check-release-notes.md
```

The file can hold the material, the desired handling, or both. When material
needs to travel beside its note, use a directory envelope:

```text
.nest/in/review-source/
  request.md
  attachments/
    source.txt
```

`request.md` is an ordinary note to the tender; `attachments/` is an ordinary
directory. These names are a useful convention, not protocol metadata. A local
`tend.md` may recognise other shapes.

Use `ingest` when copying either shape into a nest so the item is staged with a
`.landing` suffix and appears atomically under its final name:

```sh
./.nest/nestling.sh ingest check-release-notes.md
./.nest/nestling.sh ingest review-source/
```

An item waiting in `in/` is pending and available; it is not claimed, failed,
abandoned, or scheduled. Only `.tending` records an active claim, and only
`dropped/` records failure or rejection. Scheduling, urgency, and batch cadence
belong in the folder's local policy or its tender, not in the nest protocol.

## How nestlings works

An item can be a file or a directory.

```
.nest/
  in/
    item/
  out/
  dropped/
```

* items arrive in `in/`
* tended items are placed in `out/`
* failed items are placed in `dropped/`
* `.tending` means claimed
* `.landing` means being written

## Rules

1. Write protection: write as `<item>.landing`, then rename to `<item>` when complete.
2. Claim by suffix: `<item>` → `<item>.tending`
3. Tend from `in/`
4. Hatch to `out/`
5. Drop to `dropped/` with a sibling `<item>.reason.md`
6. Retry only directories explicitly marked with `.recoverable`; bounded retry
   state travels with the item as `.attempts` and `.recovery.md`

The file system is the protocol.

## Tending loop

1. Read `.nest/tend.md` if present
2. Look at `.nest/in/` when it is time to tend one item or a batch
3. Pick one available item
4. Claim it by renaming it with `.tending`
5. Apply the local policy
6. Either:
   * hatch by placing the result in `.nest/out/` using `.landing`
   * or move the item to `.nest/dropped/` and write a reason file

Other tenders must not touch anything ending in `.landing` or `.tending`.

An abandoned claim is not inferred from age alone. `stale` reports claimed
items older than a threshold without changing them; the process that owns the
nest decides whether a claim is abandoned and passes it to `resolve`. Resolution
returns a marked directory to `in/` while it is below the retry limit, otherwise
it drops the claim with a reason. Bare files and unmarked directories fail
closed and are dropped.

Set `NEST_MAX_ATTEMPTS` to a non-negative integer to change the default limit
of three. Producers should add `.recoverable` only when repeating the item is
safe. Nestlings does not decide whether a tender process is still alive.

## Passing between nests

When two folders communicate through nests, new material goes to the receiving
folder's `in/`, not the sending folder's `out/`.

The sender's `out/` records what it has tended. The receiver's `in/` holds what
it is being asked to tend.

Address the receiver with an explicit path to its nest. Adjacent repositories
need no registry:

```sh
../receiver/.nest/nestling.sh ingest ./review-brief sender--review-brief--20260827
```

`ingest` copies the file or directory as `<name>.landing` and renames it only
after the copy finishes. It refuses an existing landing or final name rather
than merging with or overwriting it. Choose a new unambiguous name when retrying
a collision; a useful shape is `<origin>--<purpose>--<token>`.

For a relationship used often, a host may replace the repeated path with a
visible symlink, for example `.nest/peers/reviewer` pointing to
`../../../reviewer/.nest`. This is optional host configuration, not shared
Nestlings state. Anyone can inspect where it leads.

Pass a request and its material as one directory envelope:

```text
sender--review-brief--20260827/
  request.md
  attachments/
    brief.md
```

Use ordinary prose in `request.md` to name the origin repository, the inbound
item name, the requested handling, and where a reply should be ingested. For
adjacent repositories, the routing lines can use repository-relative paths:

```markdown
- origin: path:../sender
- reply nest: path:../sender/.nest
```

These details are an origin trail, not mandatory protocol metadata. A
`path:` reference is resolved from the root of the repository reading the note.
When repositories do not move together, use a visible peer name or transport
instruction meaningful to the tender that will send the reply.

After tending, the receiver hatches its own result or receipt in its `out/`.
That record stays with the receiver. A reply is a new item explicitly ingested
into the origin repository's `in/`:

```sh
../sender/.nest/nestling.sh ingest ./reply-envelope receiver--reply--20260827
```

The reply envelope should refer to the inbound item name and may carry response
attachments. It is not copied from the receiver's `out/` implicitly.

If both repositories are not available on one machine, prepare the complete
envelope in a transport folder first. Synchronize or carry that finished
envelope by any agreed means, then run the receiving nest's `ingest` when it is
locally available. Network transport and synchronization are outside the local
protocol: never expose a partially synchronized directory as a final entry in
`in/`, and never use one repository's `out/` as another repository's inbox.

## tend.md

`.nest/tend.md` is an optional conventional file that states the folder's local
policy for tending items.

If present, read it before tending.

Keep it short. Keep it concrete.

A single-purpose nest can use one route:

```text
recognised customer email -> draft a reply -> hatch the draft
anything else             -> drop with a reason
```

A repository entrance can compose with other local tools without adding those
tools to the Nestlings protocol. For example, after reading the whole item,
take each applicable route in host-defined order:

```text
complete source worth retaining -> preserve it as durable evidence in Lore
current guidance worth distilling -> update the relevant memory in Glean
finite intention needing work -> shape a stitch in Loom
recurring intention -> establish it in Groundhog
material owned elsewhere -> ingest it into the receiving repository's nest
no further route needed -> hatch a receipt or result
unsafe, invalid, or unintelligible -> drop with a reason
```

These are example policy decisions, not built-in destinations. Replace their
names and ordering with the host's actual tools and conventions. Record enough
in the hatched receipt to show what went where; keep evidence, memory, plans,
schedules, and agent behavior in their owning systems rather than in `tend.md`.

### Experimental composition references

Requests and receipts may use small typed references in ordinary Markdown when
an owning system has produced something worth finding again:

```text
glean:<finding-id>
lore:<item-id>
loom:<stitch-id>
path:<repo-relative-path>
```

For example:

```markdown
- retained source: lore:2026-08-27-project-brief
- distilled guidance: glean:prefer-bounded-batches
- shaped work: loom:publish-first-brief
- generated file: path:docs/brief.md
```

The prefix identifies the owner; the owner defines and resolves the ID. `path:`
is resolved from the current repository root and can also point to a Groundhog
schedule item when its schedule path is the useful identity. Surrounding prose
states the relationship—created, revised, consulted, or routed—because the
reference itself carries no graph semantics.

Do not give `nest:` references to entries in `in/`, `out/`, or `dropped/`.
Those entries are transport records and may be swept. A request or receipt can
mention an inbound item name for correlation, but durable references should
name the durable result in Lore, Glean, Loom, or a stable repository path.

This convention remains an optional host-policy convention. Nestlings neither
parses nor validates it, and it should not be added to Glean's finding contract:
Glean already owns finding-local associations, while these references cross
several systems and include operational paths. If multiple primitives later
need to resolve the same prefixes, extract a separate family composition
specification with those owners rather than expanding the Nestlings protocol.

## Installation

From inside the target folder, stream the upstream installer:

```sh
curl -fsSL https://raw.githubusercontent.com/zealtv/nestlings/main/install.sh | bash
```

From a local Nestlings checkout, the equivalent is:

```sh
./install.sh /path/to/host-repository
```

This installs `nestling.sh`, the protocol README, a starter `tend.md`, and the
three trays. Re-running repairs the script and README and recreates missing
trays, but preserves tray contents and a host-customized `tend.md`.

For manual vendoring, copy `nestling.sh` and `README.md` into the project's
`.nest/` directory, then seed the trays:

```sh
mkdir -p <project>/.nest
cp /path/to/nestlings/.nest/nestling.sh <project>/.nest/
cp /path/to/nestlings/README.md <project>/.nest/
<project>/.nest/nestling.sh ensure
```

`ensure` creates `in/`, `out/`, and `dropped/` next to itself.
`nestling.sh` operates on the `.nest/` directory it lives in, so each
vendored copy is self-contained.

## Commands

```
./nestling.sh ensure
./nestling.sh list
./nestling.sh ingest <src> [name]
./nestling.sh claim <name>
./nestling.sh complete <name> <result-src> [out-name]
./nestling.sh drop <name> [reason...]
./nestling.sh stale [max-age-mins]   # read-only; default 10
./nestling.sh resolve <name> [reason...]   # retry marked directories or drop
./nestling.sh sweep [days]
```

`sweep` removes `out/` and `dropped/` items older than the requested number of
days (default 14; pass 0 to sweep everything regardless of modification time).
It preserves `.gitkeep` placeholders and standalone `*.reason.md` files, and
prints one line per item removed.
