# Asset Storage on Servd

Servd provides asset storage, a CDN, and off-server image transforms through the `servd/craft-asset-storage` plugin. Because Servd runs Craft on an ephemeral, load-balanced filesystem (see `limitations.md`), user-uploaded assets *must* live on the Servd filesystem rather than a local volume — files written to disk by one instance are not shared with the others and vanish on redeploy.

## Documentation

- Installing the plugin: https://servd.host/docs/installing-the-servd-plugin
- Asset volumes and filesystems: https://servd.host/docs/servd-asset-volumes-and-filesystems
- The Servd plugin (feature overview): https://servd.host/docs/the-servd-plugin
- Imager-X integration: https://servd.host/docs/imager-x-integration
- Package versions: https://packagist.org/packages/servd/craft-asset-storage

## Common Pitfalls

- Pointing user-uploaded asset volumes at a **local filesystem** instead of the Servd filesystem. On Servd's ephemeral, load-balanced infrastructure those files won't persist or be shared across instances. See `limitations.md`.
- Setting `SERVD_PROJECT_SLUG` / `SERVD_SECURITY_KEY` **in the Control Panel** rather than as env vars. The CP path stores the values in project config (and they sync across environments), which is the wrong place for per-environment secrets. Always load them from env vars.
- Re-implementing srcset generation with ImageOptimize or Imager-X "for performance." Servd already generates transforms off-server and serves them from its CDN — native Craft transforms work transparently and are the path of least resistance.
- Using `transformer: 'servd'` for **assets that aren't on a Servd volume**. The Imager-X custom transformer only works with images stored on a Servd Assets filesystem.
- Expecting the full Imager-X feature set with `transformer: 'servd'` — the Servd transformer "doesn't support a lot of Imager X's advanced features." Use the `storages` approach if you need them.

## Installation

```bash
composer require servd/craft-asset-storage
./craft plugin/install servd-asset-storage
```

Or install "Servd Assets and Helpers" from the Plugin Store and enable it in the CP. The composer package is `servd/craft-asset-storage` (org `servdhost`); the plugin handle is `servd-asset-storage`.

The current release line (`4.2.x`, latest `4.2.4.2` as of 2026-03-24 — **Verify** the exact current version on Packagist) requires `craftcms/cms: ^5.0` and PHP `^8.2`, i.e. it targets Craft 5. Earlier `4.x` releases target Craft 4 and the `3.x` line targets Craft 3.

## Credentials

The plugin authenticates with two values from the **Assets page of the Servd dashboard** (`https://app.servd.host/project-assets` — **Verify** the exact dashboard URL):

```bash
SERVD_PROJECT_SLUG="your-project-slug"
SERVD_SECURITY_KEY="your-security-key"
```

Set these as environment variables (the preferred approach — see `deploy-and-environments.md` for how Servd injects env vars per environment). The plugin also accepts them entered directly in the CP, but that persists them to project config and is discouraged for secrets.

## The Servd filesystem and volumes

After install, create a **Filesystem** of the "Servd Asset Storage" type (Settings → Filesystems → New filesystem), then attach a **Volume** to it (Settings → Assets → Volumes). In Craft 3 these were called Volumes directly; Craft 4+ splits the storage backend (Filesystem) from the content container (Volume). In Craft 5 you always create the Filesystem first and point one or more Volumes at it.

The plugin **automatically separates assets into `local`, `staging`, and `production` directories** within the Servd Assets Platform, keyed to the environment the asset was uploaded from. This means editing or deleting assets in one environment never affects another, and assets can be carried along in clone operations.

## Asset URLs and the CDN

Assets are served from the Servd CDN. The default Asset Base URL pattern is:

```
https://<project-slug>.files.svdcdn.com
```

(Legacy V2 projects use `https://cdn2.assets-servd.host`.) If you serve assets from a custom domain, the URL pattern supports these placeholders:

| Placeholder | Resolves to |
|---|---|
| `{{environment}}` | `local`, `development`, `staging`, or `production` (auto-detected, or forced) |
| `{{subfolder}}` | the Subfolder field configured on the filesystem |
| `{{filePath}}` | the combined subpath and filename |
| `{{params}}` | transform query parameters — **transform URL pattern only** |

Example custom patterns:

```
CDN:       https://files.yourdomain.com/{{environment}}/{{subfolder}}/{{filePath}}
Transform: https://images.yourdomain.com/{{environment}}/{{subfolder}}/{{filePath}}{{params}}
```

## Off-server image transforms

Image transforms are **zero-config and generated off-server** by the Servd Asset Platform, then cached and delivered from the CDN. Native Craft transforms — `asset.getUrl({width: 800})`, named transforms, ad-hoc transforms from Twig or PHP — work transparently with no template changes: the plugin intercepts the URL and returns a CDN transform URL, and the edge generates (and caches) the result on first request.

For richer transform syntax, the plugin ships two integrations:

- **Imager-X** — set `transformer: 'servd'` in `config/imager-x.php` to route Imager-X transforms through Servd's platform (requires an Imager-X Pro license; only works with assets on a Servd volume):

  ```php
  <?php

  return [
      'transformer' => 'servd',
  ];
  ```

- **ImageOptimize** — an integration that hands optimization off to the Servd platform.

Neither is required for basic transforms; native Craft transforms already run off-server.

## Other plugin features

Beyond storage and transforms, the plugin layers in several Servd-platform helpers:

- **CSRF token injection** to keep forms working under static caching.
- **Automatic static-cache busting** on entry save events (see `caching.md` for how this ties into Servd's static cache).
- **Debug bar support** in load-balanced environments.
- **Easy dynamic content includes** when static caching is enabled.

Last verified against https://servd.host/docs and `servdhost/craft-asset-storage` on 2026-05-30.
