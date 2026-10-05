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
#   - .claude-plugin/plugin.json                → .version
#   - .claude-plugin/marketplace.json           → .metadata.version
#   - .claude-plugin/marketplace.json           → .plugins[0].version
#   - skills/craft-project-setup/SKILL.md       → five user-facing version strings
#                                                 (sponsorship box, attribution example,
#                                                  HTML-comment example, drift example,
#                                                  diff-table example)
#   - skills/craft-project-setup/SKILL.md       → sponsorship box skill/reference-file/agent
#                                                 counts, recomputed from disk every run
#                                                 (not just bumped — these drift independently
#                                                 of the version number)
#   - CHANGELOG.md                              → date stamp on the matching ## X.Y.Z heading
#
# Note on the sponsorship ASCII box: trailing whitespace pads the right border to a
# fixed width. Patch/minor bumps that stay the same character width (e.g. 1.4.6 → 1.4.7)
# preserve alignment. A bump that changes width (e.g. 1.4.9 → 1.4.10) will push the right
# border by one character — fix manually after release if it crosses a width boundary.
# The skill/reference/agent counts line is rewritten and re-padded to the box's own
# width on every run (measured in Unicode characters via `perl -CSD`, not bytes, since
# the border uses multi-byte box-drawing characters) — see the "Rewrite the banner
# counts" step below. If that line's text ever grows wider than the box itself, the
# script errors out rather than silently breaking the box.
#
# Versioning policy:
#   This package follows its own semantic versioning, driven by the pack's own
#   content — it is NOT pinned to Craft's minor releases. Patch = accuracy
#   fixes/small updates; minor = new skills, new plugin references, significant
#   content additions; major = Craft's next major (5.x → 6.x, where APIs break)
#   or a major pack reorganization. The pack targets Craft 5 at its latest
#   minor; behaviour specific to a Craft minor is annotated inline so one line
#   serves any Craft 5 minor. Development happens on `main`; the `1.4.x` branch
#   is a frozen Craft 5.9 snapshot. Run this script on the branch being released
#   (e.g. `1.4.x` for a v1.4.x tag, `main` for the latest line). See README →
#   Versioning for the full policy.
#
# Requires: jq, perl (every dev box, every CI runner has both).

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

# Refuse to bump anything while a SKILL.md frontmatter is invalid or over the
# spec/listing limits — a broken frontmatter ships silently otherwise.
echo "Validating SKILL.md frontmatter"
if ! bash "$REPO_ROOT/bin/validate-skills.sh"; then
  echo "error: fix the SKILL.md frontmatter above before releasing." >&2
  exit 65
fi
echo

PLUGIN_JSON="$REPO_ROOT/.claude-plugin/plugin.json"
MARKETPLACE_JSON="$REPO_ROOT/.claude-plugin/marketplace.json"
SETUP_SKILL="$REPO_ROOT/skills/craft-project-setup/SKILL.md"
CHANGELOG="$REPO_ROOT/CHANGELOG.md"
TODAY="$(date +%Y-%m-%d)"

# Capture the previous version from plugin.json BEFORE the bump — needed to substitute
# the user-facing version strings in craft-project-setup/SKILL.md, which the manifests
# don't carry.
OLD_VERSION="$(jq -r '.version' "$PLUGIN_JSON")"
if [ -z "$OLD_VERSION" ] || [ "$OLD_VERSION" = "null" ]; then
  echo "error: could not read current .version from $PLUGIN_JSON" >&2
  exit 70
fi

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

# Bump the five user-facing version strings in craft-project-setup/SKILL.md.
# All five contain $OLD_VERSION as a substring in one of three forms:
#   v$OLD            — sponsorship box, HTML-comment example, diff-table example
#   "$OLD"           — composer.json attribution example
#   `$OLD`           — drift-detection example (backticked)
# Each form is distinct enough that the three sed expressions won't match unrelated content.
if [ -f "$SETUP_SKILL" ]; then
  if grep -qE "(v|\"|\`)${OLD_VERSION}(\"|\`| )" "$SETUP_SKILL"; then
    echo "Bumping craft-project-setup/SKILL.md version markers → $VERSION (was $OLD_VERSION)"
    tmp="$(mktemp)"
    sed -e "s|v${OLD_VERSION}|v${VERSION}|g" \
        -e "s|\"${OLD_VERSION}\"|\"${VERSION}\"|g" \
        -e "s|\`${OLD_VERSION}\`|\`${VERSION}\`|g" \
        "$SETUP_SKILL" > "$tmp"
    mv "$tmp" "$SETUP_SKILL"
  else
    echo "  warn: craft-project-setup/SKILL.md has no markers matching $OLD_VERSION — skipping (already drifted?)" >&2
  fi
