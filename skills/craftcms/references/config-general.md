# GeneralConfig Reference

Complete reference for all `config/general.php` settings in Craft CMS 5. Uses the fluent API via `GeneralConfig::create()`. For how config files are loaded and environment variables work, see `config-bootstrap.md`.

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
9. [Content & Editing](#9-content--editing)
10. [Templates](#10-templates)
11. [Performance & Maintenance](#11-performance--maintenance)
12. [Garbage Collection](#12-garbage-collection)
13. [Localization](#13-localization)
14. [Aliases & Resources](#14-aliases--resources)
15. [File Permissions & Cookies](#15-file-permissions--cookies)
16. [Headless & GraphQL](#16-headless--graphql)
17. [Accessibility](#17-accessibility)
18. [Preview](#18-preview)
19. [Development](#19-development)
20. [Dangerous Interactions](#dangerous-interactions)

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

`cpTrigger` can be set to `null` when the CP lives on a separate domain (e.g., `cms.example.com`). In this case, all requests to that domain route to the CP without needing a path segment. If you change `cpTrigger` mid-project, update any hardcoded CP URLs in bookmarks, documentation, or external integrations.

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

## 9. Content & Editing

| Setting | Type | Default | Purpose |
|---------|------|---------|---------|
| `autosaveDrafts` | `bool` | `true` | Auto-save drafts as authors edit. Disabling reduces DB writes but risks lost work. |
| `maxRevisions` | `?int` | `50` | Max entry revisions. `null` = unlimited. `0` = no revisions. |
| `maxSlugIncrement` | `int` | `100` | Max suffix number for slug collisions before using random string. |
| `slugWordSeparator` | `string` | `'-'` | Word separator in auto-generated slugs. |
| `allowUppercaseInSlug` | `bool` | `false` | Preserve uppercase in slugs. Default lowercases everything. |
| `allowSimilarTags` | `bool` | `false` | Allow similarly-named tags (e.g., "Design" and "design"). |
| `defaultWeekStartDay` | `int` | `1` (Monday) | 0=Sunday through 6=Saturday. Affects date picker UI. |
| `defaultCountryCode` | `string` | `'US'` | Default country for address fields. (Since 4.5.0) |
| `defaultTokenDuration` | `mixed` | `86400` (1 day) | Default token lifetime (preview, verification, etc). |
| `previewTokenDuration` | `mixed` | `null` | Preview token lifetime. Defaults to `defaultTokenDuration`. (Since 3.7.0) |

Changing `slugWordSeparator` or `limitAutoSlugsToAscii` mid-project does NOT update existing slugs. URLs break unless you set up redirects. Only change these before content exists or prepare a migration to update all existing slugs.

`maxRevisions` at `0` means Craft saves no revisions -- there is no undo for published changes. At `null`, revisions accumulate indefinitely, which can bloat the database significantly on active sites. The default `50` is a reasonable balance.

`autosaveDrafts` at `true` creates a draft and auto-saves it every 2 seconds while editing. This generates substantial DB write traffic. On sites with many concurrent editors, consider monitoring database load. Disabling it means unsaved changes are lost if the browser crashes or the tab is closed. Note that `autosaveDrafts` only affects the auto-save interval -- manual draft saving always works regardless.

`maxSlugIncrement` controls how Craft handles slug collisions. If "my-post" already exists, Craft tries "my-post-2", "my-post-3", etc., up to this number. After that, it appends a random string. The default `100` is generous -- collisions above `10` usually indicate a naming problem.

`defaultCountryCode` sets the initial value for Address fields. It does not validate or restrict which countries are available. Use field-level configuration to restrict country lists.

`defaultWeekStartDay` affects only the date picker UI in the CP. It does not change how Twig's `date` filter handles week calculations (those follow PHP's `intl` settings).

`previewTokenDuration` at `null` inherits from `defaultTokenDuration` (1 day). For headless setups where editors preview content on an external front-end, consider setting this shorter (e.g., 2 hours) to limit the window during which preview URLs are valid. See `headless.md` for the full preview token flow.

---

## 10. Templates

| Setting | Type | Default | Purpose |
|---------|------|---------|---------|
| `defaultTemplateExtensions` | `string[]` | `['twig', 'html']` | File extensions Craft looks for when resolving template paths. |
| `enableTemplateCaching` | `bool` | `true` | Enable `{% cache %}` tags. Disable in dev for convenience. |
| `privateTemplateTrigger` | `string` | `'_'` | Prefix identifying templates not directly accessible via URL. Empty string to disable. |
| `cpHeadTags` | `array` | `[]` | Inject HTML tags in CP `<head>`. Format: `[tagName, attributes]`. (Since 3.5.0) |

`enableTemplateCaching` at `false` makes all `{% cache %}` tags no-ops. The templates still render correctly, but no caching occurs. This is useful during development to avoid stale content. In production, leave it `true`. Note this only affects `{% cache %}` tags -- data caching (`craft.app.cache`) is controlled separately by `cacheDuration`.

`privateTemplateTrigger` at `'_'` means any template whose filename or directory name starts with `_` cannot be accessed directly via URL. The `_layouts/`, `_includes/`, `_partials/` convention works because of this. Set to empty string `''` to disable this protection (not recommended). Templates prefixed with `_` can still be included/extended from other templates -- they just can't be requested directly as a route target.

`cpHeadTags` injects tags into the CP's `<head>`. Common use: custom favicon or font loading:

```php
->cpHeadTags([
    ['link', ['rel' => 'icon', 'href' => '/favicon.ico']],
    ['link', ['rel' => 'stylesheet', 'href' => 'https://fonts.googleapis.com/css2?family=Inter']],
])
```

`defaultTemplateExtensions` controls which extensions Craft tries when resolving a template path. If you request `blog/index`, Craft looks for `blog/index.twig`, then `blog/index.html`. The order matters -- `.twig` is checked first by default. Adding more extensions (e.g., `['twig', 'html', 'xml']`) enables XML template rendering for feeds without explicit extensions in routes.

---

## 11. Performance & Maintenance

| Setting | Type | Default | Purpose |
|---------|------|---------|---------|
| `cacheDuration` | `mixed` | `86400` (1 day) | Default data cache duration. |
| `runQueueAutomatically` | `bool` | `true` | Trigger queue via web requests. Set `false` in production, use daemon. |
| `maxBackups` | `int\|false` | `20` | Max DB backups before oldest deleted. `false` = keep all. |
| `backupOnUpdate` | `bool` | `true` | Auto-backup DB before updates. |
| `backupCommand` | `string\|null\|false\|Closure` | `null` | Custom DB backup command. Supports `{file}`, `{port}`, `{server}`, `{user}`, `{password}`, `{database}`, `{schema}` placeholders. `false` to disable backups. |
| `backupCommandFormat` | `?string` | `null` | PostgreSQL backup format: `custom`, `directory`, `tar`, `plain`. No effect on MySQL. (Since 5.1.0) |
| `restoreCommand` | `string\|null\|false\|Closure` | `null` | Custom DB restore command. Same placeholders as `backupCommand`. `false` to disable restores. |
| `useFileLocks` | `?bool` | `null` | Use `LOCK_EX` when writing files. Set `false` on NFS. `null` = auto-detect. |

`runQueueAutomatically` at `true` means Craft triggers pending queue jobs by injecting a JavaScript call into CP pages and an AJAX ping into front-end pages. On high-traffic sites this ties up PHP-FPM workers processing queue jobs instead of serving requests. Set `false` in production and run a daemon:

```sh
# In a process manager (Supervisor, systemd, or DDEV custom command)
craft queue/listen --verbose
```

`cacheDuration` affects the default TTL for Craft's data cache (component configurations, element URI caches, GraphQL results). It does not affect `{% cache %}` tag duration, which defaults to the template cache duration setting on the component level.

`backupCommand` at `null` uses Craft's built-in backup mechanism. Set to `false` to disable backups entirely (useful when using an external backup solution). As a `Closure`, it receives the output file path as an argument.

`useFileLocks` at `null` auto-detects whether the filesystem supports `LOCK_EX`. On NFS mounts, file locking is often broken -- set explicitly to `false`. On local filesystems, leave at `null`.

`backupCommand` supports several placeholders that Craft substitutes before execution:

| Placeholder | Value |
|-------------|-------|
| `{file}` | Output file path |
| `{port}` | Database port |
| `{server}` | Database server |
| `{user}` | Database username |
| `{password}` | Database password (escaped) |
| `{database}` | Database name |
| `{schema}` | Database schema (PostgreSQL only) |

Example custom backup command for MySQL with compression:

```php
->backupCommand('mysqldump -h {server} -P {port} -u {user} -p{password} {database} | gzip > {file}')
```

`backupCommandFormat` only applies to PostgreSQL. The `custom` format is recommended for large databases as it supports parallel restore:

```php
->backupCommandFormat('custom')
```

---

## 12. Garbage Collection

| Setting | Type | Default | Purpose |
|---------|------|---------|---------|
| `softDeleteDuration` | `mixed` | `2592000` (30 days) | Time before soft-deleted items are hard-deleted by GC. `0` = never hard-delete. |
| `purgePendingUsersDuration` | `mixed` | `0` (disabled) | Time before pending (unactivated) users are purged. `0` = never purge. |
| `purgeStaleUserSessionDuration` | `mixed` | `7776000` (90 days) | Time before stale user sessions are purged from the DB. (Since 3.3.0) |
| `purgeUnsavedDraftsDuration` | `mixed` | `2592000` (30 days) | Time before unpublished drafts that were never updated are purged. (Since 3.2.0) |

All garbage collection settings only take effect when GC actually runs. GC is triggered probabilistically on web requests (Yii's `gcProbability` defaults to 1/1,000,000) or manually via the `gc` console command. For predictable cleanup, add `craft gc` to your cron schedule.

`softDeleteDuration` at `0` means soft-deleted items are never hard-deleted -- they remain in the database indefinitely with a `dateDeleted` timestamp. This is different from what many expect (they think `0` means "delete immediately"). To make deletes permanent immediately, this is not the right setting -- soft deletion is always the first step. The `softDeleteDuration` controls when the *hard* delete happens during GC.

`purgePendingUsersDuration` at `0` is disabled by default. When enabled, content assigned to pending users is also deleted when those users are purged. Set this carefully on sites with public registration where users may delay activating their accounts.

`purgeUnsavedDraftsDuration` targets "provisional" drafts -- drafts created automatically when an author starts editing but never explicitly saves. These accumulate in the database. The default 30-day cleanup is sensible for most sites. Set to `0` only if you need to retain all draft history indefinitely.

To ensure GC runs predictably, add to your cron schedule:

```
# Run Craft garbage collection daily at 3 AM
0 3 * * * cd /path/to/project && php craft gc --delete-all-trashed
```

The `--delete-all-trashed` flag hard-deletes all soft-deleted items regardless of `softDeleteDuration`. Use without the flag to respect the configured duration.

---

## 13. Localization

| Setting | Type | Default | Purpose |
|---------|------|---------|---------|
| `defaultCpLanguage` | `?string` | `null` | Override CP language for all users. `null` = per-user preference. |
| `defaultCpLocale` | `?string` | `null` | Override CP locale for date/number formatting. `null` = follows CP language. |
| `extraAppLocales` | `string[]` | `[]` | Additional locales beyond installed sites. |
| `localeAliases` | `array` | `[]` | Custom locale aliases with `id`, `aliasOf`, and optional `displayName`. (Since 5.0.0) |

`defaultCpLanguage` forces a single language for the entire CP. Individual users cannot override it. Use when all CP users share a language.

`defaultCpLocale` separates formatting from language. For example, the CP can display in English (`defaultCpLanguage('en')`) but format dates in the European style (`defaultCpLocale('en-GB')`).

`localeAliases` lets you create custom locales for languages not in PHP's `intl` extension:

```php
->localeAliases([
    'smj' => [
        'aliasOf' => 'sv',
        'displayName' => 'Lule Sami',
    ],
])
```

`extraAppLocales` adds locales to the list available in the CP's language dropdowns and site configuration. These locales do not need to correspond to installed sites -- they are just additional formatting options. Useful for multi-region sites where date/number formatting differs by locale.

`timezone` (in the System & Environment section) only controls display formatting and Twig date output. The database stores all timestamps in UTC always. Craft normalizes all user-submitted datetimes to UTC before saving, and converts back to the configured timezone for display. This means changing `timezone` retroactively changes how existing dates are displayed but does not alter stored data.

---

## 14. Aliases & Resources

| Setting | Type | Default | Purpose |
|---------|------|---------|---------|
| `aliases` | `array` | `[]` | Custom Yii aliases for all requests. See `config-bootstrap.md` for full alias documentation. |
| `resourceBasePath` | `string` | `'@webroot/cpresources'` | Server path for published CP resources. |
| `resourceBaseUrl` | `string` | `'@web/cpresources'` | URL for published CP resources. |

`aliases` is the primary mechanism for defining path/URL pairs used throughout Craft -- filesystem Base URLs, volume paths, email template paths. Always use `App::env()` for values that differ between environments:

```php
->aliases([
    '@assetBasePath' => App::env('ASSETS_BASE_PATH'),
    '@assetBaseUrl' => App::env('ASSETS_BASE_URL'),
])
```

`resourceBasePath` and `resourceBaseUrl` control where Craft publishes CP assets (JavaScript, CSS, fonts). These must be web-accessible. On ephemeral filesystems (containerized deployments), you may need to point these to a shared or persistent volume.

`aliases` supports dynamic values via `App::env()`:

```php
->aliases([
    '@assetBasePath' => App::env('ASSETS_BASE_PATH'),
    '@assetBaseUrl' => App::env('ASSETS_BASE_URL'),
    '@s3Bucket' => App::env('S3_BUCKET'),
    '@cdnUrl' => App::env('CDN_URL'),
])
```

These aliases can then be used in filesystem Base URL and Base Path settings in the CP. They can also be referenced in templates via the `alias()` Twig function: `{{ alias('@cdnUrl') }}`.

Craft pre-defines several aliases at bootstrap (`@web`, `@webroot`, `@storage`, `@config`, `@templates`, `@vendor`). Custom aliases defined here supplement those. If you define an alias that matches a built-in alias, yours takes precedence.

On ephemeral/containerized deployments, set `CRAFT_EPHEMERAL=true` in your environment variables. This tells Craft to avoid writing to the filesystem where possible -- compiled templates are stored in memory, and other generated files are minimized. This works in conjunction with `resourceBasePath`/`resourceBaseUrl` pointing to a writable location.

---

## 15. File Permissions & Cookies

| Setting | Type | Default | Purpose |
|---------|------|---------|---------|
| `defaultDirMode` | `mixed` | `0775` | Permissions for new directories. `null` = environment-determined. |
| `defaultFileMode` | `?int` | `null` | Permissions for new files. `null` = environment-determined. |
| `defaultCookieDomain` | `string` | `''` | Domain for cookies. Blank = browser determines. Use `'.example.com'` for subdomains. |

`defaultDirMode` and `defaultFileMode` affect all files/directories Craft creates -- compiled templates, uploads, cache files. In containerized environments, these are typically fine at defaults. On shared hosting, you may need `0755` for directories and `0644` for files.

`defaultCookieDomain` with a leading dot (e.g., `'.example.com'`) makes cookies available to all subdomains. Without it, cookies are scoped to the exact domain. Set this when your CP is on `cms.example.com` and your site is on `example.com` and you need shared sessions.

Note: `defaultDirMode` uses octal notation. In PHP, prefix with `0` for octal: `0775`, not `775`. The config file value `0775` translates to Unix permissions `rwxrwxr-x`.

---

## 16. Headless & GraphQL

Brief entries -- see `headless.md` for production guidance, token management, and schema configuration.

| Setting | Type | Default | Purpose |
|---------|------|---------|---------|
| `headlessMode` | `bool` | `false` | Disable front-end template rendering -- API-only mode. |
| `enableGql` | `bool` | `true` | Enable the GraphQL API. |
| `enableGraphqlCaching` | `bool` | `true` | Cache GraphQL query results. Schema changes auto-purge cache. |
| `enableGraphqlIntrospection` | `bool` | `true` | Allow GraphQL introspection queries. Always allowed in CP regardless. |
| `maxGraphqlBatchSize` | `int` | `0` | Max queries per batched request. `0` = unlimited. (Since 4.5.5) |
| `maxGraphqlComplexity` | `int` | `0` | Max query complexity. `0` = unlimited -- set a limit in production. |
| `maxGraphqlDepth` | `int` | `0` | Max query depth. `0` = unlimited -- set a limit in production. |
| `maxGraphqlResults` | `int` | `0` | Max results per query. `0` = unlimited. |
| `allowedGraphqlOrigins` | `array\|null\|false` | `null` | CORS origins for GraphQL. Deprecated since 4.11.0 -- use `craft\filters\Cors`. |
| `gqlTypePrefix` | `string` | `''` | Prefix for all GraphQL type names. |
| `prefixGqlRootTypes` | `bool` | `true` | Apply `gqlTypePrefix` to root `query`, `mutation`, `subscription` types. (Since 3.6.6) |
| `setGraphqlDatesToSystemTimeZone` | `bool` | `false` | Return GraphQL date values in system timezone instead of UTC. |
| `lazyGqlTypes` | `bool` | `false` | Lazily load GraphQL types to reduce memory on large schemas. (Since 5.3.0) |
| `disableGraphqlTransformDirective` | `bool` | `false` | Disable `@transform` directive globally. Deprecated since 5.9.0 -- use per-schema settings. |

All `maxGraphql*` settings default to `0` (unlimited). In production, set nonzero values to prevent denial-of-service through expensive queries. Recommended starting points: `batchSize: 10`, `complexity: 500`, `depth: 10`, `results: 1000`.

`enableGraphqlIntrospection` at `true` allows clients to discover the schema structure. Disable in production if you don't want the schema exposed to unauthenticated requests. Introspection is always available in the CP's GraphiQL playground regardless.

`lazyGqlTypes` at `true` defers loading GraphQL type definitions until they are actually requested. On schemas with many sections, volumes, and fields, this significantly reduces memory usage and startup time. (Since 5.3.0)

`setGraphqlDatesToSystemTimeZone` at `true` returns dates in the system timezone instead of UTC. This can simplify front-end date handling but breaks the convention that APIs return UTC. Document the behavior clearly for API consumers.

`gqlTypePrefix` adds a prefix to all type names. Useful when multiple Craft instances share a federated GraphQL schema and type names would otherwise collide. `prefixGqlRootTypes` controls whether the root types (`query`, `mutation`) also get the prefix.

`allowedGraphqlOrigins` is deprecated since 4.11.0. Use the `craft\filters\Cors` behavior in `config/app.web.php` instead. The filter provides more control (applies to all endpoints, not just GraphQL) and follows the standard Yii2 filter pattern. See `headless.md` for CORS configuration examples.

Production GraphQL hardening:

```php
->enableGql(true)
->enableGraphqlCaching(true)
->enableGraphqlIntrospection(false)
->maxGraphqlBatchSize(10)
->maxGraphqlComplexity(500)
->maxGraphqlDepth(10)
->maxGraphqlResults(1000)
```

---

## 17. Accessibility

| Setting | Type | Default | Purpose |
|---------|------|---------|---------|
| `accessibilityDefaults` | `array` | (see below) | Default CP accessibility preferences for new users. (Since 3.6.4) |

Sub-properties of `accessibilityDefaults`:

| Key | Type | Default | Effect |
|-----|------|---------|--------|
| `alwaysShowFocusRings` | `bool` | `false` | Show focus rings on all focused elements, not just keyboard-focused. |
| `useShapes` | `bool` | `false` | Represent statuses with shapes alongside colors (WCAG contrast compliance). |
| `underlineLinks` | `bool` | `false` | Underline links in CP for better visibility. |
| `notificationDuration` | `int` | `5000` | Auto-dismiss notification milliseconds. `0` = indefinite (never auto-dismiss). |

These are defaults for new users only. Existing users' saved preferences are not overridden. Individual users can change their accessibility preferences in their account settings.

Setting `useShapes(true)` is recommended for teams where any member may have color vision deficiency. It adds distinct shapes (circle, square, diamond) alongside status colors so that statuses are distinguishable without relying on color alone.

`notificationDuration` at `0` makes CP flash notifications persist until manually dismissed. This is useful for users who need more time to read success/error messages but can be annoying for fast-paced editors. The default 5000ms (5 seconds) is a good balance.

---

## 18. Preview

| Setting | Type | Default | Purpose |
|---------|------|---------|---------|
| `previewIframeResizerOptions` | `array` | `[]` | iFrame Resizer options for Live Preview. (Since 3.5.0) |
| `useIframeResizer` | `bool` | `false` | Enable iFrame Resizer for Live Preview. Retains scroll position for cross-origin previews. (Since 3.5.5) |

`useIframeResizer` enables the [iFrame Resizer](https://github.com/davidjbradshaw/iframe-resizer) library for Live Preview. This is useful when the preview target is on a different domain (cross-origin) -- it maintains scroll position during content updates and auto-sizes the iframe to match content height. Without it, cross-origin Live Preview works but may jump to the top on every update.

`previewIframeResizerOptions` passes options directly to the iFrame Resizer library. Common options: `{ heightCalculationMethod: 'max' }` for pages with position-fixed elements.

For headless setups where preview targets are on external domains, `useIframeResizer` is typically required for a good Live Preview experience. Without it, the iframe cannot communicate with the parent frame due to cross-origin restrictions, which causes scroll-jump issues.

Note: The front-end application must include the iFrame Resizer content window script (`iframeResizer.contentWindow.min.js`) for this to work. See the [iFrame Resizer documentation](https://github.com/davidjbradshaw/iframe-resizer) for setup instructions on the front-end side.

---

## 19. Development

| Setting | Type | Default | Purpose |
|---------|------|---------|---------|
| `devMode` | `bool` | `false` | Verbose errors, debug toolbar, expanded logging. |
| `disallowRobots` | `bool` | `false` | Send `X-Robots-Tag: none`. Auto-enabled when `devMode` is on. |
| `testToEmailAddress` | `mixed` | `null` | Redirect all system emails to this address. Accepts string or array. |
| `useIdnaNontransitionalToUnicode` | `bool` | `false` | IDNA nontransitional flag for email Unicode conversion. (Since 5.9.0) |

`devMode` does several things simultaneously: enables verbose error pages with stack traces, enables the Yii debug toolbar, expands logging to include every SQL query and template render, sets the `X-Robots-Tag: none` header, and disables template caching by default. In production, this exposes sensitive information and generates enormous log files.

`testToEmailAddress` redirects ALL system emails (activation, password reset, notifications) to the specified address. Useful in staging environments to prevent emails from reaching real users. Can be an array to send to multiple addresses:

```php
->testToEmailAddress([
    'dev@example.com' => 'Dev Team',
    'qa@example.com' => 'QA Team',
])
```

`disallowRobots` sends the `X-Robots-Tag: none` HTTP header, which tells search engine crawlers not to index the site. It is auto-enabled when `devMode` is `true`. Set explicitly on staging environments even when `devMode` is `false`.

`useIdnaNontransitionalToUnicode` controls how internationalized domain names (IDNs) in email addresses are converted. The nontransitional mode follows the latest IDNA standards (2008) instead of the transitional (2003) mode. Only enable this if you work with IDN email addresses and need strict standards compliance.

Typical development config:

```php
use craft\config\GeneralConfig;
use craft\helpers\App;

return GeneralConfig::create()
    ->devMode(App::env('CRAFT_DEV_MODE') ?? true)
    ->allowAdminChanges(true)
    ->enableTemplateCaching(false)
    ->testToEmailAddress('dev@example.com')
    ->disallowRobots(true);
```

---

## Dangerous Interactions

Settings that interact in non-obvious ways:

- **`devMode` auto-enables `disallowRobots`** -- even if you explicitly set `disallowRobots(false)`, `devMode(true)` overrides it.
- **`headlessMode` requires `baseCpUrl`** when CP and site are on different domains -- without it, the CP generates incorrect action URLs, form submissions, and asset URLs.
- **`allowAdminChanges` vs `safeMode`** -- `safeMode` is stricter, disables plugins entirely. `allowAdminChanges(false)` only prevents schema changes. Do not confuse the two.
- **`asyncCsrfInputs` must be `true` with full-page static caching** (Blitz) -- otherwise cached pages serve stale CSRF tokens that fail validation on form submission.
- **`runQueueAutomatically(false)` requires a separate daemon** -- `craft queue/listen` or a cron job running `craft queue/run`. Without it, queued jobs (transforms, search index updates, email) never execute.
- **`enableCsrfProtection` + `enableCsrfCookie`** -- the cookie is the storage mechanism. `enableCsrfCookie(false)` forces session-based CSRF storage, requiring a session start on every page that calls `csrfInput()`.
- **`trustedHosts` + `ipHeaders` + `secureProtocolHeaders`** -- all three must be configured together behind a reverse proxy. Misconfiguring one while setting another leads to incorrect IP detection or HTTPS detection failures.
- **`staticStatuses` + scheduled publishing** -- statuses won't update dynamically, so scheduled entries won't go live until the `update-statuses` command runs on cron. (Since 5.7.0)
- **`allowUpdates` auto-disabled by `allowAdminChanges(false)`** -- even if you explicitly set `allowUpdates(true)`, it has no effect when `allowAdminChanges` is `false`.
- **`softDeleteDuration(0)` is "never hard-delete"** -- soft-deleted items stay in the DB indefinitely. This is the opposite of what many developers expect (they think `0` means "delete immediately").
- **`preloadSingles` requires clearing compiled templates** -- changing this setting has no effect until you clear caches from the CP Caches utility.
- **`generateTransformsBeforePageLoad` + high-traffic pages** -- transforms generated inline block the request. On first load after a cache clear, this can cause request timeouts if the page references many transforms.
- **`maxCachedCloudImageSize` changed default in 5.9.0** -- upgrading to 5.9+ silently changes behavior from caching cloud images at 2000px to not caching them at all. If you relied on the old behavior, set explicitly.
- **`headlessMode` ignores `loginPath`, `logoutPath`, `setPasswordPath`** -- these front-end paths are not registered, so auth flows must be handled by the front-end application and API calls.
- **`disabledPlugins` per-environment causes schema mismatches** -- if a plugin is disabled in staging but enabled in production, their schema versions diverge and `project.yaml` changes can't be applied cleanly.
- **`enableGql(false)` does not remove the GraphQL endpoint route** -- it returns a 400 error instead of a 404. To fully hide the endpoint, also configure `allowedGraphqlOrigins(false)` or remove it via Cors filter.
- **`timezone` does not affect database storage** -- timestamps are always UTC in the database. Changing `timezone` retroactively changes how all existing dates are displayed.
- **`useEmailAsUsername(true)` mid-project** -- if existing users have usernames different from their emails, changing this setting can cause login issues. Migrate usernames to match emails first.
- **`disable2fa(true)` does not remove existing 2FA configurations** -- it only skips the 2FA challenge. If you re-enable 2FA later, users' existing configurations are restored.

## Quick Reference: Environment-Specific Config Pattern

The recommended pattern for environment-specific configuration without the legacy `'*'`/`'dev'`/`'production'` array syntax:

```php
use craft\config\GeneralConfig;
use craft\helpers\App;

return GeneralConfig::create()
    // Universal settings
    ->cpTrigger('admin')
    ->defaultImageQuality(90)
    ->maxUploadFileSize('64M')
    ->useEmailAsUsername(true)
    ->omitScriptNameInUrls(true)

    // Environment-conditional via env vars (env var always wins)
    ->devMode(App::env('CRAFT_DEV_MODE') ?? false)
    ->allowAdminChanges(App::env('CRAFT_ALLOW_ADMIN_CHANGES') ?? false)
    ->runQueueAutomatically(App::env('CRAFT_RUN_QUEUE_AUTOMATICALLY') ?? false)
    ->testToEmailAddress(App::env('CRAFT_TEST_TO_EMAIL_ADDRESS'))

    // Security
    ->enableCsrfProtection(true)
    ->preventUserEnumeration(true)
    ->sendPoweredByHeader(false)

    // Aliases
    ->aliases([
        '@assetBasePath' => App::env('ASSETS_BASE_PATH'),
        '@assetBaseUrl' => App::env('ASSETS_BASE_URL'),
    ]);
```

Then in `.env` per environment:

```
# .env.dev
CRAFT_DEV_MODE=1
CRAFT_ALLOW_ADMIN_CHANGES=1
CRAFT_RUN_QUEUE_AUTOMATICALLY=1
CRAFT_TEST_TO_EMAIL_ADDRESS=dev@example.com

# .env.production
CRAFT_DEV_MODE=0
CRAFT_ALLOW_ADMIN_CHANGES=0
CRAFT_RUN_QUEUE_AUTOMATICALLY=0
```
