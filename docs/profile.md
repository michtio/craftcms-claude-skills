# Project profile

A project can carry one profile file that answers the setup questions in advance and names the outside builders the gated-build flow may use. The file is optional. Without it, nothing in the pack changes.

Status: the profile format and its checker ship now. The gated build reads `builders` and `gate_tests` (the `craft-gated-build` skill). Project setup reads the answers, choices and extra steps once that feature ships.

## Location

`.ai/skills-profile.json` at the project root, committed with the project. The schema is `schema/skills-profile.schema.json` (JSON Schema 2020-12). Check a file with:

```bash
python3 bin/profile_check.py .ai/skills-profile.json
```

It exits 0 when the file is valid, 1 with a message naming the key when it is not, and 2 on a usage error.

## Shared with the Laravel pack

The Craft pack and the Laravel pack read the same file and ship the same schema. Shared keys sit at the top level. Pack-specific keys sit under `craft` or `laravel`. Each pack ignores the other pack's section, so one file can serve both. A team tool may write the file; `managed_by` records which one. A person can also write it by hand.

The schema file is shared byte for byte with the Laravel pack. Each pack types its own section (`craft` or `laravel`); the other pack's section is left open.

Unknown keys are kept and ignored, at every level. `version` is the only key whose unknown value hard-fails: a file with a `version` other than `1` is rejected. A newer team tool never breaks an older pack, and a pack never deletes a key it does not know.

## Keys

| Key | Type | Meaning |
|---|---|---|
| `version` | integer, required | Profile format version. Always `1`. |
| `managed_by` | object | Informational. `tool` and `version` of the team tool that wrote the file. |
| `gate_tests` | `locked` or `builder-written` | Who writes the gate tests. `locked`: a separate gate writer writes them and they are locked before the build. `builder-written`: the builder writes its own tests. |
| `builders` | list | Outside builders, tried in the order listed. Each item has `name`, `command` and `timeout_minutes`. |
| `builders[].name` | string, required | A label for the builder. Never a model or vendor name in the pack's own files. |
| `builders[].command` | string, required | The command to run. It is called as `<command> <brief-file> <handback-file>`. |
| `builders[].timeout_minutes` | number above 0 | Minutes to wait before the run counts as failed. |
| `setup.steps` | list | Extra setup steps, in order. Each item has `name` and `command`. They run after the generated files exist. |
| `verdicts` | object | Review verdict settings. Used by the Laravel pack and ignored by Craft. |
| `craft.answers` | object | Answers to the project setup questions, so they are not asked again. |
| `craft.answers.hosting` | string | The hosting target, for example `craft-cloud`. |
| `craft.answers.passwordless` | boolean | Whether the project uses passwordless sign-in. |
| `craft.answers.dev_root` | string | The folder that holds the developer's projects, for example `~/dev`. |
| `craft.choices` | object | Setup choices, such as which tool integrations to configure. |
| `craft.choices.chrome_devtools_mcp` | boolean | Configure the Chrome DevTools MCP server for browser checks. |
| `craft.choices.craft_mcp` | boolean | Configure the Craft MCP server. |
| `laravel` | object | Laravel pack keys. Ignored by the Craft pack. |

### Gate flow

`gate_tests` picks the gate flow. With `locked`, the gate tests are written first by a separate gate writer, committed, and then locked: the builder must not edit them, and the lock check proves it by diff. With `builder-written`, the builder writes tests itself and no lock check applies.

### Outside builders

An outside builder is any command that reads a brief and writes a hand-back. It can be a local AI running on the developer's machine, a hosted service, or a script. The pack never names one. The pack tries the builders in order and falls back to its own builder when none succeeds.

## Example

```json
{
  "version": 1,
  "managed_by": {"tool": "team-tool", "version": "0.3.0"},
  "gate_tests": "locked",
  "builders": [
    {"name": "local-first", "command": "./scripts/build-local.sh", "timeout_minutes": 45},
    {"name": "hosted-second", "command": "./scripts/build-hosted.sh", "timeout_minutes": 30}
  ],
  "setup": {
    "steps": [
      {"name": "install", "command": "ddev composer install"},
      {"name": "migrate", "command": "ddev craft up"}
    ]
  },
  "verdicts": {"format": "per-requirement"},
  "craft": {
    "answers": {"hosting": "craft-cloud", "passwordless": true, "dev_root": "~/dev"},
    "choices": {"chrome_devtools_mcp": true, "craft_mcp": false}
  },
  "laravel": {"queue_driver": "redis"}
}
```
