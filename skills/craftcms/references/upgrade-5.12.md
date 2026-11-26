# Upgrade Checklist: Craft 5.11 → 5.12.4 [5.12+]

[5.12+] A checklist for taking a site or plugin from 5.11.x to 5.12.4. Each line has a version tag and points at the reference that explains it. Work top to bottom: the first group is what the upgrade itself writes or requires, the rest is behaviour that changes silently.

[5.12+] Source of truth: Craft's CHANGELOG (5.12.0 to 5.12.4) and the 5.12.4 source (https://github.com/craftcms/cms/blob/5.12.4/CHANGELOG.md).

## Contents

- Before you upgrade
- Run the upgrade locally
- Silent behaviour changes: templates
- Silent behaviour changes: content and assets
- Silent behaviour changes: plugin and module code
- New features that stay off until you opt in
- Deploy

## Before you upgrade

- [ ] [5.12.3+] **Target 5.12.4, not 5.12.0.** 5.12.3 is the pack's minimum safe version (5.12.1 to 5.12.3 fix the web-installer advisory GHSA-pcf5-h66c-9wxw, an RCE, an SSRF and several authorization bypasses). A project below it gets a warning from the skills' version check.
- [ ] [5.12+] PHP stays `^8.2`; no hosting bump. `mcp/sdk` needs `ext-fileinfo`, which Craft itself doesn't require: check CI images and minimal hosts. `deployment.md` → "Composer Notes for 5.12".
- [ ] [5.12+] New dependency `league/oauth2-server` ^9 brings `lcobucci/jwt` ^5. A project or plugin pinning `lcobucci/jwt` ^4 will likely conflict.
- [ ] [5.12+] `php-http/discovery` (a Composer plugin, via `mcp/sdk`) is optional: when `config.allow-plugins` doesn't list it, non-interactive runs skip it silently (no CI failure), and an interactive `ddev composer update` asks once and writes the answer to `composer.json` (commit it). Adding `"php-http/discovery": true` up front avoids the prompt. `deployment.md` → "Composer Notes for 5.12".

## Run the upgrade locally

- [ ] [5.12+] `ddev composer update craftcms/cms -W`, then `ddev craft up`. Migrations: `m261007_100000_oauth`, `m261014_000000_field_tips_and_warnings`, `m261022_000000_volume_propagation_method`, `m261104_000000_snake_case_mcp_tool_names`.
- [ ] [5.12+] **Commit `config/project/` after `craft up`.** Every `config/project/volumes/*.yaml` gains `propagationMethod` (`all` on multi-site installs, `custom` on single-site installs), and the schema version moves to 5.12. `craft-content-modeling` skill `infrastructure.md` → "Asset Propagation (Volumes)".
- [ ] [5.12+] Single-site installs: volumes are now Custom and the setting is hidden. If a second site may ever be added, switch shared volumes to **Save assets to all sites** before adding it. Same reference → "The add-a-second-site trap".
- [ ] [5.12+] Multi-site installs: existing volumes stay All, but **new volumes default to Custom**. Pick deliberately; for shared media choose All. Same reference.
- [ ] [5.12+] Existing Color fields default to the "Hex only" GraphQL mode, new ones to "Full data". `craft-content-modeling` skill `field-types.md` → "Color".

## Silent behaviour changes: templates

- [ ] [changed 5.12] **`.eagerly()` now honours `limit`, `offset` and `orderBy`.** Before 5.12 they were ignored in loops, so listings printed every related element. Audit `.eagerly().limit(…)` calls, and give differing slices of one field their own alias (`eagerly('galleryPreview')`). `craft-content-modeling` skill `relations-and-eager-loading.md` → ".eagerly() Limitations".
- [ ] [changed 5.12] `orderBy` in `.with()` criteria must pass `Db::isSafeOrderBy()` [5.12+] (`'postDate desc'`, not `{postDate: 'desc'}`), or it's dropped with a log warning. On 5.11.5/5.11.5.1 it was dropped entirely. Same reference → "With Criteria".
- [ ] [changed 5.12] **Case filters** (`upper`, `lower`, `title`, `capitalize`) take a `language` argument defaulting to the current app language, so output changes for languages such as Turkish, Dutch or Greek. Pass `('en')` where you need the old casing. `craft-twig-guidelines` skill → "Case Filters Follow the Site Language".
- [ ] [changed 5.12] **Color values can be 8-digit hex** (`#rrggbbaa`) once an editor picks a translucent colour. Templates that concatenate alpha onto `{{ entry.brand }}` or slice the `#` off break. `craft-content-modeling` skill `field-types.md` → "What breaks with 8-digit hex".
- [ ] [5.12+] **Icon fields can hold custom-set icons** (`set-handle:name`) with no Font Awesome class once a `customIconPath` or plugin icon set exists. Branch on `icon.set` and output `icon.svg`. `craft-content-modeling` skill `field-types.md` → "Icon"; plugin side in `events.md` → "Icon Sets".
- [ ] [changed 5.12] Twig 3.30 (5.12.0) then 3.31.1 (5.12.3): macro-call deprecations, `matches` throwing on PCRE errors, `spaceless` deprecated. `craft-twig-guidelines` skill → "Twig 3.29 to 3.31".
- [ ] [deprecated 5.12] `ElementCollection::render()` → the `Collection` `render()` macro; `ElementHelper::renderElements()` → `Template::render()` [5.12+]; list renders get a `loop` variable. `craft-site` skill `element-partials.md` → "The `{% render %}` Tag"; PHP side in `elements.md` → "Rendering Elements".
- [ ] [changed 5.12] Assets in a Custom volume only exist in some sites: an Assets field on another site's entry renders empty. `craft-content-modeling` skill `infrastructure.md` → "Assets may not exist in the current site".

