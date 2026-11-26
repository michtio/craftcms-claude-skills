#!/bin/sh
# Every deterministic quality gate of the pack, in one command. No model calls,
# no network. CI runs exactly this; run it before every commit that touches
# skills/, agents/, bin/ or evals/.
#
#   sh bin/check.sh
#
# Gates (each prints one line; the run fails if any fails):
#   frontmatter       bin/validate-skills.sh (YAML, listing cap, version-script wiring)
#   version-script    bin/test-craft-version.sh golden outputs (sh)
#   tag-lint          version tags in skills/, plus the linter and floor self-tests
#   agent-budget      each agent file + its preloaded SKILL.md files <= 48 KB (bin/agent_budget.py)
#   contents          references > 30 KB start with a current line-numbered Contents block
#   symbols           every Craft symbol named in skills/ exists in craftcms/cms (bin/craft_source.py)
#   tables            MCP tool catalogue and config defaults match the source
#   facts             every behaviour case's facts hold (evals/facts_check.py)
#   routing           lexical routing vs evals/routing-baseline.json (evals/lexical_route.py)
#   release-evals     the release-time runner stops at a usage limit (stub claude, no model)
# Each check that reads a fixture must also FAIL on its bad fixture; those
# negative tests run here too, so a check that silently stops checking fails.
#
# Requires: python3 (3.9+), ruby (validate-skills.sh), POSIX sh.

set -u

repo=$(cd "$(dirname "$0")/.." && pwd)
cd "$repo" || exit 2

log=$(mktemp)
trap 'rm -f "$log"' EXIT
failed=0

# gate NAME COMMAND...: run, print ok/FAIL, show output on failure.
gate() {
    name=$1
    shift
    if "$@" >"$log" 2>&1; then
        printf 'ok    %s\n' "$name"
    else
        printf 'FAIL  %s\n' "$name"
        sed 's/^/      /' "$log"
        failed=1
    fi
}

# must_fail NAME COMMAND...: the command must exit non-zero (a self-test).
must_fail() {
    name=$1
    shift
    if "$@" >"$log" 2>&1; then
        printf 'FAIL  %s (expected a failure, got none)\n' "$name"
        failed=1
    else
        printf 'ok    %s\n' "$name"
    fi
}

# grep_ok NAME PATTERN COMMAND...: the command's output must match PATTERN.
grep_ok() {
    name=$1
    pattern=$2
    shift 2
    "$@" >"$log" 2>&1
    if grep -q "$pattern" "$log"; then
        printf 'ok    %s\n' "$name"
    else
        printf 'FAIL  %s (output did not match %s)\n' "$name" "$pattern"
        sed 's/^/      /' "$log"
        failed=1
    fi
}

gate      "frontmatter"                    bash bin/validate-skills.sh
gate      "version-script golden outputs"  sh bin/test-craft-version.sh
gate      "tag-lint skills/"               python3 bin/craft_tags.py lint skills
must_fail "tag-lint self-test (untagged craft\\filters\\Cors)" python3 bin/craft_tags.py lint evals/fixtures/tags/untagged-cors.md
grep_ok   "tag-lint self-test (3 invalid tags)" '^3 finding(s)' python3 bin/craft_tags.py lint evals/fixtures/tags/grammar.md
grep_ok   "floor self-test (patch-release security bullets)" '^5\.12\.3	' python3 bin/craft_tags.py floor --changelog evals/fixtures/tags/changelog-floor.md
gate      "agent startup budget (48 KB)" python3 bin/agent_budget.py
gate      "contents blocks (references > 30 KB)" python3 bin/contents.py --check
gate      "symbols skills/"                python3 bin/craft_source.py verify
must_fail "symbols self-test (craft\\services\\Mcp::getTools())" python3 bin/craft_source.py verify evals/fixtures/symbols/bad-symbol.md
gate      "tables (MCP catalogue, config defaults)" python3 bin/craft_source.py tables
must_fail "tables self-test (project_config_status at read)" python3 bin/craft_source.py tables --catalogue evals/fixtures/tables/catalogue-wrong-scope.md evals/fixtures/symbols
gate      "facts (behaviour cases)"        python3 evals/facts_check.py
gate      "routing (lexical baseline)"     python3 evals/lexical_route.py
must_fail "routing self-test (flooded listing)" python3 evals/lexical_route.py --self-test
grep_ok   "release-evals self-test (stops at a usage limit, stub claude)" 'errors: 1 (1 usage limit).*model calls: 1$' \
          python3 evals/release_evals.py --assume-changed skills/craft-mcp/references/oauth-server.md \
          --claude-bin evals/fixtures/stub-claude/claude-limit --workers 1 --no-cache

if [ "$failed" -ne 0 ]; then
    echo "check.sh: FAILED"
    exit 1
fi
echo "check.sh: all gates passed"
