#!/usr/bin/env bash
#
# Craft CMS Claude Skills — Uninstaller
#
# Removes symlinks created by install.sh. Only removes symlinks that point
# back to this repository — manually created files are never touched.
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_DIR="${HOME}/.claude"
SKILLS_DIR="${CLAUDE_DIR}/skills"
AGENTS_DIR="${CLAUDE_DIR}/agents"

GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m'

echo ""
echo "🔧 Craft CMS Claude Skills — Uninstaller"
echo "========================================="
echo ""

removed=0
skipped=0

# =========================================================================
# Skills
# =========================================================================

echo "Skills:"
for skill_dir in "${SCRIPT_DIR}/skills/"*/; do
    [ -d "${skill_dir}" ] || continue
    skill_name="$(basename "${skill_dir}")"
    target="${SKILLS_DIR}/${skill_name}"

    if [ -L "${target}" ] && [ "$(readlink "${target}")" = "${skill_dir}" ]; then
        rm "${target}"
        echo -e "  ${GREEN}✓ Removed ${skill_name}${NC}"
        ((removed++))
    elif [ -e "${target}" ]; then
        echo -e "  ${YELLOW}⚠ ${skill_name}${NC} — not a symlink to this repo, skipping"
        ((skipped++))
    fi
done

echo ""

# =========================================================================
# Agents
# =========================================================================

echo "Agents:"
for agent_file in "${SCRIPT_DIR}/agents/"*.md; do
    [ -f "${agent_file}" ] || continue
    agent_name="$(basename "${agent_file}")"
    target="${AGENTS_DIR}/${agent_name}"

    if [ -L "${target}" ] && [ "$(readlink "${target}")" = "${agent_file}" ]; then
        rm "${target}"
        echo -e "  ${GREEN}✓ Removed ${agent_name}${NC}"
        ((removed++))
    elif [ -e "${target}" ]; then
        echo -e "  ${YELLOW}⚠ ${agent_name}${NC} — not a symlink to this repo, skipping"
        ((skipped++))
    fi
done

echo ""
echo "========================================="
echo -e "  ${GREEN}Removed:${NC} ${removed}"
echo -e "  ${YELLOW}Skipped:${NC} ${skipped}"
echo ""
echo "Done. Skills and agents have been unlinked."
echo "The repository at ${SCRIPT_DIR} has not been deleted."
