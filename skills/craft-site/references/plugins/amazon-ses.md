# Amazon SES

Mail transport adapter by PutYourLightsOn. Replaces Craft's default Sendmail/SMTP transport with Amazon Simple Email Service via the Symfony Amazon Mailer. Zero configuration beyond AWS credentials — no Twig API, no CP section, just a transport swap. Used in 5/6 projects.

`putyourlightson/craft-amazon-ses` — Free (MIT)

## Documentation

- Docs: https://putyourlightson.com/plugins/amazon-ses
- GitHub: https://github.com/putyourlightson/craft-amazon-ses

## Setup

1. Install via Plugin Store or Composer
2. CP → Settings → Email → Transport Type → "Amazon SES"
3. Enter AWS region and credentials

Credentials can be left blank to use the default AWS credential provider chain (environment variables, IAM roles, etc.).

## Configuration

All settings are configured via the CP email settings UI. Environment variables are supported:

| Setting | Env Example | Description |
|---------|-------------|-------------|
| Region | `$AWS_REGION` | AWS region (e.g., `eu-west-1`) |
| API Key | `$AWS_ACCESS_KEY_ID` | AWS access key (blank for credential chain) |
| Secret | `$AWS_SECRET_ACCESS_KEY` | AWS secret key (blank for credential chain) |
| Configuration Set | `$SES_CONFIGURATION_SET` | Optional — for bounce/complaint tracking via SNS |

### Environment-Based Config

Use `.env` for credentials:

```env
# .env
AWS_REGION=eu-west-1
AWS_ACCESS_KEY_ID=AKIAXXXXXXXXXX
AWS_SECRET_ACCESS_KEY=your-secret-key
SES_CONFIGURATION_SET=my-config-set
```

Then reference `$AWS_REGION` etc. in the CP email settings.

## Common Pitfalls

- Not verifying sender domain/email in SES — AWS requires domain verification (DKIM + SPF via Route 53 or manual DNS) before sending. Without it, emails fail silently or bounce.
- Using SES in sandbox mode — new SES accounts are sandboxed (can only send to verified addresses). Request production access before launch.
- Missing SNS configuration for bounces — if using a Configuration Set, configure SNS topics for bounces and complaints. This is especially important with Campaign plugin.
- Hardcoding credentials — use environment variables or IAM roles, never hardcode keys in the CP.
- Not setting the right region — SES endpoints are regional. Use the same region as your verified domain.

## No Twig/PHP API

This plugin has no Twig API, no console commands, and no config file. It registers a mail transport adapter — that's it. All email sending goes through Craft's standard `Craft::$app->mailer->compose()` API.

For the full AWS SES setup pattern including DKIM, SPF, and DMARC configuration, see `references/third-party-integration.md` in this skill.

## Pair With

- **Campaign** — Campaign sends email campaigns through Craft's mailer, so Amazon SES handles delivery. Campaign has webhook support for SES bounce/complaint notifications via SNS.
- **Formie** — form notification emails route through SES when configured as the transport
- **Sherlock** — monitoring alerts go through Craft's mailer → SES
