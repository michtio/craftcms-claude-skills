# Formie

Drag-and-drop form builder by Verbb. Forms are Craft element types with conditional logic, multi-step pages, CRM/email integrations, spam protection, file uploads, and full template control. Used on every project.

`verbb/formie` — $99

## Documentation

- Overview: https://verbb.io/craft-plugins/formie/docs/get-started/introduction
- Rendering forms: https://verbb.io/craft-plugins/formie/docs/template-guides/rendering-forms
- Rendering fields: https://verbb.io/craft-plugins/formie/docs/template-guides/rendering-fields
- Available variables: https://verbb.io/craft-plugins/formie/docs/template-guides/available-variables
- Theme config: https://verbb.io/craft-plugins/formie/docs/theming/theme-config
- Custom rendering: https://verbb.io/craft-plugins/formie/docs/theming/custom-rendering
- Events: https://verbb.io/craft-plugins/formie/docs/developers/events
- Hooks: https://verbb.io/craft-plugins/formie/docs/developers/hooks

When unsure about a Formie feature, `web_fetch` the relevant docs page.

## Common Pitfalls

- Forgetting `data-fui-form="{{ form.configJson }}"` on custom `<form>` elements — without it, Formie's JavaScript won't initialise (no validation, no captchas, no AJAX submission).
- Not calling `craft.formie.registerAssets(form)` when rendering pages/fields individually — `renderForm()` does this automatically, but `renderPage()` and `renderField()` do not.
- Placing `registerAssets()` after the `<form>` tag — it must be called before the form renders so CSS/JS is injected in the correct location.
- Missing `csrfInput()`, `actionInput()`, and `hiddenInput('handle', form.handle)` in custom form templates — all three are required for submission processing.
- Using Blitz with forms without `{% dynamicInclude %}` — CSRF tokens get frozen in the cache. Either exclude form pages from Blitz or use dynamic includes.
- Overriding `getFrontEndInputHtml()` in custom fields instead of `getFrontEndInputTemplatePath()` — the template path method is the correct extension point.
- Not prefixing custom form IDs with `formie-form-` — Formie's JavaScript relies on this prefix to bind functionality.

## Rendering

### One-Line Rendering (Most Common)

```twig
{{ craft.formie.renderForm('contactForm') }}
```

This renders the complete form including all pages, fields, buttons, captchas, CSS, and JS.

### From a Form Field on an Entry

```twig
{% set form = entry.myFormField.one() %}
{% if form %}
    {{ craft.formie.renderForm(form) }}
{% endif %}
```

### With Render Options

```twig
{{ craft.formie.renderForm('contactForm', {
    themeConfig: {
        resetClasses: true,
        form: {
            attributes: {
                class: 'my-custom-form',
            },
        },
        fieldInput: {
            resetClass: true,
            attributes: {
                class: 'form-input',
            },
        },
    },
}) }}
```

### Override Form Settings at Render Time

```twig
{% set form = craft.formie.forms.handle('contactForm').one() %}
{% do form.setSettings({
    redirectUrl: '/thank-you?id={id}',
}) %}
{{ craft.formie.renderForm(form) }}
```

## Granular Rendering

### Render Pages Individually

```twig
{% set form = craft.formie.forms.handle('contactUs').one() %}
{% do craft.formie.registerAssets(form) %}

<form method="post" data-fui-form="{{ form.configJson }}">
    {{ csrfInput() }}
    {{ actionInput('formie/submissions/submit') }}
    {{ hiddenInput('handle', form.handle) }}

    {% for page in form.getPages() %}
        {{ craft.formie.renderPage(form, page) }}
    {% endfor %}
</form>
```

### Render Fields Individually

