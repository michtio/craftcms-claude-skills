# GeneralConfig Reference — System, Routing & Infrastructure

System, routing, security, users, sessions, search, assets, and image settings for `config/general.php` in Craft CMS 5. Uses the fluent API via `GeneralConfig::create()`. For content, templates, performance, GraphQL, and remaining settings, see `config-general-extended.md`. For how config files are loaded and environment variables work, see `config-bootstrap.md`.

Every public property on `GeneralConfig` maps to a `CRAFT_{UPPER_SNAKE_CASE}` environment variable automatically. For example, `elevatedSessionDuration` maps to `CRAFT_ELEVATED_SESSION_DURATION`. The env var always wins over the config file value.

## Documentation

- General config reference: https://craftcms.com/docs/5.x/reference/config/general.html
- GeneralConfig API: https://docs.craftcms.com/api/v5/craft-config-generalconfig.html

## Common Pitfalls

- `allowAdminChanges(true)` in production -- schema changes made in CP won't sync to project.yaml
- `devMode(true)` in production -- verbose errors expose internals, massive log files
- `runQueueAutomatically(true)` on high-traffic -- ties up PHP workers, use a daemon instead
- `defaultSearchTermOptions` with `subLeft => true` on large datasets -- forces `LIKE '%term%'` instead of fulltext `MATCH/AGAINST`, causing >100s queries on 50k+ entries
- `softDeleteDuration(0)` -- means "never hard-delete" not "delete immediately" -- soft-deleted items stay forever
- Changing `slugWordSeparator` or `limitAutoSlugsToAscii` mid-project -- existing slugs don't update, URLs break
- `disabledPlugins` set per-environment -- causes schema version mismatches across environments
- `safeMode` vs `allowAdminChanges` confusion -- safeMode disables ALL plugins and config modifications
- Not setting `baseCpUrl` when the CP is on a different domain -- action URLs break in headless and multi-domain setups
- `maxGraphqlComplexity`, `maxGraphqlDepth`, and `maxGraphqlResults` all default to `0` (unlimited) -- denial-of-service vector in production

## Contents

