# Headless Apps and Request Signing

How to reliably consume a Craft Cloud environment from automated clients — static-site builds (Next.js, Nuxt, Astro), ISR/background revalidation, CI pipelines, load tests, and server-to-server webhooks. Cloud runs aggressive bot detection that prioritizes human traffic, and headless content retrieval is exactly the kind of concentrated automated burst it deprioritizes. Two things make it work: **request signing** (so trusted traffic bypasses the untrusted-bot policy) and **bounded retries** (because signed traffic can still be shed under load).

## Documentation

- Headless apps: https://craftcms.com/docs/cloud/headless-apps
- Request signing: https://craftcms.com/docs/cloud/request-signing
- RFC 9421 HTTP Message Signatures: https://httpsig.org/

When unsure about a signing detail, `WebFetch` the request-signing page — the doc carries full Node.js, k6, and PHP examples.

## Common Pitfalls

- **Unsigned build/revalidation traffic getting `429`/`503`.** Cloud's bot detection correctly identifies SSG builds and ISR revalidation as bots and rate-limits them more aggressively than browsers. The fix is signing, not backoff alone — retries against an unsigned burst just prolong the failure.
- **Assuming a signature guarantees a response.** Signatures bypass the *untrusted-bot policy*, not shared capacity limits — signed requests can still receive `429` or `503`. You need the retry policy *and* the signature.
- **Signing with a URL that doesn't match exactly.** Requests signed with the default `@target-uri` component are only valid for a URL that matches **exactly** — scheme, hostname, path, *and* query string. Use the same URL value for signing and for the actual `fetch()` call.
- **Exposing the signing key to a browser.** `$CRAFT_CLOUD_SIGNING_KEY` is a shared secret. Never ship it in client-side code or a public (`NEXT_PUBLIC_*`, `NUXT_PUBLIC_*`) env var. Keep signed requests in server-side code — a framework server route, a build script, an API handler.
- **Retrying GraphQL mutations.** Signed requests are **not consumed and not idempotent** — a retried mutation runs twice. Only retry `POST` requests containing read-only queries.
- **Relying on a framework's built-in retry.** Nuxt's `$fetch` (ofetch) can auto-retry but does not honor `Retry-After` with backoff and jitter. Wrap the request yourself or use a client that supports the full policy (e.g. Ky).
- **Swallowing exhausted retries.** Throw when retries run out. `stale-while-revalidate` layers (Next.js ISR, Nuxt `swr` route rules) keep serving the last successful result when revalidation throws — returning partial/empty data instead poisons that cache.
- **App-wide cache invalidation bursts.** Use narrow cache tags (`craft:blog`, `craft:products`) so a content change revalidates one slice, not every route at once — a full-app revalidation is exactly the burst profile that gets shed.

## Request signing

