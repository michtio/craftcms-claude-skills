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
- Form (developer API): https://verbb.io/craft-plugins/formie/docs/developers/form
- Notification model: https://verbb.io/craft-plugins/formie/docs/developers/notification
- Import/Export: https://verbb.io/craft-plugins/formie/docs/feature-tour/import-export
- Cached forms: https://verbb.io/craft-plugins/formie/docs/template-guides/cached-forms

When unsure about a Formie feature, `WebFetch` the relevant docs page.

**Version context:** the back-end API below is verified against **Formie 3.x** (the `craft-5` branch of `verbb/formie`), which requires Craft CMS 5 and PHP 8.2+.

## Common Pitfalls

- Listening for `onFormieSubmitSuccess` — **that event does not exist in Formie 3**. Use `onAfterFormieSubmit` (fires on the `<form>` after every successful ajax submit, including per-page in multi-page forms; `event.detail.nextPageId` is set on intermediate pages and empty on final completion; the form element is `event.target`, not in `detail`).
- Forgetting `data-fui-form="{{ form.configJson }}"` on custom `<form>` elements — without it, Formie's JavaScript won't initialise (no validation, no captchas, no AJAX submission).
- Not calling `craft.formie.registerAssets(form)` when rendering pages/fields individually — `renderForm()` does this automatically, but `renderPage()` and `renderField()` do not.
- Placing `registerAssets()` after the `<form>` tag — it must be called before the form renders so CSS/JS is injected in the correct location.
- Missing `csrfInput()`, `actionInput()`, and `hiddenInput('handle', form.handle)` in custom form templates — all three are required for submission processing.
- Using Blitz with forms without `{% dynamicInclude %}` — CSRF tokens get frozen in the cache. Either exclude form pages from Blitz or use dynamic includes.
- Overriding `getFrontEndInputHtml()` in custom fields instead of `getFrontEndInputTemplatePath()` — the template path method is the correct extension point.
- Not prefixing custom form IDs with `formie-form-` — Formie's JavaScript relies on this prefix to bind functionality.
- (Back-end) Translating form strings via the `site` category — Formie uses the single **`formie`** category (`Craft::t('formie', …)` / `translations/<locale>/formie.php`). See *Programmatic & Back-End* below.
- (Back-end) Assigning an HTML string to a notification's `content` in PHP — it's **ProseMirror block JSON**, not HTML. Prefer setting `templateId`.
- (Back-end) Renaming File Upload assets at `Submission::EVENT_BEFORE_SAVE` — the asset doesn't exist yet; rename at `EVENT_AFTER_SAVE`.

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

## Multi-Page Forms

- Unlimited pages; settings: `displayPageTabs`, `displayPageProgress` (progress bar, `progressPosition`), `submitMethod: page-reload | ajax`.
- Ajax mode keeps all pages in the DOM (hidden via `data-fui-page-hidden`, inputs disabled) and saves an **incomplete submission** per page (`isIncomplete`, hidden in CP by default) — useful for drop-off analysis.
- Page-level conditions (skip logic) and next-button conditions are supported.
- No built-in slide/animation transitions — Typeform-style UX is custom CSS/JS on top of `onFormiePageToggle` / `data-fui-page-hidden`.

## JavaScript Events (Formie 3)

Documented: `onFormieLoaded`, `onFormieInit` (document, `detail.formId`), `onFormieThemeReady`, `onBeforeFormieSubmit`, `onFormieValidate`/`onAfterFormieValidate` (cancelable, `detail.submitHandler`), `onAfterFormieSubmit` (per-page + final; check `detail.nextPageId`), `onFormieSubmitError`, `onFormieEvaluateConditions`, `beforeEvaluate`/`afterEvaluate` (Calculations field).

Source-verified but **undocumented**: `onFormiePageToggle` — fires on the `<form>` on every page change with `detail.data.nextPageId`, `nextPageIndex`, `totalPages`. Ideal for per-step dataLayer/GA4 tracking; re-verify on upgrades.

GTM: no GTM integration in the integrations list, but each page's submit button has "Enable JavaScript Events" with a static key/value GTM table (pushes e.g. `formPageSubmission` with `formId`/`pageId`/`pageIndex`). Dynamic payloads need manual `dataLayer.push` from the events above. Docs: https://verbb.io/craft-plugins/formie/docs/v3/template-guides/google-tag-manager

## Calculations, Scoring & Conditional Outcomes

