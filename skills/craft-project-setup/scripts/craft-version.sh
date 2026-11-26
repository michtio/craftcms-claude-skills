#!/bin/sh
# Craft version detection for craftcms-claude-skills.
#
# Prints the Craft CMS version of the project in the current directory (or a
# parent, or a cms/ subfolder) plus the rules for using version-tagged skill
# content. Prints nothing outside Craft projects. Read-only, no network, POSIX
# sh with grep/sed/awk only, and always exits 0: a failing command would abort
# the skill load that runs it.
#
# Runs from the plugin's SessionStart hook (hooks/hooks.json) and from the
# `!` line in every SKILL.md (copies in skills/*/scripts/, kept identical by
# bin/sync-version-script.sh).
#
# The three CRAFT_SAFE_FLOOR values are written by bin/refresh-craft-data.sh;
# don't edit them by hand.

CRAFT_SAFE_FLOOR="5.12.3"
CRAFT_SAFE_FLOOR_SET="2026-11-26"
CRAFT_SAFE_FLOOR_ADVISORIES="see CHANGELOG"

main() {
    root=$(find_root) || return 0

    composer_json="$root/composer.json"
    lock="$root/composer.lock"

    if is_plugin "$composer_json"; then
        report_plugin "$composer_json"
    else
        report_site "$composer_json" "$lock" "$root"
    fi
}

# Directory holding a composer.json that requires craftcms/cms (or is
# craftcms/cms-adjacent): the current directory, its cms/ subfolder, or up to
# three parents (and their cms/ subfolders).
find_root() {
    dir=$(pwd 2>/dev/null) || return 1
    depth=0
    while [ "$depth" -le 3 ] && [ -n "$dir" ]; do
        for candidate in "$dir" "$dir/cms"; do
            if [ -f "$candidate/composer.json" ] && mentions_craft "$candidate"; then
                printf '%s\n' "$candidate"
                return 0
            fi
        done
        [ "$dir" = "/" ] && break
        dir=$(dirname "$dir")
        depth=$((depth + 1))
    done
    return 1
}

mentions_craft() {
    grep -q '"craftcms/cms"' "$1/composer.json" 2>/dev/null && return 0
    [ -f "$1/composer.lock" ] && grep -q '"name": *"craftcms/cms"' "$1/composer.lock" 2>/dev/null
}

is_plugin() {
    grep -q '"type"[[:space:]]*:[[:space:]]*"craft-plugin"' "$1" 2>/dev/null
}

# Version of craftcms/cms in composer.lock: the first "version" after its
# "name" entry.
lock_version() {
    [ -f "$1" ] || return 0
    awk '
        /"name"[[:space:]]*:[[:space:]]*"craftcms\/cms"/ { found = 1; next }
        found && /"version"[[:space:]]*:/ {
            sub(/^[^:]*:[[:space:]]*"/, ""); sub(/".*$/, ""); sub(/^v/, "")
            print; exit
        }
        found && /^[[:space:]]*}/ { exit }
    ' "$1" 2>/dev/null
}

# Version actually installed: vendor/craftcms/cms/src/config/app.php 'version'.
vendor_version() {
    app="$1/vendor/craftcms/cms/src/config/app.php"
    [ -f "$app" ] || return 0
    sed -n "s/^[[:space:]]*'version'[[:space:]]*=>[[:space:]]*'\([^']*\)'.*/\1/p" "$app" 2>/dev/null | head -n 1
}

# The craftcms/cms constraint string from composer.json.
constraint() {
    sed -n 's/.*"craftcms\/cms"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$1" 2>/dev/null | head -n 1
}

# Lowest version a constraint allows: the smallest version number across its
# | / || alternatives (^5.6.0 -> 5.6.0, ^4.0|^5.0 -> 4.0.0, 5.* -> 5.0.0).
lowest_allowed() {
    printf '%s\n' "$1" | tr '|' '\n' | awk '
        {
            if (match($0, /[0-9]+(\.[0-9]+)*/)) {
                v = substr($0, RSTART, RLENGTH)
                n = split(v, p, ".")
                for (i = n + 1; i <= 3; i++) p[i] = 0
                key = sprintf("%06d%06d%06d", p[1], p[2], p[3])
                if (best == "" || key < best) { best = key; out = p[1] "." p[2] "." p[3] }
            }
        }
        END { if (out != "") print out }
    '
}

is_release() {
    printf '%s' "$1" | grep -Eq '^[0-9]+\.[0-9]+(\.[0-9]+){0,2}$'
}

