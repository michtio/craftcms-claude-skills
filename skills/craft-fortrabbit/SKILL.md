---
name: craft-fortrabbit
description: "fortrabbit (fortrabbit.com) — managed PHP hosting with a Craft CMS software template. Covers git push-to-deploy through the fortrabbit GitHub App, the build and post-deploy commands of the Craft template (migrate/all, project-config/apply, clear-caches/all), the merge deployment strategy with the /config/project replace pattern, the deploy file (.fortrabbit/deploy.yml) and its replace-by-default trap, the CRAFT_* ENV vars mapped from FORTRABBIT_DB_* platform variables, production settings (dev mode, admin changes, updates off), the persistent storage for asset volumes and rsync sync, MySQL over SSH and an SSH tunnel, the Craft queue and image transforms in a worker job, crons, platform limits (no root, no sendmail, heavy binaries in jobs only), and DDEV local development."
when_to_use: "Triggers on: .fortrabbit/deploy.yml, .fortrabbit/deploy.yaml, .fortrabbit/deploy.json, FORTRABBIT_DB_HOST, FORTRABBIT_DB_NAME, FORTRABBIT_ENVIRONMENT_NAME, FORTRABBIT_MAIN_DOMAIN, *.frbit.app, *.frbit.cloud, ssh.<region>.frbit.app, an en-xxxxxx environment ID, the frbit CLI or fortrabbit MCP server in a Craft project, the fortrabbit jobs component or worker job, deploy Craft to fortrabbit, host Craft on fortrabbit. Do NOT trigger for Craft Cloud (craft-cloud skill), Servd (servd skill), generic Craft deployment on Forge, Ploi or bare metal (craftcms/deployment.md), or DDEV setup unrelated to a fortrabbit project (ddev)."
---

# fortrabbit — Managed PHP Hosting for Craft CMS

Reference for running Craft CMS 4 and 5 on fortrabbit (fortrabbit.com), a managed PHP hosting platform. Covers git deployment and the Craft software template, the deploy file, ENV vars, the persistent storage and asset volumes, MySQL access over SSH, the Craft queue and image transforms in worker jobs, platform limits, and local development with DDEV.

This skill is scoped to **Craft on fortrabbit specifically**: what differs from running Craft yourself on Forge or bare metal. For generic Craft deployment, see the `craftcms` skill's `deployment.md`. For Craft Cloud, see `craft-cloud`; for Servd, see `servd`.

## Companion Skills — Load When Needed

- **`craftcms`** — When the topic intersects plugin or module PHP (queue jobs, filesystem code, console commands).
- **`craft-site`** — When the topic intersects templates (transforms in Twig, `{% cache %}` tags).
- **`ddev`** — For local development; fortrabbit has no first-party local environment, DDEV is the common local stack.
- **`craft-plugins`** — For Blitz, Imager-X or other plugin configuration on a fortrabbit site.

## Documentation

