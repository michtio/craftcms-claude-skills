# Custom Domains and DNS

Add a custom domain in the Cloud Console, prove ownership with a TXT record, validate the certificate with provided records, then route traffic via CNAME. SSL is auto-issued by Cloudflare. `www` is not auto-created.

## Documentation

- Domains: https://craftcms.com/docs/cloud/domains
- Cloudflare (Orange-to-Orange): https://craftcms.com/docs/cloud/cloudflare

## Common Pitfalls

- Adding a CNAME for `example.com` (the apex) and expecting it to work everywhere. Most DNS providers can't put CNAME on the apex — use the two A records Cloud provides in the Route Traffic step instead. CNAME flattening is provider-specific (Cloudflare and a few others support it).
- Pointing the domain at Cloud before the TXT ownership record propagates. Cloud rejects the routing until it can verify ownership via `_cf-custom-hostname` + your domain.
- Adding the root domain only and expecting `www.example.com` to also work. `www` is a separate hostname — add it explicitly if you want it. The docs are explicit.
- Removing the verification TXT records after the initial validation. Cloudflare may re-check periodically — leave the records in place.
- Trying to manage Cloudflare's edge config yourself (page rules, transform rules, workers) on a domain Cloud is fronting. Cloud's edge layer is the boundary; you can't add another Cloudflare layer in front (Orange-to-Orange has a specific setup — see Cloudflare doc).

## Adding a domain

In the Cloud Console: **Domains → New domain**.

1. Enter the root domain (`example.com` — not `https://example.com`, no path).
2. Optionally pick an environment to route to (you can do this later).
3. Cloud walks you through verification, certificate validation, and traffic routing in turn.

You complete each step in the DNS provider's UI, then return to Cloud to confirm.

## Required DNS records

### 1. Ownership verification (TXT)

| Type | Name | Value |
|---|---|---|
| TXT | `_cf-custom-hostname.example.com` | Provided by Cloud |

Cloud uses this to confirm you control the domain before issuing a cert or accepting traffic.

### 2. Certificate validation (CNAME + 2 TXT)

Cloud's Console shows three records — typically one CNAME and two TXT — that complete the SSL certificate handshake with Cloudflare's CA. Copy them as shown.

### 3. Traffic routing

**For subdomains** (preferred wherever possible):

| Type | Name | Value |
|---|---|---|
| CNAME | `www.example.com` (or any subdomain) | `edge.craft.cloud` |

**For apex domains** (when CNAME flattening isn't available):

Cloud's Route Traffic step shows two A-record IPs to use:

| Type | Name | Value |
|---|---|---|
| A | `example.com` | IP from Route Traffic step |
| A | `example.com` | (second) IP from Route Traffic step |

If your DNS provider supports CNAME flattening (Cloudflare, Route 53 with alias records, DNSimple, others), use a flattened CNAME → `edge.craft.cloud` instead of the A records — it stays correct if Cloud's edge IPs change.

## SSL

Cloudflare auto-issues and rotates SSL certificates for every domain pointed at Cloud. There's no manual certificate management — no Let's Encrypt cron, no upload step. Once the ownership TXT and cert-validation CNAME/TXT records are in place, SSL is live within minutes.

## The `www` subdomain

Not auto-created. If you want `www.example.com` to work alongside `example.com`, add it as a separate domain in the Cloud Console, with its own DNS records.

A common pattern: redirect `www` → apex (or vice versa) via `redirects:` in `craft-cloud.yaml`. See `config-file.md` (Redirects).

## Preview domains

Every environment gets an auto-assigned preview URL:

```
project-{handle}-environment-{prefix}.preview.craft.cloud
```

Examples:
- `project-acme-marketing-environment-b62dec18.preview.craft.cloud`
- `project-acme-marketing-environment-a1f0e29b.preview.craft.cloud`

The handle is the project's URL slug; the prefix is the first segment of the environment's UUID. Access via the globe icon in Console.

Preview URLs are useful for:
- Sharing a staging environment with a stakeholder before DNS cutover.
- Per-branch testing when each Cloud environment tracks a different Git branch.
- Final verification before swinging production DNS.

## Pricing

Every project includes one root domain plus unlimited subdomains on that root. Additional root domains can be purchased — pricing isn't documented inline; check the Console for current rates (the survey noted "$20/mo each" historically, but verify against the Console UI).

## Cloudflare Orange-to-Orange

If your domain is already proxied through Cloudflare on your own account (orange cloud icon in Cloudflare DNS), Cloud needs a specific setup so Cloud's Cloudflare layer doesn't conflict with yours. See the dedicated [Cloudflare doc](https://craftcms.com/docs/cloud/cloudflare) for the configuration. The short version: enable Custom Hostnames on your Cloudflare account and follow the documented record set rather than the default subdomain CNAME flow.

If your domain isn't proxied through your own Cloudflare account, you don't need this — the default DNS flow handles everything.

## DNS propagation

Cloud notes: "anywhere from a couple of minutes to 24 hours." Plan DNS cutover during a low-traffic window if minutes matter. For pre-cutover validation, use the preview URL.

Last verified against https://craftcms.com/docs/cloud/domains and https://craftcms.com/docs/cloud/cloudflare on 2026-05-28.
