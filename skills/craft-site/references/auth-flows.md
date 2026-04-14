# Front-End Authentication Flows Reference

> Complete form templates and patterns for user authentication on the front end of a Craft CMS 5 site. Every form is copy-pasteable with proper error handling.

## Documentation

- Controller actions: https://craftcms.com/docs/5.x/reference/controller-actions.html
- User management: https://craftcms.com/docs/5.x/system/user-management.html
- User element: https://craftcms.com/docs/5.x/reference/element-types/users.html

## Common Pitfalls

- Missing `{{ csrfInput() }}` on forms -- silent failure, Craft rejects the POST with no useful error.
- Missing `{{ actionInput('users/...') }}` -- form posts to the template URL instead of the controller action.
- Not using `{{ redirectInput() }}` -- user lands on homepage instead of the intended destination.
- Showing registration form to logged-in users -- use `{% requireGuest %}` to redirect them away.
- Not checking `currentUser` before showing edit profile -- use `{% requireLogin %}` to force authentication.
- Forgetting `currentPassword` when changing email or password on profile update -- Craft requires it for identity verification.
- Not setting `setPasswordPath` and `invalidUserTokenPath` in general config -- password reset emails link to paths that don't exist or show Craft's default error page.
- Exposing user enumeration via different error messages for valid/invalid emails -- enable `preventUserEnumeration` to return the same response regardless.
- Forgetting to enable public registration in Settings > Users > Settings -- registration form silently fails.
- Using `username` field when `useEmailAsUsername` is `true` -- the field does not exist, validation fails.
- Not handling the `user` variable for registration/profile validation errors -- Craft passes it back on failed saves.
- Missing `{{ flashes() }}` or manual flash message handling -- success states have no visible feedback.

## Contents

