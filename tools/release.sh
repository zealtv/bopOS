#!/usr/bin/env bash
# Release bopOS: turn a green development main into one tagged commit on the
# public repository's main. The cycle and checklist: docs/releasing.md.
#
#   tools/release.sh prepare vX.Y.Z
#       check the tree, test the exported tree, commit "Release vX.Y.Z", tag it
#   tools/release.sh export vX.Y.Z [--root] [--public <url-or-path>]
#       build the public commit and its tag from the development tag
#   tools/release.sh publish vX.Y.Z [--root [--replacing <sha>]] [--dry-run] [--public <url-or-path>]
#       push them to the public repository, then create or update the GitHub release
#   tools/release.sh list
#       show the development tags and their exports
#
# The public repository defaults to https://github.com/zealtv/bopOS.git.
# --public, or BOPOS_RELEASE_PUBLIC, points export and publish elsewhere, such
# as a local bare repository for a rehearsal. --dry-run prints every push and
# gh call instead of running it.
#
# --root, once only: export the release as a commit with no parent, the start
# of a fresh public history. Into an empty target, publish --root is a plain
# push. Into a target that has a main, it replaces that main: export --root
# records the main it replaces, publish --root needs it spelled out
# (--replacing <sha>), refuses while the target has any v* tag, and pushes
# with a lease, so it fails if main moved since. Without --root nothing is
# ever forced: public main only fast-forwards.
#
# BOPOS_RELEASE_TESTS replaces prepare's tests (fast, then browser, run in a
# Git checkout of the exported tree) with another command. The output and the
# tag message say so.
# BOPOS_RELEASE_GITHUB_REPO names the GitHub repository (OWNER/NAME) for the
# release when the target isn't a GitHub URL; "none" skips the release.
set -euo pipefail

caller_dir=$(pwd)
cd "$(dirname "$0")/.."
root=$(pwd)

# A hook's environment would point git at another repository or index.
unset GIT_DIR GIT_WORK_TREE GIT_INDEX_FILE GIT_OBJECT_DIRECTORY \
    GIT_ALTERNATE_OBJECT_DIRECTORIES GIT_COMMON_DIR GIT_PREFIX GIT_NAMESPACE

default_public=https://github.com/zealtv/bopOS.git
manifest_path=tools/release-manifest
default_tests='./tools/run-tests.sh fast && ./tools/run-tests.sh browser'
# Local refs. The development tag vX.Y.Z stays in refs/tags; the public commit
# and the public tag of the same name live apart from it until publish pushes
# them to the public repository's main and refs/tags/vX.Y.Z.
ns=refs/bopos-release
#   $ns/public-main     the public main as last fetched by export (the parent)
#   $ns/<tag>/commit    the public release commit
#   $ns/<tag>/tag       its annotated public tag object, named <tag>
#   $ns/<tag>/replaces  for a root export only: the public main it replaces
#                       (absent when the target was empty)

die() {
    echo "release: $*" >&2
    exit 1
}

usage() {
    awk 'NR > 1 && /^#/ { sub(/^# ?/, ""); print; next } NR > 1 { exit }' "$0" >&2
    exit "${1:-2}"
}

work=
cleanup() {
    if [ -n "$work" ]; then
        rm -rf "$work"
    fi
}
trap cleanup EXIT
work=$(mktemp -d "${TMPDIR:-/tmp}/bopos-release.XXXXXX")

check_tag() {
    [ -n "$tag" ] || usage
    printf '%s\n' "$tag" | grep -E '^v[0-9]+\.[0-9]+\.[0-9]+$' >/dev/null ||
        die "expected a version tag like v1.2.3, not '$tag'"
}

# The only way publish reaches the public repository or GitHub. Under
# --dry-run it prints the command and returns.
act() {
    if [ "$dry" = 1 ]; then
        printf 'dry run, not executed:'
        printf ' %q' "$@"
        printf '\n'
    else
        "$@"
    fi
}

