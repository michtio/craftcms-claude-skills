# Plugin Example Templates & Front-End Render Builders

> How a plugin ships front-end templates and Twig render builders that integrators can drop in, restyle, and enhance — without shipping footguns.

This file covers the two front-end surfaces a plugin exposes to a *site's* templates:

1. **Example templates** — a copyable bundle of ready-made pages (login, account, members area) so integrators start from a working, styled reference instead of a blank file.
2. **Render builders** — fluent `craft.<handle>.<thing>({...}).render()` Twig objects that emit a self-contained, progressively-enhanced control.

Both are consumed in Twig but *authored* in the plugin. For the PHP-side conventions (the console command class, the `\Twig\Markup` return type, the `__toString()` trap), see the craftcms skill's `architecture.md` and `events.md`. For the site's own template chain, see `boilerplate-routing.md`.

## Documentation

- Twig templates in Craft: https://craftcms.com/docs/5.x/development/twig.html
- Template roots / plugin templates: https://craftcms.com/docs/5.x/extend/template-roots.html
- Console commands: https://craftcms.com/docs/5.x/extend/commands.html
- Craft Commerce example templates (the reference model): https://craftcms.com/docs/commerce/5.x/system/example-templates.html

## Contents

- [Why Ship Example Templates](#why-ship-example-templates) — the bare-fragment footgun
- [Bundle Structure](#bundle-structure) — canonical folder, layout shell, page pattern
- [The Install Console Command](#the-install-console-command) — copy, rename, rewrite, refuse
- [Integration Story](#integration-story) — restyle in place vs. swap the extends
- [Front-End Render Builders](#front-end-render-builders) — the fluent BaseTag shape
- [Progressive Enhancement Discipline](#progressive-enhancement-discipline) — the OTP carrier example

## Why Ship Example Templates

A plugin with a front end (member accounts, a booking flow, a comment form) needs
templates in the *site's* `templates/` directory to render at all. The tempting
shortcut — shipping bare body fragments the integrator is expected to `{% include %}`
into their own layout — is a real footgun:

- A fragment with no `<html>`, `<head>`, or `<body>` renders as a broken page if
  the integrator hits its URL directly before wiring it in.
- Flash notices, skip links, and CSRF-bearing chrome have nowhere to live, so each
  page re-implements them (or forgets to).
- There's no working reference to *look at* — the integrator can't see the intended
  markup and interactions running before they start editing.

The fix is the model Craft Commerce uses for its example templates: ship a **complete,
self-contained, copyable bundle** with its own layout shell, and give the integrator
a one-command install. They get a working, styled starting point on day one, then
restyle it in place or reskin the shell.

## Bundle Structure

Ship the bundle under a **canonical folder name** inside the plugin (e.g.
`example-templates/members/`) that the install command copies into the site's
`templates/` (e.g. `templates/members/`). The bundle owns everything it needs to
render standalone:

```
example-templates/members/
├── _private/
│   └── layouts/
│       └── main.twig          ← the HTML shell — the ONE file integrators reskin
├── index.twig                 ← {% redirect %} to the real entry page
├── login.twig                 ← {% extends %} the shell, fills {% block main %}
├── register.twig
└── account/
    └── index.twig
```

### The layout shell (`_private/layouts/main.twig`)

The shell renders the document once — everything that should appear on every page
lives here, not repeated per page:

```twig
{# example-templates/members/_private/layouts/main.twig #}
<!DOCTYPE html>
<html lang="{{ craft.app.language|slice(0, 2) }}">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{% block title %}{{ siteName }}{% endblock %}</title>

    {# Tailwind via CDN so the bundle looks right with zero buildchain #}
    <script src="https://cdn.tailwindcss.com"></script>

    {# Page-specific <head> additions hook in here #}
    {% block extraHead %}{% endblock %}
</head>
<body class="min-h-screen bg-gray-50 text-gray-900">

    {# Skip link — rendered once, in the shell #}
    <a href="#main" class="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:m-2 focus:rounded focus:bg-white focus:p-3">
        {{ 'Skip to main content'|t('members') }}
    </a>

    {# Nav — one include, in the shell #}
    {% include 'members/_private/nav' %}

    {# Flash notices — rendered ONCE here, never per page #}
    {% for type in ['notice', 'error'] %}
        {% set message = craft.app.session.getFlash(type) %}
        {% if message %}
            <div role="alert" class="mx-auto max-w-xl rounded p-3 {{ type == 'error' ? 'bg-red-100 text-red-800' : 'bg-green-100 text-green-800' }}">
                {{ message }}
            </div>
        {% endif %}
    {% endfor %}

    <main id="main" class="mx-auto max-w-xl p-6">
        {% block main %}{% endblock %}
    </main>

</body>
</html>
```

### Every page extends the shell

Pages carry no chrome — they fill `{% block main %}` (and optionally `extraHead`):

```twig
{# example-templates/members/login.twig #}
{% extends 'members/_private/layouts/main' %}

{% block title %}{{ 'Sign in'|t('members') }}{% endblock %}

{% block main %}
    <h1 class="text-2xl font-bold">{{ 'Sign in'|t('members') }}</h1>

    <form method="post" class="mt-4 space-y-4">
        {{ csrfInput() }}
        {{ actionInput('users/login') }}
        {# ... fields ... #}
        <button type="submit" class="rounded bg-blue-600 px-4 py-2 text-white">
            {{ 'Sign in'|t('members') }}
        </button>
    </form>
{% endblock %}
```

### `index.twig` redirects

The bundle's entry file is a `{% redirect %}`, so hitting the folder root lands on
a real page rather than a directory listing or blank template:

```twig
{# example-templates/members/index.twig #}
{% redirect 'members/account' %}
```

### Conventions that make the bundle robust

- **Fixed, root-relative paths.** Reference bundle templates by their full path from
  `templates/` (`members/_private/layouts/main`), not through a `{% set prefix = … %}`
  variable convention. Fixed paths are greppable and the install command can rewrite
  them mechanically on rename (see below). A prefix-variable convention hides the real
  paths from both the integrator and the rename logic.
- **Tailwind utilities + CDN stylesheet in the shell.** The bundle styles itself with
  Tailwind utility classes and links the Tailwind CDN in the shell `<head>`, so it
  looks correct with zero buildchain. Integrators on a real Vite/Tailwind setup swap
  the CDN line for their own asset include.
- **`_private/` for internals.** The layout and any partials live under a `_private/`
  subfolder so it's obvious which files are chrome (reskin these) versus pages
  (route to these).

## The Install Console Command

Don't make integrators copy files by hand — ship a console command that does it,
following the Commerce `commerce/example-templates` model. Register a
`<handle>/example-templates` command that:

- **Copies** the canonical bundle into the site's `templates/`.
- **Prompts for a folder name** (defaulting to the canonical name, e.g. `members`),
  so two installs or a naming clash can be resolved at install time.
- **Rewrites the bundle's internal root-relative references on rename.** If the
  integrator installs into `templates/portal/` instead of `templates/members/`, every
  `{% extends 'members/...' %}` and `{% include 'members/...' %}` inside the copied
  files must become `portal/...`. This is exactly why paths are fixed and root-relative
  — a mechanical find-and-replace of the old folder prefix is safe and complete.
- **Refuses to overwrite an existing target folder** unless `--overwrite` is passed,
  so a second run can't silently clobber the integrator's edits.

```bash
# Copy into templates/members/ (prompts for the folder name)
ddev craft members/example-templates

# Install under a different folder name, overwriting if it exists
ddev craft members/example-templates --overwrite
```

The PHP command class lives in the plugin (`src/console/controllers/`). For the
console command conventions — options, prompts, `$this->stdout()` output, exit
codes — see the craftcms skill's `console-commands.md`.

## Integration Story

Because the bundle is self-contained, the integrator has exactly two paths, and both
are cheap:

1. **Restyle in place.** Edit the Tailwind utility classes on the pages and the shell.
   The markup, routing, and interactions keep working; only the look changes.
2. **Swap the shell.** Change the one `{% extends %}` line per page to point at the
   site's own layout (`_boilerplate/_layouts/generic-page-layout`, say), and delete
   `_private/layouts/main.twig`. Because chrome (skip link, nav, flash notices) lives
   in the shell rather than scattered through the pages, re-homing it is a per-page
   one-liner, not a per-page rewrite.

Ship both paths in the plugin's `docs/` so integrators know the bundle is meant to be
edited, not treated as vendor code.

## Front-End Render Builders

For a widget a plugin renders into a site's page — a segmented OTP input, a rating
control, an address autocompleter — expose a **fluent render builder** rather than a
raw `{% include %}` of a plugin template. The shape (modeled on Password Policy's
fluent tag):

```twig
{# Consumer usage — ALWAYS call .render() #}
{{ craft.members.otpInput({ name: 'code', digits: 6 }).render() }}

{# Or build it up fluently #}
{% set otp = craft.members.otpInput().name('code').digits(6) %}
{{ otp.render() }}
```

The builder is a `BaseTag` class with these rules:

- **Config-array constructor whose keys MUST match the chainable setters.** Passing
  `{ digits: 6 }` calls the same path as `.digits(6)`. An **unknown key throws** — so a
  typo like `{ digitz: 6 }` fails loudly at render time instead of being silently
  ignored. This is the whole point: mistyped options surface immediately.
- **`render(): \Twig\Markup`** is the public method. It wraps a private
  `_renderHtml(): string` that builds the actual markup. Returning `\Twig\Markup`
  (not a bare `string`) tells Twig the HTML is already safe, so it isn't re-escaped.
- **Consumers must call `{{ tag.render() }}`, never `{{ tag }}`.** A bare `{{ tag }}`
  goes through `__toString()`, and Twig auto-escapes the returned string — the HTML
  renders as visible `&lt;input&gt;` tags. `__toString()` exists only as a
  convenience fallback for non-Twig contexts (logging, debugging). Document the
  `.render()` requirement prominently. For the full explanation of this double-escape
  trap, see the craftcms skill's `events.md`.
- **Lazy client-asset registration.** The builder registers its client asset (a
  vanilla-JS bundle + neutral CSS) the first time it renders on a page — not eagerly
  at plugin bootstrap — so pages that never use the widget don't pay for its JS/CSS.
  Keep the JS framework-free and the CSS visually neutral so it drops into any site's
  design without fighting the host stylesheet.

For the PHP side of the builder — the setter/property mapping, the constructor that
rejects unknown keys, and the asset-bundle registration — see the craftcms skill's
`architecture.md` (render-builder note) and the Vite/asset guidance in
`plugin-vite.md`.

## Progressive Enhancement Discipline

The builder's rendered control must **work fully with JavaScript disabled**. The
server renders a plain, functional control; the client asset *upgrades* it. This is
the rule, not a nicety — a control that only works once JS runs will silently break
for a fraction of every site's traffic.

The instructive example is a **segmented OTP input** (one box per digit):

- **Server render:** a single, ordinary `<input name="code" required>`. Submitting the
  form without any JS works — the user types the whole code into one field.
- **Enhancement:** JS renders the per-digit boxes on top and keeps the **original
  single input as the submitted-value carrier** — the segmented boxes write into it.
  The form still posts one `code` value; the enhancement is purely visual/UX.
- **The load-bearing detail:** on enhancement, JS **drops the `required` attribute**
  from the original input. If the enhanced UI hides that original input (moves it
  off-screen, sets `display:none`) while it still carries `required`, the browser's
  native validation refuses to submit the form and *can't focus the hidden field to
  show why* — the form silently won't submit and the user has no idea what's wrong.
  Removing `required` at enhancement time (validation then lives in the enhanced
  control and on the server) avoids a hidden-but-required control blocking submit.

```
No JS:   [ 1 2 3 4 5 6 ]  ← single <input required>, submits fine
JS on:   [1][2][3][4][5][6]  ← segmented boxes write into the (now non-required,
                                visually-replaced) carrier input, which submits
```

The general discipline this illustrates:

- Render a working plain control server-side; never depend on JS for baseline function.
- When the enhanced control replaces a native input visually, the native input often
  stays as the value carrier — audit what attributes on that hidden carrier (`required`,
  `pattern`, `disabled`) can now block or alter submission, and reconcile them at
  enhancement time.
- Keep server-side validation regardless — the enhanced client control is UX, not a
  security or correctness boundary.

One more consequence of enhancement: the classes, `data-` attributes, and input
names the plugin's JS reads are a **markup contract**. A bundle page an integrator
rewrites by hand must keep those hooks, or the widget renders fine and silently
never enhances. Plugin authors: document the hooks as public API and resolve them
via `data-` attributes with hardcoded fallbacks — see the craftcms skill's
`architecture.md` (The JS-to-markup contract is public API). Integrators: see
`third-party-integration.md` (Hand-Written Templates for Plugin Widgets).

For where progressive-enhancement widgets sit relative to Alpine/Vue and the JS
boundary decision tree, see `javascript-boundaries.md`.
