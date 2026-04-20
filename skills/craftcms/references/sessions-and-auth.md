# Sessions & Auth Internals

How Craft CMS 5's session and authentication system works under the hood: the dual-layer session model, auth token lifecycle, session invalidation on password change, the `passwordResetRequired` gap, elevated sessions, and patterns for plugins that manage user auth state. For session **configuration** (Redis, durations, cookie settings), see `config-app.md` and `config-general.md`. For permission checks and authorization events, see `permissions.md` and `element-authorization.md`.

## Documentation

- User management: https://craftcms.com/docs/5.x/system/user-management.html
- Session config: https://craftcms.com/docs/5.x/reference/config/general.html

## Common Pitfalls

- Assuming `passwordResetRequired = true` forces immediate logout — it does not. The flag is only checked during authentication (login flow), not on every request. A user with an active session continues normally until the session expires.
- Thinking Redis/Memcached session storage replaces DB tokens — Craft maintains auth tokens in `Table::SESSIONS` (database) regardless of the PHP session backend. Deleting DB rows invalidates sessions even when PHP sessions live in Redis.
- Calling `Craft::$app->getUser()->logout()` to invalidate other sessions — this only logs out the current user. To invalidate all sessions for a specific user, delete their rows from `Table::SESSIONS`.
- Setting `elevatedSessionDuration` to `0` in production — this disables the password re-entry requirement for sensitive operations entirely. `getHasElevatedSession()` always returns `true`.
- Not understanding that `securityKey` change invalidates everything — changing `CRAFT_SECURITY_KEY` invalidates all sessions, password reset tokens, and encrypted field values across all users.

## Contents

