# Password Policy

Password enforcement plugin by CraftPulse. Enforces minimum/maximum length, character requirements (uppercase, lowercase, numbers, symbols), "Have I Been Pwned" database checking, password strength indicator, and password retention/expiry with forced resets. CraftPulse's own plugin.

`craftpulse/craft-password-policy` — Free

## Documentation

- GitHub: https://github.com/craftpulse/craft-password-policy
- Plugin Store: https://plugins.craftcms.com/password-policy

## Common Pitfalls

- Setting `minLength` below 6 — Craft's own minimum is 6 characters. The plugin enforces this as a floor and validation will reject lower values.
- Enabling `pwned` check without considering network latency — the Have I Been Pwned API is called on every password save. For high-traffic registration forms, this adds a network round-trip. It's a security trade-off worth making, but be aware of the performance impact.
- Enabling `retentionUtilities` without configuring `expiryAmount` and `expiryPeriod` — retention features need both values set to work correctly.
- Forgetting that admin (user ID 1) is excluded from forced resets — the retention service intentionally skips the primary admin account to prevent lockout.
- Not running retention checks on a schedule — password expiry only triggers when the retention console command or queue job runs. Set up a cron job.

## Settings

All settings are configured in the CP under Settings → Password Policy, or via config file:

```php
// config/password-policy.php
return [
    '*' => [
        // Minimum password length (floor: 6, Craft's minimum)
        'minLength' => 12,

        // Maximum password length (0 = no maximum)
        'maxLength' => 0,

        // Require mixed case (uppercase + lowercase)
        'cases' => true,

        // Require at least one number
        'numbers' => true,

        // Require at least one special character (!@#$%^&*)
        'symbols' => true,

        // Show password strength indicator in CP
        'showStrengthIndicator' => true,

        // Check password against Have I Been Pwned database
        'pwned' => true,

        // Enable password retention/expiry features
        'retentionUtilities' => false,

        // Password expiry period (amount + period)
        'expiryAmount' => 90,
        'expiryPeriod' => 'day',    // day, week, month, year

        // Generate CSP nonces for inline scripts
        'cspNonce' => false,
    ],
];
```

## How It Works

### Password Validation

The plugin registers custom validation rules on the `User` element via `DefineRulesEvent`. When a user sets or changes their password, the rules enforce:

1. **Length** — minimum (and optional maximum) character count
2. **Character requirements** — mixed case, numbers, symbols (based on settings)
3. **Pwned check** — queries the Have I Been Pwned API using k-anonymity (only the first 5 chars of the SHA-1 hash are sent, never the full password)

The validation pattern is generated dynamically from the enabled settings — only active rules are included in the regex.

### Password Strength Indicator

When `showStrengthIndicator` is enabled, the CP shows a visual strength meter on password fields. This gives editors real-time feedback while typing.

### Password Retention

When `retentionUtilities` is enabled:

- A CP utility page shows retention status and allows manual forced resets
- Expired passwords trigger `passwordResetRequired = true` on the user
- Users must change their password on next login
- The primary admin (user ID 1) is always excluded from forced resets

## Console Commands

```bash
# Force reset all expired passwords (queue job)
ddev craft password-policy/retention/force-reset-passwords

# Force reset with --queue flag (queue only, don't run immediately)
ddev craft password-policy/retention/force-reset-passwords --queue
```

Set up a cron job for automatic retention checking:

```bash
# Check daily at 2am
0 2 * * * cd /var/www/html && php craft password-policy/retention/force-reset-passwords --queue
```

## Architecture

| Service | Responsibility |
|---------|---------------|
| `PasswordService` | Generates validation regex pattern and error messages from settings |
| `RetentionService` | Handles password expiry checks, forced resets via queue jobs |
| `SecurityService` | Security-related utilities |
| `PwnedValidator` | Queries Have I Been Pwned API with k-anonymity |

### Events

The plugin hooks into Craft's user lifecycle via:

- `User::EVENT_DEFINE_RULES` — adds password validation rules
- `View::EVENT_BEFORE_RENDER_PAGE_TEMPLATE` — injects strength indicator JS
- `Plugins::EVENT_AFTER_INSTALL_PLUGIN` — initial setup

## Recommended Settings

For most projects:

```php
'minLength' => 12,
'maxLength' => 0,          // No max — let password managers generate long passwords
'cases' => true,
'numbers' => true,
'symbols' => false,        // Controversial — NIST guidelines no longer recommend
'showStrengthIndicator' => true,
'pwned' => true,           // Always enable — negligible performance cost
'retentionUtilities' => false, // Enable only if compliance requires it
```

## Pair With

- **Sherlock** — security scanning and monitoring alongside password enforcement
