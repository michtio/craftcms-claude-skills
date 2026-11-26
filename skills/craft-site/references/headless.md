# Headless & Hybrid Patterns

## Documentation

- Headless mode: https://craftcms.com/docs/5.x/reference/config/general.html#headlessmode
- GraphQL API: https://craftcms.com/docs/5.x/development/graphql.html
- Preview targets: https://craftcms.com/docs/5.x/reference/element-types/entries.html#preview-targets
- CORS filter: https://docs.craftcms.com/api/v5/craft-filters-cors.html
- Authenticating as a user (OAuth, PATs): https://craftcms.com/docs/5.x/development/graphql.html#authenticating-as-a-user

## Common Pitfalls

- Enabling `headlessMode` when you only need API endpoints alongside templates — it disables ALL template rendering and element URI routing. For hybrid setups, leave it OFF.
- Not setting `baseCpUrl` when `headlessMode` is on and the CP is on a different domain — the CP generates incorrect URLs for itself.
- Missing CORS configuration for cross-origin API requests — browsers block responses without proper `Access-Control-Allow-Origin` headers, but the request still hits the server.
- Not forwarding the preview token from the front-end back to Craft API calls — Craft returns published content instead of draft/revision content during preview.
- Setting `maxGraphqlComplexity`, `maxGraphqlDepth`, or `maxGraphqlResults` to `0` in production — zero means unlimited, which is a denial-of-service vector.
- Not sending the `X-Craft-Site` header for multi-site API consumers — Craft defaults to the primary site, silently returning wrong-language content.
- Leaving the public GraphQL schema enabled without auditing its scope — it exposes content to unauthenticated requests.
- Selecting `author`, `authors`, or `uploader` from a schema without **Query for users** — [changed 5.11] those fields (plus `authorId`, `authorIds`, `draftCreator`, `revisionCreator`, `uploaderId`) only exist in schemas with the Users → "Query for users" scope (`usergroups.everyone`). Before 5.11, read access to any one user group was enough (`Gql::canQueryUsers()`); from 5.11 it takes the all-users scope (`Gql::canQueryAllUsers()` [5.11+]), so a schema scoped to specific user groups loses these fields and a front end that worked on 5.10 fails query validation. When supporting both, grant **Query for users**. Grant the scope on the private schema the front end uses (not the public one, unless author accounts are meant to be public) or stop selecting author data.
- Querying a Color field created in 5.12 as a plain string: [5.12+] new Color fields default to GraphQL Mode "Full data", which returns an object, so `{ accentColor }` fails with "must have a selection of subfields". Select subfields (`accentColor { hex rgba }`) or set the field to "Hex only". Existing fields stay Hex only, and hex can be 8-digit for translucent colours [changed 5.12]. Before 5.12: always a 6-digit hex string.
- Using OAuth tokens for build-time fetching [5.12+]: no client-credentials grant and a 1-hour lifetime. Keep a schema token for SSG/ISR builds; OAuth is for members acting as themselves.
- Sending an OAuth access token or personal access token in `X-Craft-Authorization` [5.12+]: it gets a 401. Only schema tokens can use that header.
- Relying on `allowedGraphqlOrigins` — [deprecated 5.3] (already deprecated in 4.11.0). Use the `craft\filters\Cors` filter [5.3+] instead; before 5.3 `allowedGraphqlOrigins` is the only option.

## Contents

