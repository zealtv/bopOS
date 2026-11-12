#!/usr/bin/env bash
set -eu

repo_dir=$(cd "$(dirname "$0")/.." && pwd)
cd "$repo_dir"
current=$(git config --get core.hooksPath || true)
if [ -n "$current" ] && [ "$current" != tools/hooks ]; then
    echo "bopOS: core.hooksPath already points to '$current'; integrate tools/hooks/pre-commit there before changing it." >&2
    exit 1
fi
if [ -z "$current" ] && [ -x "$(git rev-parse --git-path hooks/pre-commit)" ]; then
    echo "bopOS: an existing pre-commit hook is installed; integrate tools/hooks/pre-commit before replacing it." >&2
    exit 1
fi
git config --local core.hooksPath tools/hooks
echo "bopOS: installed versioned hooks (fast tests before every commit)."
