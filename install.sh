#!/usr/bin/env bash
#
# Craft CMS Claude Skills — Installer
#
# Symlinks skills and agents into ~/.claude/ without overwriting existing files.
# Run from the repository root: bash install.sh
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_DIR="${HOME}/.claude"
SKILLS_DIR="${CLAUDE_DIR}/skills"
AGENTS_DIR="${CLAUDE_DIR}/agents"

GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m'

echo ""
echo "🔧 Craft CMS Claude Skills — Installer"
echo "========================================="
echo ""

# Ensure target directories exist
mkdir -p "${SKILLS_DIR}"
mkdir -p "${AGENTS_DIR}"

# Track counts
linked=0
skipped=0

# =========================================================================
# Skills
# =========================================================================

echo "Skills:"
for skill_dir in "${SCRIPT_DIR}/skills/"*/; do
    [ -d "${skill_dir}" ] || continue
    skill_name="$(basename "${skill_dir}")"
    target="${SKILLS_DIR}/${skill_name}"

    if [ -e "${target}" ] || [ -L "${target}" ]; then
        echo -e "  ${YELLOW}⚠ ${skill_name}${NC} — already exists, skipping"
        ((skipped++))
    else
        ln -s "${skill_dir}" "${target}"
        echo -e "  ${GREEN}✓ ${skill_name}${NC}"
        ((linked++))
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

    if [ -e "${target}" ] || [ -L "${target}" ]; then
        echo -e "  ${YELLOW}⚠ ${agent_name}${NC} — already exists, skipping"
        ((skipped++))
    else
        ln -s "${agent_file}" "${target}"
        echo -e "  ${GREEN}✓ ${agent_name}${NC}"
        ((linked++))
    fi
done

echo ""
echo "========================================="
echo -e "  ${GREEN}Linked:${NC}  ${linked}"
echo -e "  ${YELLOW}Skipped:${NC} ${skipped}"
echo ""

if [ ${skipped} -gt 0 ]; then
    echo "Skipped items already exist in ~/.claude/. To force reinstall,"
    echo "run uninstall.sh first, then install.sh again."
    echo ""
fi

echo "Project template available at:"
echo "  ${SCRIPT_DIR}/project-template/"
echo ""
echo "Reference CLAUDE.md available at:"
echo "  ${SCRIPT_DIR}/reference/CLAUDE.md"
echo ""
echo "Done."