```twig
{% set form = craft.formie.forms.handle('contactUs').one() %}
{% do craft.formie.registerAssets(form) %}

<form method="post" data-fui-form="{{ form.configJson }}">
    {{ csrfInput() }}
    {{ actionInput('formie/submissions/submit') }}
    {{ hiddenInput('handle', form.handle) }}

    {% for field in form.getFields() %}
        {{ craft.formie.renderField(form, field) }}
    {% endfor %}

    <button type="submit">Send</button>
</form>
```

### CSS and JS Separately

```twig
{% do craft.formie.renderFormCss(form) %}
{% do craft.formie.renderFormJs(form) %}
```

## Theme Config (Tailwind/Utility CSS)

Theme config lets you style every form component without custom templates — perfect for Tailwind:

```twig
{{ craft.formie.renderForm('contactForm', {
    themeConfig: {
        resetClasses: true,

        formWrapper: {
            attributes: { class: 'max-w-lg mx-auto' },
        },
        field: {
            attributes: { class: 'mb-6' },
        },
        fieldLabel: {
            attributes: { class: 'block text-sm font-medium text-gray-700 mb-1' },
        },
        fieldInput: {
            resetClass: true,
            attributes: { class: 'w-full rounded-lg border border-gray-300 px-4 py-2 focus:ring-2 focus:ring-brand-primary focus:border-transparent' },
        },
        fieldInstructions: {
            attributes: { class: 'text-sm text-gray-500 mt-1' },
        },
        fieldError: {
            attributes: { class: 'text-sm text-red-600 mt-1' },
        },
        submitButton: {
            resetClass: true,
            attributes: { class: 'rounded-lg bg-brand-primary px-6 py-3 text-white font-medium hover:bg-brand-primary-dark transition-colors' },
        },
    },
}) }}
```

Theme config supports Twig expressions in class values for dynamic styling based on field properties.

## Twig Functions

| Function | Description |
|----------|-------------|
| `craft.formie.renderForm(form, options)` | Render complete form |
| `craft.formie.renderPage(form, page, options)` | Render single page |
| `craft.formie.renderField(form, field, options)` | Render single field |
| `craft.formie.registerAssets(form)` | Register CSS + JS |
| `craft.formie.renderFormCss(form)` | Register CSS only |
| `craft.formie.renderFormJs(form)` | Register JS only |
| `craft.formie.forms.handle('x').one()` | Fetch form by handle |
| `form.getPages()` | Get all pages |
| `form.getFields()` | Get all fields (across all pages) |
| `form.getCurrentPage()` | Current page (multi-step) |
| `form.getNextPage()` | Next page or null |
| `form.getPreviousPage()` | Previous page or null |
| `form.configJson` | JSON config for `data-fui-form` attribute |

## Querying Submissions

```twig
{% set submissions = craft.formie.submissions
    .form('contactForm')
    .limit(10)
    .orderBy('dateCreated DESC')
    .all() %}

{% for submission in submissions %}
    {{ submission.title }} — {{ submission.getFieldValue('email') }}
{% endfor %}
```

## PHP Hooks

Insert content at specific points without overriding templates:

```php
use yii\base\Event;

Craft::$app->getView()->hook('formie.form.start', function(array &$context) {
    return '<div class="form-intro">Required fields are marked *</div>';
});
```

Available hooks: `formie.form.start`, `formie.form.end`, `formie.page.start`, `formie.page.end`, `formie.field.field-before`, `formie.field.field-after`.

## Integrations

Formie supports CRM, email marketing, and webhook integrations configured per-form in the CP:

- **Email marketing**: Mailchimp, ActiveCampaign, Campaign Monitor, Constant Contact
- **CRM**: HubSpot, Salesforce, Zoho, Pipedrive, SharpSpring
- **Webhooks**: Custom URL endpoints, Zapier, n8n
- **Spam protection**: reCAPTCHA v2/v3, hCaptcha, Snaptcha, Honeypot
- **Misc**: Slack, Trello, Google Sheets

## Pair With

- **Snaptcha** — invisible anti-spam for additional protection
- **Blitz** — use `{% dynamicInclude %}` for forms on cached pages
