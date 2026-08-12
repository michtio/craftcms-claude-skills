# Warp

Passwordless front-end auth for Craft members, by CraftPulse: magic-link and one-time-code (OTP) sign-in, passkeys (WebAuthn), passwordless registration, and session/device management. Built on Auth Kit (`craftpulse/craft-auth-kit`) — a Composer **library**, not a plugin: it installs as a dependency, never appears in the plugins list, and needs no install step.

`craftpulse/craft-warp` — Commercial (Plugin Store). Craft 5.10+, PHP 8.2+.

## Documentation

- GitHub: https://github.com/craftpulse/craft-warp
- Docs: `docs/setup.md`, `docs/configuration.md`, `docs/templates.md`, `docs/endpoints.md`, `docs/console-commands.md`, `docs/privacy.md` in the repo
- Plugin Store: https://plugins.craftcms.com/warp

## Common Pitfalls

- **Hand-building a magic-link URL with `token`** — the query param is **`mlToken`**. Craft's web app reserves `token` for its own routed tokens and 400s any request naming it with a value Craft didn't issue, so a `token=`-built URL never reaches Warp's controller at all.
- **Posting Craft's hashed `redirect` to `warp/auth/verify-code`** — that action reads a plain **`returnUrl`** body param and ignores `redirectInput()` entirely; the member silently lands on the site root. The asymmetry is deliberate: `warp/auth/request` *does* use Craft's `redirect` (the channel-swap script rewrites it), a verified code goes straight to the destination the credential was issued for.
- **Printing a builder without `.render()`** — `{{ craft.warp.otpForm() }}` goes through `__toString()`, which Twig escapes, so the markup appears on the page as visible tags. Always terminate with `.render()`.
- **Differentiating known/unknown addresses in page copy** — `warp/auth/request` answers identically for a known address, an unknown one, and a suspended account (enumeration safety). The "check your email" page you redirect to must read the same in every case.
- **Passing `digits` to size the code input** — `digits` sizes the *input*, not the code. The server issues codes at the configured `otpDigits` length regardless, so a disagreeing `digits` caps the input below a valid code's length and makes sign-in impossible (Warp logs a warning). Change the `otpDigits` setting instead.
- **Treating `session.isNewLocation` as boolean** — it's tri-state: `true` new place, `false` assessed and known, `null` never asked (pre-5.0.2 sessions, or no registry row). Test with `is same as(true)`; never render `null` as "not new".
- **Rendering a revoke button for every session** — a session whose `uid` is `null` cannot be signed out individually; branch on it ("Sign out everywhere else" still clears those).
- **`{{ input.id }}` on a builder** — Twig resolves `id` to the one-argument *setter*. Use `{{ input.getId() }}`, and read it **before** `.render()` (reading fixes the generated id for the render).
- **Tailwind preflight / CSS resets eating the digit boxes** — anything that zeroes `border-width` globally beats Warp's layered baseline and leaves white boxes on a white card. Give the boxes an explicit border: `boxAttrs: { class: 'border border-gray-300' }`.
- **`w-full` on the email input not going full width** — Warp's baseline caps the email inputs at `max-width: 24rem`; a width utility doesn't lift a cap. Use the important form (`max-w-none!` in Tailwind 4) or an un-layered rule of your own.
- **Not handling the 403 `reauthRequired` branch** — the three passkey routes are recent-auth gated: a session older than `recentAuthDuration` gets `403 {"reauthRequired": true}`. Send the member to the sign-in page (that *is* re-authentication for a passwordless member). The two session routes and the nudge dismiss are deliberately **not** gated.

## Setup

Warp changes nothing on install. To open a member area:

```bash
ddev craft warp/example-templates     # copy the styled example member area into templates/
```

Then point Craft's `loginPath` (general config) at the copied login page (e.g. `members/login`), and choose login methods + registration in the CP under **Warp**. Emails ride Craft's system messages, so they're customized in Settings → Email Messages, per site.

## The `craft.warp` variable

