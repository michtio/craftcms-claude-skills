#!/bin/sh
# Copies bin/craft-version.sh into every skill as scripts/craft-version.sh.
#
# Each skill needs its own copy: install.sh symlinks skills one directory at a
# time, so a skill can only rely on files inside its own folder
# (${CLAUDE_SKILL_DIR}). bin/validate-skills.sh fails when a copy drifts.
#
#   sh bin/sync-version-script.sh

repo=$(cd "$(dirname "$0")/.." && pwd)
for skill_dir in "$repo"/skills/*/; do
    mkdir -p "$skill_dir/scripts"
    cp "$repo/bin/craft-version.sh" "$skill_dir/scripts/craft-version.sh"
done
echo "synced craft-version.sh into $(ls -d "$repo"/skills/*/ | wc -l | tr -d ' ') skills"
