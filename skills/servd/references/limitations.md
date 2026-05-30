# Servd Limitations, Constraints, and Detection Signals

What Servd's platform constrains — the ephemeral load-balanced filesystem, plugin/feature limits — plus a documented-vs-unknown map, a Servd-vs-Craft-Cloud comparison for Craft developers, and the repo signals that identify a Servd project.

The first sections are **documented** facts from Servd's own docs. Anything inferred or not explicitly documented is flagged **Verify** and kept in a clearly-labelled section. Broader plugin guidance beyond what Servd documents is labelled **community/inferred knowledge**, not Servd doctrine.

## Documentation

- Handling runtime-created files: https://servd.host/docs/handling-runtime-created-files
- The Servd workflow: https://servd.host/docs/the-servd-workflow
- Dedicated queue runner: https://servd.host/docs/dedicated-queue-runner
- Plugin source: https://github.com/servdhost/craft-asset-storage

## Filesystem constraints (documented)

Servd runs on **ephemeral file systems and load-balanced instances**. This is the single most important constraint, and it breaks self-hosted habits in two ways the docs spell out:

- **Resets:** "the filesystem will be regularly reset, resulting in the locally stored file being removed." Anything written directly to disk at runtime can vanish at any time.
- **Load balancing:** "if the project is load balanced the file will only be downloaded to one of the instances' filesystems." A file written by one request is invisible to the next request served by a different instance.

The practical rule: **do not rely on `\Craft::$app->path->getStoragePath()` (or any direct disk write) for persistent runtime-created files.** Servd's docs give two supported approaches:

1. **Store data in Craft's data cache.** On Servd, "Craft's data cache is automatically mapped to a stateful Redis server," so `Craft::$app->cache->set()` / `->get()` persist across resets and instances. Use this for small data and computed values. See `database-and-queue.md` for the Redis surface.
2. **Push runtime files to a remote asset volume** via Flysystem — `$filesystem->writeFileFromStream()` to store, `$filesystem->getFileStream()` to retrieve. The docs suggest a hybrid pattern: check for a locally cached copy first, download from the remote volume only on a miss. This trades a little latency for correctness under load balancing. See `asset-storage.md` for the Servd filesystem.

Plugin and module PHP that creates files at runtime must use one of these. Code that writes to `getStoragePath()` and reads it back later is silently broken on Servd even though it works locally.

## Plugin and feature constraints

There is **no official Servd plugin-compatibility matrix.** Servd documents a small number of concrete points; everything beyond them is inference.

**Documented:**