# public_tree <tree-ish>: write the tree a release exports from <tree-ish>
# and print its id. Only top-level entries change: everything below them,
# the pd/bop submodule pointer included, is the same object. Refuses when the
# manifest doesn't classify a top-level entry.
public_tree() {
    git cat-file -e "$1:$manifest_path" 2>/dev/null ||
        die "$1 has no $manifest_path, the export allowlist"
    git show "$1:$manifest_path" > "$work/manifest"
    git ls-tree "$1" > "$work/source.lstree"
    if ! awk -F '\t' -v manifest="$work/manifest" -v left="$work/left-out" '
        BEGIN {
            while ((getline line < manifest) > 0) {
                sub(/#.*/, "", line)
                n = split(line, f, " ")
                if (n == 0) continue
                if (n != 2 || (f[1] != "public" && f[1] != "private")) {
                    print "release: bad manifest line: " line > "/dev/stderr"
                    bad = 1
                    continue
                }
                if ((f[2] in kind) && kind[f[2]] != f[1]) {
                    print "release: " f[2] " is both public and private in the manifest" > "/dev/stderr"
                    bad = 1
                }
                kind[f[2]] = f[1]
            }
            printf "" > left
        }
        {
            name = substr($0, index($0, "\t") + 1)
            if (!(name in kind)) {
                print "release: top-level entry " name " is on neither list in the manifest" > "/dev/stderr"
                bad = 1
            } else if (kind[name] == "public") {
                print
            } else {
                print name > left
            }
        }
        END { exit bad }' "$work/source.lstree" > "$work/public.lstree"; then
        die "classify every top-level entry in $manifest_path before releasing"
    fi
    tree=$(git mktree < "$work/public.lstree")
    for required in VERSION CHANGELOG.md "$manifest_path"; do
        git cat-file -e "$tree:$required" 2>/dev/null ||
            die "the exported tree would lack $required"
    done
    echo "$tree"
}

# changelog_section <tree-ish>: the CHANGELOG.md section for $tag, heading first.
changelog_section() {
    git show "$1:CHANGELOG.md" | awk -v h="## $tag" '
        /^## / {
            if (on) exit
            on = ($0 == h || index($0, h " ") == 1 || index($0, h ":") == 1)
        }
        on { print }'
}

