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
#   agent-budget      each agent file + its preloaded SKILL.md files <= 48 KB; checker <= 16 KB,
#                     deep reviewer preloads nothing, no reviewer on effort xhigh, declared agent caps (bin/agent_budget.py)
#   contents          references > 30 KB start with a current line-numbered Contents block
#   symbols           every Craft symbol named in skills/ exists in craftcms/cms (bin/craft_source.py)
#   tables            MCP tool catalogue and config defaults match the source
#   facts             every behaviour case's facts hold (evals/facts_check.py)
#   routing           lexical routing vs evals/routing-baseline.json (evals/lexical_route.py)
#   handback          the hand-back checker (bin/handback_check.py) with must-fail fixtures
#   run-builder       bin/run_builder.py passes the builder's exit code through and kills it at the timeout
#   profile, neutral  profile schema checker and the neutral-wording check, with must-fail fixtures
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
gate      "agent startup budget (48 KB; checker 16 KB; no xhigh reviewers; agent caps <= 5)" python3 bin/agent_budget.py
must_fail "agent gate self-test (xhigh reviewer)" python3 bin/agent_budget.py --agents evals/fixtures/agents/xhigh-reviewer
must_fail "agent cap self-test (Agent tool, no cap line)" python3 bin/agent_budget.py --agents evals/fixtures/agents/no-cap
must_fail "agent cap self-test (cap 6)" python3 bin/agent_budget.py --agents evals/fixtures/agents/cap-6
must_fail "agent cap self-test (checker with Agent)" python3 bin/agent_budget.py --agents evals/fixtures/agents/checker-with-agent
gate      "hand-back check (complete hand-back)" python3 bin/handback_check.py --brief evals/fixtures/handback/brief.md evals/fixtures/handback/complete.md
must_fail "hand-back self-test (no working-tree lock line)" python3 bin/handback_check.py --brief evals/fixtures/handback/brief.md evals/fixtures/handback/missing-lock-line.md
must_fail "hand-back self-test (no Gate flow line)" python3 bin/handback_check.py --brief evals/fixtures/handback/brief.md evals/fixtures/handback/missing-gate-flow.md
must_fail "hand-back self-test (no R5 line)" python3 bin/handback_check.py --brief evals/fixtures/handback/brief.md evals/fixtures/handback/missing-r-line.md
must_fail "hand-back self-test (R2: DONE)" python3 bin/handback_check.py --brief evals/fixtures/handback/brief.md evals/fixtures/handback/bad-status.md
must_fail "hand-back self-test (no Builder line)" python3 bin/handback_check.py --brief evals/fixtures/handback/brief.md evals/fixtures/handback/missing-builder.md
must_fail "hand-back self-test (committed lock exit 1)" python3 bin/handback_check.py --brief evals/fixtures/handback/brief.md evals/fixtures/handback/lock-nonzero.md
gate      "hand-back BOM tolerated" python3 bin/handback_check.py --brief evals/fixtures/handback/brief.md evals/fixtures/handback/complete-bom.md
gate      "hand-back builder-written, no gate commit" python3 bin/handback_check.py --brief evals/fixtures/handback/brief-none.md evals/fixtures/handback/complete-builder-written.md
gate      "hand-back fenced R heading ignored" python3 bin/handback_check.py --brief evals/fixtures/handback/brief-fenced-example.md evals/fixtures/handback/complete.md
must_fail "hand-back self-test (flow downgrade)" python3 bin/handback_check.py --brief evals/fixtures/handback/brief.md evals/fixtures/handback/flow-downgrade.md
must_fail "hand-back self-test (wrong sha)" python3 bin/handback_check.py --brief evals/fixtures/handback/brief.md evals/fixtures/handback/wrong-sha.md
must_fail "hand-back self-test (duplicate R line)" python3 bin/handback_check.py --brief evals/fixtures/handback/brief.md evals/fixtures/handback/dup-r.md
must_fail "hand-back self-test (duplicate lock line)" python3 bin/handback_check.py --brief evals/fixtures/handback/brief.md evals/fixtures/handback/dup-lock.md
must_fail "hand-back self-test (duplicate flow line)" python3 bin/handback_check.py --brief evals/fixtures/handback/brief.md evals/fixtures/handback/dup-flow.md
must_fail "hand-back self-test (fenced hand-back)" python3 bin/handback_check.py --brief evals/fixtures/handback/brief.md evals/fixtures/handback/fenced.md
must_fail "hand-back self-test (unknown R id)" python3 bin/handback_check.py --brief evals/fixtures/handback/brief.md evals/fixtures/handback/unknown-r.md
grep_ok   "run-builder (exit 3 passes through)" '^builder exit: 3$' python3 bin/run_builder.py --cwd evals/fixtures/gated-build --timeout-minutes 1 --command ./bin/stub-unavailable /nonexistent/brief.md /nonexistent/handback.md
grep_ok   "run-builder (timeout kills the builder)" '^builder exit: timeout$' python3 bin/run_builder.py --cwd evals --timeout-minutes 0.01 --command 'sleep 30;' /nonexistent/brief.md /nonexistent/handback.md
gate      "contents blocks (references > 30 KB)" python3 bin/contents.py --check
gate      "symbols skills/"                python3 bin/craft_source.py verify
must_fail "symbols self-test (craft\\services\\Mcp::getTools())" python3 bin/craft_source.py verify evals/fixtures/symbols/bad-symbol.md
gate      "tables (MCP catalogue, config defaults)" python3 bin/craft_source.py tables
must_fail "tables self-test (project_config_status at read)" python3 bin/craft_source.py tables --catalogue evals/fixtures/tables/catalogue-wrong-scope.md evals/fixtures/symbols
gate      "facts (behaviour cases)"        python3 evals/facts_check.py
must_fail "facts self-test (builder case with runs 2)" python3 evals/facts_check.py evals/fixtures/runs/builder-runs-2.json
gate      "routing (lexical baseline)"     python3 evals/lexical_route.py
must_fail "routing self-test (flooded listing)" python3 evals/lexical_route.py --self-test
gate      "profile schema (valid fixture)" python3 bin/profile_check.py evals/fixtures/profile/valid.json
must_fail "profile self-test (missing version)" python3 bin/profile_check.py evals/fixtures/profile/invalid-missing-version.json
must_fail "profile self-test (gate_tests enum)" python3 bin/profile_check.py evals/fixtures/profile/invalid-gate-tests-enum.json
must_fail "profile self-test (builder without command)" python3 bin/profile_check.py evals/fixtures/profile/invalid-builder-no-command.json
must_fail "profile self-test (negative timeout)" python3 bin/profile_check.py evals/fixtures/profile/invalid-negative-timeout.json
must_fail "profile self-test (NaN timeout)" python3 bin/profile_check.py evals/fixtures/profile/invalid-timeout-nan.json
must_fail "profile self-test (setup.steps not a list)" python3 bin/profile_check.py evals/fixtures/profile/invalid-setup-steps-not-list.json
gate      "neutral wording (pack files)" python3 bin/neutral_check.py skills agents docs schema README.md CHANGELOG.md .claude-plugin project-template reference hooks
must_fail "neutral self-test (names a model as builder)" python3 bin/neutral_check.py evals/fixtures/neutral/names-a-model.md
must_fail "neutral self-test (version suffix)" python3 bin/neutral_check.py evals/fixtures/neutral/names-with-version.md
must_fail "neutral self-test (allowed phrase plus a builder)" python3 bin/neutral_check.py evals/fixtures/neutral/allowed-plus-builder.md
must_fail "neutral self-test (directory with a .sh file)" python3 bin/neutral_check.py evals/fixtures/neutral/dir-with-sh
gate      "neutral self-test (allowed mention)" python3 bin/neutral_check.py evals/fixtures/neutral/allowed-mention.md
grep_ok   "release-evals self-test (stops at a usage limit, stub claude)" 'errors: 1 (1 usage limit).*model calls: 1$' \
          python3 evals/release_evals.py --assume-changed skills/craft-mcp/references/oauth-server.md \
          --claude-bin evals/fixtures/stub-claude/claude-limit --workers 1 --no-cache

if [ "$failed" -ne 0 ]; then
    echo "check.sh: FAILED"
    exit 1
fi
echo "check.sh: all gates passed"
