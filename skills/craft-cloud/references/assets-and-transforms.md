# Assets and Image Transforms on Cloud

Cloud replaces local asset filesystems and Craft's native image transformer with platform-managed equivalents. User assets live in a Cloud-managed S3 bucket; transforms run at the edge via Cloudflare and serve modern formats automatically.

## Documentation

- Assets reference: https://craftcms.com/docs/cloud/assets
- Cloud filesystem source: https://github.com/craftcms/cloud-extension-yii2/blob/main/src/fs/AssetsFs.php
- Image transformer source: https://github.com/craftcms/cloud-extension-yii2/tree/main/src/imagetransforms

## Common Pitfalls

- Leaving the **Subpath** blank on the Cloud filesystem. Even with a single filesystem, the docs are explicit: "Filesystems' base paths cannot overlap!" Use the Subpath option to reserve root space — e.g. `assets/` — so future filesystems (or future environments) can coexist.
- Running `aws s3 sync` without the `assets/` segment in the destination URL. "Files uploaded outside of [the `assets/` subpath] will be undiscoverable by Craft." Wrong destination, lost migration.
- Continuing to use ImageOptimize / Imager-X to generate srcset on Cloud. Cloud transforms images at the edge — these plugins duplicate the work and can produce stale references. See `limitations.md` (Plugin compatibility).
- Expecting `transform.mode = 'stretch'` to actually stretch. On Cloud the workers treat `stretch` like CSS `object-fit: cover` — proportional fill rather than independent W/H scaling. If you need pixel-exact stretching, generate the transform off-platform.
- Uploading an animated GIF over 50MP across all frames. Cloud rejects it.

## The Cloud filesystem type

The extension registers a `craft\cloud\fs\AssetsFs` filesystem type. Configure it as a normal Craft filesystem (Settings → Filesystems → New filesystem → type = Cloud), then point one or more asset volumes at it.

### Required settings

- **Subpath** (required) — automatically appended to both Base Path and URL. Use a value like `assets/` for the primary user-uploaded files. The third segment in the resulting S3 URL must be a subpath; files uploaded outside it are invisible to Craft.
- **Local Filesystem** section (recommended) — when migrating an existing site, copy the original Base Path and Base URL here. This lets local dev keep reading files from the same on-disk location while production reads from Cloud.

Internal filesystem types (you don't configure these — the extension manages them):

| FS class | Backs |
|---|---|
| `BuildArtifactsFs` | Build artifacts uploaded between phases |
| `BuildsFs` | Build metadata |
| `CpResourcesFs` | CP asset bundles published to the CDN at build time |
| `StorageFs` | Craft's `storage/` path |
| `TmpFs` | Temp paths returned by `Craft::$app->getPath()->getTempPath()` |

See `extension.md` (Filesystem types) for the full table.

## Image transforms at the edge

Every image transform call — `asset.getUrl({width: 800})`, named transforms, ad-hoc transforms, transforms from Twig or PHP — runs through Cloud's edge workers. Existing templates work without changes.

### Auto-negotiated formats

When no explicit format is specified, Cloud serves WEBP or AVIF based on the client's `Accept` header. Same URL, different bytes per client. Fall back to the original format for clients that don't support either.

### Limits

| Limit | Value |
|---|---|
| Maximum source file size | 70MB |
| Maximum source megapixels | 100MP |
| Maximum source megapixels (animated, total across frames) | 50MP |
| Maximum longest-edge output | 12,000px |
| Maximum longest-edge output for AVIF | 1,600px |

Sources exceeding these limits won't transform — Craft will fall back to the original. For images that need to ship at >12,000px on the long edge, deliver the original file directly (skip the transform).

### Stretch mode

`stretch` doesn't independently scale width and height — Cloud treats it like CSS `object-fit: cover`. The image fills the target box proportionally; the longer dimension is clipped. If you need true stretch semantics (rare for content images), do the resizing off-platform and upload pre-sized assets.

## Migrating assets from a self-hosted site

The supported tool is the AWS S3 CLI's `sync` command. Cloud's bucket address comes from the project and environment UUIDs (visible in Console).

```sh
# Push local files into the Cloud bucket
aws s3 sync ./web/craft-cloud-assets/ s3://{project-uuid}/{environment-uuid}/assets/

# Pull Cloud files back to local (e.g. to refresh a dev environment)
aws s3 sync s3://{project-uuid}/{environment-uuid}/assets/ ./web/craft-cloud-assets/ --delete
```

The third URL segment (`assets/`) is mandatory and must match the Subpath you configured on the filesystem. Run periodically during the migration window to catch new uploads on the legacy site.

For the broader migration sequence (DB + assets + DNS cutover), see `migration.md`.

## What you don't need to do

- Generate srcsets in templates manually for Cloud's benefit — the existing transform calls produce all the URLs you need.
- Configure a CDN — Cloud's edge layer is the CDN.
- Set up a transform queue worker — transforms are synchronous edge operations, not Craft queue jobs.
- Install Cloudflare separately — Cloud is built on Cloudflare; you don't manage it.

Last verified against https://craftcms.com/docs/cloud/assets and `craftcms/cloud-extension-yii2@main` on 2026-05-28.