# check_release_files <tree-ish>: VERSION says $tag, and CHANGELOG.md has one
# dated, finished section for it.
check_release_files() {
    version=${tag#v}
    actual=$(git show "$1:VERSION" 2>/dev/null | tr -d '[:space:]') || true
    [ "$actual" = "$version" ] ||
        die "VERSION reads '${actual}', not $version"
    escaped=$(printf '%s' "$tag" | sed 's/\./\\./g')
    headings=$(git show "$1:CHANGELOG.md" 2>/dev/null |
        grep -E "^## ${escaped}([ :]|\$)") || true
    [ -n "$headings" ] ||
        die "CHANGELOG.md has no section '## $tag (YYYY-MM-DD)'"
    [ "$(printf '%s\n' "$headings" | wc -l | tr -d ' ')" = 1 ] ||
        die "CHANGELOG.md has more than one section for $tag"
    printf '%s\n' "$headings" |
        grep -E "^## ${escaped} \([0-9]{4}-[0-9]{2}-[0-9]{2}\)(:.*)?\$" >/dev/null ||
        die "CHANGELOG.md's heading for $tag isn't dated: '$headings' (want '## $tag (YYYY-MM-DD)', optionally followed by ': <compatibility line>')"
    section=$(changelog_section "$1")
    if printf '%s\n' "$section" | grep '^\*\*Draft' >/dev/null; then
        die "CHANGELOG.md's $tag section is still marked as a draft"
    fi
    [ -n "$(printf '%s\n' "$section" | sed 1d | tr -d '[:space:]')" ] ||
        die "CHANGELOG.md's $tag section is empty"
}

# release_notes <tree-ish>: the GitHub release notes, the heading's
# compatibility line first, then the section's body.
release_notes() {
    changelog_section "$1" | awk '
        NR == 1 { i = index($0, "): "); if (i) print substr($0, i + 3); next }
        { print }'
}

resolve_public() {
    case $public in
        /* | *://* | *:*) ;;
        *) public=$caller_dir/$public ;;
    esac
}

# release_tags <target>: the v* tags the target has, one per line.
release_tags() {
    git ls-remote --tags "$1" > "$work/remote-tags" ||
        die "could not read tags from $1"
    cut -f2 "$work/remote-tags" | sed -n 's|^refs/tags/\(v[^^]*\).*|\1|p' | sort -u
}

# refuse_release_tags <target>: a root release starts the public history, so
# the history it replaces must hold no release.
refuse_release_tags() {
    existing=$(release_tags "$1")
    [ -z "$existing" ] ||
        die "--root starts the public history afresh, but $1 already has release tags: $(printf '%s\n' "$existing" | tr '\n' ' ')- a released history is never replaced"
}

github_repo() {
    if [ -n "${BOPOS_RELEASE_GITHUB_REPO+set}" ]; then
        [ "$BOPOS_RELEASE_GITHUB_REPO" = none ] || echo "$BOPOS_RELEASE_GITHUB_REPO"
        return 0
    fi
    case $1 in
        https://github.com/*) repo=${1#https://github.com/} ;;
        git@github.com:*) repo=${1#git@github.com:} ;;
        ssh://git@github.com/*) repo=${1#ssh://git@github.com/} ;;
        *) return 0 ;;
    esac
    repo=${repo%/}
    repo=${repo%.git}
    case $repo in
        */*/* | /* | */) ;;
        */*) echo "$repo" ;;
    esac
}

# run_release_tests <public tree>: run the release tests in a fresh Git
# checkout of the exported tree (some tests call git, so a plain copy won't
# do). The pd/bop submodule is not checked out there.
run_release_tests() {
    candidate=$(git commit-tree --no-gpg-sign "$1" -m "release candidate $tag")
    git update-ref "$ns/candidate" "$candidate"
    checkout=$work/exported
    git init -q -b main "$checkout"
    if ! git -C "$checkout" fetch -q --no-tags "$root" "$ns/candidate"; then
        git update-ref -d "$ns/candidate"
        die "could not copy the exported tree into $checkout"
    fi
    git update-ref -d "$ns/candidate"
    git -C "$checkout" reset -q --hard FETCH_HEAD
    echo "release: running the release tests in a checkout of the exported tree:"
    echo "release:   $tests"
    if ! (cd "$checkout" && sh -c "$tests"); then
        die "the release tests failed on the exported tree; nothing was committed or tagged"
    fi
}

cmd_prepare() {
    check_tag
    branch=$(git symbolic-ref -q --short HEAD) || true
    [ "$branch" = main ] ||
        die "on '${branch:-a detached HEAD}', not main: prepare releases from the development main"
    dirty=$(git status --porcelain=v1 --untracked-files=normal --ignore-submodules=none |
        awk '{ path = substr($0, 4) } path != "VERSION" && path != "CHANGELOG.md"')
    [ -z "$dirty" ] ||
        die "the tree has changes besides VERSION and CHANGELOG.md; commit or remove them first:
$dirty"
    if git rev-parse -q --verify "refs/tags/$tag" >/dev/null; then
        if [ "$(git rev-parse "$tag^{commit}")" = "$(git rev-parse HEAD)" ] &&
            [ -z "$(git status --porcelain=v1)" ]; then
            echo "release: $tag is already prepared at HEAD; next: tools/release.sh export $tag"
            return 0
        fi
        die "tag $tag already exists, at $(git rev-parse --short "$tag^{commit}")"
    fi

    # The tree the release commit will have: HEAD plus VERSION and CHANGELOG.md
    # as they stand.
    GIT_INDEX_FILE=$work/index git read-tree HEAD
    GIT_INDEX_FILE=$work/index git update-index --add --remove -- VERSION CHANGELOG.md
    dev_tree=$(GIT_INDEX_FILE=$work/index git write-tree)
    check_release_files "$dev_tree"
    pub_tree=$(public_tree "$dev_tree")

    if [ -n "${BOPOS_RELEASE_TESTS+set}" ]; then
        tests=$BOPOS_RELEASE_TESTS
        record="Release tests REPLACED by BOPOS_RELEASE_TESTS, not the standard fast and browser tiers: $tests"
        echo "release: WARNING: $record" >&2
    else
        tests=$default_tests
        record="Release tests passed on the exported tree: $tests"
    fi
    run_release_tests "$pub_tree"

    git add -- VERSION CHANGELOG.md
    if ! git diff --cached --quiet; then
        git commit -m "Release $tag"
    elif [ "$(git log -1 --format=%s)" != "Release $tag" ]; then
        git commit --allow-empty -m "Release $tag"
    fi
    [ "$(git rev-parse 'HEAD^{tree}')" = "$dev_tree" ] ||
        die "HEAD's tree differs from the tree that was tested; inspect HEAD (not tagged)"
    git tag -a "$tag" -m "bopOS $tag

$record
Tested public tree: $pub_tree"
    if [ -n "${BOPOS_RELEASE_TESTS+set}" ]; then
        echo "release: WARNING: $tag was tagged without the standard release tests (BOPOS_RELEASE_TESTS); its tag message says so." >&2
    fi
    echo "release: prepared $tag at $(git rev-parse --short HEAD)"
    echo "release: next: git push origin main $tag, then tools/release.sh export $tag"
}

cmd_export() {
    check_tag
    resolve_public
    git rev-parse -q --verify "refs/tags/$tag" >/dev/null ||
        die "no development tag $tag; run tools/release.sh prepare $tag"
    [ "$(git cat-file -t "refs/tags/$tag")" = tag ] ||
        die "$tag is a lightweight tag; prepare makes an annotated one"
    release_commit=$(git rev-parse "$tag^{commit}")
    check_release_files "$release_commit"
    pub_tree=$(public_tree "$release_commit")
    git cat-file tag "refs/tags/$tag" | grep -x "Tested public tree: $pub_tree" >/dev/null ||
        die "the tag $tag records no release-test run of the tree it exports; make it with tools/release.sh prepare"

    git ls-remote "$public" > "$work/remote-refs" ||
        die "could not read $public"
    if [ "$root_mode" = 1 ] && [ ! -s "$work/remote-refs" ]; then
        # An empty target: the root commit replaces nothing there.
        echo "release: $public is empty"
        base=
        if git rev-parse -q --verify "$ns/public-main" >/dev/null; then
            git update-ref -d "$ns/public-main"
        fi
    else
        echo "release: fetching main from $public"
        git fetch -q --no-tags --no-recurse-submodules "$public" "+refs/heads/main:$ns/public-main" ||
            die "could not fetch main from $public"
        base=$(git rev-parse "$ns/public-main")
    fi
    stored=$(git rev-parse -q --verify "$ns/$tag/commit") || true
    stored_tag=$(git rev-parse -q --verify "$ns/$tag/tag") || true
    if [ -n "$stored" ] && [ "$stored" = "$base" ]; then
        [ "$(git rev-parse "$stored^{tree}")" = "$pub_tree" ] ||
            die "public main is $tag's earlier export, but its tree differs from the tag's"
        echo "release: $tag is already exported and is the public main ($(git rev-parse --short "$stored"))"
        return 0
    fi
    remote_tag=$(git ls-remote "$public" "refs/tags/$tag" | cut -f1) ||
        die "could not read tags from $public"
    if [ -n "$remote_tag" ] && [ "$remote_tag" != "$stored_tag" ]; then
        die "$public already has a tag $tag ($remote_tag) that this checkout didn't export"
    fi
    if [ "$root_mode" = 1 ]; then
        refuse_release_tags "$public"
    fi
    stored_replaces=$(git rev-parse -q --verify "$ns/$tag/replaces") || true

    # Identity and date come from the release commit, so the same tag and the
    # same public main always export to the same commit and tag objects.
    name=$(git log -1 --format=%cn "$release_commit")
    email=$(git log -1 --format=%ce "$release_commit")
    date=$(git log -1 --format=%cd --date=raw "$release_commit")
    # A root export has no parent; otherwise the parent is public main.
    if [ "$root_mode" = 1 ]; then
        set -- "$pub_tree"
    else
        set -- "$pub_tree" -p "$base"
    fi
    commit=$(GIT_AUTHOR_NAME=$name GIT_AUTHOR_EMAIL=$email GIT_AUTHOR_DATE=$date \
        GIT_COMMITTER_NAME=$name GIT_COMMITTER_EMAIL=$email GIT_COMMITTER_DATE=$date \
        git commit-tree --no-gpg-sign "$@" -m "bopOS $tag")
    public_tag=$(printf 'object %s\ntype commit\ntag %s\ntagger %s <%s> %s\n\nbopOS %s\n' \
        "$commit" "$tag" "$name" "$email" "$date" "$tag" | git mktag)
    # A root commit is the same whatever main it replaces, so a root export
    # also goes stale when the main it recorded replacing moved.
    if { [ -n "$stored" ] && [ "$stored" != "$commit" ]; } ||
        { [ "$root_mode" = 1 ] && [ -n "$stored" ] && [ "$stored_replaces" != "$base" ]; }; then
        die "an earlier export of $tag ($(git rev-parse --short "$stored")) differs from this one: public main or the tag moved since, or one export used --root and the other didn't. If it was never published, remove it and export again:
  git update-ref -d $ns/$tag/commit && git update-ref -d $ns/$tag/tag && git update-ref -d $ns/$tag/replaces"
    fi
    git update-ref "$ns/$tag/commit" "$commit"
    git update-ref "$ns/$tag/tag" "$public_tag"
    if [ -n "$base" ] && [ "$root_mode" = 1 ]; then
        git update-ref "$ns/$tag/replaces" "$base"
    elif [ -n "$stored_replaces" ]; then
        git update-ref -d "$ns/$tag/replaces"
    fi
    echo "release: exported $tag"
    if [ "$root_mode" = 1 ]; then
        echo "release:   parent  none: a root commit, the start of a fresh public history"
        if [ -n "$base" ]; then
            echo "release:   replaces public main $base   ($ns/$tag/replaces)"
        else
            echo "release:   replaces nothing: $public is empty"
        fi
    else
        echo "release:   parent  $(git rev-parse --short "$base")  (public main)"
    fi
    echo "release:   commit  $(git rev-parse --short "$commit")  bopOS $tag   ($ns/$tag/commit)"
    echo "release:   tag     $tag -> $(git rev-parse --short "$commit")   ($ns/$tag/tag)"
    echo "release:   left out: $(tr '\n' ' ' < "$work/left-out")"
    if [ "$root_mode" = 1 ] && [ -n "$base" ]; then
        echo "release: next: tools/release.sh publish $tag --root --replacing $base --dry-run"
    elif [ "$root_mode" = 1 ]; then
        echo "release: next: tools/release.sh publish $tag --root --dry-run"
    else
        echo "release: next: tools/release.sh publish $tag --dry-run"
    fi
}

cmd_publish() {
    check_tag
    resolve_public
    commit=$(git rev-parse -q --verify "$ns/$tag/commit") ||
        die "no export of $tag; run tools/release.sh export $tag"
    public_tag=$(git rev-parse -q --verify "$ns/$tag/tag") ||
        die "no public tag for $tag; run tools/release.sh export $tag"
    [ "$(git cat-file -t "$public_tag")" = tag ] &&
        [ "$(git rev-parse "$public_tag^{commit}")" = "$commit" ] ||
        die "$ns/$tag/tag doesn't point at $tag's export"
    git ls-remote "$public" > "$work/remote-refs" ||
        die "could not read $public"
    remote_main=$(awk -F '\t' '$2 == "refs/heads/main" { print $1 }' "$work/remote-refs")
    remote_tag=$(awk -F '\t' -v ref="refs/tags/$tag" '$2 == ref { print $1 }' "$work/remote-refs")
    if parent=$(git rev-parse -q --verify "$commit^"); then
        [ "$root_mode" = 0 ] ||
            die "$tag's export has a parent, so it isn't a root export; publish it without --root, or remove it and run tools/release.sh export $tag --root"
    else
        [ "$root_mode" = 1 ] ||
            die "$tag's export is a root commit, the start of a fresh public history; publish it with --root (and --replacing <the public main it replaces>, unless the target is empty)"
        parent=
    fi
    replaces=$(git rev-parse -q --verify "$ns/$tag/replaces") || replaces=
    if [ -n "$replacing" ]; then
        [ -n "$replaces" ] ||
            die "$tag's root export was made for an empty target and records no main to replace; publish without --replacing, or remove the export and export again against $public"
        case $replaces in
            "$replacing"*) ;;
            *) die "--replacing $replacing isn't the public main $tag's root export replaces ($replaces)" ;;
        esac
    fi

    # How public main gets to the export: forward (a fast-forward from its
    # parent), empty (a root export creating main in an empty target) or
    # replace (a root export replacing main under a lease).
    route=
    if [ "$remote_main" = "$commit" ]; then
        main_state=present
    elif [ -n "$parent" ]; then
        [ "$remote_main" = "$parent" ] ||
            die "main on $public is at ${remote_main:-nothing}, which is neither $tag's export ($(git rev-parse --short "$commit")) nor its parent ($(git rev-parse --short "$parent")); export again"
        main_state=missing
        route=forward
    elif [ ! -s "$work/remote-refs" ]; then
        [ -z "$replacing" ] ||
            die "$public is empty, so there is no main to replace; publish into it without --replacing"
        main_state=missing
        route=empty
    else
        [ -n "$replacing" ] ||
            die "publish --root would replace main on $public (${remote_main:-none, in a target with other refs}); name the main it replaces with --replacing <sha> (export --root printed it)"
        [ -n "$remote_main" ] && [ "$remote_main" = "$replaces" ] ||
            die "main on $public is at ${remote_main:-nothing}, which is neither $tag's export ($(git rev-parse --short "$commit")) nor the main it replaces ($(git rev-parse --short "$replaces")); export again"
        main_state=missing
        route=replace
    fi
    case $remote_tag in
        "$public_tag") tag_state=present ;;
        "") tag_state=missing ;;
        *) die "$public already has a different tag $tag ($remote_tag)" ;;
    esac

    release_notes "$commit" > "$work/notes.md"
    [ -s "$work/notes.md" ] || die "no CHANGELOG.md notes for $tag"
    if [ "$dry" = 1 ]; then
        echo "release: dry run: nothing below is executed. Release notes:"
        sed 's/^/  | /' "$work/notes.md"
    fi

    if [ "$main_state" = present ] && [ "$tag_state" = present ]; then
        echo "release: $public already has $tag on main"
    elif [ "$route" = replace ]; then
        refuse_release_tags "$public"
        echo "release: REPLACING public main $replaces on $public with $tag's root commit $commit."
        echo "release: The lease refuses the push if main is no longer $replaces."
        # The lease covers main only; the tag is new and never forced.
        act git push --atomic --no-follow-tags --recurse-submodules=no \
            "--force-with-lease=refs/heads/main:$replaces" "$public" \
            "$ns/$tag/commit:refs/heads/main" "$ns/$tag/tag:refs/tags/$tag"
        if [ "$dry" = 0 ]; then
            [ "$(git ls-remote "$public" refs/heads/main | cut -f1)" = "$commit" ] ||
                die "main on $public isn't $tag's export after the push"
            echo "release: pushed $tag to $public; public main's history now starts at $tag"
        fi
    else
        if [ "$route" = empty ]; then
            echo "release: $public is empty; $tag's root commit starts its main."
        fi
        act git push --atomic --no-follow-tags --recurse-submodules=no "$public" \
            "$ns/$tag/commit:refs/heads/main" "$ns/$tag/tag:refs/tags/$tag"
        if [ "$dry" = 0 ]; then
            [ "$(git ls-remote "$public" refs/heads/main | cut -f1)" = "$commit" ] ||
                die "main on $public isn't $tag's export after the push"
            echo "release: pushed $tag to $public"
        fi
    fi

    repo=$(github_repo "$public")
    if [ -z "$repo" ]; then
        echo "release: $public is not on GitHub; no GitHub release"
        return 0
    fi
    title="bopOS $tag"
    if [ "$dry" = 1 ]; then
        echo "release: the real run picks one of these by 'gh release view $tag --repo $repo':"
        act gh release create "$tag" --repo "$repo" --verify-tag --title "$title" --notes-file "$work/notes.md"
        act gh release edit "$tag" --repo "$repo" --title "$title" --notes-file "$work/notes.md"
        return 0
    fi
    command -v gh >/dev/null || die "gh is not installed; the push is done, re-run publish once it is"
    if gh release view "$tag" --repo "$repo" >/dev/null 2>&1; then
        act gh release edit "$tag" --repo "$repo" --title "$title" --notes-file "$work/notes.md"
    else
        act gh release create "$tag" --repo "$repo" --verify-tag --title "$title" --notes-file "$work/notes.md"
    fi
    echo "release: published $tag on $repo"
}

cmd_list() {
    for t in $(git tag -l 'v*' --sort=-v:refname); do
        exported=$(git rev-parse -q --verify --short "$ns/$t/commit") || exported=-
        if replaces=$(git rev-parse -q --verify --short "$ns/$t/replaces"); then
            exported="$exported (root, replaces $replaces)"
        fi
        echo "$t  development $(git rev-parse --short "$t^{commit}")  public export $exported"
    done
    if base=$(git rev-parse -q --verify --short "$ns/public-main"); then
        echo "public main as last fetched by export: $base"
    fi
}

command=${1:-help}
[ $# -eq 0 ] || shift
tag=
dry=0
root_mode=0
replacing=
public=${BOPOS_RELEASE_PUBLIC:-$default_public}
while [ $# -gt 0 ]; do
    case $1 in
        --dry-run) dry=1 ;;
        --root) root_mode=1 ;;
        --replacing)
            [ $# -ge 2 ] || die "--replacing needs the public main's commit id"
            replacing=$2
            shift
            ;;
        --replacing=*) replacing=${1#--replacing=} ;;
        --public)
            [ $# -ge 2 ] || die "--public needs a URL or path"
            public=$2
            shift
            ;;
        --public=*) public=${1#--public=} ;;
        -*) die "unknown option $1" ;;
        *)
            [ -z "$tag" ] || die "unexpected argument $1"
            tag=$1
            ;;
    esac
    shift
done
case $command in
    prepare | export | list) [ "$dry" = 0 ] || die "--dry-run applies to publish only" ;;
esac
case $command in
    export | publish) ;;
    *) [ "$root_mode" = 0 ] || die "--root applies to export and publish only" ;;
esac
if [ -n "$replacing" ]; then
    [ "$command" = publish ] && [ "$root_mode" = 1 ] ||
        die "--replacing applies to publish --root only"
    printf '%s\n' "$replacing" | grep -E '^[0-9a-f]{7,40}$' >/dev/null ||
        die "--replacing wants a commit id (7 to 40 lowercase hex digits), not '$replacing'"
fi

case $command in
    prepare) cmd_prepare ;;
    export) cmd_export ;;
    publish) cmd_publish ;;
    list) cmd_list ;;
    help | -h | --help) usage 0 ;;
    *) usage ;;
esac