- [Dual-Layer Session Model](#dual-layer-session-model)
- [Auth Token Lifecycle](#auth-token-lifecycle)
- [Session Invalidation on Password Change](#session-invalidation-on-password-change)
- [The passwordResetRequired Gap](#the-passwordresetrequired-gap)
- [Elevated Sessions](#elevated-sessions)
- [Session Configuration Quick Reference](#session-configuration-quick-reference)
- [Plugin Patterns](#plugin-patterns)

## Dual-Layer Session Model

Craft uses two independent layers for session management:

### Layer 1: PHP Sessions

The standard PHP session mechanism, stored via whatever backend is configured:

| Backend | Config Location | Notes |
|---------|----------------|-------|
| Files (default) | No config needed | `craft\web\Session` handles it |
| Redis | `config/app.web.php` | Requires `yii2-redis` package |
| Memcached | `config/app.web.php` | Requires `yii2-memcached` package |
| Database | `config/app.web.php` | Uses `Table::PHPSESSIONS` (`{{%phpsessions}}`) |

PHP sessions hold transient data: flash messages, return URLs, CSRF tokens, form data. They are tied to the browser's session cookie (`CraftSessionId` by default).

### Layer 2: Auth Tokens (Database)

Independently of PHP session storage, Craft maintains auth tokens in the `{{%sessions}}` table (`Table::SESSIONS`):

| Column | Type | Purpose |
|--------|------|---------|
| `id` | `int` | Primary key |
| `userId` | `int` | FK to `{{%users}}` |
| `token` | `char(100)` | Unique auth token |
| `dateCreated` | `datetime` | When the session was created |
| `dateUpdated` | `datetime` | Last activity timestamp |

**This table is always in the database**, even when Redis or Memcached handles PHP sessions. Token validation happens on every authenticated request by querying this table.

### How the two layers connect

On login:
1. Craft creates a PHP session (layer 1)
2. Craft generates an auth token and stores it in both the PHP session and `Table::SESSIONS` (layer 2)
3. The browser receives the session cookie

On every authenticated request:
1. PHP session is restored from the cookie (layer 1)
2. Craft reads the auth token from the PHP session
3. Craft validates the token against `Table::SESSIONS` (layer 2)
4. If the token doesn't exist in the DB → user is logged out, even if the PHP session is valid

This means: **deleting rows from `Table::SESSIONS` is the authoritative way to invalidate sessions**, regardless of the PHP session backend.

## Auth Token Lifecycle

### Login

When `Craft::$app->getUser()->login()` succeeds:
1. Password is verified against the stored hash
2. Auth token is generated and written to `Table::SESSIONS`
3. Token is stored in the PHP session
4. `User::$authTokenTimestamp` is set
5. "Remember Me" cookie is set if requested (stores token for session restoration)

### Token validation (every request)

`craft\web\User::validateToken()` runs on every authenticated request:
1. Reads token from PHP session
2. Queries `Table::SESSIONS` for matching `userId` + `token`
3. If no match → forces logout
4. If match → updates `dateUpdated` timestamp

### Logout

`Craft::$app->getUser()->logout()`:
1. Deletes the current session's token from `Table::SESSIONS`
2. Destroys the PHP session
3. Clears the "Remember Me" cookie

### Session expiry

Craft checks the `dateUpdated` column against `userSessionDuration` (or `rememberedUserSessionDuration`). Stale tokens are cleaned up by garbage collection (`Gc::EVENT_RUN`). The `purgeStaleUserSessionDuration` config setting controls how long to keep expired session rows (default: 90 days).

## Session Invalidation on Password Change

When a user's password changes (either self-service or admin-initiated), Craft automatically invalidates all other sessions for that user:

1. During `User::afterSave()`, Craft detects `$this->newPassword` is set
2. Queries `Table::SESSIONS` for all rows matching the user's ID
3. Deletes all rows **except** the current session's token: `['not', ['token' => $currentToken]]`
4. Result: every other browser/device is immediately logged out on next request

This is automatic — no plugin code needed for password-change invalidation.

### What triggers this

- User changes their own password via the CP profile page
- Admin changes a user's password via their edit screen
- Password reset flow (user clicks reset link, enters new password)
- Programmatic: setting `$user->newPassword` and saving

### What does NOT trigger this

- Setting `passwordResetRequired = true` without changing the password
- Changing the user's email address
- Suspending or deactivating a user (suspension prevents new logins but doesn't kill existing sessions)
- Changing user group membership

## The passwordResetRequired Gap

`passwordResetRequired` is a boolean field on the User element. When set to `true`, it forces the user to choose a new password on their next login.

**Critical detail:** This flag is checked inside `getAuthStatus()`, which is called **during authentication only** (the login flow). It is NOT checked on every request via `renewAuthStatus()`.

This means:
- A user with `passwordResetRequired = true` and an **active session** continues using the site normally
- The flag only takes effect when they log out and try to log in again (or their session expires)
- To force an immediate re-authentication, you must also delete their sessions from `Table::SESSIONS`

### Force-logout pattern for plugins

```php
use craft\db\Table;

// Set the flag
$user->passwordResetRequired = true;
Craft::$app->getElements()->saveElement($user);

// Force immediate logout by deleting all sessions
Craft::$app->getDb()->createCommand()
    ->delete(Table::SESSIONS, ['userId' => $user->id])
    ->execute();
```

This is the only reliable way to force immediate re-authentication. The user's next request will fail token validation and redirect to login, where the `passwordResetRequired` flag takes effect.

## Elevated Sessions

Elevated sessions are a second-factor gate for sensitive CP operations. After re-entering their password, the user enters an "elevated" state for a limited time.

### How it works

1. User triggers a sensitive action (change password, manage users, edit GraphQL tokens)
2. Craft's JS layer (`ElevatedSessionManager.js`) shows a password re-entry modal
3. User enters password → POST to `users/start-elevated-session`
4. Craft stores the elevated session timeout in the PHP session
5. `getHasElevatedSession()` returns `true` until the timeout expires

### Configuration

| Setting | Default | Effect |
|---------|---------|--------|
| `elevatedSessionDuration` | `300` (5 min) | How long the elevated state lasts. `0` disables — `getHasElevatedSession()` always returns `true`. |

### Controller enforcement

```php
// Require elevated session before sensitive action
$this->requireElevatedSession();

// This calls getHasElevatedSession() on the User component
// If not elevated, throws a 403 that the JS layer catches to show the modal
```

### Operations that require elevation

Built-in operations that call `requireElevatedSession()`:
- Changing user email address
- Changing user password
- Managing user groups and permissions
- Editing GraphQL schemas and tokens
- Plugin settings changes (when `$requireAdmin` is true)

Plugins should call `$this->requireElevatedSession()` in controller actions that modify authentication state, security settings, or access controls.

## Session Configuration Quick Reference

For full config details, see `config-general.md` and `config-app.md`. Quick reference:

| Setting | Location | Default | Purpose |
|---------|----------|---------|---------|
| `userSessionDuration` | general.php | `3600` (1h) | Active session lifetime |
| `rememberedUserSessionDuration` | general.php | `1209600` (14d) | "Remember Me" lifetime |
| `elevatedSessionDuration` | general.php | `300` (5min) | Elevated session window |
| `phpSessionName` | general.php | `'CraftSessionId'` | Session cookie name |
| `requireMatchingUserAgentForSession` | general.php | `true` | Validate user agent on restore |
| `requireUserAgentAndIpForSession` | general.php | `true` | Require UA+IP for new session |
| `purgeStaleUserSessionDuration` | general.php | `7776000` (90d) | Cleanup of expired DB tokens |
| `session` component | app.web.php | DB-backed | Redis/Memcached override |

## Plugin Patterns

### Invalidating all sessions for a user

```php
use craft\db\Table;

/**
 * Force-logout a user from all devices.
 *
 * @param int $userId
 */
public function invalidateAllSessions(int $userId): void
{
    Craft::$app->getDb()->createCommand()
        ->delete(Table::SESSIONS, ['userId' => $userId])
        ->execute();
}
```

### Invalidating all sessions except current

```php
use craft\db\Table;

/**
 * Force-logout a user from all devices except the current one.
 *
 * @param int $userId
 */
public function invalidateOtherSessions(int $userId): void
{
    $currentToken = Craft::$app->getUser()->getToken();

    Craft::$app->getDb()->createCommand()
        ->delete(Table::SESSIONS, [
            'and',
            ['userId' => $userId],
            ['not', ['token' => $currentToken]],
        ])
        ->execute();
}
```

### Counting active sessions

```php
use craft\db\Table;

/**
 * Count active sessions for a user.
 *
 * @param int $userId
 * @return int
 */
public function getActiveSessionCount(int $userId): int
{
    return (int)(new \craft\db\Query())
        ->from(Table::SESSIONS)
        ->where(['userId' => $userId])
        ->count();
}
```

### Checking if a user has been force-reset

```php
// Check if user needs to reset password on next login
if ($user->passwordResetRequired) {
    // User will be prompted on next login
    // But they may still have active sessions
    $hasActiveSessions = $this->getActiveSessionCount($user->id) > 0;

    if ($hasActiveSessions) {
        // Force immediate logout if needed
        $this->invalidateAllSessions($user->id);
    }
}
```

### GDPR-safe session purge

For GDPR compliance, combine session deletion with the GC event for automatic cleanup:

```php
use craft\services\Gc;
use yii\base\Event;

Event::on(
    Gc::class,
    Gc::EVENT_RUN,
    function() {
        // Purge sessions for deactivated users
        Craft::$app->getDb()->createCommand()
            ->delete(Table::SESSIONS, [
                'userId' => (new \craft\db\Query())
                    ->select('id')
                    ->from(Table::USERS)
                    ->where(['active' => false]),
            ])
            ->execute();
    }
);
```