Templates never touch a Warp service or record — everything goes through `craft.warp`. Data accessors are read as properties; the four render builders are called as functions and terminated with `.render()`.

| Accessor | Returns |
|---|---|
| `loginMethods` | Enabled channels, subset of `magic-link` / `otp` |
| `registrationEnabled` | Warp's `enableRegistration` AND Craft's `allowPublicRegistration` |
| `otpDigits` | Configured code length (size custom inputs from this, never hardcode) |
| `tokenLifetime` | Issued-credential validity as human text ("15 minutes") — same formatting as the emails, so page and email never disagree |
| `requestedEmail` | Address the visitor last requested a credential for, or `null` (session-echoed; cleared by a successful verify) |
| `hasPasskeys` / `passkeys` | Current user's enrollment state / list (`credentialName`, `dateLastUsed`, `uid` for `warp/passkeys/delete`) |
| `sessions` | `SessionInfo` models: `deviceLabel`, `deviceType`, `city`, `ip`, `lastSeen`, `isCurrent`, tri-state `isNewLocation`, `uid` for `warp/sessions/revoke` (nullable) |
| `showPasskeyNudge` | Whether to show the enrollment nudge (reading it changes nothing; holds for the session) |
| `webauthnJsUrl` | Published URL of the WebAuthn client script, for hand-wired ceremonies |

Auth Kit also registers `craft.authKit`; its passkey accessors are the same ones `craft.warp` re-exposes, so never reach for it.

## Render builders

Four builders: `requestForm()` (the email form — one field drives both sign-in and sign-up), `otpForm()` (whole code-entry form), `otpInput()` (segmented code input alone, for composing your own form), `passkeyButton()` (passkey section — belongs *beside* the email form, never instead of it). All fluent: options-array keys match chainable setters, and an **unknown option throws** rather than being ignored.

```twig
{{ craft.warp.requestForm({
    linkSentUrl: 'members/link-sent',
    otpVerifyUrl: 'members/otp-verify',
    returnUrl: url('members/account'),
    email: craft.warp.requestedEmail,
}).render() }}
```

Attribute rules (every element has an `*Attrs` option, every string a copy option):

- A `class` you pass **accumulates onto** Warp's own class; pass `resetClass: true` in the same array to own it outright.
- A `data` array **merges key by key**, so your data attribute never takes `data-warp-otp` (etc.) with it — those are the client scripts' contract.
- Any other attribute is replaced outright; `null`/`false` removes it.

`renderCss: false` per render, or globally in `config/warp.php`, drops the stylesheet (markup and behavior unaffected — then style `enhancedClass` yourself, since hiding the original input is the one rule the widget depends on). The three scripts always load; they're the affordance, not decoration, and degrade to plain-form behavior without JS.

### CSS: the `warp` cascade layer

All cosmetic rules live in an `@layer warp`, so any **un-layered** site rule beats them with no `!important` — that's the escape from Craft injecting plugin CSS after your stylesheet. Two rules are deliberately un-layered (behavior, not style): the passkey `[hidden]` handling and `warp-otp--enhanced` (hides the raw input once the boxes exist). Between *two* layers, later-declared wins — so a runtime-injected framework layer order (Tailwind 4 Play CDN) is not guaranteed against `warp`; when a layered utility must win, use the framework's important form (`max-w-none!`) or an un-layered rule. `docs/templates.md` lists every property the baseline sets, so you can tell whether a class of yours is competing at all.

## Endpoints

Ten action routes, always via `actionUrl()`. Conventions: **CSRF on every POST**; **`Accept: application/json` switches the response to JSON** (otherwise redirect + flash); **the HTTP status carries the outcome** (200 success, 400 failure, 429 rate-limited) — read the status, not a body flag; only `warp/nudge/dismiss` sends a `success` key.