- **Filesystem-writing plugins.** Any plugin that persists files to local disk at runtime is subject to the ephemeral/load-balanced constraint above — it must use Redis (Craft's data cache) or a remote volume, or its writes are lost. This is the dominant compatibility concern on Servd.
- **Transform plugins via `servd/craft-asset-storage`.** The plugin provides off-server image transforms and ships integrations so the common transform plugins work through the Servd platform: **Imager-X** via `transformer: 'servd'`, and **ImageOptimize**. Transforms execute off-server and are delivered from the `*.files.svdcdn.com` CDN rather than the app container. See `asset-storage.md`.
- **Blitz** works, but must run **alongside** Servd's static cache in **reverse-proxy mode** — not in its default server-rewrite mode, which the load balancer breaks. See `caching.md`.

**Cron — not a documented user-configurable feature.** Servd's public docs do not describe a way to register arbitrary cron entries. Recurring work should be modelled as **Craft queue jobs** processed by the **Dedicated Queue Runner** (Enhanced and Pro plans; the runner isolates the queue from user requests). The queue runner page notes Craft launches jobs "in response to actions performed by users or on a schedule" but gives no guidance on configuring scheduled tasks. Treat scheduled execution as **Verify** for a given plan, and design around queue jobs. See `database-and-queue.md`.

### Community / inferred knowledge (not Servd doctrine)

The following is reasonable inference from the documented constraints, **not** anything Servd publishes. Verify per plugin against its own repo and the plugin author's statements:

- Plugins that are pure logic / CP UI (form builders, field managers, SEO meta generation, spam filters) generally have no Servd-specific concern — they don't write to disk at runtime.
- Plugins that cache to disk, generate files on a schedule, or shell out to system binaries are the risk category. Audit the plugin source for `getStoragePath()` / `getRuntimePath()` writes and for cron assumptions.
- Search-engine integrations (Typesense, Algolia, Meilisearch) run against an external service, so the Servd container constraints don't apply to the engine itself.

When a plugin's behaviour on Servd is uncertain, reproduce the file-write path locally and confirm it routes through Redis or a remote volume before relying on it.

## Documented vs unknown (the gaps)

| Topic | Status |
|---|---|
| Ephemeral + load-balanced filesystem | **Documented** (handling-runtime-created-files) |
| Redis-backed data cache | **Documented** |
| Remote-volume Flysystem pattern | **Documented** |
| Off-server transforms, Imager-X/ImageOptimize integration | **Documented** (plugin README + asset docs) |
| Blitz reverse-proxy mode | **Documented** (caching-with-blitz) |
| Dedicated Queue Runner + plan availability | **Documented** (Enhanced/Pro) |
| Arbitrary cron / scheduled tasks | **Verify** — not documented as user-configurable |
| Full third-party plugin compatibility matrix | **Unknown** — no official list |
| Exact plan tiers / quotas / limits | **Verify** — not in the public docs surveyed here |
| Runtime caps (request timeout, upload size, build duration) | **Verify** — not documented in the pages surveyed |

## Servd vs Craft Cloud

Both are managed Craft hosting with git deploy, ephemeral filesystems, S3-backed assets, off-server transforms, and dashboard-managed env vars. Where they differ matters when porting a project or choosing a host:

| Concern | Servd | Craft Cloud |
|---|---|---|
| Repo config | `servd.yaml` (build) + dashboard | `craft-cloud.yaml` |
| Asset layer | `servd/craft-asset-storage` plugin | `craftcms/cloud` bundled filesystem |
| Database | MariaDB **or** MySQL 8 | MySQL 8 / Postgres 15 (**no MariaDB**) |
| SSH | **Yes** (used for the DB tunnel) | None |
| First-party CLI | None — plugin console commands + dashboard | `craftcms/cloud` + `php craft cloud/up` |
| Caching | Servd static cache; **Blitz runs alongside** in reverse-proxy mode | Edge static caching; **Blitz redundant** |
| Transforms | Off-server via `*.files.svdcdn.com` | Cloudflare Images at the edge |
| Queue | Dedicated Queue Runner (paid plans) | Auto-processed |
| Shared by both | Git deploy, ephemeral filesystem, S3-backed assets, dashboard-managed env vars | same |

The headline differences for a Craft developer: Servd keeps SSH (so a normal DB tunnel works) and runs Blitz alongside its own cache, whereas Cloud has no SSH, makes Blitz redundant, and ships a first-party CLI. See `deploy-and-environments.md` for Servd's workflow, `caching.md` for the Blitz contrast, and `asset-storage.md` for the transform pipeline.

## Detection signals

Use these to decide whether a repo is a Servd project — they feed the `craft-project-setup` skill. A repo is a **Servd project** if **any** of the following is true:

- **`composer.json` requires `servd/craft-asset-storage`** — the strongest signal. The plugin is effectively mandatory for assets on Servd.
- **A `servd.yaml` file exists at the repo root** — the build-step config.
- **The environment defines `SERVD_PROJECT_SLUG`, `SERVD_SECURITY_KEY`, or `SERVD_BUNDLE_HASH`** — Servd-injected env vars (the first two come from the dashboard's Assets page).

Note: there is **no `servd.json` and no `.servd` directory** — do not look for them. The asset-storage plugin handle (`servd-asset-storage`) and the `*.files.svdcdn.com` CDN domain in config or templates are corroborating signals but secondary to the three above.

Last verified against https://servd.host/docs/handling-runtime-created-files, https://servd.host/docs/the-servd-workflow, https://servd.host/docs/dedicated-queue-runner, and https://github.com/servdhost/craft-asset-storage on 2026-05-30. Plugin-compatibility inference is community knowledge and may drift faster than the documented surface.
