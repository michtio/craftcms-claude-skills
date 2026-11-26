# Dates, Environment, Database and Registration Scope

Runtime conventions that a Craft plugin gets subtly wrong: which date API goes where and how to parse a database datetime, reading environment variables and `$VAR` settings, query and schema conventions (including when `Db::parseParam()` is the wrong tool and how to accept a forwarded `orderBy`), and why component-type registration must not sit behind a request-context check.

## Date Handling

- **Elements and element queries**: `craft\helpers\DateTimeHelper`.
- **Services** (date arithmetic): `Carbon\Carbon`.
- Never mix both in the same class.
- **Name the timezone when parsing a value that came out of the database.** Datetime columns hold naive UTC strings (`Db::prepareDateForDb()` formats in UTC without an offset), while Craft sets the PHP process timezone to `system.timeZone` — so `strtotime()` or bare `new DateTime()` on a raw column value shifts every comparison by the full UTC offset on a non-UTC install, and is silently correct on a UTC one. Use `DateTimeHelper::toDateTime($value)` (naive input is assumed UTC by default) or `Carbon::createFromFormat('Y-m-d H:i:s', $value, 'UTC')`. See the `craftcms` skill's `architecture.md` (Record-to-Model Hydration Boundary → Those strings are naive UTC).

## Environment Access

- **`craft\helpers\App::env('VAR')`, never `getenv()`** — in plugin code AND in every config-file example that appears in docs. `getenv()` is not thread-safe, returns `string|false`, and skips values only present in `$_SERVER`; `App::env()` is Craft's own convention, normalizes `'true'`/`'false'` to booleans, and is what core docs show. A config example gets the `use craft\helpers\App;` line.
- `App::parseEnv()` when the stored value may be a `$VAR` reference or an alias (settings-model getters resolving env-able fields). It resolves a whole-string `$VAR`, a `$VAR/subpath` [5.5+], a `$VAR` in any slash-delimited segment or `${VAR}` anywhere in the string [5.9+]; nothing else. [changed 5.11] Before 5.11, a `$` inside free text (`"$58 million"`) had its unresolved token stripped out of the string (craftcms/cms#19522); now it is left untouched. When supporting both, don't route arbitrary user copy through it.
- [5.12.2+] `craft\helpers\UrlHelper::absoluteUrl($url, $baseUrl = null)` to resolve a root-relative or protocol-relative URL (`/uploads/a.png`, `//cdn.example.com/a.png`) against a base URL the way a browser would; the base defaults to the current site's base URL, and the URL comes back unchanged when it's already absolute or the base isn't. Before 5.12.2: prefix `UrlHelper::baseSiteUrl()` yourself, or `UrlHelper::siteUrl()` for site paths.
- `Craft::$app->getConfig()->doesEnvVarExist('NAME')` [5.11+] before offering to write a variable to the project's `.env`. It greps the file, so it answers "declared in `.env`", not "set in the environment"; use `App::env()` for the latter.

## Database Conventions

- `[[column]]` quoting in Yii2 join conditions.
- `addSelect()` in `beforePrepare()` — safely additive.
- `postDate` and `expiryDate` in `addSelect()` and indexed on element tables.
- `Db::parseParam()` for query parameters. `Db::parseDateParam()` for dates. But **not** for literal comparison — it treats a leading/trailing `*` as a `LIKE` wildcard; use a raw `andWhere(['col' => $value])` when comparing stored values exactly.
- Foreign keys with explicit `CASCADE` / `SET NULL` behavior.
- [5.12+] Forwarding a request-, template- or settings-supplied `orderBy` into a query: accept it only when `craft\helpers\Db::isSafeOrderBy($orderBy)` is true (an `ExpressionInterface`, a comma-separated column list with optional `asc`/`desc`, or an array of columns set to `SORT_ASC`/`SORT_DESC`). Craft applies the same check to eager-loading criteria. Before 5.12: allow-list the column names yourself.

## Component-Type Registration Scope

Registering `EVENT_REGISTER_ELEMENT_TYPES` / `EVENT_REGISTER_FIELD_TYPES` inside a `getIsCpRequest()` (or other request-context) branch in `init()` — component-type registration must run in **every** context (CP, console, site) or the type disappears from `getAllElementTypes()` in console/queue requests, and `Gc::hardDeleteElements()` silently stops purging its trashed rows. Register unconditionally; only CP-*rendering*/routing (URL rules, asset bundles, nav) may be gated. See the `craftcms` skill's `events.md` → "Registration scope".

## Parsing Raw DB Datetimes

Parsing a raw DB datetime with `strtotime()` or `new DateTime()` — those columns are naive UTC strings and the process timezone is `system.timeZone`, so the result is off by the full offset on any non-UTC install. Parse with an explicit UTC zone. See Date Handling above.

## Literal Comparisons

Using `Db::parseParam()` for a literal comparison — a leading or trailing `*` becomes a SQL `LIKE` wildcard, so a uniqueness check on a stored pattern silently becomes a prefix match. Use a raw `andWhere(['col' => $value])`. See the `craftcms` skill's `architecture.md`.
