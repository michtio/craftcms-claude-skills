#!/bin/sh
# Golden-output tests for bin/craft-version.sh.
#
# Each folder in evals/fixtures/version/ is a fake project. The script runs in
# that folder (or in the subfolder named by its .run_from file) under every
# POSIX shell available, must exit 0, and must print exactly expected.txt
# (an empty expected.txt means "prints nothing").
#
# Usage:
#   sh bin/test-craft-version.sh            # check
#   sh bin/test-craft-version.sh --update   # rewrite expected.txt files (review the diff!)

repo=$(cd "$(dirname "$0")/.." && pwd)
script="$repo/bin/craft-version.sh"
fixtures="$repo/evals/fixtures/version"
update=0
[ "$1" = "--update" ] && update=1

shells=""
for s in sh dash bash; do
    command -v "$s" >/dev/null 2>&1 && shells="$shells $s"
done

fail=0
count=0
for dir in "$fixtures"/*/; do
    name=$(basename "$dir")
    run_dir="$dir"
    [ -f "$dir/.run_from" ] && run_dir="$dir/$(cat "$dir/.run_from")"
    expected="$dir/expected.txt"

    for shell in $shells; do
        flag=""
        [ "$shell" = "bash" ] && flag="--posix"
        actual=$(cd "$run_dir" && $shell $flag "$script"; echo "exit=$?")

        if [ "$update" -eq 1 ] && [ "$shell" = "sh" ]; then
            printf '%s\n' "$actual" | sed '$d' > "$expected"
        fi

        count=$((count + 1))
        want=$(cat "$expected" 2>/dev/null; echo "exit=0")
        if [ "$actual" != "$want" ]; then
            fail=$((fail + 1))
            echo "FAIL $name ($shell)"
            printf '%s\n' "$want" > /tmp/craft-version-want.$$
            printf '%s\n' "$actual" > /tmp/craft-version-got.$$
            diff /tmp/craft-version-want.$$ /tmp/craft-version-got.$$ | sed 's/^/    /'
            rm -f /tmp/craft-version-want.$$ /tmp/craft-version-got.$$
        fi
    done
done

echo "$((count - fail))/$count passed (shells:$shells)"
[ "$fail" -eq 0 ]
