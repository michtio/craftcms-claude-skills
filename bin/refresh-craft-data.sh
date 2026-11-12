#!/bin/sh
# Refreshes everything the pack derives from Craft's 5.x CHANGELOG, in one go.
# Run at every pack release (bin/release.sh reminds you), then review the diff.
#
#   1. fetches craftcms/cms CHANGELOG.md (5.x branch) with gh
#   2. rebuilds the symbol map the tag linter uses (bin/data/craft-symbols.tsv,
#      bin/data/craft-releases.txt)
#   3. sets the minimum safe version in bin/craft-version.sh to the latest
#      release with a ### Security section; the "set" date changes only when the
#      floor does, so a second run makes no changes
#   4. regenerates skills/craftcms/references/version-table.md from the tags
#   5. syncs scripts/craft-version.sh into every skill and, when the floor
#      moved, rewrites the golden outputs of bin/test-craft-version.sh
#
#   sh bin/refresh-craft-data.sh [path/to/CHANGELOG.md]   # optional local copy
#
# Requires: gh (authenticated) unless a CHANGELOG path is given, python3.

set -eu

repo=$(cd "$(dirname "$0")/.." && pwd)
cd "$repo"

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

if [ $# -ge 1 ]; then
    cp "$1" "$tmp/CHANGELOG.md"
else
    gh api -H 'Accept: application/vnd.github.raw' 'repos/craftcms/cms/contents/CHANGELOG.md?ref=5.x' > "$tmp/CHANGELOG.md"
fi
grep -q '^## 5\.' "$tmp/CHANGELOG.md" || { echo "CHANGELOG fetch looks wrong" >&2; exit 1; }

python3 bin/craft_tags.py map --changelog "$tmp/CHANGELOG.md"

floor_line=$(python3 bin/craft_tags.py floor --changelog "$tmp/CHANGELOG.md")
new_floor=$(printf '%s' "$floor_line" | cut -f1)
new_advisories=$(printf '%s' "$floor_line" | cut -f2)
old_floor=$(sed -n 's/^CRAFT_SAFE_FLOOR="\(.*\)"$/\1/p' bin/craft-version.sh)

floor_moved=0
if [ "$new_floor" != "$old_floor" ]; then
    today=$(date +%Y-%m-%d)
    sed -i.bak \
        -e "s/^CRAFT_SAFE_FLOOR=\".*\"$/CRAFT_SAFE_FLOOR=\"$new_floor\"/" \
        -e "s/^CRAFT_SAFE_FLOOR_SET=\".*\"$/CRAFT_SAFE_FLOOR_SET=\"$today\"/" \
        -e "s/^CRAFT_SAFE_FLOOR_ADVISORIES=\".*\"$/CRAFT_SAFE_FLOOR_ADVISORIES=\"$new_advisories\"/" \
        bin/craft-version.sh
    rm -f bin/craft-version.sh.bak
    floor_moved=1
    echo "minimum safe version: $old_floor -> $new_floor ($new_advisories)"
else
    echo "minimum safe version unchanged: $old_floor"
fi

python3 bin/craft_tags.py table
sh bin/sync-version-script.sh

if [ "$floor_moved" -eq 1 ]; then
    sh bin/test-craft-version.sh --update >/dev/null
    echo "golden outputs rewritten for the new floor: review evals/fixtures/version/*/expected.txt in the diff"
fi
sh bin/test-craft-version.sh

echo "done; review: git diff -- bin/ skills/craftcms/references/version-table.md evals/fixtures/version"
