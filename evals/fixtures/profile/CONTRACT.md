# S1 gate contract: profile schema, docs, neutral-wording check

Spec: extension-points PRD R1, R8; AC1, AC8; plan AD1, AD2, AD9. The builder
makes every item below hold and does not edit the fixtures or
`evals/tests/test_ext_s1.py`. Run the tests with
`python3 -m unittest discover -s evals/tests -p 'test_ext_s1.py' -v`
(the repo has no test-runner convention; stdlib unittest, nothing wired into CI
beyond `bin/check.sh`).

## 1. Profile checker

`python3 bin/profile_check.py <file>...` (standard library only).

- `valid.json` exits 0 (prints nothing required).
- Each invalid fixture exits 1 and its output contains the substring:

| Fixture | Substring in output |
|---|---|
| `invalid-missing-version.json` | `version` |
| `invalid-gate-tests-enum.json` | `gate_tests` |
| `invalid-builder-no-command.json` | `command` |
| `invalid-negative-timeout.json` | `timeout_minutes` |
| `invalid-setup-steps-not-list.json` | `setup.steps` |

- Unknown keys (`laravel`, `future_key`) are accepted: the schema must not set
  `additionalProperties: false` at any level the profile shares.
- Rules: `version` required integer 1; `gate_tests` enum `locked` |
  `builder-written`; each builder requires `name` and `command` (strings) and
  `timeout_minutes` is a positive number; `setup.steps` is a list of
  `{name, command}`.

## 2. Schema

`schema/skills-profile.schema.json` exists, parses as JSON and has `"$schema"`.

## 3. Docs

`docs/profile.md` states the location `.ai/skills-profile.json` and names every
key: `version`, `managed_by`, `gate_tests`, `locked`, `builder-written`,
`builders`, `name`, `command`, `timeout_minutes`, `setup.steps`, `verdicts`,
`craft.answers`, `hosting`, `passwordless`, `dev_root`, `craft.choices`,
`chrome_devtools_mcp`, `craft_mcp`. It says `verdicts` is used by the Laravel pack
and ignored by Craft, and that unknown keys are kept. The tests grep for each.

## 4. Neutral-wording check

`python3 bin/neutral_check.py <path>...`; each path is a file or a directory
(recursed; `.md`, `.json`, `.txt`, `.yml`, `.yaml`, `.tsv` files). Exit 1 with
`<path>:<line>: ...` plus the matched term when a line names a deny-listed term;
exit 0 otherwise.

- Deny list: `bin/data/builder-names.txt`. One term per line, `#` comments and
  blank lines ignored, each term matched case-insensitively as a whole word.
  At least: qwen, mistral, glm, ollama, llama, deepseek, gpt, gemini, vllm.
- Allowlist: `bin/data/builder-names-allow.tsv`. Tab-separated
  `phrase<TAB>reason`, `#` comments ignored, a reason is mandatory. A line is
  exempt when it contains the phrase (case-insensitive). The allowlist must
  contain `Gemini CLI` (MCP client named as a connection target, not a builder).
- `names-a-model.md` exits 1; `allowed-mention.md` exits 0.
- `skills/ agents/ docs/ schema/` exits 0. Fix any real hit by rewording or by
  an allowlist entry with a reason, never by weakening the deny list.

## 5. `bin/check.sh`

- `must_fail` line for each of the five invalid profiles, running
  `python3 bin/profile_check.py <fixture>`.
- `gate` line for `python3 bin/profile_check.py evals/fixtures/profile/valid.json`.
- `must_fail` line for `python3 bin/neutral_check.py evals/fixtures/neutral/names-a-model.md`.
- `gate` line for `python3 bin/neutral_check.py evals/fixtures/neutral/allowed-mention.md`.
- `gate` line for `python3 bin/neutral_check.py skills agents docs schema`.
- `sh bin/check.sh` exits 0 on the repo.
