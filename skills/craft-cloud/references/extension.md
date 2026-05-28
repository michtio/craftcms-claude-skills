# The `craftcms/cloud` Extension Package

The Yii2 module that adapts Craft to run on Cloud's serverless infrastructure. It auto-bootstraps when present, overrides Craft components for the Lambda environment, and surfaces a few Cloud-specific APIs (`App::isEphemeral()`, `cloud.esi(...)`, the Cloud filesystem types).

## Source & docs

- Source: https://github.com/craftcms/cloud-extension-yii2
- Composer: `craftcms/cloud` (type `yii2-extension`)
- Docs: https://craftcms.com/docs/cloud/extension
- Plugin development guidance: https://craftcms.com/docs/cloud/plugin-development

This reference is verified against `craftcms/cloud-extension-yii2@main` on 2026-05-28 — the docs page is intentionally light, so most of what follows comes from reading the source directly.

## Table of contents

- [Common Pitfalls](#common-pitfalls)
- [What the extension provides](#what-the-extension-provides)
  - [Auto-bootstrap behavior](#auto-bootstrap-behavior)
- [Ephemeral filesystem](#ephemeral-filesystem)
  - [How to check](#how-to-check)
  - [Path service for transient writes](#path-service-for-transient-writes)
  - [The pattern in plugin code](#the-pattern-in-plugin-code)
- [`cloud.esi(...)` — Edge Side Includes](#cloudesi--edge-side-includes)
  - [Signature](#signature)
  - [Constraints](#constraints)
  - [Mechanics under the hood](#mechanics-under-the-hood)
- [`cloud/up` — what runs during the Migrate phase](#cloudup--what-runs-during-the-migrate-phase)
  - [Hooking the deploy events from a plugin](#hooking-the-deploy-events-from-a-plugin)
- [Console commands the extension adds](#console-commands-the-extension-adds)
- [Filesystem types](#filesystem-types)
- [Binary responses — `sendContentAsFile()` auto-upload](#binary-responses--sendcontentasfile-auto-upload)
- [What the extension does NOT provide](#what-the-extension-does-not-provide)

## Common Pitfalls

- Installing `craftcms/cloud` manually and committing it. Use `php craft setup/cloud` (or the equivalent project-config flow) so the extension's config files and `craft-cloud.yaml` get scaffolded together.
- Trying to `\craft\cloud\Module::getInstance()` before the bootstrap completes. The module sets itself as Yii's instance early in `bootstrap()`, but module-scoped APIs aren't usable until `init()` finishes. Reach for them in `Craft::$app->getResponse()`-style callsites, not at plugin construction time.
- Writing to disk without `App::isEphemeral()` guards. Lambda's filesystem is ephemeral; writes outside Craft's path service don't persist across requests. See [Ephemeral filesystem](#ephemeral-filesystem) below.
- Logging to files via custom Monolog channels. The extension routes `Craft::info/warning/error()` to a Cloud-managed log target; bypassing that loses the output.

## What the extension provides

The `craft\cloud\Module` class is a `\yii\base\Module` with `BootstrapInterface`. When the package is installed, Yii auto-bootstraps it. The module:

- Registers a Twig extension exposing `cloud.*` template helpers (most notably `cloud.esi(...)`).
- Registers Craft components: `staticCache` (edge cache invalidation), `urlSigner` (presigned-URL generation for assets).
- Hooks element events to enable Cloud-native image transforms via the `ImageTransformer` and `ImageTransformBehavior` classes.
- Caps execution: 60 seconds for web requests, 890 seconds (15 minutes minus a 10s buffer) for CLI commands. These match the documented Cloud limits and ensure PHP times out before Lambda kills the process.
- Auto-wires filesystem types (`AssetsFs`, `BuildsFs`, `CpResourcesFs`, `StorageFs`, `TmpFs`, etc.) so user assets, build artifacts, CP resources, and Craft's storage path all point to the right S3-backed locations.
- Routes logs to Cloud's log target via `craft\log\MonologTarget`.

### Auto-bootstrap behavior

The module bootstraps differently for web vs console requests — `controllerNamespace` is set to `craft\cloud\controllers` (web) or `craft\cloud\cli\controllers` (console). Local development is detected automatically and the bootstrap is largely a no-op locally; you can leave the extension installed in your dev environment without it hijacking your local DDEV setup.

## Ephemeral filesystem

Cloud runs Craft on AWS Lambda — disk writes are not durable across requests. Craft sets the `CRAFT_EPHEMERAL` environment variable on Cloud so application code can detect the environment.

### How to check

```php
use craft\helpers\App;

if (App::isEphemeral()) {
    // We're on Cloud (or any other environment that flags itself ephemeral).
    // Don't write to disk except through the Path service.
}
```

### Path service for transient writes

When you do need a transient write (a temp file for processing, a scratch directory for an export, etc.), use Craft's Path service. On Cloud, these paths are backed by the appropriate filesystem types — temp files go to `TmpFs`, runtime storage goes to `StorageFs`, etc.

```php
$tempPath = Craft::$app->getPath()->getTempPath();
$storagePath = Craft::$app->getPath()->getStoragePath();
$cachePath = Craft::$app->getPath()->getCachePath();
```

Anything written outside these paths — `file_put_contents('/var/log/myplugin.log', ...)`, `mkdir(__DIR__ . '/cache')`, etc. — is lost when Lambda recycles the container, which can happen between any two requests.

### The pattern in plugin code

The skill-creator pattern is: **gate every disk write on a single check at the top of the function, then use the Path service for the actual write**.

```php
public function exportToFile(string $filename): string
{
    if (App::isEphemeral()) {
        $path = Craft::$app->getPath()->getTempPath() . '/' . $filename;
    } else {
        $path = $this->_legacyLocalExportPath . '/' . $filename;
    }

    file_put_contents($path, $this->_buildExport());

    return $path;
}
```

For plugins that target Cloud as a first-class environment, drop the fallback branch — use the Path service unconditionally. The Path service works correctly on self-hosted Craft too.

## `cloud.esi(...)` — Edge Side Includes

A Twig helper for embedding dynamic content inside an edge-cached page. The edge cache serves the surrounding HTML; the ESI fragment is rendered fresh per request via a signed subrequest.

```twig
{# Cached page with a dynamic island #}
{% expires in 1 hour %}

<header>{{ siteName }}</header>

<aside>
    {# This fragment is re-rendered every request, even when the rest is cached #}
    {{ cloud.esi('_partials/account-nav.twig') }}
</aside>

<main>{{ content|raw }}</main>

{# Passing scalar variables (IDs/handles only — no objects, no collections) #}
{{ cloud.esi('_partials/recommendations.twig', { sourceId: entry.id }) }}
```

### Signature

`cloud.esi(template, variables = {})` — first arg is a Twig template path resolved like any `include`; second arg is an optional object of **scalar** variables.

### Constraints

- **Scalar variables only.** Pass IDs or handles, re-fetch the full object inside the fragment.
- **No parent context inheritance.** The fragment runs as a fresh subrequest; variables must be passed explicitly.
- **`text/html` and `text/plain` responses only.** ESI tags are only parsed in those response types.
- **No nesting.** Don't put `cloud.esi(...)` inside another ESI fragment.

For the full ESI surface (when to use vs avoid, behavior at the gateway, cookie-forwarding caveats), see `caching-and-edge.md`.

### Mechanics under the hood

`cloud.esi(...)` dispatches to `craft\cloud\Esi` (the Twig variable) and the matching `craft\cloud\controllers\EsiController` (the subrequest handler). The helper emits a signed `<esi:include>` tag at the edge, which the gateway resolves by making a tamper-protected subrequest. You don't write a controller — point `cloud.esi(...)` at any internal Twig template and the controller handles dispatch.

## `cloud/up` — what runs during the Migrate phase

`php craft cloud/up` is invoked automatically during the Migrate phase of a deploy. Verified from `craftcms/cloud-extension-yii2/src/cli/controllers/UpController.php`:

```text
1. trigger EVENT_BEFORE_UP (cancelable — plugins can abort the deploy)
2. run craft setup/php-session-table   (ensures PHP session table exists)
3. run craft setup/db-cache-table      (ensures DB cache table exists)
4. if Craft is installed:
     run craft up                       (migrations + project config)
     purge edge static cache
5. trigger EVENT_AFTER_UP (cancelable)
```

You don't run this command yourself in normal operation — it runs server-side during every deploy. The events are useful for plugins that need to hook deploys (e.g. invalidate a custom cache, post a deploy notification to Slack, recompute a derived index).

### Hooking the deploy events from a plugin

```php
use craft\cloud\cli\controllers\UpController;
use craft\events\CancelableEvent;
use yii\base\Event;

Event::on(
    UpController::class,
    UpController::EVENT_AFTER_UP,
    function (CancelableEvent $event) {
        // Runs once per successful deploy, after migrations + project config + cache purge.
        MyPlugin::getInstance()->getDeployNotifier()->notifySlack();
    }
);
```

The `EVENT_BEFORE_UP` variant is cancelable — setting `$event->isValid = false` in the handler aborts the deploy. Use sparingly; a cancelled migrate phase leaves the old version live but the build artifact is wasted.

## Console commands the extension adds

All under the `cloud` controller namespace (`php craft cloud/<command>`):

| Command | Purpose | Used by |
|---|---|---|
| `cloud/up` | Migrate phase entry point | Cloud's deploy pipeline (don't run manually) |
| `cloud/setup` | Initial extension wiring on a project | Developers, once per project (also accessible as `setup/cloud`) |
| `cloud/build` | Build phase entry point | Cloud's deploy pipeline |
| `cloud/asset-bundles` | Publishes asset bundles to the CDN | Build phase |
| `cloud/assets` | Asset operations | Internal |
| `cloud/queue` | Queue worker | Cloud's queue runner |
| `cloud/static-cache` | Static cache management | Manual cache operations |
| `cloud/info` | Diagnostics | Manual debugging via Console |

Most of these are infrastructure-only and you won't run them by hand. `cloud/info` and `cloud/static-cache` are the two worth knowing about manually — `cloud/info` reports environment details, and `cloud/static-cache` lets you purge or inspect the edge cache.

## Filesystem types

The extension provides several `craft\base\Fs` implementations, all S3-backed via Flysystem. The one you'll configure as a normal Craft filesystem (in the CP) is `AssetsFs`. The others are internal:

| FS class | Purpose |
|---|---|
| `craft\cloud\fs\AssetsFs` | **User-facing** — for asset volumes. Configure as a normal filesystem in the CP. |
| `craft\cloud\fs\BuildArtifactsFs` | Build artifact storage |
| `craft\cloud\fs\BuildsFs` | Build metadata |
| `craft\cloud\fs\CpResourcesFs` | CP asset bundles published to the CDN |
| `craft\cloud\fs\StorageFs` | Craft's `storage/` path |
| `craft\cloud\fs\TmpFs` | Temp paths |

See `assets-and-transforms.md` for how to configure `AssetsFs` for a Craft asset volume.

## Binary responses — `sendContentAsFile()` auto-upload

Plugins that serve binary content (file exports, generated PDFs, etc.) via `Craft::$app->getResponse()->sendContentAsFile(...)` get an automatic Cloud-friendly treatment: the extension uploads the binary to S3 and returns a 302 redirect to a pre-signed URL. This sidesteps Lambda's response-size cap (6MB) and the 60-second request timeout.

You don't need to write Cloud-specific code for this — `sendContentAsFile()` works the same way you'd use it on self-hosted Craft. The extension intercepts and rewrites the response transparently.

## What the extension does NOT provide

- **Mail.** No SMTP, no managed transactional email service. You configure your own mailer (Postmark, SES, SendGrid, Resend, etc.). See `limitations.md` (Mail).
- **A log-tailing UI.** Logs are routed to a Cloud-managed target, but the surfacing UI is the Console command runner's output history — there's no live tail view documented. See `limitations.md` (Logs).
- **A `craft-cloud` standalone CLI binary.** All Cloud-specific commands run through `php craft cloud/*` from inside the Craft application. There's no separate binary in `vendor/bin/` or PATH.

Last verified against `craftcms/cloud-extension-yii2@main` (composer.json, `src/Module.php`, `src/cli/controllers/UpController.php`, `src/fs/`, `src/twig/`) on 2026-05-28.
