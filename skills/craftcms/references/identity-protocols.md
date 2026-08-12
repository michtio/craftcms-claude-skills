# Identity Protocols: OIDC and SCIM in Plugins

Protocol domain knowledge for building SSO, login, and user-provisioning features in Craft plugins. Nothing here is a Craft API — these are the protocol-level facts that produce wrong designs when reasoned about from memory instead of checked against vendor documentation or a live endpoint. Each one did.

## Contents

- Back-channel vs front-channel logout
- Never derive the signing-algorithm allowlist from discovery
- An issuer is not a tenancy boundary
- SCIM: `active: false` is not a termination
- SCIM: PATCH operations are ordered and atomic
- Vendor behaviour beats the RFC — document the deviation

## Back-channel vs front-channel logout

The two OIDC logout mechanisms are routinely confused, and the names don't help:

- **Front-channel logout** is the *browser-mediated* one: the OP renders hidden iframes pointing at each RP's logout URI. It is the **fragile** mechanism — it depends on third-party cookies being sent in an iframe context, and it erodes further with every browser privacy tightening. Don't build new session-termination logic on it.
- **Back-channel logout** is a **server-to-server POST** of a signed `logout_token` (a JWT) to the RP's registered endpoint. No browser involved, so no cookie problem — but also no session cookie to identify *which* local session to kill. Terminating a session from a back-channel call requires a **stored mapping from the provider's `sid` claim to the local session**, persisted at login time. Without that table, back-channel logout can only ever be a no-op.

If a plugin supports both, they are two different code paths with different inputs (browser request with cookies vs bare POST with a JWT), not one handler with a flag.

## Never derive the signing-algorithm allowlist from discovery

The discovery document's `id_token_signing_alg_values_supported` reports **OP capability**, not the client's contract — and it is network-fetched input. A live Keycloak deployment advertises `HS256, HS384, HS512` in that list; deriving the accepted-algorithm set from it therefore reopens exactly the HMAC-downgrade attack (symmetric-key confusion) that a fixed allowlist exists to close.

The correct shape: a **hard-coded class constant** listing the algorithms the plugin will ever accept (asymmetric only, e.g. `RS256`, `ES256`), with a per-provider *setting* that selects from within that constant. Discovery may inform a default suggestion in the UI; it must never widen the accepted set at verification time.

## An issuer is not a tenancy boundary

A single global issuer admits every account that issuer serves. The canonical case: Google's issuer is `https://accounts.google.com` for **every** Google account, personal Gmail included — only the `hd` (hosted domain) claim bounds an organisation, and it must be explicitly validated.

The compounding trap is generic-OIDC plus JIT provisioning: "anyone who can authenticate gets an account created" plus "anyone with a Google account can authenticate" equals open registration wearing an SSO badge. Any provider whose issuer is shared across tenants needs an explicit tenancy claim check (`hd`, `tid`, or vendor equivalent) as a hard gate before provisioning, and the plugin's docs must say which claim it checks.

## SCIM: `active: false` is not a termination

Identity providers send `active: false` for **routine, recoverable events** — a user dropped from a provisioning scope, a licence change, a temporary suspension on the IdP side. Mapping it to a destructive local action (deleting the user, purging their content ownership) destroys real records on an ordinary directory event.

Map `active: false` to Craft's *suspend* (recoverable), and reserve destruction for an explicit SCIM `DELETE` — and even then, prefer deactivation with retention unless the deployment demands otherwise. Make the mapping a setting; directory conventions differ per vendor.

## SCIM: PATCH operations are ordered and atomic

RFC 7644 §3.5.2 requires PATCH operations to be applied **in payload order**, and the request to succeed or fail **atomically**. An implementation that buckets operations by type (all removes, then all adds) gives the wrong result for the RFC's own remove-then-add example — re-adding a value the same payload removed. Process the operations array in order, inside one transaction.

## Vendor behaviour beats the RFC — document the deviation

Where a vendor's live behaviour conflicts with the letter of the spec, the vendor wins: their payloads are what actually arrives. But code that silently accommodates a deviation becomes unexplainable within a release cycle. The practice: accommodate the observed behaviour, and **document the deviation at the accommodation site** (which vendor, what they send, which spec clause it violates, when it was observed) — in a code comment and, if integrators can observe it, in the plugin docs.
