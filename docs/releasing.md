# Releasing bopOS

As of 2026-11-12, before the first release (v1.0.0). This describes the cycle
decided on 2026-11-12.

## The shape

- **Development happens in a private development repository.** It stays green:
  every commit passes the fast tests (the pre-commit hook,
  [VERIFICATION.md](VERIFICATION.md)).
- **A release is one commit on this public repository's `main`**, tagged
  `vMAJOR.MINOR.PATCH`. It holds the framework tree at that version, without
  development-only material, and appears as a GitHub release with that
  version's [CHANGELOG](../CHANGELOG.md) section as its notes.
- **Devices track public `main`.** `install-device.sh` clones it and
  **Update bopOS** (`bash/update.sh`) fast-forwards it. From v1.0.0 on,
  public `main` only ever moves forward, one release at a time. An update
  therefore always lands on a release, and each device's current release is
  its own `main`.
- **v1.0.0 starts a fresh public history.** It is the first commit of public
  `main`, with no parent: the pre-release history doesn't lead to it
  ([The first release](#the-first-release-starts-a-fresh-history)). A device
  that was installed before v1.0.0 needs a one-time resync to reach it
  ([INSTALL.md](INSTALL.md#moving-a-device-from-before-v100)). Every release
  after it fast-forwards.
- **`VERSION`** at the repository root holds the version the tree is, or is
  heading towards.

## Version numbers

Numbering starts at **1.0.0**. **The major number means fleet compatibility:** a
dashboard and nodes on the same major interoperate, whatever their minor and
patch.

- **Major**: any change that would break a fleet running mixed releases.
  - An incompatible change to the [OSC contract](OSC-CONTRACT.md): removing
    or changing the meaning of a message, field or port that an older node or
    dashboard relies on.
  - Project or show files that older dashboards of the same major can't open.
  - An update that a device's existing `bash/update.sh` can't apply by
    itself. For example, it needs a fresh install, a re-flash or hands on
    the device.
- **Minor**: additive features. New messages or fields that older peers can
  ignore, additive contract amendments, new dashboard capabilities, and
  provisioning changes that `update.sh` applies by itself (the provision-level
  check).
- **Patch**: fixes, with no change to the contract or file formats.

Each CHANGELOG entry records the compatibility facts alongside the framework
version: the OSC contract version (`python/osc_contract.py`), the provision
level (`systemd/provision-level`) and the project storage schema
(`dashboard/state.py` `SCHEMA`). As of 2026-11-12 these read contract 1.26,
provision level 1 and schema 1.

## Mixed fleets

A fleet is migrated deliberately, so some devices may run an older release for
a while. A show fleet may stay on its release through a run while a test bench
moves ahead. Releases must not assume every device is current:

- A release within a major works alongside earlier releases of that major.
- The dashboard may show that a device runs an older release. It must not press
  the operator to update a show.
- A device stays on its release simply by not being updated: nothing updates
  devices automatically.

**Fixing an older line.** This is a proposal, not yet decided. Public `main`
only moves forward. When a fleet held on an older minor needs a fix that can't
wait for it to migrate:

- branch `release/<X.Y>` on the public repository from that release's tag;
- tag the fix there as the next patch, `vX.Y.(Z+1)`;
- switch that fleet's checkouts to `release/<X.Y>` (`BOPOS_BRANCH` does this
  for a fresh install);
- carry the fix into the next release on `main` as well.

Do this only when a held-back fleet actually needs it.

## The cycle

1. **Plan** the release: its scope is bounded and agreed before work starts.
   Review the backlog for anything the release makes obsolete or should take in.
2. **Build** in the development repository. Every commit passes the fast tests.
3. **Accept.** The release is reviewed and toured, and the fixes the tour finds
   land before it is accepted. Each release states whether it needs a
   hardware check on real devices, and why. The check is decided case by case;
   software and hardware results are recorded separately.
4. **Release** only on explicit acceptance, following the checklist.
5. **Migrate** fleets deliberately, one at a time, when their operators choose.

## Release checklist

`tools/release.sh` automates steps 3–5 and refuses when a check fails.
`tools/release.sh help` prints its usage. It runs in the development
repository.

1. Set `VERSION` to `X.Y.Z`.
2. Turn `CHANGELOG.md`'s unreleased entry into
   `## vX.Y.Z (YYYY-MM-DD): contract … · provision level … · schema …`, with
   that release's compatibility facts, and remove its draft marker.
3. `tools/release.sh prepare vX.Y.Z`. It refuses unless:
   - the checkout is on the development `main`, with no changes besides
     `VERSION` and `CHANGELOG.md` (no untracked files either), and no tag
     `vX.Y.Z` exists yet;
   - `VERSION` reads `X.Y.Z`, and `CHANGELOG.md` has exactly one `## vX.Y.Z`
     section, dated, not empty and not marked as a draft;
   - every top-level entry of the tree is listed in
     `tools/release-manifest`, the export allowlist, as public or private;
   - the fast and browser tests (`./tools/run-tests.sh fast`, then `browser`)
     pass in a fresh Git checkout of the exported tree, not only in the
     development tree. The `pd/bop` submodule isn't checked out there.

   It then commits "Release vX.Y.Z", which runs the pre-commit hook's fast
   tests on the development tree as well, and makes the annotated tag
   `vX.Y.Z`. The tag's message records which tests ran and the exported tree
   they ran on. Push the commit and the tag to the development repository.

   `BOPOS_RELEASE_TESTS` replaces the tests with another command, for
   example the fast tier alone on a machine without Playwright. Prepare then
   prints a warning, and the tag's message says the standard tests were
   replaced and by what.
4. `tools/release.sh export vX.Y.Z`. It builds the public commit from the tag
   and pushes nothing:
   - its tree is the tag's tree with only the entries
     `tools/release-manifest` lists as public. It is built with Git plumbing,
     so the `pd/bop` submodule pointer survives unchanged;
   - its parent is the public `main` as fetched now, so devices fast-forward;
     its message is `bopOS vX.Y.Z`;
   - an annotated public tag `vX.Y.Z` points at it.

   Export refuses when a top-level entry is on neither list, when the tag's
   message records no test run of exactly this tree, or when the public
   repository already has a different `vX.Y.Z`. The same tag and the same
   public `main` always give the same commit, so re-running it is safe.
   v1.0.0 exports with `--root` instead
   ([below](#the-first-release-starts-a-fresh-history)).
5. `tools/release.sh publish vX.Y.Z --dry-run`, then without `--dry-run`. It
   checks that the public `main` is still the export's parent (or already the
   export) and that the public repository has no other `vX.Y.Z` tag. Then it
   pushes the commit to `main` and the tag, together and never forced, and
   creates the GitHub release "bopOS vX.Y.Z" with the version's CHANGELOG
   section as its notes, compatibility line first. On a re-run it pushes
   nothing new and updates the release notes. `--dry-run` prints the notes and
   every push and `gh` call without running them. v1.0.0 publishes with
   `--root` (below).
6. Check a fresh `git clone --recursive` of the public repository: one new
   commit on top of the previous release (for v1.0.0, the only commit),
   tagged `vX.Y.Z`; no
   development-only paths; `python3 python/version_identity.py` prints
   `X.Y.Z`; and the fast tests pass.
7. If the release calls for it, update a test device from public `main` and
   confirm it comes back reporting the new version (`bopos version`).

### The first release starts a fresh history

v1.0.0 is the first commit of a fresh public history rather than a commit on
the pre-release one. It goes into a new, **empty** public repository, created
by hand before the release; the pre-release history is archived separately.
`tools/release.sh` never creates, renames or deletes repositories.

Steps 4 and 5 then take `--root`, which is opt-in and meant for this one
release:

- `tools/release.sh export v1.0.0 --root` builds the same tree as a normal
  export, as a commit with **no parent**. Against an empty repository it
  reports that the release replaces nothing.
- `tools/release.sh publish v1.0.0 --root --dry-run`, then without
  `--dry-run`. Into an empty repository (no branches, no tags) this is a
  plain push that creates `main` and the tag `v1.0.0`; nothing is forced. A
  repository with refs but no `main` is refused.
- Re-running publish after it succeeded reports the release as present and
  pushes nothing.

A root commit doesn't depend on its target, so the same tag always exports to
the same commit, whichever repository it goes into.

**Replacing an existing `main` instead.** The tool can also publish the root
release over a repository that still has its pre-release `main`. Export
`--root` then records that `main` (`refs/bopos-release/<tag>/replaces`) and
prints it, and publish also needs it spelled out by the operator:
`publish v1.0.0 --root --replacing <sha>`. Publish refuses unless `<sha>`
matches what export recorded and the target's `main` still is that commit,
and while the target has any `v*` tag: a released history is never replaced.
The push replaces `main` under a lease
(`--force-with-lease=refs/heads/main:<sha>`), so it fails if `main` moved
after the check, and the dry run prints this forced push. Into an empty
repository, `--replacing` is refused.

Without `--root`, nothing is ever forced. A root export can't be published
without `--root`, and once the target has the v1.0.0 tag, `--root` refuses.
Every later release (v1.0.1, v1.1.0, …) uses the plain steps and
fast-forwards from v1.0.0.

### Rehearsing a release

`--public <url-or-path>`, or `BOPOS_RELEASE_PUBLIC`, sends export and publish
to another repository instead of `https://github.com/zealtv/bopOS.git`, such as
a local bare copy of the public repository. A target that isn't a GitHub URL
gets no GitHub release. `BOPOS_RELEASE_GITHUB_REPO` names one if needed, and
`none` skips it.

### Where an export waits before publish

The development repository holds two tags named `vX.Y.Z`: the development tag
on the "Release" commit, in `refs/tags/<tag>`, and the public tag on the export
commit. So export keeps the public pair apart, as
`refs/bopos-release/<tag>/commit` and `refs/bopos-release/<tag>/tag`, and
records the public `main` it built on as refs/bopos-release/public-main.
Publish pushes them to the public repository's `main` and `refs/tags/<tag>`.
`tools/release.sh list` shows each tag and its export. The tool fetches from
the public repository without tags, since its tags would collide with the
development ones.

**Open item:** the public repository carries no licence file yet, as of
2026-11-12; the choice is deferred. Third-party material is listed in
[THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md).