- [headlessMode Configuration](#headlessmode-configuration)
- [GraphQL API](#graphql-api)
- [CORS Configuration](#cors-configuration)
- [Preview with External Front-Ends](#preview-with-external-front-ends)
- [Hybrid Patterns](#hybrid-patterns)
- [Authentication for API Consumers](#authentication-for-api-consumers)
- [Signed-In Members over OAuth](#signed-in-members-over-oauth-512)
- [Front-End Framework Patterns](#front-end-framework-patterns)

## headlessMode Configuration

Enable in `config/general.php`:

```php
return GeneralConfig::create()
    ->headlessMode(true)
    ->baseCpUrl('https://cms.example.com');
```

When `headlessMode` is `true`, Craft changes these behaviors:

1. **Front-end responses default to JSON** — `Content-Type: application/json` unless explicitly overridden.
2. **Twig auto-escaping switches to JS strategy** — uses JavaScript-safe escaping instead of HTML escaping.
3. **Element URI routing is disabled** — requests to entry/category URIs do not resolve to elements.
4. **Template rendering returns 404** — any request that would normally render a Twig template returns a 404 response.
5. **Project config routes are skipped** — routes defined in Settings > Routes are ignored.
6. **Action URLs route through the CP base URL** — action requests use `baseCpUrl` as the base, not the site URL.
7. **`loginPath`, `logoutPath`, `setPasswordPath` are ignored** — these front-end paths are not registered.
8. **User activation and password-reset emails use CP URLs** — links point to the CP domain, not the site domain.
9. **GraphQL endpoint remains accessible** — the `graphql/api` route works regardless.
10. **The CP functions normally** — `headlessMode` only affects front-end (site) requests.

`headlessMode` is all-or-nothing. There is no per-site toggle. For projects that need both Twig templates and API endpoints, leave `headlessMode` off and use hybrid patterns instead.

## GraphQL API

### Endpoint

The default endpoint is `actions/graphql/api`. When using the `verbs` route pattern, Craft also registers `graphql/api` as a GET/POST endpoint. Configure a custom endpoint path via the `graphqlApiEndpoint` config setting (default: `graphql/api`, set to `false` to disable).

### Authentication and Schema Resolution

Craft resolves which GraphQL schema to use in this order (`GraphqlController::_schema()`, https://github.com/craftcms/cms/blob/5.12.4/src/controllers/GraphqlController.php):

1. **`X-Craft-Gql-Schema` header**: admin sessions only (`requireAdmin`); a schema UID, or `*` for the full schema. This is what the CP GraphiQL playground uses.
2. **A JWT bearer token** [5.12+]: an OAuth access token or personal access token (detected by exactly two dots; schema tokens have none). Craft authenticates it from the `Authorization` header, runs the request as that user, and builds a per-user schema from their permissions. An invalid or expired JWT is a 401, never a fallback to public data. Before 5.12: no such step.
3. **A schema token**: `X-Craft-Authorization: Bearer <token>` is read *before* `Authorization: Bearer <token>` (`Request::getBearerToken()` [5.1+]). Use `X-Craft-Authorization` where the web server or a proxy strips `Authorization`.
4. **Public schema**: used when no recognised token is sent and the public schema is enabled.

The header order in step 3 applies to schema tokens only. [5.12+] An OAuth access token or PAT must go in `Authorization`; sent only in `X-Craft-Authorization` it gets a 401 (observed in a runtime check; `OAuth::authenticate()` reads only `Authorization`).

A schema token Craft doesn't recognise is not an error: Craft silently falls back to the public schema, so a typo'd token returns public data instead of failing. With no public schema, the response is `Missing Authorization header`, even though a header was sent. An expired or disabled token fails with `Invalid Authorization header`.

```
GET /api
Authorization: Bearer abc123def456
```

Private schema tokens are created in the CP under Settings > GraphQL > Tokens. Each token is scoped to one schema. The full authentication table (lifetimes, who each credential acts as, which core components a signed-in user gets) is in the `craftcms` skill's `graphql.md`.

Schema scopes decide which fields *exist*, not just which return data. [changed 5.11] The user-related fields (`author`, `authors`, `uploader`, and their id variants) are absent from any schema without **Query for users**. Before 5.11, read access to any one user group was enough; a schema with no user scope never had them. Selecting them is a validation error, not an empty result. The `craftcms` skill's `graphql.md` (the 5.11 additions section) has the full list. [changed 5.12.1] For OAuth/PAT requests, field layout conditions apply too: a field hidden from the user by a user condition is not in their schema (`Cannot query field …`), and a field hidden by an element condition resolves to `null`. Before 5.12.1: authenticated requests ignored layout conditions.

### Settings Queries for Site-Aware Front Ends [5.12+]

Enable **Query for sites** on the schema and the front end can build language switchers and hreflang without hardcoding sites:

```graphql
{
  sites { handle language baseUrl primary }
  entry(slug: "about") { title site { handle language } }
}
```

`sections`/`entryTypes`/`volumes` queries exist too, but they list every section, entry type or volume regardless of the schema's content scope. Keep them off the public schema. [5.12+] Before 5.12: hardcode the site list in the front end, or expose it through a global set. Per-site content still needs `X-Craft-Site` or the `site:` argument.

### Rate Limiting

Configure in `config/general.php`:

| Setting | Default | Purpose |
|---------|---------|---------|
| `maxGraphqlBatchSize` | `0` (unlimited) | Max queries per batched request |
| `maxGraphqlComplexity` | `0` (unlimited) | Max query complexity score |
| `maxGraphqlDepth` | `0` (unlimited) | Max nesting depth |
| `maxGraphqlResults` | `0` (unlimited) | Max results per query |

Set all four to nonzero values in production. Recommended starting points: `batchSize: 10`, `complexity: 500`, `depth: 10`, `results: 1000`.

### Caching

Enable with `enableGraphqlCaching` (default: `true`). Craft caches responses per query+variables+schema combination. Override per-request by sending the `x-craft-gql-cache: no-cache` header.

GraphQL caches are automatically invalidated when relevant elements change. Disable caching during development to avoid stale responses.

### Batched Queries

Send an array of query objects in a single POST:

```json
[
  {
    "query": "{ entries(section: \"news\") { title } }",
    "variables": {},
    "operationName": null
  },
  {
    "query": "{ globalSet(handle: \"siteInfo\") { ... on siteInfo_GlobalSet { siteTitle } } }",
    "variables": {},
    "operationName": null
  }
]
```

Craft returns an array of results in the same order. Limit batch size with `maxGraphqlBatchSize`.

## CORS Configuration

### Legacy: `allowedGraphqlOrigins` (deprecated 4.11.0)

Still works but only applies to the GraphQL endpoint:

```php
// config/general.php
return GeneralConfig::create()
    ->allowedGraphqlOrigins(['https://app.example.com', 'https://staging.example.com'])
    // or false to disable CORS entirely
    // or null to allow all origins (not recommended)
;
```

### Modern: `craft\filters\Cors` [5.3+]

Configure in `config/app.web.php`. Applies to any controller action, not just GraphQL:

```php
use craft\filters\Cors;

return [
    'as corsFilter' => [
        'class' => Cors::class,
        'cors' => [
            'Origin' => [
                'https://app.example.com',
                'https://staging.example.com',
            ],
            'Access-Control-Request-Method' => ['GET', 'POST', 'OPTIONS'],
            'Access-Control-Request-Headers' => [
                'Authorization',
                'Content-Type',
                'X-Craft-Authorization',
                'X-Craft-Site',
                'X-Craft-Token',
            ],
            'Access-Control-Allow-Credentials' => true,
            'Access-Control-Max-Age' => 86400,
        ],
    ],
];
```

For per-site CORS (multi-site with different allowed origins), use `match` on the current site handle to set `'Origin'` conditionally in the same structure.

Prefer the `Cors` filter over `allowedGraphqlOrigins` — it covers all endpoints, not just GraphQL.

## Preview with External Front-Ends

### How Preview Tokens Work

1. An author clicks "Preview" in the CP.
2. Craft generates a short-lived token and opens the preview target URL with `?token=<value>` appended.
3. The front-end application receives the token, then forwards it back to Craft on every API request as `X-Craft-Token: <value>`.
4. Craft uses the token to resolve drafts and unsaved changes instead of the published version.

The token is required on the API call, not the front-end URL. If the front-end does not forward the token, Craft returns published content.

### Configure Preview Targets

Set preview targets on each section in Settings > Sections > [Section] > Preview Targets. For headless setups, point to the front-end application:

| Label | URL |
|-------|-----|
| Front-end | `https://app.example.com/blog/{slug}?token={token}` |

The `{token}` tag is replaced with the preview token. The `{slug}`, `{uri}`, `{url}`, and other entry attribute tags are available.

### Token Duration

Configure `previewTokenDuration` in `config/general.php` (default: 1 day). Set to a `DateInterval` string or integer (seconds):

```php
return GeneralConfig::create()
    ->previewTokenDuration('PT2H')  // 2 hours
;
```

### Example: Next.js Preview

Create an API route (`/api/preview`) that reads the `token` query param, enables Draft Mode, stores the token in a cookie, and redirects to the page. On every subsequent data fetch, read the cookie and forward it:

```js
async function fetchCraftGraphQL(query, variables = {}, previewToken = null) {
  const headers = {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${process.env.CRAFT_GQL_TOKEN}`,
    'X-Craft-Site': 'default',
  };
  if (previewToken) {
    headers['X-Craft-Token'] = previewToken;
  }
  const res = await fetch(process.env.CRAFT_GQL_ENDPOINT, {
    method: 'POST',
    headers,
    body: JSON.stringify({ query, variables }),
  });
  return res.json();
}
```

## Hybrid Patterns

Hybrid setups serve some pages via Twig templates and expose content via API for other consumers. Leave `headlessMode` off.

### Key Principles

- **GraphQL and Element API endpoints work alongside Twig templates** — no special configuration needed. The GraphQL endpoint is always available when enabled in config.
- **Twig templates can return JSON** — use `{% header "Content-Type: application/json" %}` and `{% exit 200 %}` to create simple JSON endpoints without GraphQL.
- **Per-site approach** — create one site for Twig rendering and another for API consumers. Each site can have its own base URL, language, and template path.
- **Preview targets can mix** — some sections preview on Craft's template URLs, others on the external front-end. Configure per section.
- **GraphQL schemas scope per site** — a token's schema can include entries from specific sites only.

### Twig JSON Endpoint

For simple data needs without GraphQL overhead, use `{% header "Content-Type: application/json" %}`, build the data structure with `map` and `json_encode`, and end with `{% exit 200 %}`. Register as a route in Settings > Routes or via `EVENT_REGISTER_SITE_URL_RULES`.

### Per-Site Hybrid

In Settings > Sites, create two sites:

| Site Handle | Base URL | Purpose |
|-------------|----------|---------|
| `web` | `https://example.com` | Twig templates |
| `api` | `https://api.example.com` | API consumers |

Entries propagate to both sites. The `web` site uses templates. The `api` site has no templates — consumers use GraphQL with `X-Craft-Site: api`. The GraphQL token's schema scopes to the `api` site's content.

## Authentication for API Consumers

### Token Types

| Token Type | Header | Lifetime | Acts as | Use Case |
|------------|--------|----------|---------|----------|
| GraphQL schema token | `Authorization: Bearer <token>`, or `X-Craft-Authorization: Bearer <token>` (read first) | Until its optional expiry, or until disabled | Nobody; the token's schema decides access | Server-to-server calls, build pipelines (SSG/ISR), server-side routes |
| OAuth access token [5.12+] | `Authorization: Bearer <jwt>` only | 1 hour; refresh token 30 days, rotated on use | The signed-in user, within their permissions | SPA or native app where members sign in ("Log in with Craft") |
| Personal access token [5.12+] | `Authorization: Bearer <jwt>` only | 7, 30, 90 or 365 days; shown once | The user who created it in My Account > Tokens | Scripts that should act as a named user |
| Public schema | None | Always active (if enabled) | Nobody | Public content, no auth needed |
| Preview token | `X-Craft-Token: <token>` | Configurable (`previewTokenDuration`) | Adds draft content to the credential above | CP preview of drafts |
| Admin direct schema | `X-Craft-Gql-Schema: <schema-uid>` | Session-based | The logged-in admin | CP GraphiQL playground |

[5.12+] Before 5.12: only schema tokens, the public schema, preview tokens and the admin header exist.

**Headless builds keep schema tokens.** Craft's OAuth server has no client-credentials grant (only `authorization_code` with PKCE and `refresh_token`), access tokens expire after an hour, and OAuth requests never see globals, categories or tags. A build server or server-side data layer that reads content with no user involved should keep using a schema token.

### Signed-In Members over OAuth [5.12+]

For a front end where members sign in and query or edit content as themselves. The OAuth server setup on the Craft side (signing keys on every environment, `config/oauth.php`, redirect domains, registration rate limit) is in the `craft-mcp` skill.

1. **Discover.** Call the API without a token: the 401's `WWW-Authenticate` header carries `resource_metadata="…/.well-known/oauth-protected-resource/…"`. That metadata names the authorization server; its metadata lists the endpoints. [changed 5.12.1] For GraphQL these are site action URLs (`/actions/oauth/authorize?oauthResource=graphql`, `…/token`, `…/register`), and metadata is served only from `.well-known` URLs. Before 5.12.1: discovery advertised CP URLs.
2. **Register a client** through the registration endpoint (dynamic client registration; public clients, no client secret). Registration is rate-limited per IP.
3. **Authorize** with authorization code + PKCE (`S256`), requesting `graphql:read`, or `graphql:write` for mutations. Signed-out members are sent to the front-end `loginPath` (or `actions/users/login`), because the `graphql` resource doesn't require control panel access.
4. **Exchange the code** at the token endpoint. Store the access token (1 hour) and refresh token (30 days, rotated on each refresh, so always keep the newest one).
5. **Query as the member** with `Authorization: Bearer <access token>`:

```graphql
{
  currentUser { id fullName email }
  entries(section: "savedRecipes") { title }
}
```

What the member's schema contains is decided by their permissions, not by a saved schema:

- `currentUser` exists only on OAuth/PAT requests. With a schema token it's a validation error.
- Members need **View entries** on each section they query (and save/create/delete permissions for mutations, plus the `graphql:write` scope).
- On a multi-site install they need a site permission for at least one site, or every request fails with `403 Schema doesn't have access to the "…" site`.
- Drafts, revisions, disabled elements and the sections/entry types/volumes settings queries need control panel access.
- Globals, categories and tags are never available. Fetch them with a schema token on the server.
- [5.12.3+] While the system is offline, OAuth requests work only for users allowed to access the site (or CP) when the system is off. Before 5.12.3: OAuth GraphQL requests failed while offline.
- Results are cached separately per user.

The authorization flow (code exchange, refresh) belongs on a server or BFF where possible; a pure SPA must keep the refresh token in memory or secure storage, never in `localStorage`.

### Multi-Site Routing

Send `X-Craft-Site: <siteHandle>` on every request to control which site's content Craft returns. Without this header, Craft uses the primary site.

```
POST /api
Authorization: Bearer abc123
X-Craft-Site: french
Content-Type: application/json

{"query": "{ entries(section: \"news\") { title } }"}
```

This returns entries from the `french` site with French titles and field values.

### Security Recommendations

- Create separate tokens per consumer (front-end app, mobile app, build pipeline) so you can revoke individually.
- Scope each token's schema to only the sections, volumes, and global sets that consumer needs.
- Never expose a private token in client-side JavaScript — use it in server-side API routes or build scripts only.
- Disable the public schema unless you explicitly need unauthenticated access.
- [5.12+] OAuth is not a replacement for server tokens: there's no client-credentials grant, and globals, categories and tags aren't available to OAuth requests.
- [5.12+] Members sign in through OAuth; never hand a front end a personal access token or a schema token with mutation access.
- Set `maxGraphqlComplexity`, `maxGraphqlDepth`, and `maxGraphqlResults` to nonzero values.

## Front-End Framework Patterns

### Common Across All Frameworks

Every front-end framework follows the same integration pattern:

1. **Auth** — store the Bearer token in an environment variable, send on every request.
2. **Site context** — send `X-Craft-Site` header to select the site.
3. **Preview** — receive `?token=<value>` from Craft, store it, forward as `X-Craft-Token` on API calls.
4. **Revalidation** — configure a webhook in Craft (Settings > Webhooks or a plugin) that hits the framework's revalidation endpoint when content changes.
5. **Error handling** — check for `errors` array in the GraphQL response, not just HTTP status codes.

### Next.js

- Use `graphql-request` or plain `fetch` with the Bearer token.
- Preview: create an API route (`/api/preview`) that enables [Draft Mode](https://nextjs.org/docs/app/building-your-application/configuring/draft-mode) and stores the Craft token in a cookie.
- ISR: use `revalidateTag` or `revalidatePath` triggered by a Craft webhook on entry save.
- Static generation: fetch all entry slugs at build time for `generateStaticParams`.

### Nuxt

- Use `useFetch` or `useAsyncData` with `$fetch` in composables.
- Preview: create route middleware that reads the `token` query param and stores it in a `useState` composable, then passes it in API headers.
- SSR/SSG: use `routeRules` to configure caching per route pattern.
- Multi-site: set `X-Craft-Site` based on the active Nuxt i18n locale.

### Astro

- Fetch content from GraphQL at build time in `.astro` frontmatter or content collection loaders.
- Hybrid SSR: enable `output: 'hybrid'` for pages that need on-demand rendering (preview, personalized content).
- Preview: use an Astro middleware to read the token param and inject it into fetch headers.
- Static: rebuild via webhook — trigger `astro build` from a CI pipeline when Craft fires a save webhook.