else
  echo "  warn: $SETUP_SKILL not found — skipping" >&2
fi

# Recompute the "N skills · N reference files · N agents" banner line in the
# same sponsorship box. These counts drift independently of the version number
# — a skill or reference file can be added/removed without a version bump
# touching this line, and a version bump shouldn't require remembering to
# update it by hand. Always recompute from disk rather than trusting the old
# numbers.
if [ -f "$SETUP_SKILL" ]; then
  SKILL_COUNT="$(find "$REPO_ROOT/skills" -mindepth 2 -maxdepth 2 -type f -name 'SKILL.md' | wc -l | tr -d '[:space:]')"
  REF_COUNT="$(find "$REPO_ROOT/skills" -type f -name '*.md' -path '*/references/*' | wc -l | tr -d '[:space:]')"
  AGENT_COUNT="$(find "$REPO_ROOT/agents" -maxdepth 1 -type f -name '*.md' | wc -l | tr -d '[:space:]')"

  echo "Recomputing craft-project-setup/SKILL.md banner counts → ${SKILL_COUNT} skills · ${REF_COUNT} reference files · ${AGENT_COUNT} agents"

  PERL_SCRIPT="$(mktemp)"
  cat > "$PERL_SCRIPT" <<'PERL_EOF'
use utf8;
use strict;
use warnings;

# Width and content are measured in Unicode characters (via -CSD), not bytes —
# the box border and the │ sides are multi-byte UTF-8 box-drawing characters,
# and a byte count would misjudge the padding needed to keep the right border
# aligned.
my $file = shift @ARGV;

open(my $fh, "<:encoding(UTF-8)", $file) or die "release.sh: cannot open $file: $!\n";
local $/;
my $content = <$fh>;
close $fh;

my ($border) = $content =~ /^(\x{250C}\x{2500}+\x{2510})$/m;
die "release.sh: could not find the banner box's top border in $file — skipping count rewrite, fix manually\n"
    unless defined $border;
my $inner_width = length($border) - 2; # minus the two corner characters

my $skills = $ENV{SKILL_COUNT};
my $refs   = $ENV{REF_COUNT};
my $agents = $ENV{AGENT_COUNT};

my $text = "   ${skills} skills \x{B7} ${refs} reference files \x{B7} ${agents} agents";
die "release.sh: new banner text ($skills skills / $refs reference files / $agents agents) is wider "
  . "than the box (inner width $inner_width) — widen the box manually in $file\n"
    if length($text) > $inner_width;
$text .= (" " x ($inner_width - length($text)));
my $new_line = "\x{2502}${text}\x{2502}";

my $replacements = ($content =~
    s/^\x{2502}\s*\d+\s+skills?\s+\x{B7}\s+\d+\s+reference\s+files?\s+\x{B7}\s+\d+\s+agents?\s*\x{2502}$/$new_line/m);
die "release.sh: could not find the skills/reference-files/agents banner line in $file — add it back manually\n"
    unless $replacements;

open(my $out, ">:encoding(UTF-8)", $file) or die "release.sh: cannot write $file: $!\n";
print $out $content;
close $out;
PERL_EOF

  SKILL_COUNT="$SKILL_COUNT" REF_COUNT="$REF_COUNT" AGENT_COUNT="$AGENT_COUNT" \
    perl -CSD "$PERL_SCRIPT" "$SETUP_SKILL"
  rm -f "$PERL_SCRIPT"
fi

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

CURRENT_BRANCH="$(git -C "$REPO_ROOT" rev-parse --abbrev-ref HEAD)"

echo
echo "Done. Review the diff:"
echo "  git diff -- .claude-plugin/ CHANGELOG.md"
echo
echo "Then commit, tag, push (on branch ${CURRENT_BRANCH}):"
echo "  git add .claude-plugin/ CHANGELOG.md"
echo "  git commit -m 'chore(release): v$VERSION'"
echo "  git tag -a v$VERSION -m 'v$VERSION'"
echo "  git push origin ${CURRENT_BRANCH} v$VERSION"