1. [System & Environment](#1-system--environment)
2. [Routing & URLs](#2-routing--urls)
3. [Security & Authentication](#3-security--authentication)
4. [Users & Sessions](#4-users--sessions)
5. [Account Paths](#5-account-paths)
6. [Search](#6-search)
7. [Assets & Uploads](#7-assets--uploads)
8. [Image Handling](#8-image-handling)

**Continued in `config-general-extended.md`:** Content & Editing, Templates, Performance, Garbage Collection, Localization, Aliases, Headless & GraphQL, Accessibility, Preview, Development, Dangerous Interactions.

---

## 1. System & Environment

| Setting | Type | Default | Purpose |
|---------|------|---------|---------|
| `devMode` | `bool` | `false` | Verbose errors, debug toolbar, expanded logging. Never `true` in production. |
| `isSystemLive` | `bool\|null` | `null` | Override System Status from CP. `null` = use CP setting. `true`/`false` = override. |
| `safeMode` | `bool` | `false` | Disables all plugins and config modifications. For troubleshooting only. (Since 5.1.0) |
| `allowAdminChanges` | `bool` | `true` | Allow schema/plugin changes in CP. Set `false` in production. |
| `allowUpdates` | `bool` | `true` | Allow one-click updates from CP. Auto-disabled when `allowAdminChanges` is `false`. |
| `buildId` | `?string` | `null` | Unique build identifier (Git SHA, deploy timestamp). Used for cache busting. (Since 4.0.0) |
| `disabledPlugins` | `string[]\|string\|null` | `null` | Plugin handles to disable regardless of project config. `'*'` disables all. Do NOT vary per-environment. |
| `disabledUtilities` | `string[]` | `[]` | Utility IDs to hide from CP. (Since 4.6.0) |
| `timezone` | `?string` | `null` | PHP timezone for display. Does NOT affect DB storage (always UTC). |
| `phpMaxMemoryLimit` | `?string` | `null` | Memory limit for heavy operations (transforms, updates). Only works if PHP's `memory_limit` isn't `-1`. |
| `limitAutoSlugsToAscii` | `bool` | `false` | Transliterate Unicode to ASCII in auto-generated slugs (JavaScript-side only). |
| `handleCasing` | `string` | `GeneralConfig::CAMEL_CASE` | Casing for auto-generated handles. Options: `CAMEL_CASE`, `PASCAL_CASE`, `SNAKE_CASE`. (Since 3.6.0) |
| `preloadSingles` | `bool` | `false` | Preload Single entries as Twig globals based on variable references. Clear compiled templates after changing. (Since 4.4.0) |
| `staticStatuses` | `bool` | `false` | Entry statuses only update on save or via `update-statuses` command, not dynamically. (Since 5.7.0) |
| `partialTemplatesPath` | `string` | `'_partials'` | Path within `templates/` for element partial templates used by `entry.render()`. (Since 5.0.0) |
| `errorTemplatePrefix` | `string` | `''` | Prefix for error template paths. E.g., `'_'` makes 404 look for `_404.twig`. |
| `translationDebugOutput` | `bool` | `false` | Wrap translated strings with `@@@` symbols to identify untranslated text. |
| `systemTemplateCss` | `?string` | `null` | URL to CSS file for system front-end templates (login, set password). (Since 5.6.0) |

`devMode` auto-enables `disallowRobots`. `safeMode` is stricter than `allowAdminChanges(false)` -- it disables plugins entirely. `allowAdminChanges` and `allowUpdates` are independent controls but `allowUpdates` is auto-disabled when `allowAdminChanges` is `false`. A locked-down production should have both `false`.

`isSystemLive` has three states: `null` defers to the CP System Status toggle. `true` forces the system live regardless of CP setting. `false` forces offline mode regardless. The offline page renders `templates/503.twig` if it exists, otherwise Craft's built-in offline template.

`staticStatuses` is a performance optimization for large sites. When enabled, Craft does not dynamically check whether scheduled entries should be live -- you must run `craft update-statuses` on a cron schedule (typically every minute) to flip statuses at the correct time.

`preloadSingles` works by analyzing compiled Twig templates for variable names matching Single entry handles. It then preloads those entries automatically. After changing this setting, you must clear compiled templates from the Caches utility, otherwise the setting has no effect. When enabled, templates can reference Singles directly as variables (e.g., `{{ homepage.heroTitle }}`) without an explicit element query.

Typical production `config/general.php`:

```php
use craft\config\GeneralConfig;
use craft\helpers\App;

return GeneralConfig::create()
    ->devMode(App::env('CRAFT_DEV_MODE') ?? false)
    ->allowAdminChanges(false)
    ->allowUpdates(false)
    ->runQueueAutomatically(false)
    ->buildId(App::env('BUILD_ID'));
```

---

## 2. Routing & URLs

| Setting | Type | Default | Purpose |
|---------|------|---------|---------|
| `cpTrigger` | `?string` | `'admin'` | URL segment for the control panel. Set `null` for CP-only domains. |
| `actionTrigger` | `string` | `'actions'` | URL segment for controller actions. |
| `omitScriptNameInUrls` | `bool` | `false` | Remove `index.php` from URLs (requires rewrite rules). |
| `addTrailingSlashesToUrls` | `bool` | `false` | Append trailing slashes to generated URLs. |
| `baseCpUrl` | `?string` | `null` | Explicit CP URL -- required when CP domain differs from site domain. |
| `loginPath` | `mixed` | `'login'` | Front-end login path. `false` to disable. |
| `logoutPath` | `mixed` | `'logout'` | Front-end logout path. `false` to disable. |
| `pageTrigger` | `string` | `'p'` | URL param or segment for pagination (`?p=2` or `/p2`). |
| `pathParam` | `?string` | `'p'` | Query param Craft checks for the request path. `null` for PATH_INFO-only routing. |
| `usePathInfo` | `bool` | `false` | Use PATH_INFO instead of query params in generated URLs. |
| `siteToken` | `string` | `'siteToken'` | Query param for requesting a specific site. |
| `tokenParam` | `string` | `'token'` | Query param for Craft tokens (preview, verification). |
| `indexTemplateFilenames` | `string[]` | `['index']` | Filenames Craft looks for as directory index templates. |
| `postLoginRedirect` | `mixed` | `''` | Redirect after front-end login. |
| `postCpLoginRedirect` | `mixed` | `'dashboard'` | Redirect after CP login. |
| `postLogoutRedirect` | `mixed` | `''` | Redirect after front-end logout. |

`cpTrigger` is configurable via `CRAFT_CP_TRIGGER` env var or `cpTrigger` in `config/general.php`. Default is `'admin'` but many projects use `'cp'` or other values. Set to `null` when the CP lives on a separate domain (e.g., `cms.example.com`) — all requests to that domain route to the CP without needing a path segment.

**Never hardcode `/admin/` in URLs.** Always use helpers:

```php
// PHP — use UrlHelper
use craft\helpers\UrlHelper;

UrlHelper::cpUrl('my-plugin/items');           // → {cpTrigger}/my-plugin/items
UrlHelper::actionUrl('my-plugin/api/sync');    // → {actionTrigger}/my-plugin/api/sync
```

```twig
{# Twig — use cpUrl() function #}
<a href="{{ cpUrl('my-plugin/items') }}">Manage Items</a>
```

CP URL rules registered via `EVENT_REGISTER_CP_URL_RULES` define paths *after* the trigger — the rule `'my-plugin/items/<itemId:\d+>'` resolves to `{cpTrigger}/my-plugin/items/123` at runtime. In documentation, write CP URLs as `{cpTrigger}/my-plugin/path`, not `/admin/my-plugin/path`.

If you change `cpTrigger` mid-project, update bookmarks, external integrations, and any documentation that references the old path.

`pageTrigger` behavior depends on whether `omitScriptNameInUrls` is `true`. When `true`, pagination uses path segments like `/p2`. When `false`, it uses query params like `?p=2`. The value must not conflict with any section URI patterns.

`pathParam` set to `null` forces Craft to rely entirely on `PATH_INFO` for routing. This requires Apache's `AcceptPathInfo On` or equivalent Nginx configuration. Most modern setups leave this at the default `'p'`. When using Nginx, the rewrite rule in your server block handles path routing regardless of this setting.

`baseCpUrl` is critical in multi-domain setups. Without it, Craft derives the CP URL from the incoming request. If your site is at `example.com` and your CP at `cms.example.com`, action URLs generated on the site domain will point to the wrong host. Always set this when `headlessMode` is `true`.

`tokenParam` controls the query parameter name for Craft tokens used in preview URLs, verification links, and other tokenized requests. Rarely needs changing unless it conflicts with another system's query parameter.

`postLoginRedirect` and `postCpLoginRedirect` support Twig object template syntax for dynamic redirects. For example, `postLoginRedirect('account/{currentUser.username}')` redirects to the user's profile page.

`addTrailingSlashesToUrls` only affects URLs generated by Craft (element URLs, pagination links). It does not enforce trailing slashes on incoming requests -- use server-level redirects (Nginx rewrite, `.htaccess`) for that. Mixing Craft-generated trailing slashes with server-enforced non-trailing slashes causes redirect loops.

---

## 3. Security & Authentication

| Setting | Type | Default | Purpose |
|---------|------|---------|---------|
| `securityKey` | `string` | `''` | Encryption key for cookies, sessions, encrypted fields. Use `CRAFT_SECURITY_KEY` env var. |
| `enableCsrfProtection` | `bool` | `true` | CSRF token validation. Never disable. |
| `enableCsrfCookie` | `bool` | `true` | Persist CSRF token in cookie. If `false`, stored in session (requires session start per page). |
| `csrfTokenName` | `string` | `'CRAFT_CSRF_TOKEN'` | Name of the CSRF token param/cookie. |
| `asyncCsrfInputs` | `bool` | `false` | Load CSRF tokens via AJAX. Required for full-page static caching. (Since 5.1.0) |
| `blowfishHashCost` | `int` | `13` | Password hash cost. Higher = slower/more secure. Time doubles per increment. |
| `sameSiteCookieValue` | `?string` | `null` | SameSite flag on cookies (`'Lax'`, `'Strict'`, `'None'`). |
| `secureHeaders` | `?array` | `null` | Headers subject to trusted host validation. |
| `secureProtocolHeaders` | `?array` | `null` | Headers checked for HTTPS detection behind proxies. |
| `permissionsPolicyHeader` | `?string` | `null` | Sets Permissions-Policy header. Deprecated since 4.11.0 -- use `craft\filters\Headers`. |
| `trustedHosts` | `array` | `['any']` | Hosts trusted for proxy headers. Default trusts all -- restrict in production. |
| `ipHeaders` | `?string[]` | `null` | Headers containing real client IP (e.g., `X-Forwarded-For`, `CF-Connecting-IP`). |
| `httpProxy` | `?string` | `null` | Proxy for outgoing HTTP requests. Format: `'http://host:port'`. |
| `enableBasicHttpAuth` | `bool` | `false` | Support HTTP Basic auth on front-end. Deprecated since 4.13.0. |
| `requireMatchingUserAgentForSession` | `bool` | `true` | Require matching user agent when restoring session from cookie. |
| `requireUserAgentAndIpForSession` | `bool` | `true` | Require user agent + IP to create a new session. |
| `useSecureCookies` | `bool\|string` | `'auto'` | Set 'secure' flag on cookies. `'auto'` = set when accessed via HTTPS. |
| `useSslOnTokenizedUrls` | `bool\|string` | `'auto'` | Force HTTPS on tokenized URLs. `'auto'` checks site base URL. |
| `sendPoweredByHeader` | `bool` | `true` | Send `X-Powered-By: Craft CMS` header. Disable to hide platform identity. |
| `sendContentLengthHeader` | `bool` | `false` | Send `Content-Length` header with responses. |
| `preventUserEnumeration` | `bool` | `false` | Return identical responses for valid/invalid usernames in forgot password. |
| `sanitizeSvgUploads` | `bool` | `true` | Strip scripts from SVG uploads. |
| `sanitizeCpImageUploads` | `bool` | `true` | Sanitize images uploaded in CP (user photos, etc). |
| `storeUserIps` | `bool` | `false` | Store user IP addresses in the system. (Since 3.1.0) |
| `enableTwigSandbox` | `bool` | `false` | Sandbox user-defined Twig templates against injection. (Since 5.9.0) |

`asyncCsrfInputs` must be `true` when using full-page static caching (Blitz). Without it, cached pages serve the original CSRF token which is invalid for other users. The `csrfInput()` Twig function outputs a placeholder `<input>` that is populated via AJAX from `actions/users/session-info`.

`trustedHosts` at `['any']` trusts all proxy headers -- restrict to your actual load balancer IPs in production. When behind a reverse proxy, you must configure `trustedHosts`, `ipHeaders`, and `secureProtocolHeaders` together:

```php
->trustedHosts(['10.0.0.0/8', '172.16.0.0/12'])
->ipHeaders(['X-Forwarded-For', 'CF-Connecting-IP'])
->secureProtocolHeaders([
    'X-Forwarded-Proto' => ['https'],
])
```

`securityKey` must be identical across all servers in the same environment. If it changes, all sessions, encrypted field values, and password reset tokens become invalid. Use `CRAFT_SECURITY_KEY` env var and never commit it to version control.

`blowfishHashCost` at `13` means each password hash takes ~0.1s on modern hardware. Increasing to `14` doubles that to ~0.2s. Going above `15` is rarely justified -- it slows logins noticeably without meaningful security gain against offline attacks.

`enableCsrfProtection` + `enableCsrfCookie` interact: the cookie is the storage mechanism for the CSRF token. If you set `enableCsrfCookie(false)`, every page that needs a CSRF token will start a PHP session, which can impact performance and cacheability.

`enableTwigSandbox` restricts what Twig code can do in user-defined templates (e.g., templates entered in CMS fields). It does not affect templates in the `templates/` directory.

`preventUserEnumeration` makes the forgot-password and login responses identical whether the email/username exists or not. Without it, an attacker can probe which emails have accounts by observing different error messages. Enable this on public-facing sites.

`storeUserIps` enables logging of user IP addresses in the `users_sessions` table and user activity logs. Some jurisdictions (GDPR) require explicit consent before storing IP addresses. Leave `false` unless you have a legal basis for storing them.

Production security baseline:

```php
->enableCsrfProtection(true)
->preventUserEnumeration(true)
->sanitizeSvgUploads(true)
->sanitizeCpImageUploads(true)
->sendPoweredByHeader(false)
->requireMatchingUserAgentForSession(true)
->requireUserAgentAndIpForSession(true)
->trustedHosts(['10.0.0.0/8'])  // Your actual load balancer CIDR
->ipHeaders(['X-Forwarded-For'])
->secureProtocolHeaders(['X-Forwarded-Proto' => ['https']])
```

---

## 4. Users & Sessions

| Setting | Type | Default | Purpose |
|---------|------|---------|---------|
| `userSessionDuration` | `mixed` | `3600` (1 hr) | Session duration in seconds. `0` = until browser closes. |
| `rememberedUserSessionDuration` | `mixed` | `1209600` (14 days) | Duration when "Remember Me" is checked. |
| `elevatedSessionDuration` | `mixed` | `300` (5 min) | Seconds of elevated session after password re-entry. `0` to disable. |
| `maxInvalidLogins` | `int\|false` | `5` | Failed logins before lockout. `false` to disable lockouts entirely. |
| `invalidLoginWindowDuration` | `mixed` | `3600` (1 hr) | Window for tracking failed login attempts. |
| `cooldownDuration` | `mixed` | `300` (5 min) | Lockout duration after `maxInvalidLogins` exceeded. `0` = indefinite until manual unlock. |
| `rememberUsernameDuration` | `mixed` | `31536000` (1 yr) | How long CP remembers username on login page. `0` to disable. |
| `useEmailAsUsername` | `bool` | `false` | Hide username field, use email as identifier. |
| `autoLoginAfterAccountActivation` | `bool` | `false` | Auto-login after account activation. |
| `deferPublicRegistrationPassword` | `bool` | `false` | Skip password on registration -- users set it after email verification. |
| `phpSessionName` | `string` | `'CraftSessionId'` | PHP session cookie name. |
| `showFirstAndLastNameFields` | `bool` | `false` | Show separate first/last name fields instead of single Full Name field. (Since 4.6.0) |
| `disable2fa` | `bool` | `false` | Disable two-factor authentication entirely. (Since 5.6.0) |
| `extraLastNamePrefixes` | `string[]` | `[]` | Additional last name prefixes for the name parser (e.g., `['van', 'von']`). (Since 4.3.0) |
| `extraNameSalutations` | `string[]` | `[]` | Additional name salutations for the name parser (e.g., `['Lady', 'Sire']`). (Since 4.3.0) |
| `extraNameSuffixes` | `string[]` | `[]` | Additional name suffixes for the name parser (e.g., `['CCNA', 'OBE']`). (Since 4.3.0) |

Duration settings accept several formats: integer seconds (`3600`), `DateInterval` string (`'PT1H'`), or human-readable shorthand (`'1 hour'`). Craft normalizes all of these via `ConfigHelper::durationInSeconds()`.

`elevatedSessionDuration` controls the window after re-entering a password during which Craft allows sensitive operations (changing passwords, managing user groups). Set to `0` to disable elevated sessions entirely -- not recommended for production.

`cooldownDuration` at `0` means indefinite lockout. The user must be manually unlocked by an admin or wait for the `invalidLoginWindowDuration` to expire and reset the counter.

`useEmailAsUsername` is common for front-end user registration flows. When enabled, the username field is hidden in the CP and email is used everywhere. Changing this mid-project on an existing user base can cause issues if usernames and emails differ.

`deferPublicRegistrationPassword` works with front-end registration forms. Instead of requiring a password at signup, the user receives an email with an activation link and sets their password then. Pair with `autoLoginAfterAccountActivation` for a seamless flow.

`disable2fa` completely removes two-factor authentication from the CP. Use sparingly -- this is a security regression. Intended for environments where 2FA is handled at a different layer (SSO, VPN).

Session duration values accept the same formats as other durations: integer seconds, `DateInterval` strings (`'PT1H'`), or human-readable strings (`'1 hour'`). For security-sensitive sites, shorter session durations are recommended:

```php
->userSessionDuration(1800)             // 30 minutes
->rememberedUserSessionDuration(604800) // 7 days
->elevatedSessionDuration(120)          // 2 minutes
```

`phpSessionName` rarely needs changing. The main use case is when multiple Craft installations share a domain and you need to prevent session cookie collisions. In that case, give each installation a unique session name.

---

## 5. Account Paths

Settings controlling where users are redirected during auth flows. All accept URI strings or `false` to disable. Per-site values are supported by passing an array keyed by site handle.

| Setting | Type | Default | Purpose |
|---------|------|---------|---------|
| `loginPath` | `mixed` | `'login'` | Front-end login page path. |
| `logoutPath` | `mixed` | `'logout'` | Front-end logout path. |
| `setPasswordPath` | `mixed` | `'setpassword'` | Front-end set/reset password form. |
| `setPasswordRequestPath` | `mixed` | `null` | Page where users request password change. Redirects `.well-known/change-password`. (Since 3.5.14) |
| `setPasswordSuccessPath` | `mixed` | `''` | Redirect after successful password set. |
| `activateAccountSuccessPath` | `mixed` | `''` | Redirect after account activation (non-CP users). |
| `verifyEmailPath` | `mixed` | `'verifyemail'` | Front-end email verification link path. (Since 3.4.0) |
| `verifyEmailSuccessPath` | `mixed` | `''` | Redirect after successful email verification. (Since 3.1.20) |
| `invalidUserTokenPath` | `mixed` | `null` | Redirect when verification/reset token is invalid or expired. Defaults to `loginPath`. |
| `postLoginRedirect` | `mixed` | `''` | Redirect after front-end login. |
| `postCpLoginRedirect` | `mixed` | `'dashboard'` | Redirect after CP login. |
| `postLogoutRedirect` | `mixed` | `''` | Redirect after front-end logout. |
| `verificationCodeDuration` | `mixed` | `86400` (1 day) | How long verification codes (email verify, password reset) remain valid. |

Per-site example:

```php
->loginPath([
    'english' => 'login',
    'french' => 'connexion',
])
```

When `setPasswordPath` is set, you must also set `invalidUserTokenPath` to handle expired or invalid tokens. Without it, users clicking an expired password-reset link see a generic error instead of being redirected to a helpful page.

`verificationCodeDuration` affects both email verification links and password reset links. Setting it too low (e.g., 1 hour) causes frequent "invalid token" errors for users who don't check email promptly. The default of 1 day is generous. For high-security applications, 2-4 hours is reasonable.

`activateAccountSuccessPath` and `verifyEmailSuccessPath` are often confused. `activateAccountSuccessPath` is for brand-new users activating their account for the first time. `verifyEmailSuccessPath` is for existing users verifying a changed email address. Both can be set to the same page, but distinguishing them allows for different messaging.

`setPasswordRequestPath` is used by `.well-known/change-password` -- a standard that password managers use to direct users to your site's password change page. Without this setting, the `.well-known/change-password` redirect does not work.

Complete front-end auth flow configuration:

```php
->loginPath('account/login')
->logoutPath('account/logout')
->setPasswordPath('account/set-password')
->setPasswordRequestPath('account/forgot-password')
->setPasswordSuccessPath('account/password-updated')
->activateAccountSuccessPath('account/welcome')
->verifyEmailPath('account/verify-email')
->verifyEmailSuccessPath('account/email-verified')
->invalidUserTokenPath('account/invalid-token')
->postLoginRedirect('account')
->postLogoutRedirect('/')
->autoLoginAfterAccountActivation(true)
->deferPublicRegistrationPassword(true)
```

---

## 6. Search

| Setting | Type | Default | Purpose |
|---------|------|---------|---------|
| `defaultSearchTermOptions` | `array` | `[]` | Default options applied to every search term. |

Sub-options for `defaultSearchTermOptions`:

| Key | Type | Default | Effect |
|-----|------|---------|--------|
| `subLeft` | `bool` | `false` | Match terms with preceding characters. **Forces `LIKE '%term%'` -- destroys performance on large datasets.** |
| `subRight` | `bool` | `true` | Match terms with following characters. Safe -- fulltext still used. |
| `exclude` | `bool` | `false` | Exclude matching records. |
| `exact` | `bool` | `false` | Require exact match only. |

MySQL fulltext indexes only work when there is no leading wildcard. `subLeft => true` adds a leading wildcard to every search, forcing a full table scan via `LIKE '%term%'` instead of using the FULLTEXT index with `MATCH() AGAINST()`. On a `searchindex` table with 50k+ rows, this means >100 second queries.

`subRight => true` (the default) is fine -- trailing wildcards still use the fulltext index.

The `minFullTextWordLength` on the search component (configured in `config/app.php` -- see the app config reference) interacts here: words shorter than this threshold silently fall back to `LIKE` regardless of `subLeft`. On MySQL, the default `ft_min_word_len` is 4, meaning searches for 1-3 character terms always use `LIKE`.

Only change `subLeft` to `true` on small datasets (<10k entries) where partial prefix matching genuinely matters. For large sites, implement a dedicated search solution (Algolia, Meilisearch, Elasticsearch) instead.

Example of safe configuration for CP search enhancement:

```php
->defaultSearchTermOptions([
    'subRight' => true,  // default, safe
    // 'subLeft' => true,  // DO NOT enable on large datasets
])
```

Note: These defaults only apply when no explicit search options are provided in the query. Element queries using `.search('*term*')` with explicit wildcards bypass these defaults.

---

## 7. Assets & Uploads

| Setting | Type | Default | Purpose |
|---------|------|---------|---------|
| `maxUploadFileSize` | `int\|string` | `16777216` (16 MB) | Max upload size. Accepts int (bytes) or string (`'64M'`). |
| `allowedFileExtensions` | `string[]` | (87 extensions) | File extensions allowed for upload. Replaces the entire default list when set. |
| `extraAllowedFileExtensions` | `string[]` | `[]` | Additional extensions beyond the default set. Preferred over overriding `allowedFileExtensions`. |
| `extraFileKinds` | `array` | `[]` | Define custom file categories. Must pair with `extraAllowedFileExtensions`. (Since 3.0.37) |
| `filenameWordSeparator` | `string\|false` | `'-'` | Separator for words in uploaded filenames. `false` = leave spaces. |
| `convertFilenamesToAscii` | `bool` | `false` | Transliterate Unicode to ASCII in uploaded filenames (e.g., cafe.jpg). |
| `brokenImagePath` | `?string` | `null` | Server path to fallback image for 404 image requests. Supports aliases. (Since 3.5.0) |
| `revAssetUrls` | `bool` | `false` | Append `?v={dateModified}` to asset URLs for cache busting. |
| `tempAssetUploadFs` | `?string` | `null` | Filesystem handle for temporary asset uploads. (Since 5.0.0) |

`maxUploadFileSize` is also constrained by PHP's `upload_max_filesize` and `post_max_size` ini settings. The effective limit is the lowest of all three. In DDEV, these PHP settings are configured via `.ddev/php/my-php.ini`.

`extraAllowedFileExtensions` is additive -- it appends to the default 87 extensions. Prefer this over `allowedFileExtensions` which replaces the entire list and requires you to maintain the full set.

`extraFileKinds` defines custom file groups for use in asset field restrictions:

```php
->extraFileKinds([
    'fonts' => [
        'label' => 'Fonts',
        'extensions' => ['woff', 'woff2', 'ttf', 'otf', 'eot'],
    ],
])
->extraAllowedFileExtensions(['woff', 'woff2', 'ttf', 'otf', 'eot'])
```

`tempAssetUploadFs` specifies an alternative filesystem for temporary uploads (before assets are moved to their final volume). Useful when the default local temp directory has size or permission constraints, or on ephemeral/read-only filesystems where local temp storage is not available.

`brokenImagePath` is served when an image asset returns 404 (deleted, moved, or transform not yet generated). Supports Yii aliases: `->brokenImagePath('@webroot/img/placeholder.png')`. Without this, missing images return a standard 404 response.

`revAssetUrls` appends `?v={dateModified}` to all asset URLs. This is a simple cache-busting mechanism that forces browsers to re-download assets when they change. When using a CDN with aggressive caching, this prevents stale assets from being served after updates. It is not necessary when using hashed filenames or a CDN that supports cache invalidation.

---

## 8. Image Handling

| Setting | Type | Default | Purpose |
|---------|------|---------|---------|
| `defaultImageQuality` | `int` | `82` | JPEG/WebP quality for transforms. |
| `imageDriver` | `mixed` | `'auto'` | Image processing library: `'auto'`, `'gd'`, or `'imagick'`. |
| `imageEditorRatios` | `array` | (see below) | Selectable aspect ratios in the image editor. Format: `label => ratio`. |
| `generateTransformsBeforePageLoad` | `bool` | `false` | Generate transforms inline instead of via queue. Slower page loads. |
| `maxCachedCloudImageSize` | `int` | `0` | Max dimension for cached cloud images. `0` = never cache. Default changed from `2000` to `0` in 5.9.0. |
| `optimizeImageFilesize` | `bool` | `true` | Strip unnecessary image data to reduce file size. |
| `upscaleImages` | `bool` | `true` | Allow transforms to upscale beyond original dimensions. |
| `rasterizeSvgThumbs` | `bool` | `false` | Rasterize SVG thumbnails. Requires ImageMagick. |
| `rotateImagesOnUploadByExifData` | `bool` | `true` | Auto-rotate images based on EXIF orientation on upload. |
| `preserveCmykColorspace` | `bool` | `false` | Preserve CMYK colorspace instead of converting to sRGB. ImageMagick only. (Since 3.0.8) |
| `preserveExifData` | `bool` | `false` | Preserve EXIF data when manipulating images. Increases file size. ImageMagick only. |
| `preserveImageColorProfiles` | `bool` | `true` | Preserve ICC color profiles when manipulating images. |
| `transformGifs` | `bool` | `true` | Whether GIF files should be transformed. Set `false` to skip GIF processing. |
| `transformSvgs` | `bool` | `true` | Whether SVG files should be transformed. (Since 3.7.1) |

Default `imageEditorRatios`:

```php
[
    'Unconstrained' => 'none',
    'Original' => 'original',
    'Square' => 1,
    '16:9' => 1.78,
    '10:8' => 1.25,
    '7:5' => 1.4,
    '4:3' => 1.33,
    '5:3' => 1.67,
    '3:2' => 1.5,
]
```

`imageDriver` at `'auto'` prefers ImageMagick when available, falling back to GD. ImageMagick supports more formats and operations (CMYK, EXIF, SVG rasterization). The `preserveCmykColorspace`, `preserveExifData`, and `rasterizeSvgThumbs` settings only work with ImageMagick.

`maxCachedCloudImageSize` was changed from `2000` to `0` in Craft 5.9.0. At `0`, Craft does not create local copies of remote images -- transforms are applied directly by the filesystem (e.g., S3/CloudFront). Set this to a nonzero value only if your cloud filesystem does not support transforms.

`generateTransformsBeforePageLoad` generates all image transforms synchronously during the page request instead of queueing them. This avoids 404s for transforms that haven't been generated yet, but blocks the request until all transforms are complete. On pages with many transforms, this can cause timeouts.

`transformGifs` at `false` means GIF files are served as-is, preserving animation. When `true`, transforms strip animation and output a single frame. Set to `false` if animated GIFs are important to your content.

`optimizeImageFilesize` at `true` strips metadata and unnecessary data from images during transforms. This reduces file size (sometimes significantly for photos with large EXIF payloads) but removes metadata that might be useful for attribution or rights management. If `preserveExifData` is also `true`, the EXIF data is kept while other optimizations still apply.

`preserveImageColorProfiles` at `true` (the default) keeps ICC profiles during transforms. Disabling this can reduce file size but may cause color shifts, especially for CMYK-origin images displayed on calibrated monitors. Leave `true` unless file size is critical and color accuracy is not.

ImageMagick vs GD comparison for transforms:

| Feature | GD | ImageMagick |
|---------|-----|-------------|
| CMYK support | No | Yes |
| EXIF preservation | No | Yes |
| SVG rasterization | No | Yes |
| Animated GIF handling | Limited | Full |
| WebP support | PHP 7.1+ | Yes |
| Memory usage | Lower | Higher |
| Color profile handling | Basic | Full |

---

