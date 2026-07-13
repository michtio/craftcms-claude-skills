# Front-End Authentication Flows Reference

> Form templates for login, registration, and password reset on the front end of a Craft CMS 5 site. Every form is copy-pasteable with proper error handling. For account management (edit profile, email verification, access control tags, session helpers), see `auth-account.md`.

## Documentation

- Controller actions: https://craftcms.com/docs/5.x/reference/controller-actions.html
- User management: https://craftcms.com/docs/5.x/system/user-management.html
- User element: https://craftcms.com/docs/5.x/reference/element-types/users.html

## Common Pitfalls

- Missing `{{ csrfInput() }}` on forms -- silent failure, Craft rejects the POST with no useful error.
- Missing `{{ actionInput('users/...') }}` -- form posts to the template URL instead of the controller action.
- Not using `{{ redirectInput() }}` -- user lands on homepage instead of the intended destination.
- Showing registration form to logged-in users -- use `{% requireGuest %}` to redirect them away.
- Not setting `setPasswordPath` and `invalidUserTokenPath` in general config -- password reset emails link to paths that don't exist or show Craft's default error page.
- Exposing user enumeration via different error messages for valid/invalid emails -- enable `preventUserEnumeration` to return the same response regardless.
- Forgetting to enable public registration in Settings > Users > Settings -- registration form silently fails.
- Using `username` field when `useEmailAsUsername` is `true` -- the field does not exist, validation fails.
- Not handling the `user` variable for registration validation errors -- Craft passes it back on failed saves.

## Contents

- [Login Form](#login-form)
- [Registration Form](#registration-form)
- [Password Reset Request](#password-reset-request)
- [Set New Password](#set-new-password)
- [Failure Redirect Landings](#failure-redirect-landings)
- [WebAuthn / Passkey UX Copy](#webauthn--passkey-ux-copy)
- [One-Shot returnUrl Semantics](#one-shot-returnurl-semantics)
- [Session-Carried Form State](#session-carried-form-state)

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

## Failure Redirect Landings

When a public (anonymous) controller action fails and sets an error flash, it must redirect to a page that actually renders that flash and lets the user act on it. Redirecting to a bare site root or a page with no flash surface produces an "invisible flash" bug: the message is set correctly, but the destination never renders it, so the visitor sees an unexplained bounce and has no way to retry.

The rule: a failure redirect target must both **render `flash`** and **let the user retry**. For a login flow, that means Craft's `loginPath` (where the login form and its error region live) -- not `UrlHelper::siteUrl()` or the homepage. The same holds for any custom anonymous action you build (a magic-link request, an invite acceptance, a re-auth step): send failures back to the form the visitor came from, not somewhere generic.

This is the front-end counterpart to the server-side rule in the `craftcms` skill's `controllers.md` (Common Pitfalls -- failure redirect lands where no flash surface exists). If you own the controller action, fix the redirect target there; if you only own templates, make sure the path Craft lands on renders `flash` (see the flash-handling blocks in [Password Reset Request](#password-reset-request) and, in `auth-account.md`, `flashes()`).

## WebAuthn / Passkey UX Copy

When you wire a WebAuthn (passkey) sign-in or registration ceremony on the front end, the browser's `navigator.credentials.*` call rejects with a `DOMException` when the user cancels the prompt or lets it time out. Its `.message` is written for developers and is not something to show a visitor. Branch on the exception's `name` instead:

- `NotAllowedError` -- the user dismissed or ignored the prompt, or it timed out. This is a normal user action, not an error to alarm them with.
- `AbortError` -- the ceremony was aborted (e.g. a competing request or a navigation).

For those two cases, show your own human-friendly copy. Only surface `error.message` for genuine server-reported failures (a failed assertion, an unknown credential), never for a cancelled or timed-out ceremony.

```js
try {
  const credential = await navigator.credentials.get({ publicKey: options });
  // ... post the assertion to your verify action
} catch (error) {
  if (error.name === 'NotAllowedError' || error.name === 'AbortError') {
    // User cancelled or the prompt timed out — friendly, non-alarming copy.
    showMessage('Passkey sign-in was cancelled. You can try again or use your password.');
  } else {
    // A real failure the server or platform reported — safe to show its detail.
    showMessage(error.message);
  }
}
```

Keep the cancel/timeout copy reassuring and offer the fallback path (password, another passkey) so a dismissed prompt is never a dead end.

## One-Shot returnUrl Semantics

A re-auth interruption (an elevated-session or step-up prompt that sends the visitor to sign in, then back) carries a `returnUrl` so the visitor lands where they left off. That `returnUrl` should ride **exactly one** page view: read it into the sign-in form on load, then strip it from the visible URL with `history.replaceState(...)`. Otherwise the URL keeps the stale `returnUrl` query param, and a later sign-in the visitor starts from that same URL inherits a destination that no longer makes sense.

```js
const params = new URLSearchParams(window.location.search);
const returnUrl = params.get('returnUrl');

if (returnUrl) {
  // Seed the form so this sign-in returns to where the interruption happened.
  document.querySelector('input[name="returnUrl"]').value = returnUrl;

  // Consume it: strip it from the address bar so a later sign-in from this
  // same URL doesn't inherit a stale destination.
  params.delete('returnUrl');
  const clean = window.location.pathname + (params.toString() ? `?${params}` : '');
  history.replaceState(null, '', clean);
}
```

The client-side strip is a UX nicety, not a security control. **Always also validate the `returnUrl` server-side as same-site** before redirecting to it -- never trust a client-supplied redirect target, regardless of what the JS does. Craft's `redirectInput()` and the controllers' redirect helpers validate against the current site; if you accept a redirect target in your own action, enforce the same-site check yourself. See the `craftcms` skill's `controllers.md` for the server-side redirect-validation stance.

## Session-Carried Form State

Some flows must return an identical response whether or not the submitted account exists, so an attacker can't probe which emails are registered (account enumeration). The password-reset request is the canonical case (see [Password Reset Request](#password-reset-request) and `preventUserEnumeration`), but the same shape applies to any custom flow you build -- a magic-link request, a "resend activation" form -- that branches on account existence and redirects between pages.

When such a flow redirects from one form page to another, carry the visitor's **own typed input** (typically their email) in the session so a legitimate member is never forced to re-type it after the redirect. The critical detail: set that session value **unconditionally, before** the exists / not-exists branch runs. If you set it only in the "account exists" branch, the two branches diverge -- a stored-vs-empty value, a different redirect, a timing difference -- and that difference is exactly the enumeration signal you were trying to remove. The unconditional set is what keeps both responses indistinguishable.

This is the front-end view of the server-side rule in the `craftcms` skill's `controllers.md` (Common Pitfalls -- enumeration-safe redirect flow drops the visitor's typed input). On the template side, read the carried value back into the field's `value` on the destination page so the member sees their email already filled in.
