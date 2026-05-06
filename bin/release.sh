#!/usr/bin/env bash
#
# Bump the version across every manifest site in one pass, plus stamp the
# CHANGELOG date for the matching heading.
#
#   bin/release.sh <version>
#
#   bin/release.sh 1.3.1
#
# This script ONLY edits files. It does NOT commit, tag, or push — review
# the diff yourself before publishing. The companion workflow at
# `.github/workflows/release-validation.yml` will fail the run if any of
# these sites disagree with the pushed tag.
#
# Sites updated:
#   - .claude-plugin/plugin.json         → .version
#   - .claude-plugin/marketplace.json    → .metadata.version
#   - .claude-plugin/marketplace.json    → .plugins[0].version
#   - CHANGELOG.md                       → date stamp on the matching ## X.Y.Z heading
#
# Requires: jq (every dev box, every CI runner has it).

set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "Usage: bin/release.sh <version>" >&2
  echo "Example: bin/release.sh 1.3.1" >&2
  exit 64
fi

VERSION="$1"

# Validate semver shape — major.minor.patch with optional -prerelease.
if ! [[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+(-[A-Za-z0-9.-]+)?$ ]]; then
  echo "error: '$VERSION' is not a valid semver. Expected MAJOR.MINOR.PATCH or MAJOR.MINOR.PATCH-prerelease." >&2
  exit 64
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PLUGIN_JSON="$REPO_ROOT/.claude-plugin/plugin.json"
MARKETPLACE_JSON="$REPO_ROOT/.claude-plugin/marketplace.json"
CHANGELOG="$REPO_ROOT/CHANGELOG.md"
TODAY="$(date +%Y-%m-%d)"

bump_json() {
  local file="$1"
  local jq_expr="$2"
  local tmp
  tmp="$(mktemp)"
  jq "$jq_expr" "$file" > "$tmp"
  mv "$tmp" "$file"
}

echo "Bumping plugin.json → $VERSION"
bump_json "$PLUGIN_JSON" ".version = \"$VERSION\""

echo "Bumping marketplace.json metadata.version → $VERSION"
bump_json "$MARKETPLACE_JSON" ".metadata.version = \"$VERSION\""

echo "Bumping marketplace.json plugins[0].version → $VERSION"
bump_json "$MARKETPLACE_JSON" ".plugins[0].version = \"$VERSION\""

echo "Stamping CHANGELOG.md heading for $VERSION → $TODAY"
# Replace the existing "## X.Y.Z ..." heading for this version with today's date.
# Awk match anchors on `^## VERSION` followed by whitespace, so `1.3.10` won't
# false-match on a `1.3.1` search. If no entry exists for this version yet, we
# warn — that's a signal the dev forgot to write the CHANGELOG entry.
if grep -qE "^## ${VERSION}[[:space:]]" "$CHANGELOG"; then
  tmp="$(mktemp)"
  awk -v ver="$VERSION" -v today="$TODAY" '
    $0 ~ "^## " ver "[ \t]" { print "## " ver " -- " today; next }
    { print }
  ' "$CHANGELOG" > "$tmp"
  mv "$tmp" "$CHANGELOG"
else
  echo "  warn: no '## ${VERSION}' heading found in CHANGELOG.md — add the entry before tagging." >&2
fi

echo
echo "Done. Review the diff:"
echo "  git diff -- .claude-plugin/ CHANGELOG.md"
echo
echo "Then commit, tag, push:"
echo "  git add .claude-plugin/ CHANGELOG.md"
echo "  git commit -m 'chore(release): v$VERSION'"
echo "  git tag -a v$VERSION -m 'v$VERSION'"
echo "  git push origin main v$VERSION"
