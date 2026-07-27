#!/usr/bin/env bash

set -u

repo_dir=$(cd "$(dirname "$0")/.." && pwd)
tier=${1:-fast}

usage() {
    echo "usage: ./tools/run-tests.sh [fast|browser|all]" >&2
}

if [ "$#" -gt 1 ]; then
    usage
    exit 2
fi

case "$tier" in
    fast|browser|all) ;;
    *)
        usage
        exit 2
        ;;
esac

if [ -n "${BOPOS_PYTHON:-}" ]; then
    test_python=$BOPOS_PYTHON
else
    test_python=${HOME}/.venvs/bopos/bin/python
fi

if [ ! -x "$test_python" ]; then
    echo "bopOS test Python is not executable: $test_python" >&2
    echo "Set BOPOS_PYTHON to a project Python, or create the documented venv:" >&2
    echo "  python3 -m venv ~/.venvs/bopos" >&2
    echo "  ~/.venvs/bopos/bin/pip install -r dashboard/requirements.txt pyOSC3" >&2
    exit 2
fi

cd "$repo_dir" || exit 2
export PYTHONDONTWRITEBYTECODE=1

run_fast() {
    echo "=== fast: browser-free living suite ==="
    "$test_python" -m unittest discover -s tests -p 'test_*.py'
}

run_browser() {
    browser_names=()
    browser_results=()
    browser_status=0

    for verifier in tests/verify_*.py; do
        [ -f "$verifier" ] || continue
        name=${verifier#tests/}
        echo
        echo "=== browser: $name ==="
        if "$test_python" "$verifier"; then
            result=PASS
        else
            result=FAIL
            browser_status=1
        fi
        browser_names[${#browser_names[@]}]=$name
        browser_results[${#browser_results[@]}]=$result
    done

    echo
    echo "=== browser summary ==="
    if [ "${#browser_names[@]}" -eq 0 ]; then
        echo "No tests/verify_*.py files found."
    else
        index=0
        while [ "$index" -lt "${#browser_names[@]}" ]; do
            printf '%s %s\n' \
                "${browser_results[$index]}" "${browser_names[$index]}"
            index=$((index + 1))
        done
    fi
    return "$browser_status"
}

case "$tier" in
    fast)
        run_fast
        ;;
    browser)
        run_browser
        ;;
    all)
        overall_status=0
        run_fast || overall_status=1
        run_browser || overall_status=1
        exit "$overall_status"
        ;;
esac
