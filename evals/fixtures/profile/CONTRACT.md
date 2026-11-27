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
- Flag `--schema <file>`: validate against that schema instead of
  `schema/skills-profile.schema.json`. The checker supports only the keywords the
  profile schema uses. A schema using any other keyword exits 2 (usage error) and
  names the keyword; annotation keywords (`$schema`, `$id`, `title`,
  `description`) are ignored. `schema-unknown-keyword.json` (uses `minimum`) with
  `--schema` exits 2 on `valid.json`.
- `invalid-timeout-nan.json` (`"timeout_minutes": NaN`, which Python's json
  accepts) exits 1 and names `timeout_minutes`. NaN and infinity are never valid.
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

`python3 bin/neutral_check.py [--allow <file>] <path>...`; each path is a file or
a directory. Exit 1 with `<path>:<line>: ...` plus the matched term when a line
names a deny-listed term; exit 0 otherwise; exit 2 on a usage error.

- Directory recursion scans every file, whatever its extension, and skips a file
  that contains a NUL byte or fails to decode as UTF-8. `neutral/dir-with-sh/`
  (a `.sh` naming a model) exits 1 when the directory is scanned.
- Deny list: `bin/data/builder-names.txt`. One term per line, `#` comments and
  blank lines ignored, matched case-insensitively. Boundaries are letters only:
  a term hits when the characters before and after it are not letters, so digits,
  underscores and hyphens attached still hit (`Qwen3`, `GPT4`, `gpt_4`, `Llama3`,
  `qwen-2`) while a term inside a longer word does not (`Ruglmore`). Required
  terms: qwen, mistral, glm, ollama, llama, deepseek, gpt, gemini, vllm, chatgpt,
  openai, codex, copilot, codestral, devstral.
- Allowlist: `bin/data/builder-names-allow.tsv`, or the file given by `--allow`.
  Tab-separated `phrase<TAB>reason`, `#` comments ignored, a reason is mandatory,
  an empty phrase is a usage error (exit 2). A phrase exempts only its own
  occurrence (case-insensitive), not the rest of the line: a deny term elsewhere
  on the line still hits. The allowlist must contain `Gemini CLI`.
- `names-a-model.md`, `names-with-version.md` and `allowed-plus-builder.md` exit
  1 (the last on `qwen`); `allowed-mention.md` exits 0.
- `--allow evals/fixtures/neutral/allow-empty-phrase.tsv` exits 2.
- The pack scan is `skills agents docs schema README.md CHANGELOG.md
  .claude-plugin project-template reference hooks` and exits 0. It never scans
  `bin/data` or `evals/fixtures`. Fix any real hit by rewording or by an allowlist
  entry with a reason, never by weakening the deny list.

## 5. `bin/check.sh`

- `must_fail` line for each of the five invalid profiles, running
  `python3 bin/profile_check.py <fixture>`.
- `gate` line for `python3 bin/profile_check.py evals/fixtures/profile/valid.json`.
- `must_fail` lines for `names-a-model.md`, `names-with-version.md`,
  `allowed-plus-builder.md` and the directory `evals/fixtures/neutral/dir-with-sh`.
- `gate` line for `python3 bin/neutral_check.py evals/fixtures/neutral/allowed-mention.md`.
- `gate` line for the pack scan (paths in section 4).
- `must_fail` line for `invalid-timeout-nan.json`.

- `sh bin/check.sh` exits 0 on the repo.