| Route | Method, auth | Notes |
|---|---|---|
| `warp/auth/request` | POST, anonymous | `email`, `channel`, `returnUrl`, Craft `redirect`. Identical response in every branch (enumeration-safe). 5/IP/60s + per-address throttle |
| `warp/auth/verify-code` | POST, anonymous | `email`, `code`, **`returnUrl` (not `redirect`)**. Opaque failure message. 10/IP/60s + `otpMaxAttempts` burns the code |
| `warp/auth/verify-link` | GET, anonymous | **`mlToken`** + `returnUrl`. Failure → `loginPath` with fail flash |
| `warp/auth/verify-registration` | GET, anonymous | Same shape; provisions the account and signs in |
| `warp/passkeys/creation-options` | POST, member, JSON-only | Recent-auth gated (403 `reauthRequired`) |
| `warp/passkeys/verify-creation` | POST, member, JSON-only | `credentials`, `credentialName` (empty name refused). Gated |
| `warp/passkeys/delete` | POST, member, JSON-only | `uid`. Gated. Unknown `uid` is a silent no-op (no probing) |
| `warp/sessions/revoke` | POST, member | `uid`. **Not** gated — cleanup is defensive |
| `warp/sessions/revoke-others` | POST, member | No params; answers `count`. Not gated |
| `warp/nudge/dismiss` | POST, member | Clears the nudge for the session. Not gated |

Passkey *sign-in* posts to two **core** endpoints (`auth/passkey-request-options`, `users/login-with-passkey`); `passkeyButton()` wires them.

**Return URLs**: validated against the base URL of the site the request was made against (longest-base-URL match, like Craft's own request-site resolution) — site-relative paths and same-site absolute URLs pass; other hosts, other *sites* of the same install, protocol-relative and `javascript:` tricks are dropped for the site root.

## Hand-written markup

Warp registers no site template root — every page is yours, the example bundle is a starting point, and the builders are declinable. The DOM hooks the always-loaded scripts read are **documented public API** (`docs/templates.md`): `input[data-warp-otp]` + its `data-warp-otp-*` attributes for the code input, `form[data-warp-request]` + `data-warp-redirect` per channel radio, `[data-warp-passkey]` + `data-warp-passkey-*` for the ceremony. A fully hand-written page must also register the asset bundle(s) itself (e.g. `craftpulse\warp\assetbundles\warpotp\WarpOtpAsset`) — without it the markup still posts, but nothing enhances.

## Settings

CP settings screen (project-config backed) or `config/warp.php`. Six numeric settings are env-aware (`$WARP_TOKEN_TTL` style): `tokenTtl`, `otpDigits`, `otpMaxAttempts`, `perEmailLimit`, `perEmailWindow`, `recentAuthDuration` — in PHP read them through the typed getters (`getTokenTtl()`), never the raw property. Others: `loginMethods`, `enableRegistration`, `registrationGroupUid`, `enablePasskeyNudge`, `notifyOnNewLocation`, `anonymizeIp`, `geoDatabaseUrl`, `renderCss`.

Permissions: `warp:view-overview`, `warp:manage-settings` (kebab-case, under a Warp heading). With `allowAdminChanges` off, the settings screen renders disabled and the save action fails closed.

Optional coarse geo (city on sessions, new-location alerts) needs an MMDB database: `ddev craft warp/geo/refresh` downloads it; without one, location features quietly stay off and `isNewLocation` is assessed as `false`, not `null`.

**Fixed values**: the sign-in log is pruned after 90 days (GC pass, not configurable); the session registry rides Craft's own GC. New-location alerts are deduped for 24h across CraftPulse security plugins via the shared Auth Kit history.

## Passwordless means passwordless

Members created through Warp **never have a password** — registration provisions an active, password-less account. Warp ships no password-set/reset UI and never calls password validation. A site that adds its own password surface elsewhere integrates policy via Auth Kit's `PasswordValidatorInterface`; Warp is not in that path. GDPR/what-to-disclose material is in `docs/privacy.md`.

## Pair With

- **Password Policy** — only if the site keeps a separate password surface; Warp itself needs no password rules.
- **Blitz / static caching** — the passkey button emits Craft's own CSRF field specifically so `asyncCsrfInputs` can swap in a fresh token on a cached page; keep that mechanism intact rather than templating your own static token.
