# `craft-cloud.yaml` — The Cloud Configuration File

The single platform-level config file Cloud reads. Lives at the repo root. Drives the build container, runtime web server, edge static cache, and URL rewrites.

## Documentation

- Configuration reference: https://craftcms.com/docs/cloud/config
- Static caching rules: https://craftcms.com/docs/cloud/static-caching
- Redirects and rewrites: https://craftcms.com/docs/cloud/redirects

## Common Pitfalls

- Putting it anywhere other than the repo root. Cloud looks for `craft-cloud.yaml` at the repo root only.
- Omitting `php-version`. It's the one required key — builds fail without it.
- Setting `node-version` without `npm-script` when your `package.json` doesn't have a `build` script. The default `npm-script` is `build`; if your build script is named differently (e.g. `production`), set `npm-script: production` explicitly.
- Leaving `webroot` set to the wrong directory after restructuring. Default is `web`. Common drift case: project moved to `public/` but `webroot` not updated.
- Trying to add post-deploy hooks or shell commands in `craft-cloud.yaml`. Not supported — there are no `build-hooks` / `post-deploy` / `commands` keys. Use the Console scheduled commands for recurring tasks; for one-off post-deploy work, run it manually in Console after the deploy completes.
- Treating `redirects:` / `rewrites:` as a `.htaccess` replacement for arbitrary rules. They're limited to simple from/to mappings — complex conditional rewrites aren't supported.

## Minimal viable config

```yaml
php-version: "8.3"
```

That's it. Everything else is optional with sensible defaults.

## All keys

| Key | Type | Default | Purpose |
|---|---|---|---|
| `php-version` | string (required) | — | PHP version for build + runtime. Quoted to keep `"8.3"` from being parsed as a number. |
| `node-version` | string | (no Node) | Node version. **Setting this triggers `npm clean-install` + `npm run <npm-script>` during build.** Omit if your project doesn't need a build step. |
| `node-path` | string | repo root | Directory to `cd` into before running `npm` commands. Set this when `package.json` lives in a subdirectory (e.g. `frontend/`). |
| `npm-script` | string | `build` | The npm script name to run. Override when your script is named `production`, `dist`, etc. |
| `artifact-path` | string | (whole project) | Path or paths to upload as the deploy artifact after the build phase. Useful for excluding `node_modules` or source files. |
| `app-path` | string | repo root | Where Craft's PHP application lives if not at the repo root. |
| `webroot` | string | `web` | The public document root, relative to `app-path`. Update if you've renamed `web/` to `public/`. |
| `cache.rules` | list | (no rules) | Edge static caching rules — see [Static Cache Rules](#static-cache-rules) below. |
| `redirects` | list | (none) | URL redirects — see [Redirects](#redirects) below. |
| `rewrites` | list | (none) | URL rewrites — see [Rewrites](#rewrites) below. |

## Worked example

A typical Craft site with a Vite build, custom webroot, and edge caching for the marketing pages:

```yaml
php-version: "8.3"

node-version: "20"
npm-script: build

webroot: web

cache.rules:
  - pattern: "/account/*"
    query-string:
      mode: include
      keys: all
  - pattern: "/blog/*"
    query-string:
      mode: exclude
      keys:
        - utm_source
        - utm_medium
        - utm_campaign
  - pattern: "/*"
    query-string:
      mode: exclude
      keys: all

redirects:
  - from: "/old-blog/(.*)"
    to: "/blog/$1"
    status: 301

rewrites:
  - from: "/legacy-api/(.*)"
    to: "/api/v1/$1"
```

## Static cache rules

The `cache.rules` list controls how the edge layer keys cached responses. Each rule needs a `pattern` plus at least one of `query-string` or `session`.

**Important — duration is not a `cache.rules` key.** How long to cache is set in the response itself, via the `{% expires %}` Twig tag or `$this->response->getHeaders()->set('Cache-Control', ...)` in a controller. `cache.rules` controls *what to cache*, not *for how long*.

**Order matters — first match wins.** List rules from most specific to least specific.

```yaml
cache.rules:
  - pattern: "/search"
    query-string:
      mode: include
      keys:
        - q
        - category
  - pattern: "/blog/*"
    query-string:
      mode: exclude
      keys:
        - utm_source
        - utm_medium
    session:
      - AD_SOURCE
  - pattern: "/*"
    query-string:
      mode: exclude
      keys: all
```

For the full cache-rules surface (every `mode` value, session-cookie semantics, opt-out mechanisms, ESI), see `caching-and-edge.md`.

## Redirects

Server-level HTTP redirects, evaluated before the request reaches PHP.

```yaml
redirects:
  - from: "/old-page"
    to: "/new-page"
    status: 301
  - from: "/blog/(.*)"
    to: "/articles/$1"
    status: 302
```

- `from` — path pattern. Supports regex capture groups.
- `to` — destination. Use `$1`, `$2`, etc. for captures.
- `status` — `301` for permanent, `302` for temporary. Choose based on whether the change is final.

## Rewrites

Internal URL rewrites — the user sees the original URL, the server serves a different one. Use sparingly; redirects are usually clearer for content moves.

```yaml
rewrites:
  - from: "/api/legacy/(.*)"
    to: "/api/v1/$1"
```

Same `from` / `to` semantics as redirects, but no status code (the URL doesn't change in the browser).

## What `craft-cloud.yaml` does NOT configure

- Environment variables — those live in the Craft Console UI per environment, not in this file. See `deploy-pipeline.md` (Build-time vs runtime variables).
- Database connection — auto-wired by the Cloud extension. Don't set `CRAFT_DB_*` vars; don't touch `config/db.php`.
- Mail — Cloud has no built-in mail service. Configure your own SMTP transport in `config/app.php` or via env vars. See `limitations.md` (Mail).
- Custom domains — added via the Craft Console UI, not this file. See `domains.md`.
- Scheduled commands — managed in Craft Console under Commands → Scheduled Commands. See `commands-and-cron.md`.
- Queue runner — auto-handled by Cloud. No queue daemon to configure.
- Asset filesystem details — configured as a normal Craft filesystem using the Cloud extension's `AssetsFs` type. See `assets-and-transforms.md`.

Last verified against https://craftcms.com/docs/cloud/config on 2026-05-28.
