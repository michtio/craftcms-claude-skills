# Plugin Development for Cloud Compatibility

Every constraint, recommendation, and pattern for shipping a Craft plugin that works on Cloud. Most of these are minor adjustments; a few require architectural changes (file writes, asset bundles, queue jobs).

## Documentation

- Plugin development: https://craftcms.com/docs/cloud/plugin-development
- Plugin store testing: https://plugins.craftcms.com/ (Console UI shows "Tested on Craft Cloud" flag)

## Table of contents

- [Common Pitfalls](#common-pitfalls)
- [Minimum Craft version](#minimum-craft-version)
- [Asset bundles](#asset-bundles)
  - [Register the bundle properly](#register-the-bundle-properly)
  - [What you can't do](#what-you-cant-do)
  - [composer.json type requirement](#composerjson-type-requirement)
- [File writes — `App::isEphemeral()` gating](#file-writes--appisephemeral-gating)
  - [Path service for transient writes](#path-service-for-transient-writes)
  - [Pattern for Cloud-first plugins](#pattern-for-cloud-first-plugins)
- [Logging](#logging)
- [Queue jobs](#queue-jobs)
- [Don't do synchronous external I/O in save hooks](#dont-do-synchronous-external-io-in-save-hooks)
- [CSRF and cookies](#csrf-and-cookies)
  - [Use `csrfInput()`, never raw token output](#use-csrfinput-never-raw-token-output)
  - [Avoid cookies on cacheable site requests](#avoid-cookies-on-cacheable-site-requests)
  - [Sessions](#sessions)
- [Binary responses — auto-handled](#binary-responses--auto-handled)
- [User-uploaded files](#user-uploaded-files)
- [The "Tested on Craft Cloud" flag](#the-tested-on-craft-cloud-flag)
- [Quick checklist](#quick-checklist)

## Common Pitfalls

- Publishing CP assets at runtime via `Craft::$app->getAssetManager()->publish(...)` or by writing files into `@webroot/cpresources`. The docs are explicit: "Publishing one-off or ad-hoc assets at runtime is **not** supported on Cloud." Use an asset bundle with a `sourcePath` rooted at your plugin's alias, registered via `registerAssetBundle()`.
- Building `<input type="hidden" name="CRAFT_CSRF_TOKEN" value="{{ craft.app.request.getCsrfToken() }}">` manually. The docs warn this "can leak one user's CSRF tokens to another" because Cloud's static cache fronts the page. Always use the `csrfInput()` function — Cloud force-enables `asyncCsrfInputs`, so the function emits an async-fetched input that's compatible with the cache.
- An asset bundle class that hits the database in its constructor or `init()`. Cloud builds run without DB access; the asset publisher needs to instantiate every bundle to publish it to the CDN. The docs: "Bundle classes must be instantiable _even if Craft is not installed, or cannot connect to a database_."
- Writing logs to a file via `file_put_contents()`, `error_log()`, or a custom Monolog file handler. Lambda's filesystem is ephemeral; the file vanishes before anyone reads it.
- A queue job that processes a large dataset linearly. The 15-minute cap hits, Lambda kills the process, Craft retries from scratch, same death. Use `BaseBatchedJob` and split into chunks.
- Making a synchronous external HTTP call inside `EVENT_AFTER_SAVE_ELEMENT` (or any save hook). A blocking, un-timeout-guarded call stalls every save — and during a resave or migration it stalls `cloud/up`, eating into the deploy's CLI cap. Queue it. See [Don't do synchronous external I/O in save hooks](#dont-do-synchronous-external-io-in-save-hooks).
- A controller that sets a cookie on a cacheable site request. Once the cookie is set, the response carries `Set-Cookie` and bypasses the edge cache for that user. If you really do need a cookie, accept the cache bypass — but check whether you can avoid the cookie via JS-driven personalization instead.

## Minimum Craft version

**Craft 4.6 or later.** Per the docs: "Plugins must support at least Craft 4.6 (the minimum version of Craft required to run on Cloud)."

If your plugin's `composer.json` requires `craftcms/cms: ^5` exclusively, you're already above the floor. Plugins targeting Craft 4 should set the constraint to `^4.6 || ^5`.

## Asset bundles

The single biggest rule: **all static assets must ship in an asset bundle**, with a `sourcePath` that begins with your plugin's predefined Composer alias.

```php
class MyPluginCpAsset extends AssetBundle
{
    public function init(): void
    {
        // sourcePath uses the plugin's alias, not a hardcoded path.
        $this->sourcePath = '@vendor/my-plugin/web/assets/cp/dist';

        $this->depends = [CpAsset::class];

        $this->js = ['my-plugin.js'];
        $this->css = ['my-plugin.css'];

        parent::init();
    }
}
```

### Register the bundle properly

```php
// In a controller action:
$this->getView()->registerAssetBundle(MyPluginCpAsset::class);

// Or in a Twig template:
{% do view.registerAssetBundle("vendor\\myplugin\\web\\assets\\MyPluginCpAsset") %}
```

The asset publisher (`AssetBundlePublisher` in the Cloud extension) walks every registered bundle at build time and uploads the files to the CDN. By release time, every `js`/`css`/`@webpack`-published file is already at a CDN URL.

### What you can't do

- **No runtime publishing.** No `Craft::$app->getAssetManager()->publish(...)` calls. No writes into `@webroot/cpresources`. The build-time publisher is the only path.
- **No assets outside the bundle path.** Files in `src/web/assets/cp/dist/` get published; files in `src/random/path/` don't.
- **No DB-dependent bundle classes.** The constructor and `init()` must work without a DB connection — the publisher runs in the build container, which has no DB access.

### composer.json type requirement

The plugin's `composer.json` must declare:

```json
{
    "type": "craft-plugin"
}
```

For downstream packages (libraries with their own asset bundles depended on by a plugin), the type must begin with `craft` or `yii`. Generic Composer packages (`library`, `project`, no type) won't have their assets discovered.

## File writes — `App::isEphemeral()` gating

Cloud sets `CRAFT_EPHEMERAL` in the environment. Detect it in code:

```php
use craft\helpers\App;

if (App::isEphemeral()) {
    $path = Craft::$app->getPath()->getTempPath();
} else {
    $path = $this->_legacyLocalPath;
}

file_put_contents($path . '/export.csv', $data);
```

### Path service for transient writes

```php
$path = Craft::$app->getPath();

$temp = $path->getTempPath();           // scratch space
$storage = $path->getStoragePath();     // longer-lived runtime state
$cache = $path->getCachePath();         // cached data
```

Don't hardcode paths under `__DIR__`, don't construct paths from `Yii::getAlias('@webroot/storage/...')`, don't use `sys_get_temp_dir()` (which works but bypasses Craft's machinery). Use the Path service uniformly — it works on self-hosted Craft too, so plugins that target Cloud also stay portable.

### Pattern for Cloud-first plugins

If your plugin targets Cloud as a first-class environment, drop the `if (App::isEphemeral())` fallback. Use the Path service unconditionally — it produces correct paths on every Craft deployment, Cloud or self-hosted.

## Logging

Use Craft's logger, not files:

```php
Craft::info('Sync completed: ' . $count . ' records', __METHOD__);
Craft::warning('Skipped row: ' . $id, __METHOD__);
Craft::error('API call failed: ' . $e->getMessage(), __METHOD__);
```

Or for structured logs:

```php
Craft::$app->getLogger()->log(
    'API call failed',
    \yii\log\Logger::LEVEL_ERROR,
    'my-plugin',
);
```

These route to Cloud's log target automatically. Files written to `storage/logs/myplugin.log` (or anywhere else) disappear when Lambda recycles the container — which can happen between any two requests, often within seconds.

## Queue jobs

Cloud auto-processes queue jobs (no scheduled runner needed). Constraints:

- **15-minute per-job cap.** Lambda kills jobs at 15 minutes.
- **Use batched jobs** for long-running work. `BaseBatchedJob` is the canonical pattern.
- **Don't assume a job will run to completion.** Design for resumption — record progress to the DB so a killed job's retry picks up where it stopped, not from scratch.

For the full queue-job authoring pattern (TTR, retries, progress reporting, batched jobs), see the `craftcms` skill's `queue-jobs.md`.

## Don't do synchronous external I/O in save hooks

A blocking external call in an element save hook is a latent stall everywhere, but on Cloud it's specifically a deploy hazard. This applies equally to the element-level event (`Element::EVENT_AFTER_SAVE`) and the service-level event (`Elements::EVENT_AFTER_SAVE_ELEMENT`) — the example below uses the element event, but the hazard is the same for both. The pattern to avoid:

```php
// Wrong — synchronous, un-timeout-guarded HTTP on every element save.
Event::on(
    Entry::class,
    Element::EVENT_AFTER_SAVE,
    function (ModelEvent $event) {
        // Blocks the request until the remote responds (or hangs).
        $this->_searchClient->upsert($event->sender);
    }
);
```

Why it bites harder on Cloud:

- **It stalls the request.** Web requests have a 60s cap; a slow or hanging upstream burns it on every save.
- **It stalls deploys.** A bulk `resave/entries`, or a content migration that saves elements, fires the same hook once per element — each one now waits on the network. Run during `cloud/up`, that serialized latency eats the deploy's CLI cap (≈890s) and can fail the Migrate phase outright.
- **It can't be retried cleanly.** A save half-succeeds (element written, remote call failed) with no built-in recovery.

Queue the work instead — the save hook should enqueue, not perform, the external call:

```php
Event::on(
    Entry::class,
    Element::EVENT_AFTER_SAVE,
    function (ModelEvent $event) {
        // Don't enqueue for drafts/revisions/propagating saves.
        if ($event->sender->getIsDraft() || $event->sender->getIsRevision() || $event->sender->propagating) {
            return;
        }

        Craft::$app->getQueue()->push(new SyncToSearchJob([
            'elementId' => $event->sender->id,
            'siteId' => $event->sender->siteId,
        ]));
    }
);
```

The job runs asynchronously (Cloud auto-processes the queue), carries its own TTR and retry semantics, and keeps both request handling and `cloud/up` off the network's critical path. If the call must be guarded inline for some reason, set an explicit short timeout on the HTTP client and swallow/log failures — never let a save block indefinitely on a third party.

## CSRF and cookies

### Use `csrfInput()`, never raw token output

```twig
{# Right — generates the async-CSRF-compatible input #}
<form method="post">
    {{ csrfInput() }}
    {# ... #}
</form>

{# Wrong — direct token output bypasses async handling and can leak tokens across users behind the edge cache #}
<form method="post">
    <input type="hidden" name="CRAFT_CSRF_TOKEN" value="{{ craft.app.request.getCsrfToken() }}">
</form>
```

The docs warn explicitly: building the input manually "can leak one user's CSRF tokens to another." This isn't theoretical — Cloud's edge cache will serve cached HTML to multiple users, and a baked-in token belongs to whoever generated the cache entry.

### Avoid cookies on cacheable site requests

Setting a cookie via `setcookie()` or `Craft::$app->getResponse()->getCookies()->add(...)` on a site request emits `Set-Cookie`, which busts the edge cache for that user. If the page would otherwise be cacheable, the cookie cost is high.

Alternatives:
- Use JS to read/write cookies client-side after the cached HTML loads.
- Use localStorage for things that don't need to round-trip to the server.
- Accept the cache bypass if the cookie is genuinely required (e.g. authenticated session pages).

For CP-only plugins (admin tools, not site-facing), cookies are fine — CP requests bypass the static cache by default.

### Sessions

Avoid touching `$_SESSION` or `Craft::$app->getSession()` on cacheable site requests. Reading `currentUser` is fine — Craft handles the bypass automatically. Writing flash messages or storing data in session forces a cookie and breaks caching.

## Binary responses — auto-handled

If your plugin sends file downloads via `Craft::$app->getResponse()->sendContentAsFile(...)`, Cloud's extension intercepts and:

1. Uploads the binary to S3.
2. Returns a 302 redirect to a pre-signed URL.

The user's browser follows the redirect and downloads from S3 directly. This sidesteps Lambda's 6MB response cap and 60-second request timeout.

You write standard Craft code:

```php
return Craft::$app->getResponse()->sendContentAsFile(
    $this->generateZipBytes(),
    'export.zip',
    ['mimeType' => 'application/zip']
);
```

No Cloud-specific branch needed. The extension does the right thing on both Cloud and self-hosted Craft.

## User-uploaded files

Prefer **asset selection inputs** (a Craft Assets field) over direct file-upload handling in your controllers. Reasons:

- The Assets field is integrated with Cloud's filesystem — uploads go straight to S3.
- Validation, mime-type checking, virus scanning (if configured) are handled by Craft.
- The user gets a familiar UI.

If you must handle uploads directly:

- Process them inside a request that doesn't get cached.
- Move them to a Cloud-backed filesystem via the Asset service.
- Don't store uploads on the local Lambda disk — they vanish.

## The "Tested on Craft Cloud" flag

After your plugin is verified to work on Cloud, check the **Tested on Craft Cloud** flag in Craft Console under your plugin's listing. This surfaces a badge in the plugin store and signals to customers that your plugin is Cloud-ready.

There's no automated certification process — the flag is a self-attestation by the plugin author, ideally after testing on an actual Cloud project.

## Quick checklist

When auditing a plugin for Cloud compatibility:

- [ ] `composer.json` `type` is `craft-plugin`
- [ ] `composer.json` requires `craftcms/cms: ^4.6 || ^5` (or higher)
- [ ] All static assets ship in an asset bundle with `sourcePath` using the plugin's alias
- [ ] Asset bundle classes instantiate without DB access
- [ ] No runtime `publish()` calls or writes to `@webroot/cpresources`
- [ ] Every disk write goes through `Craft::$app->getPath()->...` (or is gated by `App::isEphemeral()`)
- [ ] Logs use `Craft::info/warning/error()`, never files
- [ ] Queue jobs respect the 15-minute cap (split with `BaseBatchedJob` if long)
- [ ] CSRF inputs use `csrfInput()` function, never raw token output
- [ ] No cookies set on cacheable site requests
- [ ] No session writes on cacheable site requests
- [ ] Binary responses use `sendContentAsFile()` (auto-handled by extension)
- [ ] User uploads use Assets field, not direct file handling

Last verified against https://craftcms.com/docs/cloud/plugin-development on 2026-05-28.
