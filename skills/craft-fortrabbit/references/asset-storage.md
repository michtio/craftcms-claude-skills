# Asset Storage — Persistent Volumes and Sync

fortrabbit's storage is a **persistent** file system: it holds the deployed code and runtime data such as uploads, transforms and cache files, and keeps them across deployments and restarts. Craft's local filesystems work as on a single server. Uploads never enter git, so they move between local and remote with rsync or SFTP.

## Documentation

- Craft assets: https://docs.fortrabbit.com/guides/craft-cms/assets
- Storage component: https://docs.fortrabbit.com/platform/components/storage
- Deployment strategy: https://docs.fortrabbit.com/platform/deployment/strategy
- Exclude patterns: https://docs.fortrabbit.com/platform/deployment/exclude-patterns
- SFTP: https://docs.fortrabbit.com/platform/code-access/sftp
- Craft assets docs: https://craftcms.com/docs/5.x/reference/element-types/assets.html

## Local volumes

The Craft template deploys with the **merge** strategy: files on the environment that are not in the build stay. A local volume such as `web/uploads` survives every deployment without further setup.

With the **replace** strategy (or a deploy file without `strategy`), add every volume path to the exclude patterns, or it is deleted on the next deployment:

```yaml
# .fortrabbit/deploy.yml
distribution:
  strategy: replace
  excludePatterns:
    - /web/uploads
```

Keep volume folders out of git. Craft adds a `.gitignore` when it creates a local filesystem folder; for a folder that existed before, add one by hand:

```gitignore
*
!.gitignore
```

Find the volume paths of a project:

```sh
grep -rn "path\|basePath" config/project/fs config/project/volumes 2>/dev/null
```

## Sync with rsync

rsync copies only changed files. SSH logs in at `/data/www`, the code folder, so remote paths are relative to it:

```sh
# down: fortrabbit → local
rsync -avz <env>@ssh.<region>.frbit.app:web/uploads/ ./web/uploads/

# up: local → fortrabbit, dry run first
rsync -avzn ./web/uploads/ <env>@ssh.<region>.frbit.app:web/uploads/
rsync -avz ./web/uploads/ <env>@ssh.<region>.frbit.app:web/uploads/
```

- Trailing slashes matter: `dir/` syncs the contents. Keep both sides the same shape.
- `--delete` removes files on the target that aren't on the source. Dry-run it first.
- Never sync `.env`, `.git/`, `node_modules/` or `storage/runtime/`.

After pulling assets, run `ddev craft index-assets/all` when the asset index and the files don't match.

## Sync with SFTP

Any SFTP client works with the same host and user as SSH. Many have a folder sync option. SFTP clients often hide dot files.

## S3 volumes

With the first-party `craftcms/aws-s3` plugin, Craft stores uploads in an S3 bucket instead of the environment's storage, and nothing needs syncing. It adds a service to pay for and configure, and transforms of remote images need a download and upload per transform. fortrabbit's docs recommend it for many or large files, not by default.

```sh
ddev composer require craftcms/aws-s3
ddev craft plugin/install aws-s3
```

Keep the bucket credentials in ENV vars on each environment and reference them from the filesystem settings (`$S3_KEY_ID` etc.).

## Storage size

The storage plan caps the size. Without autoscaling, a full storage stops all file writes. Common causes of growth: unrotated log files, dumps and backups left on disk, image transforms created by bots, abandoned uploads. Find large folders over SSH:

```sh
ssh <env>@ssh.<region>.frbit.app 'du -sh ./* | sort -h'
```

## Common Pitfalls

1. **Uploads gone after a deployment** — the environment deploys with `replace` (often a deploy file without `strategy`). Switch to `merge` or add the volume to `excludePatterns`.
2. **Committing uploads to git** — bloats the repo and every build, and committed copies overwrite same-named files on the environment. Keep volumes in `.gitignore`.
3. **Expecting uploads to reach local through git** — git deployment only goes up. Pull them with rsync.
4. **rsync with mismatched trailing slashes** — creates `uploads/uploads/`. Use `dir/` on both sides.
5. **Volume base URL hardcoded to the local domain** — build it from an ENV var so it resolves per environment, e.g. `$PRIMARY_SITE_URL/uploads` (Craft 5.5+) or an alias defined from `App::env()`. Avoid `@web`: Craft derives it from the request.