- **Calculations field**: Symfony Expression Language formula (not Twig) referencing `{fieldHandle}`. Radio/dropdown resolve to the selected option's *value* (label/value are separate per option, so numeric scoring works). Set **Formatting: Number** — values arrive as strings otherwise. Checkboxes resolve to an *array*; a Number-formatted calc field referencing only the checkbox field sums the array, and calc fields can chain off other calc fields.
- **Client-side only** — the result is submitted from a read-only input and is tamperable. For trusted scores, recompute server-side via `Submission::EVENT_BEFORE_SAVE` in a module.
- **No native conditional redirect/success message** (per verbb's own guide). Workaround: redirect URL is rendered as an object template against the submission — use `/result?submission={uid}`, then query `craft.formie.submissions` on the result page and branch there.
- Notifications render option **values**, not labels (verbb/formie#756) — mind numeric scoring values in user-facing emails.

## Programmatic & Back-End (PHP / Migrations / Deployment)

Everything above is front-end. This section covers building and deploying forms in PHP — the surface you need for content migrations, cross-environment deployment, multi-site translation, file handling, and caching on the back end. All class/method/property names below were verified against the `verbb/formie` `craft-5` source; items that could **not** be confirmed are flagged `UNVERIFIED` — do not present them as documented fact.

### Forms are database elements, not project config

`verbb\formie\elements\Form` extends `craft\base\Element`. Forms are **database content**, not project-config YAML — they do **not** sync via `config/project/` across environments. Two supported ways to move a form between environments:

1. **CP Import/Export (JSON).** Formie → Settings → Import/Export downloads a JSON file containing the whole form (fields, pages, notifications) for re-import in another environment. Good for one-off, CP-driven moves.
2. **Content migration (code).** Build the form in a migration — version-controlled, idempotent, runs in the deploy pipeline. Preferred when the form is part of the codebase.

**Dependency ordering** for a migration: the destination **asset volume** (for File Upload fields), any referenced **email/notification templates**, and any related elements must exist *before* the form references them. Order: volume → form (fields are created inline) → notifications.

### Creating a form in a content migration

Verified API:

- **Lookups only** on the Forms service — `Formie::$plugin->getForms()` exposes `getFormByHandle()`, `getFormById()`, `getFormByUid()`, `getAllForms()`. There is **no** `createForm()` / `saveForm()`.
- **Fields** are built via `Formie::$plugin->getFields()->createField(array $config): FieldInterface`. Field classes live under `verbb\formie\fields\*` (`SingleLineText`, `MultiLineText`, `Email`, `Dropdown`, `Checkboxes`, `Radio`, `Agree`, `FileUpload`, `Name`, `Phone`, `Number`, `Date`, …).
- **Layout** is `verbb\formie\models\FieldLayout`. (`Form` imports it with `use … as FormLayout`, so `getFormLayout()`/`setFormLayout()` operate on `FieldLayout` — there is **no separate `FormLayout` class**.) The nesting is `FieldLayout` → `FieldLayoutPage` → `FieldLayoutRow` → fields, all under `verbb\formie\models\*`. `setPages()`/`setRows()`/`setFields()` accept plain config arrays and auto-instantiate; a row passed raw field-config arrays calls `createField()` for you.
- **Save** via `Craft::$app->getElements()->saveElement($form)` — there is no forms-service save.

```php
use Craft;
use craft\db\Migration;
use verbb\formie\Formie;
use verbb\formie\elements\Form;
use verbb\formie\models\Notification;
use verbb\formie\fields\SingleLineText;
use verbb\formie\fields\Email;

/**
 * Creates the "Contact" Formie form. Idempotent.
 */
public function safeUp(): bool
{
    $forms = Formie::$plugin->getForms();

    // Idempotency guard — bail if the form already exists.
    if ($forms->getFormByHandle('contact')) {
        return true;
    }

    $form = new Form();
    $form->title = 'Contact';
    $form->handle = 'contact';

    $layout = $form->getFormLayout(); // verbb\formie\models\FieldLayout
    $layout->setPages([
        [
            'label' => 'Page 1',
            'rows' => [
                ['fields' => [
                    ['type' => SingleLineText::class, 'label' => 'Full Name', 'handle' => 'fullName', 'required' => true],
                ]],
                ['fields' => [
                    ['type' => Email::class, 'label' => 'Email', 'handle' => 'email', 'required' => true],
                ]],
            ],
        ],
    ]);
    $form->setFormLayout($layout);

    $notification = new Notification();
    $notification->name = 'Admin';
    $notification->enabled = true;
    $notification->subject = 'New submission';
    $notification->to = 'admin@example.com';
    // $notification->templateId = <email template id>;
    $form->setNotifications([$notification]);

    return Craft::$app->getElements()->saveElement($form);
}

public function safeDown(): bool
{
    $form = Formie::$plugin->getForms()->getFormByHandle('contact');

    if ($form) {
        Craft::$app->getElements()->deleteElement($form);
    }

    return true;
}
```

> **Gotcha — notification `content` is ProseMirror JSON, not HTML.** `Notification::$content` holds raw ProseMirror block JSON (rendered via `getParsedContent()`), **not** a plain-text or HTML string. Assigning an HTML string will not render correctly. For a code-built notification, prefer setting `templateId` (a Formie email template) and leaving `content` empty, or author the ProseMirror JSON shape deliberately.
>
> The field/page/row config keys beyond `type`/`label`/`handle`/`required` are derived from source, not from an official "create a form in a migration" doc example (none exists). Check per-field-class settings before relying on a specific key.

### Multi-site & translations

`Form::isLocalized()` returns `false` — **a form is a single, non-localized element** shared across all sites. There are no per-site form content rows; you translate the *strings*, not the form.

- **Static translation under the `formie` category.** All custom form strings — field labels, instructions, option labels, the Agree-field description, the submit button, error messages — render through `Craft::t('formie', '…')`. Provide `translations/<locale>/formie.php` mapping the source string to its translation.
- **This is the `formie` category, not `site`.** Formie consolidated the old `app`/`site`/`formie` mix into the single `formie` category in v2+. A common mistake is putting form-string translations in `site.php` — they won't resolve.
- **Front-end JS strings** are translated via `Rendering::EVENT_MODIFY_FRONTEND_JS_TRANSLATIONS` (`ModifyFrontendJsTranslationsEvent`).
- **Email notification render language — `UNVERIFIED`.** Which site's language a notification renders in is not stated in the docs examined. The submission carries a `siteId`, so the submission's site language is plausible, but confirm before relying on it.

### File Upload field (`verbb\formie\fields\FileUpload`)

Verified settings:

- **Destination volume:** `uploadLocationSource = 'volume:{uid}'` (or `'folder:{uid}'`); `uploadLocationSubpath` sets the subfolder and supports tokens like `{fieldHandle}`.
- **Restrictions:** `allowedKinds` (array, default `['image', 'pdf']`, enforced when `restrictFiles = true`), `sizeLimit` / `sizeMinLimit` (MB), `limitFiles` (max count).
- **Filenames:** `filenameFormat` (without extension). With no format set, the uploaded name is sanitized via `craft\helpers\Assets::prepareAssetName()`.

**Renaming uploaded files — use `EVENT_AFTER_SAVE`, not `BEFORE_SAVE`.** At `Submission::EVENT_BEFORE_SAVE` the uploaded asset does **not** yet exist (it's created during the save). The field's own `filenameFormat` runs in `FileUpload::afterElementSave()` — i.e. after the asset exists. For custom renaming, hook `Submission::EVENT_AFTER_SAVE`, read the assets off the field value, set `$asset->newFilename`, and re-save through the elements service (that pair is Craft's rename mechanism):

```php
use Craft;
use craft\events\ModelEvent;
use verbb\formie\elements\Submission;
use yii\base\Event;

Event::on(Submission::class, Submission::EVENT_AFTER_SAVE, function(ModelEvent $event) {
    $submission = $event->sender;

    // getFieldValue() on a File Upload field returns an asset query.
    $assets = $submission->getFieldValue('fileUpload')->all(); // craft\elements\Asset[]

    foreach ($assets as $asset) {
        $asset->newFilename = 'application-' . $submission->id . '-' . $asset->getFilename();
        Craft::$app->getElements()->saveElement($asset);
    }
});
```

**Attaching uploads to notification emails:** set `Notification::$attachFiles = true` ("attach user-uploaded files to the notification"). Related model properties: `$attachPdf` (string — a PDF template) and `$attachAssets` (array — exists in the model but its semantics are `UNVERIFIED` from the docs). For attaching the submitter's File Upload files, `attachFiles = true` is the verified knob.

### Captchas & caching (cached / edge pages)

- **Documented cache-breakers:** the **JavaScript captcha** and the **Duplicate captcha** — their tokens get baked into cached HTML, so they fail on a fully-cached page. (Honeypot and the external captchas don't share this exact failure.)
- **Turnstile cache-safety — `UNVERIFIED`.** The claim that Cloudflare Turnstile is fully session-free and cache-safe is **not** stated in Formie's captcha or caching docs. Don't assume it; use the universal fix below, which is captcha-agnostic.
- **The documented fix is `Formie.refreshForCache(formId)`**, wired to the `onFormieInit` event. It issues a GET to `actions/formie/forms/refresh-tokens` and updates (1) the CSRF token input, (2) the JS/Duplicate captcha tokens, and (3) the unload form hash — so a statically-cached page fetches live tokens client-side after load:

```twig
{% js %}
document.addEventListener('onFormieInit', (event) => {
    const Formie = event.detail.formie;
    Formie.refreshForCache(event.detail.formId);
});
{% endjs %}
```

- **Static / edge caching (Blitz, Craft Cloud edge):** the same approach applies — cache the HTML, refresh tokens client-side. Formie explicitly recommends Blitz for static caching. (For per-fragment dynamic content under Blitz, see the `blitz.md` reference's `{% dynamicInclude %}` note.)

### Deployment & cache-flush caution

- Forms move between environments via JSON Import/Export or a content migration (above) — not project config.
- **Avoid a full cache flush inside a content migration**, especially on Craft Cloud. Prefer targeted invalidation — `Craft::$app->getElements()->invalidateCachesForElement($form)` or tag-based invalidation — over `clear-caches/all` during the migrate phase. On Cloud, when Valkey/Redis isn't provisioned the cache falls back to a single MySQL `DbCache` table, so a global flush during the Migrate phase (where the old release is still serving live traffic) can deadlock — see the `craft-cloud` skill's `extension.md` (cache wiring) and the Build → Migrate → Release pipeline.

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