## Silent behaviour changes: content and assets

- [ ] [changed 5.12] "Delete for site" on an element's only site soft-deletes (restorable) instead of hard-deleting; [changed 5.12.1] the CP actions now refuse an element's only site. `elements.md` → "Delete for site".
- [ ] [changed 5.12] Saving a nested entry on its own bumps its owners' `dateUpdated`, which moves "recently updated" listings, feeds and sitemap `lastmod`. `drafts-revisions.md` → "`createRevision()` skips silently when `dateUpdated` didn't move".
- [ ] [changed 5.12] Addresses support drafts; raw SQL on `addresses` must exclude draft rows. `drafts-revisions.md` → Common Pitfalls.
- [ ] [changed 5.12] Default `allowedFileExtensions` gains `jxl`, `md` and `markdown`. A project overriding the setting doesn't get them. `config-general.md`.
- [ ] [changed 5.12] a DSN set inside a database config array is now parsed, so a MySQL `charset=utf8` in it is normalised to `utf8mb4` (craftcms/cms#20248).
- [ ] [changed 5.12] CP navigation: Assets settings moved to the Settings page's "Content" section, the "Media" section is gone, and filesystems live at **Settings → Assets → Filesystems** (the old `settings/filesystems` URLs still resolve). Update internal docs and runbooks.

## Silent behaviour changes: plugin and module code

- [ ] [changed 5.12] `new Asset()` saves to the **primary** site; in a Custom volume set `$asset->siteId` (or `setEnabledForSite()`). Look assets up with `getAssetById()` or `site('*')->unique()`, not `Asset::find()->id()->one()`. `elements.md` → "Assets in Custom volumes".
- [ ] [changed 5.12] Empty arrays in nested queries (`ownerId([])`, `fieldId([])`, `owner([])`, `primaryOwnerId([])`) now return nothing instead of everything. Guard empty ID lists. `elements.md` → "Nested Element Queries".
- [ ] [changed 5.12] Delete listeners: `hardDelete` is `false` for delete-for-site on the only site. `events.md` → Elements Service.
- [ ] [changed 5.12.1] The deprecated element-level `Element::EVENT_AUTHORIZE_DELETE_FOR_SITE` fires now (it never did). `element-authorization.md`.
- [ ] [changed 5.12] Element edit sidebars show a **Sites** pane instead of Status on multi-site installs; code that searched the sidebar HTML for the Status fieldset won't find it. `cp-ui-patterns.md` → "Two `.meta` treatments".
- [ ] [deprecated 5.12] `PrismJsAsset` is a shim over TanStack Highlight: custom grammars, hooks and Prism plugins stop working. Use `HighlightAsset` [5.12+]. `craft-garnish` skill `integration.md` → "Syntax Highlighting and Uploaders".
- [ ] [changed 5.12] Image Editor moved to Fabric.js v7; plugins driving its Fabric instance need retesting.
- [ ] [changed 5.12] Codeception element fixtures no longer create revisions; set `createRevisions = true` where tests assert them. `testing.md`.
- [ ] [changed 5.12.1] Field values submitted for nested entries, Content Block fields and addresses are dropped when the user can't see or edit those fields per their field layout conditions. Front-end forms that post hidden fields stop saving them.
- [ ] [5.12.1+] Project-config read-modify-write: call `ProjectConfig::acquireLock()` before reading. `architecture.md` → "Save → Project Config → Handler → Database".
- [ ] [5.12.2+] New helpers worth adopting: `UrlHelper::absoluteUrl()`, `Dashboard::isWidgetTypeAvailable()`, `owner()` with an array of owners. `craft-php-guidelines` skill; `cp-components.md`; `elements.md` → "Nested Element Queries".

## New features that stay off until you opt in

- [ ] [5.12+] **MCP servers are opt-in.** Both HTTP servers are disabled by default and nothing is exposed over HTTP until an admin enables them in **Settings → MCP** (the stdio server, `craft mcp/serve`, only runs when someone with shell access starts it). Setup, scopes and security: the `craft-mcp` skill (`skills/craft-mcp/SKILL.md`).
- [ ] [5.12+] OAuth and personal access tokens need signing keys (`craft oauth/generate-keys`) before the Tokens screen works for non-admins. `craft-mcp` skill.
- [ ] [changed 5.12.1] **GraphQL over OAuth or personal access tokens respects field layout conditions**: hidden fields are excluded from the schema (or resolve to `null` for element-specific conditions), and non-editable fields are rejected in mutations. Schema-token requests are unaffected. `graphql.md` → "Field layout conditions".
- [ ] [5.12+] `defaultRateLimit`/`defaultRateLimitDuration` rate-limit login and password-reset requests. `config-general.md`.

## Deploy

- [ ] [5.12+] Add `php craft project-config/check` before `craft up`: it fails fast when the YAML needs a newer Craft or plugin schema than the release ships (`composer.lock` and `config/project/` out of sync). The command doesn't exist on 5.11, so add the step once 5.12 is deployed. `deployment.md` → "Project Config Commands".
- [ ] [changed 5.12.1] New environments install with `php craft install --interactive=0 …`; the web installer only runs in Dev Mode. `deployment.md` → "First Install on a New Environment".
- [ ] [changed 5.12.2] CP updates (built-in `composer.phar` 2.11.2) no longer fall back to cloning a package's source when its zip download fails. Private packages need a working dist. `deployment.md` → "Composer Notes for 5.12".