- [Login Form](#login-form)
- [Registration Form](#registration-form)
- [Password Reset Request](#password-reset-request)
- [Set New Password](#set-new-password)
- [Edit Profile](#edit-profile)
- [Email Verification](#email-verification)
- [Navigation Partial](#navigation-partial)
- [Twig Access Control Tags](#twig-access-control-tags)
- [User Session in Twig](#user-session-in-twig)
- [GeneralConfig Settings That Affect Auth](#generalconfig-settings-that-affect-auth)

## Login Form

Typically at `templates/auth/login.twig` or whatever path matches the `loginPath` config setting (default: `login`).

```twig
{# --------------------------------------------------------------------------
   Login Form
   Path: templates/auth/login.twig
   Config: generalConfig.loginPath must point to this template's route
   -------------------------------------------------------------------------- #}

{% requireGuest %}

{% extends '_layouts/site' %}

{% block content %}

  <h1>Sign In</h1>

  {# --------------------------------------------------------------------------
     Error message — Craft sets this variable on failed login.
     The message is generic by default ("Invalid username or password")
     to prevent user enumeration.
     -------------------------------------------------------------------------- #}
  {% if errorMessage is defined %}
    <div role="alert">
      <p>{{ errorMessage }}</p>
    </div>
  {% endif %}

  <form method="post" accept-charset="UTF-8">

    {{ csrfInput() }}
    {{ actionInput('users/login') }}
    {{ redirectInput('account') }}

    {# --------------------------------------------------------------------------
       loginName accepts either email or username depending on config.
       When useEmailAsUsername is true, this is always the email address.
       The value is repopulated on failed login via the loginName variable.
       -------------------------------------------------------------------------- #}
    <div>
      <label for="loginName">Email</label>
      <input
        type="email"
        id="loginName"
        name="loginName"
        value="{{ loginName ?? '' }}"
        autocomplete="email"
        required
      >
    </div>

    <div>
      <label for="password">Password</label>
      <input
        type="password"
        id="password"
        name="password"
        autocomplete="current-password"
        required
      >
    </div>

    <div>
      <label>
        <input type="checkbox" name="rememberMe" value="1">
        Remember me
      </label>
    </div>

    <button type="submit">Sign In</button>

    <p><a href="{{ siteUrl('auth/forgot-password') }}">Forgot your password?</a></p>

  </form>

{% endblock %}
```

**Key variables Craft provides on failed login:**

| Variable | Type | Description |
|----------|------|-------------|
| `loginName` | `string` | The submitted email/username, for repopulating the field |
| `errorMessage` | `string` | The login failure message |
| `errorCode` | `int` | Yii error code for the failure reason |

## Registration Form

Requires public registration to be enabled: **Settings > Users > Settings > Allow public registration**. Without this, the `users/save-user` action rejects anonymous saves.

```twig
{# --------------------------------------------------------------------------
   Registration Form
   Path: templates/auth/register.twig
   Requires: Settings > Users > Settings > Allow public registration = ON
   -------------------------------------------------------------------------- #}

{% requireGuest %}

{% extends '_layouts/site' %}

{% block content %}

  <h1>Create Account</h1>

  {# --------------------------------------------------------------------------
     On validation failure, Craft routes back to this template and provides
     a `user` variable containing the unsaved User element with errors attached.
     -------------------------------------------------------------------------- #}

  <form method="post" accept-charset="UTF-8" enctype="multipart/form-data">

    {{ csrfInput() }}
    {{ actionInput('users/save-user') }}
    {{ redirectInput('account/welcome') }}

    {# --------------------------------------------------------------------------
       Full name field — Craft 5 uses fullName as the canonical name field.
       You can use firstName and lastName instead if you prefer split fields.
       -------------------------------------------------------------------------- #}
    <div>
      <label for="fullName">Full Name</label>
      <input
        type="text"
        id="fullName"
        name="fullName"
        value="{{ (user ?? null) ? user.fullName : '' }}"
        autocomplete="name"
        required
      >
      {% if (user ?? null) and user.getFirstError('fullName') %}
        <p role="alert">{{ user.getFirstError('fullName') }}</p>
      {% endif %}
    </div>

    {# --------------------------------------------------------------------------
       Email — always required. When useEmailAsUsername is true, this is also
       the login identifier and no separate username field is needed.
       -------------------------------------------------------------------------- #}
    <div>
      <label for="email">Email Address</label>
      <input
        type="email"
        id="email"
        name="email"
        value="{{ (user ?? null) ? user.email : '' }}"
        autocomplete="email"
        required
      >
      {% if (user ?? null) and user.getFirstError('email') %}
        <p role="alert">{{ user.getFirstError('email') }}</p>
      {% endif %}
    </div>

    {# --------------------------------------------------------------------------
       Username — only include when useEmailAsUsername is false.
       -------------------------------------------------------------------------- #}
    {% if not craft.app.config.general.useEmailAsUsername %}
      <div>
        <label for="username">Username</label>
        <input
          type="text"
          id="username"
          name="username"
          value="{{ (user ?? null) ? user.username : '' }}"
          autocomplete="username"
          required
        >
        {% if (user ?? null) and user.getFirstError('username') %}
          <p role="alert">{{ user.getFirstError('username') }}</p>
        {% endif %}
      </div>
    {% endif %}

    {# --------------------------------------------------------------------------
       Password — omit these fields when deferPublicRegistrationPassword is true.
       In that case, the user sets their password via an activation email instead.
       -------------------------------------------------------------------------- #}
    {% if not craft.app.config.general.deferPublicRegistrationPassword %}
      <div>
        <label for="password">Password</label>
        <input
          type="password"
          id="password"
          name="password"
          autocomplete="new-password"
          required
        >
        {% if (user ?? null) and user.getFirstError('password') %}
          <p role="alert">{{ user.getFirstError('password') }}</p>
        {% endif %}
      </div>
    {% endif %}

    {# --------------------------------------------------------------------------
       Custom user fields — use fields[fieldHandle] syntax.
       Replace `bio` and `company` with your actual custom field handles.
       -------------------------------------------------------------------------- #}
    <div>
      <label for="fields-bio">Bio</label>
      <textarea
        id="fields-bio"
        name="fields[bio]"
      >{{ (user ?? null) ? user.bio : '' }}</textarea>
      {% if (user ?? null) and user.getFirstError('bio') %}
        <p role="alert">{{ user.getFirstError('bio') }}</p>
      {% endif %}
    </div>

    <div>
      <label for="fields-company">Company</label>
      <input
        type="text"
        id="fields-company"
        name="fields[company]"
        value="{{ (user ?? null) ? user.company : '' }}"
      >
    </div>

    {# --------------------------------------------------------------------------
       Photo upload — field name must be "photo". Max one file.
       The form must have enctype="multipart/form-data".
       -------------------------------------------------------------------------- #}
    <div>
      <label for="photo">Profile Photo</label>
      <input type="file" id="photo" name="photo" accept="image/*">
    </div>

    <button type="submit">Create Account</button>

    <p>Already have an account? <a href="{{ siteUrl(craft.app.config.general.loginPath) }}">Sign in</a></p>

  </form>

{% endblock %}
```

**Config settings that affect registration:**

| Setting | Effect |
|---------|--------|
| `useEmailAsUsername` | When `true`, hides the username field entirely. Email becomes the login identifier. |
| `deferPublicRegistrationPassword` | When `true`, omit password fields from the form. User receives an activation email to set their password. |
| `autoLoginAfterAccountActivation` | When `true`, user is automatically signed in after clicking the activation link. |

**Split name fields alternative** -- replace the `fullName` field with:

```twig
<div>
  <label for="firstName">First Name</label>
  <input type="text" id="firstName" name="firstName"
    value="{{ (user ?? null) ? user.firstName : '' }}" required>
</div>
<div>
  <label for="lastName">Last Name</label>
  <input type="text" id="lastName" name="lastName"
    value="{{ (user ?? null) ? user.lastName : '' }}" required>
</div>
```

## Password Reset Request

The "forgot password" form. Sends a password reset email with a tokenized link.

```twig
{# --------------------------------------------------------------------------
   Password Reset Request
   Path: templates/auth/forgot-password.twig
   -------------------------------------------------------------------------- #}

{% requireGuest %}

{% extends '_layouts/site' %}

{% block content %}

  <h1>Reset Your Password</h1>

  {# --------------------------------------------------------------------------
     Success handling — Craft sets a flash message after sending the email.
     When preventUserEnumeration is true, the same success message shows
     regardless of whether the email address exists. This is intentional.
     -------------------------------------------------------------------------- #}
  {% set successMessage = craft.app.session.getFlash('notice') %}
  {% if successMessage %}
    <div role="status">
      <p>{{ successMessage }}</p>
    </div>
  {% endif %}

  {# --------------------------------------------------------------------------
     Error handling — shown when the form submission has errors.
     -------------------------------------------------------------------------- #}
  {% set errorMessages = craft.app.session.getFlash('error') %}
  {% if errorMessages %}
    <div role="alert">
      {% if errorMessages is iterable %}
        {% for error in errorMessages %}
          <p>{{ error }}</p>
        {% endfor %}
      {% else %}
        <p>{{ errorMessages }}</p>
      {% endif %}
    </div>
  {% endif %}

  <form method="post" accept-charset="UTF-8">

    {{ csrfInput() }}
    {{ actionInput('users/send-password-reset-email') }}

    {# --------------------------------------------------------------------------
       loginName — accepts email or username. Label should match your config.
       When useEmailAsUsername is true, this is always the email address.
       -------------------------------------------------------------------------- #}
    <div>
      <label for="loginName">Email Address</label>
      <input
        type="email"
        id="loginName"
        name="loginName"
        autocomplete="email"
        required
      >
    </div>

    <button type="submit">Send Reset Link</button>

    <p><a href="{{ siteUrl(craft.app.config.general.loginPath) }}">Back to sign in</a></p>

  </form>

{% endblock %}
```

**Important:** When `preventUserEnumeration` is `true` in general config, Craft always responds with a success message regardless of whether the email exists. This is a security best practice -- do not override this behavior with custom logic that reveals whether an account exists.

## Set New Password

The user arrives here by clicking the link in the password reset email. Craft appends `code` and `id` query params to the URL. The template path must match the `setPasswordPath` config setting.

```twig
{# --------------------------------------------------------------------------
   Set New Password
   Path: templates/auth/set-password.twig
   Config: generalConfig.setPasswordPath must match this template's route
   Config: generalConfig.invalidUserTokenPath should point to an error page
   Craft provides: code and id from the email link query params
   -------------------------------------------------------------------------- #}

{% extends '_layouts/site' %}

{% block content %}

  <h1>Set New Password</h1>

  {# --------------------------------------------------------------------------
     Error handling — Craft sets these variables on validation failure.
     Common errors: password too short, token expired, token already used.
     -------------------------------------------------------------------------- #}
  {% if errors is defined %}
    <div role="alert">
      <ul>
        {% for error in errors %}
          <li>{{ error }}</li>
        {% endfor %}
      </ul>
    </div>
  {% endif %}

  <form method="post" accept-charset="UTF-8">

    {{ csrfInput() }}
    {{ actionInput('users/set-password') }}

    {# --------------------------------------------------------------------------
       Hidden fields — code and id come from the URL query parameters that
       Craft appends to the reset link. They identify the user and validate
       the token. These are populated automatically by Craft when it routes
       to this template.
       -------------------------------------------------------------------------- #}
    {{ hiddenInput('code', code ?? '') }}
    {{ hiddenInput('id', id ?? '') }}

    <div>
      <label for="newPassword">New Password</label>
      <input
        type="password"
        id="newPassword"
        name="newPassword"
        autocomplete="new-password"
        required
      >
    </div>

    <button type="submit">Save Password</button>

  </form>

{% endblock %}
```

**Config settings that control this flow:**

| Setting | Purpose |
|---------|---------|
| `setPasswordPath` | Template route for the password reset form (e.g., `'auth/set-password'`). The email link directs here. |
| `setPasswordSuccessPath` | Redirect destination after the password is set successfully (e.g., `'auth/login'`). |
| `invalidUserTokenPath` | Redirect destination when the token is expired or invalid (e.g., `'auth/invalid-token'`). If not set, Craft shows a generic error. |

**Token expiration:** Password reset tokens expire after the duration set by the `verificationCodeDuration` config (default: `'P1D'` -- 1 day). After expiration, the user must request a new reset email.

## Edit Profile

Requires a logged-in user. The `userId` hidden field tells Craft which user to update -- it must match the current user's ID (non-admin users can only edit their own profile).

```twig
{# --------------------------------------------------------------------------
   Edit Profile
   Path: templates/account/edit.twig
   Requires: logged-in user
   -------------------------------------------------------------------------- #}

{% requireLogin %}

{% extends '_layouts/site' %}

{% block content %}

  <h1>Edit Your Profile</h1>

  {# --------------------------------------------------------------------------
     Flash messages — shown after a successful save.
     Craft sets the 'notice' flash on success.
     -------------------------------------------------------------------------- #}
  {% set successMessage = craft.app.session.getFlash('notice') %}
  {% if successMessage %}
    <div role="status">
      <p>{{ successMessage }}</p>
    </div>
  {% endif %}

  {# --------------------------------------------------------------------------
     On validation failure, Craft provides a `user` variable with the unsaved
     changes and attached errors. Fall back to `currentUser` on first load.
     -------------------------------------------------------------------------- #}
  {% set account = user ?? currentUser %}

  <form method="post" accept-charset="UTF-8" enctype="multipart/form-data">

    {{ csrfInput() }}
    {{ actionInput('users/save-user') }}
    {{ hiddenInput('userId', account.id) }}
    {{ redirectInput('account') }}

    {# --------------------------------------------------------------------------
       Full name
       -------------------------------------------------------------------------- #}
    <div>
      <label for="fullName">Full Name</label>
      <input
        type="text"
        id="fullName"
        name="fullName"
        value="{{ account.fullName }}"
        autocomplete="name"
      >
      {% if account.getFirstError('fullName') %}
        <p role="alert">{{ account.getFirstError('fullName') }}</p>
      {% endif %}
    </div>

    {# --------------------------------------------------------------------------
       Email — changing this requires currentPassword for verification.
       -------------------------------------------------------------------------- #}
    <div>
      <label for="email">Email Address</label>
      <input
        type="email"
        id="email"
        name="email"
        value="{{ account.email }}"
        autocomplete="email"
      >
      {% if account.getFirstError('email') %}
        <p role="alert">{{ account.getFirstError('email') }}</p>
      {% endif %}
    </div>

    {# --------------------------------------------------------------------------
       Username — only when useEmailAsUsername is false.
       -------------------------------------------------------------------------- #}
    {% if not craft.app.config.general.useEmailAsUsername %}
      <div>
        <label for="username">Username</label>
        <input
          type="text"
          id="username"
          name="username"
          value="{{ account.username }}"
          autocomplete="username"
        >
        {% if account.getFirstError('username') %}
          <p role="alert">{{ account.getFirstError('username') }}</p>
        {% endif %}
      </div>
    {% endif %}

    {# --------------------------------------------------------------------------
       New password — optional. Only fill in to change password.
       Both newPassword and currentPassword are required together.
       -------------------------------------------------------------------------- #}
    <div>
      <label for="newPassword">New Password <small>(leave blank to keep current)</small></label>
      <input
        type="password"
        id="newPassword"
        name="newPassword"
        autocomplete="new-password"
      >
      {% if account.getFirstError('newPassword') %}
        <p role="alert">{{ account.getFirstError('newPassword') }}</p>
      {% endif %}
    </div>

    {# --------------------------------------------------------------------------
       Custom user fields — use fields[fieldHandle] syntax.
       Replace these with your actual custom field handles.
       -------------------------------------------------------------------------- #}
    <div>
      <label for="fields-bio">Bio</label>
      <textarea id="fields-bio" name="fields[bio]">{{ account.bio ?? '' }}</textarea>
    </div>

    <div>
      <label for="fields-company">Company</label>
      <input
        type="text"
        id="fields-company"
        name="fields[company]"
        value="{{ account.company ?? '' }}"
      >
    </div>

    {# --------------------------------------------------------------------------
       Photo upload — replaces the existing photo.
       -------------------------------------------------------------------------- #}
    <div>
      <label for="photo">Profile Photo</label>
      {% if account.photo %}
        <img src="{{ account.photo.getUrl({ width: 100, height: 100 }) }}" alt="" width="100" height="100">
      {% endif %}
      <input type="file" id="photo" name="photo" accept="image/*">
    </div>

    {# --------------------------------------------------------------------------
       Current password — REQUIRED when changing email or password.
       Craft enforces this server-side. If the user is only updating their
       name or custom fields, this can be left empty.
       Show this field whenever the form includes email or password fields.
       -------------------------------------------------------------------------- #}
    <div>
      <label for="currentPassword">Current Password <small>(required to change email or password)</small></label>
      <input
        type="password"
        id="currentPassword"
        name="currentPassword"
        autocomplete="current-password"
      >
      {% if account.getFirstError('currentPassword') %}
        <p role="alert">{{ account.getFirstError('currentPassword') }}</p>
      {% endif %}
    </div>

    <button type="submit">Save Profile</button>

  </form>

{% endblock %}
```

**Important notes:**

- `currentPassword` is enforced server-side for email and password changes. Craft returns a validation error if it is missing or incorrect.
- Non-admin users can only save their own profile. The `userId` hidden input must match `currentUser.id`.
- The `user` variable on validation failure contains the unsaved state with errors. On first load it is not defined, so fall back to `currentUser`.
- Photo upload requires `enctype="multipart/form-data"` on the form element.

## Email Verification

Email verification is not a form you build -- it is a redirect flow Craft handles automatically.

### How it works

1. User registers (or changes their email address).
2. Craft sends a verification email with a tokenized link.
3. User clicks the link -- Craft verifies the token and activates the account.
4. Craft redirects to `verifyEmailSuccessPath` (or `activateAccountSuccessPath` for first-time activation).

### Config settings

| Setting | Purpose |
|---------|---------|
| `verifyEmailPath` | The front-end path Craft routes to when the user clicks the verification link (default: `'verifyemail'`). Craft handles verification at this path automatically -- you do not need a template here unless you want a custom loading/interstitial page. |
| `verifyEmailSuccessPath` | Redirect after successful verification (e.g., `'account'`). |
| `activateAccountSuccessPath` | Redirect after first-time account activation. Falls back to `verifyEmailSuccessPath` if not set. |
| `autoLoginAfterAccountActivation` | When `true`, the user is signed in automatically after activation instead of being redirected to the login page. |

### Verification success template

If you set `verifyEmailSuccessPath` to a route like `'auth/verified'`, create a simple confirmation template:

```twig
{# --------------------------------------------------------------------------
   Email Verified Confirmation
   Path: templates/auth/verified.twig
   -------------------------------------------------------------------------- #}

{% extends '_layouts/site' %}

{% block content %}

  <h1>Email Verified</h1>
  <p>Your email address has been verified. You can now sign in.</p>
  <a href="{{ siteUrl(craft.app.config.general.loginPath) }}">Sign In</a>

{% endblock %}
```

### Invalid token template

If you set `invalidUserTokenPath` to `'auth/invalid-token'`, create an error page:

```twig
{# --------------------------------------------------------------------------
   Invalid or Expired Token
   Path: templates/auth/invalid-token.twig
   -------------------------------------------------------------------------- #}

{% extends '_layouts/site' %}

{% block content %}

  <h1>Link Expired</h1>
  <p>This verification link has expired or has already been used.</p>
  <p><a href="{{ siteUrl('auth/forgot-password') }}">Request a new link</a></p>

{% endblock %}
```

## Navigation Partial

Conditional logged-in/logged-out state for site navigation. Include this in your layout or nav component.

```twig
{# --------------------------------------------------------------------------
   Auth Navigation Partial
   Path: templates/_partials/auth-nav.twig
   Usage: {% include '_partials/auth-nav' only %}
   -------------------------------------------------------------------------- #}

{% if currentUser %}
  <div>
    {% if currentUser.photo %}
      <img
        src="{{ currentUser.photo.getUrl({ width: 32, height: 32 }) }}"
        alt=""
        width="32"
        height="32"
        loading="lazy"
      >
    {% endif %}
    <span>{{ currentUser.fullName }}</span>
    <a href="{{ siteUrl('account') }}">My Account</a>
    <a href="{{ logoutUrl }}">Sign Out</a>
  </div>
{% else %}
  <div>
    <a href="{{ siteUrl(craft.app.config.general.loginPath) }}">Sign In</a>
    <a href="{{ siteUrl('auth/register') }}">Create Account</a>
  </div>
{% endif %}
```

**Built-in URL helpers:**

| Helper | Output |
|--------|--------|
| `{{ logoutUrl }}` | The full logout URL. Craft handles session destruction and redirects to `postLogoutRedirect`. |
| `{{ loginUrl }}` | Alias for `siteUrl(craft.app.config.general.loginPath)`. Available in Craft 5. |

## Twig Access Control Tags

These tags go at the top of a template, before any output. They short-circuit rendering and redirect or throw errors.

### `{% requireLogin %}`

Redirects anonymous users to the login page (the `loginPath` config setting). After login, the user is sent back to the originally requested page.

```twig
{% requireLogin %}
{# Everything below only renders for authenticated users #}
```

### `{% requireGuest %}`

Redirects logged-in users away from pages they should not see (login, registration). Redirects to the site homepage by default, or the path specified in the tag.

```twig
{% requireGuest %}
{# Only anonymous visitors see this page #}
```

### `{% requirePermission 'permissionHandle' %}`

Returns a 403 error if the current user does not have the specified permission. Works for both logged-in users without the permission and anonymous visitors.

```twig
{% requirePermission 'accessSiteSection:memberArea' %}
{# Only users with this permission see this page #}
```

### `{% requireAdmin %}`

Returns a 403 error if the current user is not an admin. Use sparingly on the front end.

```twig
{% requireAdmin %}
{# Admin-only diagnostic page #}
```

## User Session in Twig

### `currentUser`

The logged-in user element, or `null` if anonymous. Available globally in all templates.

```twig
{# Basic properties #}
{{ currentUser.fullName }}
{{ currentUser.firstName }}
{{ currentUser.lastName }}
{{ currentUser.email }}
{{ currentUser.username }}
{{ currentUser.id }}

{# Date properties #}
{{ currentUser.dateCreated|date('Y-m-d') }}
{{ currentUser.lastLoginDate|date('Y-m-d H:i') }}

{# User photo — returns an Asset element or null #}
{% if currentUser.photo %}
  <img src="{{ currentUser.photo.getUrl({ width: 200, height: 200 }) }}" alt="">
{% endif %}

{# Custom fields — accessed directly by field handle #}
{{ currentUser.bio }}
{{ currentUser.company }}
```

### Permission checks

```twig
{# Check a specific permission #}
{% if currentUser and currentUser.can('accessSiteSection:memberArea') %}
  <a href="{{ siteUrl('members') }}">Member Area</a>
{% endif %}

{# Check group membership #}
{% if currentUser and currentUser.isInGroup('premiumMembers') %}
  {# Premium content #}
{% endif %}

{# Check admin status #}
{% if currentUser and currentUser.admin %}
  <a href="{{ cpUrl() }}">Control Panel</a>
{% endif %}
```

**Always null-check `currentUser` before calling methods on it.** In templates behind `{% requireLogin %}` you can skip the null check since the tag guarantees authentication, but in shared partials and layouts, always check.

### Common permissions for front-end gating

| Permission | Description |
|------------|-------------|
| `accessSiteSection:{sectionUid}` | Access entries in a section (by section UID) |
| `viewEntries:{sectionUid}` | View entries in a section |
| `createEntries:{sectionUid}` | Create entries in a section |
| `editPeerEntries:{sectionUid}` | Edit other users' entries |

Permissions are typically assigned to user groups in **Settings > Users > User Groups**.

## GeneralConfig Settings That Affect Auth

Configure these in `config/general.php`. All settings below use their default values.

| Setting | Default | Purpose |
|---------|---------|---------|
| `loginPath` | `'login'` | Front-end login page path. Craft redirects here for `{% requireLogin %}`. |
| `logoutPath` | `'logout'` | Front-end logout trigger path. GET request to this path destroys the session. |
| `setPasswordPath` | `''` | Password reset form path. The email link directs here with `code` and `id` params. **Must be set for password reset to work.** |
| `setPasswordSuccessPath` | `''` | Redirect after password is set successfully. |
| `activateAccountSuccessPath` | `''` | Redirect after first-time account activation via email link. |
| `verifyEmailPath` | `''` | Email verification handler path. Craft intercepts requests here to verify the token. |
| `verifyEmailSuccessPath` | `''` | Redirect after successful email verification. |
| `invalidUserTokenPath` | `''` | Redirect when a verification/reset token is expired or invalid. If empty, Craft shows a generic error. |
| `postLoginRedirect` | `''` | Default redirect after login when no `redirectInput` is specified. |
| `postLogoutRedirect` | `''` | Default redirect after logout. |
| `useEmailAsUsername` | `false` | When `true`, email is the login identifier. No separate username field. |
| `deferPublicRegistrationPassword` | `false` | When `true`, password is set via activation email instead of the registration form. |
| `preventUserEnumeration` | `false` | When `true`, login and password reset always return generic messages, preventing attackers from discovering valid accounts. |
| `autoLoginAfterAccountActivation` | `false` | When `true`, user is signed in automatically after clicking the activation link. |
| `rememberedUserSessionDuration` | `'P14D'` | Session duration when "Remember me" is checked (default: 14 days). |
| `userSessionDuration` | `'PT1H'` | Session duration for normal logins (default: 1 hour). Set to `0` for session-only (expires when browser closes). |
| `requireMatchingUserAgentForSession` | `true` | Invalidates session if user agent changes. Prevents session hijacking but can cause issues with browser updates. |
| `verificationCodeDuration` | `'P1D'` | How long verification/reset tokens remain valid (default: 1 day). |
| `elevatedSessionDuration` | `'PT5M'` | Duration of elevated session after re-entering password (default: 5 minutes). |

### Minimum viable config for front-end auth

```php
// config/general.php
return \craft\config\GeneralConfig::create()
    ->loginPath('auth/login')
    ->logoutPath('auth/logout')
    ->setPasswordPath('auth/set-password')
    ->setPasswordSuccessPath('auth/login')
    ->verifyEmailPath('auth/verify')
    ->verifyEmailSuccessPath('auth/verified')
    ->invalidUserTokenPath('auth/invalid-token')
    ->postLoginRedirect('account')
    ->postLogoutRedirect('/')
    ->useEmailAsUsername(true)
    ->preventUserEnumeration(true)
;
```

This configures all auth paths under an `auth/` prefix, uses email as the login identifier, and prevents user enumeration. Adjust paths to match your template structure.