# 0 when $1 < $2 (dotted numeric versions, up to four parts).
version_lt() {
    awk -v a="$1" -v b="$2" 'BEGIN {
        na = split(a, x, "."); nb = split(b, y, ".")
        for (i = 1; i <= 4; i++) {
            xi = (i <= na) ? x[i] + 0 : 0; yi = (i <= nb) ? y[i] + 0 : 0
            if (xi < yi) exit 0
            if (xi > yi) exit 1
        }
        exit 1
    }'
}

major() {
    printf '%s' "$1" | sed 's/\..*//'
}

eol_notice() {
    echo "This pack targets Craft 5 (5.0-5.12.x). Craft $1 is end of life (Craft 4 security support ended 2026-04-30): say so once, and treat Craft 5 guidance as needing an upgrade first."
}

rules() {
    echo "Version rules: tags such as [5.10+], [5.11.4+], [changed 5.12], [deprecated 5.12], [removed 5.12] and [<plugin> 5.1+] mark version-specific content in these skills. Compare every tag with the version above before using what it marks. When the project is below a tag, say which version the feature needs and how to upgrade, and give the alternative listed after \"Before 5.x:\" when there is one."
}

report_site() {
    composer_json=$1; lock=$2; root=$3
    locked=$(lock_version "$lock")
    installed=$(vendor_version "$root")

    if [ -z "$locked" ] && [ -z "$installed" ]; then
        c=$(constraint "$composer_json")
        echo "Craft project (site): Craft version unknown (no readable composer.lock${c:+; composer.json requires craftcms/cms $c}). Check composer.lock or ask before version-specific advice."
        return 0
    fi

    if [ -n "$locked" ] && [ -n "$installed" ] && [ "$locked" != "$installed" ]; then
        echo "Craft project (site): craftcms/cms $locked in composer.lock, but $installed installed in vendor/."
        echo "Drift: vendor/ does not match composer.lock; run \`ddev composer install\`. Until then, $installed is what runs locally and $locked is what deploys."
        running=$installed
    else
        running=${installed:-$locked}
        echo "Craft project (site): craftcms/cms $running."
    fi

    if ! is_release "$running"; then
        echo "That is not a tagged release, so version tags can't be compared reliably; ask which release it tracks."
        return 0
    fi

    m=$(major "$running")
    if [ "$m" -lt 5 ] 2>/dev/null; then
        eol_notice "$m"
        return 0
    fi

    lowest=$running
    if [ -n "$locked" ] && is_release "$locked" && version_lt "$locked" "$lowest"; then
        lowest=$locked
    fi
    if version_lt "$lowest" "$CRAFT_SAFE_FLOOR"; then
        echo "Security: $lowest is below the minimum safe Craft version, $CRAFT_SAFE_FLOOR (set $CRAFT_SAFE_FLOOR_SET; $CRAFT_SAFE_FLOOR_ADVISORIES). Craft does not backport security fixes to older minors. In every answer about this site, warn once: upgrade to $CRAFT_SAFE_FLOOR or later, run \`ddev composer audit\` (it covers plugins too), and check the security fixes in Craft's CHANGELOG, because advisories are published 30 days after the fix."
    fi

    rules
}

report_plugin() {
    composer_json=$1
    c=$(constraint "$composer_json")
    if [ -z "$c" ]; then
        echo "Craft plugin: no craftcms/cms requirement found in composer.json. Ask which Craft versions it supports before version-specific advice."
        return 0
    fi
    lowest=$(lowest_allowed "$c")
    if [ -z "$lowest" ]; then
        echo "Craft plugin: craftcms/cms constraint \"$c\" has no readable lowest version. Ask which Craft versions it supports."
        return 0
    fi

    echo "Craft plugin: requires craftcms/cms \"$c\", so the lowest supported Craft version is $lowest."
    if [ "$(major "$lowest")" -lt 5 ] 2>/dev/null; then
        echo "The constraint still allows Craft $(major "$lowest"). This pack covers Craft 5 only, and Craft 4 is end of life (security support ended 2026-04-30); code for Craft 5 and suggest dropping the older major from the constraint."
        lowest="5.0.0"
    fi
    echo "Any Craft API tagged above $lowest needs either a constraint bump (e.g. \"craftcms/cms\": \"^5.10.0\") or a runtime guard (version_compare(Craft::\$app->getVersion(), '5.10.0', '>=')); say which and why."
    rules
}

main 2>/dev/null
exit 0