Authoritative sources used to write this skill (fortrabbit's own docs):

- Docs landing (every page listed): https://docs.fortrabbit.com/llms.txt
- Craft CMS guides: https://docs.fortrabbit.com/guides/craft-cms
- Craft setup: https://docs.fortrabbit.com/guides/craft-cms/setup
- Craft deployment: https://docs.fortrabbit.com/guides/craft-cms/deployment
- Craft ENV vars: https://docs.fortrabbit.com/guides/craft-cms/env-vars
- Craft production settings: https://docs.fortrabbit.com/guides/craft-cms/production-settings
- Craft assets: https://docs.fortrabbit.com/guides/craft-cms/assets
- Craft database: https://docs.fortrabbit.com/guides/craft-cms/database
- Craft queue jobs: https://docs.fortrabbit.com/guides/craft-cms/queueing
- Craft image transforms: https://docs.fortrabbit.com/guides/craft-cms/image-transforms
- Deploy file: https://docs.fortrabbit.com/platform/deployment/deploy-file
- Software templates: https://docs.fortrabbit.com/platform/concepts/software-templates
- Limits: https://docs.fortrabbit.com/platform/concepts/limits
- CLI, MCP server, agent skills: https://docs.fortrabbit.com/platform/automation/cli, https://docs.fortrabbit.com/platform/automation/mcp, https://docs.fortrabbit.com/platform/automation/agent-skills

Any page is available as Markdown: insert `/raw` and append `.md`, e.g. `https://docs.fortrabbit.com/raw/guides/craft-cms/deployment.md`. Per-claim URLs appear in each reference file. Last verified against the docs on 2026-11-04.

## What's Different on fortrabbit vs Self-Hosted

Each row is a place self-hosted habits will mislead you.

| Concern | Self-hosted | fortrabbit |
|---|---|---|
| Objects | One server | An **app** has one or more **environments** (`en-xxxxxx`), e.g. production and staging. Each has its own code, database, ENV vars, SSH access and default domain `<env>.<region>.frbit.app` |
| Deploy | Whatever you've wired | **Git push** to the connected branch, through the fortrabbit GitHub App. Composer runs in the build; post-deploy commands run once the code is live |
| Deploy config | Deploy script | The **Craft software template** sets root path `web`, build and post-deploy commands, strategy. Edit in the dashboard, or commit a **deploy file** `.fortrabbit/deploy.yml` |
| `craft up` | Add it to the deploy script | Template post-deploy commands: `php craft migrate/all`, `php craft project-config/apply`, `php craft clear-caches/all` |
| Filesystem | Local disk | **Persistent storage**: survives deployments and restarts. Local asset volumes work. The **merge** strategy keeps uploads in place |
| Env vars | `.env` on the server | Dashboard ENV vars per environment. The template maps `CRAFT_DB_*` to platform variables `${FORTRABBIT_DB_*}`. No `.env` on the server |
| Production config | Yours to set | Template sets `CRAFT_DEV_MODE=false`, `CRAFT_ALLOW_ADMIN_CHANGES=false`, `CRAFT_ALLOW_UPDATES=false` |
| Database | Whatever you installed | **MySQL** only, one database per environment, reached from inside the environment or over SSH |
| Queue | Daemon via supervisor | Default web-triggered queue. A **worker job** in the jobs component runs `php craft queue/listen` |
| Cron | `crontab` | **Cron jobs** in the jobs component, configured in the dashboard, times in UTC |
| SSH | Root or sudo | `ssh <env>@ssh.<region>.frbit.app`, **no root**, nothing installable at runtime |
| Mail | Local MTA | No `sendmail`: PHP `mail()` fails. Use SMTP or a transactional mail provider |

## fortrabbit Tooling

fortrabbit has three first-party routes besides the dashboard. Use them to look up IDs, read deployment logs and change ENV vars instead of asking the user to copy values out of the dashboard.

| Task | MCP server | `frbit` CLI |
|---|---|---|
| Find the app and environment of this repo | `list_git_repositories`, `get_app`, `list_environments` | `frbit apps list --json`, `frbit environments list --json` |
| Deploy the latest commit again | (push to the branch) | `frbit environments deploy <env>` |
| Status and log of a failed build or post-deploy command | `get_deployment`, `get_deployment_logs` | `frbit deployments list --environment <env>`, `frbit deployments logs <dp>` |
| Read or change ENV vars (`CRAFT_*`, `PRIMARY_SITE_URL`) | `get_environment`, `update_environment` | `frbit environments variables get` / `update` |
| Restart after an ENV var change | – | `frbit environments restart <env>` |
| Create an app with the Craft template | `create_app` | `frbit apps create` |

- MCP server: `https://mcp.fortrabbit.com/mcp`, OAuth sign-in in the browser. Add it with `claude mcp add --transport http fortrabbit https://mcp.fortrabbit.com/mcp`.
- CLI: `brew install fortrabbit/tap/frbit` or `npm install --global @fortrabbit/cli`, then `frbit auth login`. In CI, set `FRBIT_TOKEN` to an API token with `write` scope.
- REST API: `https://api.fortrabbit.com/v1`, endpoints in `https://api.fortrabbit.com/v1/docs`.
- fortrabbit's own agent plugin bundles the MCP server with a general `fortrabbit` skill for non-Craft tasks (any PHP app, SSH, troubleshooting): `/plugin marketplace add fortrabbit/agent-skills`, then `/plugin install fortrabbit@fortrabbit`. Source: https://github.com/fortrabbit/agent-skills.
- Never ask for a password or API token in the chat: sign-in happens in the browser, and the database password stays in the dashboard.

## Common Pitfalls (Cross-Cutting)

- **A deploy file without `strategy`.** Without the key the deployment uses `replace`, also when the dashboard was set to `merge`. Every local asset volume is then deleted on the next deployment unless it is in `excludePatterns`. Copy the template values into the file: `strategy: merge`, `replacePatterns: [/config/project]`. See `references/deploy-and-environments.md`.
- **A deploy file that drops the post-deploy commands.** A key left out falls back to "no commands", not to the dashboard. Without `php craft project-config/apply`, schema changes stop reaching the environment. See `references/deploy-and-environments.md`.
- **Making schema or plugin changes on the environment.** `CRAFT_ALLOW_ADMIN_CHANGES=false` blocks them, and the next deployment applies the project config from git over them. Change locally, commit `config/project`, push. See `references/deploy-and-environments.md`.
- **Updating Craft in the control panel.** `CRAFT_ALLOW_UPDATES=false` hides updates. Run `ddev craft update all` locally, commit `composer.json` and `composer.lock`, push.
- **Importing the local database without the local security key.** The template generates a random `CRAFT_SECURITY_KEY`; data encrypted locally can't be read with it. Copy the local key into the environment's ENV vars. See `references/database.md`.
- **Running the queue in web requests.** Craft's default AJAX queue runner and on-demand image transforms block the PHP processes that serve the site, ending in 504s or memory kills. Run the queue in a worker job and set `CRAFT_RUN_QUEUE_AUTOMATICALLY=false` on that environment. See `references/limitations.md`.
- **Expecting assets in git.** Uploads stay on the environment; git deployment only goes up. Sync volumes with rsync. See `references/asset-storage.md`.
- **Fixing code over SSH.** Files changed over SSH are overwritten by the next git deployment. Fix in git.

## Reference Files

Read the relevant reference file(s) for your task. Multiple files often apply.

**Task examples:**

- "Deploy a Craft site to fortrabbit" → `deploy-and-environments.md`
- "Move the deployment settings into the repo" → `deploy-and-environments.md` (deploy file)
- "Why did my uploads disappear after a deployment?" → `deploy-and-environments.md` + `asset-storage.md`
- "Set up staging and production" → `deploy-and-environments.md`
- "Which ENV vars does Craft need on fortrabbit?" → `deploy-and-environments.md`
- "Push the local database to fortrabbit" → `database.md`
- "Connect TablePlus to the fortrabbit database" → `database.md`
- "Sync assets between local and fortrabbit" → `asset-storage.md`
- "Use S3 for assets instead" → `asset-storage.md`
- "Set up local development for a fortrabbit project" → `local-dev.md`
- "Pull production content to DDEV" → `local-dev.md`
- "Run the Craft queue / image transforms in the background" → `limitations.md`
- "Why does PHP `mail()` not work?" → `limitations.md`
- "Can I install ImageMagick, wkhtmltopdf or a global npm package?" → `limitations.md`

Load only the reference files your task needs.

| Reference | Scope | ~Lines |
|---|---|---:|
| `references/deploy-and-environments.md` | Apps and environments, the GitHub App, build and post-deploy commands of the Craft template, merge strategy and the `/config/project` replace pattern, the deploy file, ENV vars and platform variables, production settings, updates and major upgrades | ~200 |
| `references/database.md` | MySQL per environment, credentials via platform variables, dump and import over SSH, SSH tunnel for clients, security key and table prefix, backups | ~80 |
| `references/asset-storage.md` | Persistent storage, local volumes and `.gitignore`, rsync and SFTP sync, S3 volumes, exclude patterns with `replace` | ~90 |
| `references/local-dev.md` | DDEV config for a fortrabbit project, `ddev auth ssh`, pulling the database and volumes down, multi-environment config with `CRAFT_ENVIRONMENT` | ~75 |
| `references/limitations.md` | No root, jobs component (worker for the queue, crons), heavy binaries in jobs only, image transforms, mail, PDF, SSH rate limit, and the repo **detection signals** | ~90 |