Cloud validates [RFC 9421 HTTP Message Signatures](https://httpsig.org/) **at the gateway**, using each environment's `$CRAFT_CLOUD_SIGNING_KEY` [system variable](https://craftcms.com/docs/cloud/environments) as an HMAC-SHA256 shared secret.

Mechanics that matter:

- **Validity window: five minutes maximum** at the gateway. Generate the signature per request, not per build.
- **Not consumed, not idempotent** — unlike a Craft token URL, the same signed request can be replayed within the window.
- **Default signed components: `@method` + `@target-uri`.** Pass additional [covered components](https://www.rfc-editor.org/rfc/rfc9421.html#name-http-message-components) (e.g. `content-type`) when those values must also be signed.
- **Failed validation is not rejection.** An invalid or absent signature just means the request falls back to normal bot- and rate-limiting rules; if no policy triggers, it reaches Craft like any other request. So a signing bug degrades quietly into intermittent 429s rather than failing loudly — verify signing works by load, not by a single request succeeding.
- Signature validation happens before Craft; the platform doesn't hand your app the verdict. If your endpoint needs its own trust decision, layer a separate shared secret check in the application.

### From Node.js

The docs' canonical helper uses [`http-message-sig`](https://www.npmjs.com/package/http-message-sig) (any RFC 9421 implementation works):

```js
// request-signatures.js
import crypto from 'node:crypto';
import { signatureHeadersSync } from 'http-message-sig';

const { CRAFT_CLOUD_SIGNING_KEY } = process.env;

export function getSignatureHeaders(request, components = ['@method', '@target-uri']) {
  return signatureHeadersSync(request, {
    key: 'sig',
    signer: {
      keyid: 'hmac',
      alg: 'hmac-sha256',
      signSync: (data) =>
        crypto.createHmac('sha256', CRAFT_CLOUD_SIGNING_KEY).update(data).digest(),
    },
    components,
    created: new Date(),
  });
}
```

Spread the returned headers into the real request's headers, using the **same** `method`/`url` values for signing and sending.

### From Craft (PHP)

Any Craft project running on Cloud can sign outbound requests — useful for console commands, queue jobs, or environment-to-environment calls:

```php
use Craft;
use craft\cloud\Module;
use GuzzleHttp\Psr7\Request;

$signer = Module::getInstance()->getRequestSigner();

$request = new Request('POST', 'https://api.example.test/webhook', [
    'Content-Type' => 'application/json',
], json_encode(['event' => 'order.paid'], JSON_THROW_ON_ERROR));

$response = Craft::createGuzzleClient()->send($signer->sign($request));
```

A k6 load-test example (hand-rolled signature base, no dependency) is in the request-signing doc.

## The retry policy

The docs are prescriptive; treat this as the contract:

1. Treat every non-2xx response as a failure.
2. For `429` and `503`, honor `Retry-After` (both delta-seconds and HTTP-date forms) and retry with **exponential backoff plus jitter**, bounded by a total deadline (the docs' example uses 30 s).
3. Only retry `POST` requests containing **read-only GraphQL queries** — never mutations.
4. When retries are exhausted, **throw** — so the framework's `stale-while-revalidate` layer preserves the last successful result instead of publishing partial content.

[Ky](https://github.com/sindresorhus/ky) implements this (`retry: { statusCodes: [429, 503], jitter: true }` + `totalTimeout`); the headless-apps doc also ships a dependency-free `fetchWithRetry()` wrapper to copy.

## Framework integration

- **Next.js** — wrap the data-fetching function in `unstable_cache` with `revalidate` and **narrow tags** (`['craft:blog']`); sign inside the function; when revalidation throws, Next.js keeps serving the last good result. ISR on Vercel and Netlify's current Next.js adapter both provide the stale-while-revalidate behavior.
- **Nuxt** — keep the signed request in a **server route** (`server/api/blog.get.js`) using a compliant retry helper, and apply `routeRules: { '/api/blog': { swr: 300 } }`. Don't rely on `$fetch`/ofetch retry (no `Retry-After`/backoff policy). The `isr` route rule works on Vercel/Netlify but adapter behavior differs — verify the deployed response headers before trusting CDN caching.
- **Astro** — prerendered pages should **let a failed Craft request fail the build**: Netlify's atomic deploys and Vercel's promote-on-success both leave the current production build in place, which beats publishing partial content. For on-demand rendering, Astro 7's route cache API provides `stale-while-revalidate` semantics.

## Pair With

- `caching-and-edge.md` — a headless app's GraphQL responses can themselves be edge-cached via `cache:` → `rules:`; fewer origin hits means fewer chances to be rate-limited.
- `deploy-pipeline.md` — `$CRAFT_CLOUD_SIGNING_KEY` is a reserved system variable (never set it yourself); build-time vs runtime variable rules.
- The `craftcms` skill's GraphQL reference for schema/token setup on the Craft side.

Last verified against https://craftcms.com/docs/cloud/headless-apps and https://craftcms.com/docs/cloud/request-signing (fetched from `craftcms/docs@main`) on 2026-09-02.
