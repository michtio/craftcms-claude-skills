---
name: craft-site
description: "Craft CMS 5 front-end Twig development: atomic design, template architecture, components, Vite buildchain. Covers atoms/molecules/organisms, props/extends/block patterns, layout chains, view routing, content builders, image presets, Tailwind named-key collections, multi-brand CSS tokens, JavaScript boundaries (Alpine/DataStar/Vue, tabs, accordions), and front-end auth (login, registration, password reset, profiles)."
when_to_use: "Triggers on: {% include ... only %}, {% embed %}, _atoms/_molecules/_organisms/_views/_builders, component--variant.twig, _component--props.twig, collect({}), utilities prop, data-brand theming, hero/card components, Matrix block rendering, craft.vite.script, vite.config.ts, responsive images, srcset, image transforms, SEOmatic meta/OpenGraph, multi-language, hreflang, Formie form styling, XML sitemap, search page and Sprig/htmx live search, headless GraphQL, Next.js/Nuxt/Astro, fluent BaseTag {{ tag.render() }}. Always use when creating, editing, or reviewing Craft front-end Twig templates, components, layouts, views, builders, buildchain, or front-end auth, including plugin template integration (Blitz, SEOmatic, Sprig, Formie, Imager-X). Do NOT trigger for PHP plugin/module development (craftcms) or content modeling (craft-content-modeling)."
allowed-tools: "Bash(sh ${CLAUDE_SKILL_DIR}/scripts/craft-version.sh)"
---

# Craft CMS 5 — Front-End Twig (Atomic Design)

## Craft Version of This Project

!`sh ${CLAUDE_SKILL_DIR}/scripts/craft-version.sh`

If no Craft version line appears above, establish the version before any version-specific advice: `craftcms/cms` in `composer.lock` for a site, the lowest version the `craftcms/cms` constraint in `composer.json` allows for a plugin, or ask. Then check it against the version tags in this skill (`[5.10+]`, `[changed 5.12]`, `[seomatic 5.1+]`).

Atomic design system patterns for Craft CMS 5 site templates. Vanilla Twig —
no module dependency. Works with any Craft 5 project.

This skill is scoped to **front-end template architecture** — component design,
routing, composition, theming, and buildchain. For extending Craft (plugins,
modules, PHP), see the `craftcms` skill.

## Companion Skills — Always Load Together

When this skill triggers, also load:

- **`craft-twig-guidelines`**: Twig coding standards (naming, null handling, whitespace, include isolation, Craft helpers). Required for any Twig code.
- **`craft-content-modeling`**: sections, entry types, fields, Matrix, relations. Required when deciding what content to query.
- **`ddev`**: all Vite, npm and Craft CLI commands run through DDEV.
- **`craft-cloud`**: when hosted on Craft Cloud (`craft-cloud.yaml` or `craftcms/cloud`). Edge static caching rules, `cloud.esi(...)` islands, edge transform constraints, `csrfInput()` on cacheable pages.
- **`servd`**: when hosted on Servd (`servd.yaml` or `servd/craft-asset-storage`). Servd static caching, `{% dynamicInclude %}` islands, Blitz in reverse-proxy mode, off-server transforms.
- **`craft-fortrabbit`**: when hosted on fortrabbit (`.fortrabbit/deploy.yml` or `FORTRABBIT_*` vars). Asset volumes and deployments, queue and transforms in a worker job, site URL from `FORTRABBIT_MAIN_DOMAIN`.
- **`craft-plugins`**: when the task names a third-party plugin (Formie, SEOmatic, Blitz, ...). Per-plugin configuration, Twig API and pitfalls (see Plugin References below).

## Documentation

- Twig in Craft: https://craftcms.com/docs/5.x/development/twig.html
- Template tags: https://craftcms.com/docs/5.x/reference/twig/tags.html
- Template functions: https://craftcms.com/docs/5.x/reference/twig/functions.html
- Twig 3 docs: https://twig.symfony.com/doc/3.x/

Use `WebFetch` on specific doc pages when a reference file doesn't cover enough detail.

## Common Pitfalls (Cross-Cutting)

- Missing `only` on `{% include %}` — ambient variables leak in silently.
- Variant logic via conditionals (`{% if variant == 'x' %}`) instead of extends/block.
- Naming atoms by parent context (`hero-button`) instead of visual treatment (`button--primary`).
- `utilities` prop used as override — it's additive. Override via named-slot merge.
- Queries inside views — views receive data, they don't fetch it.
- Missing `.eagerly()` on relation fields in views — causes N+1 queries.
- Missing `devMode` fallback in builders for unknown block types.
- A CSP nonce, `csrfInput()`, active nav state or language switcher inside `{% cache %}`. The first render is replayed to everyone. See `template-caching.md`.
- Hardcoded Tailwind colors (`bg-yellow-600`) instead of brand tokens (`bg-brand-accent`).
- Mixing buttons and links — buttons are actions (resolve to `<a>`, `<button>`, or `<span>` from props), links are navigation (always `<a>`). Separate atom categories.
- Tracking/analytics inside components — decouple to data attributes at view/page level.
- Forgetting `project-config/touch` after editing YAML outside the CP — Git pulls, manual edits, and merge conflict resolution don't update `dateModified`. Run `ddev craft project-config/touch` then `ddev craft up`, or `craft up` on other environments won't detect the change.

## Core Conventions

- Element type resolves from props (`url` → `<a>`, `type` → `<button>`, fallback `<span>`); external links are detected from the URL, never passed as a prop. See `atomic-patterns.md` (Component System Conventions).
- Icons are FontAwesome class strings; [5.12+] custom-set icons (`custom:name`) have no FA class, so branch on `icon.set` and output `icon.svg|raw`.
- One image atom with config-driven presets; structural skeletons with slots use `{% embed %}`.
- Multi-brand theming: `data-brand="{{ currentSite.handle }}"` on `<html>`, three token layers. Tailwind v4 cascade layers don't replace named keys. See `tailwind-conventions.md` (CSS & Theming Conventions).
- `collect()` builds props and classes. JS: Twig → Alpine/DataStar → Vue. See `boilerplate-routing.md` (Routing Conventions).

## Reference Files

Read the relevant reference file(s) for your task. Multiple files often apply together.

**Task examples:**
- "Build a new card component" → read `atomic-patterns.md` + `composition-patterns.md` + `component-inventory.md` + `tailwind-conventions.md`
- "Set up a new project's template structure" → read `boilerplate-routing.md` + `component-inventory.md`
- "Add a content builder for a Matrix field" → read `boilerplate-routing.md` + `composition-patterns.md`
- "Handle responsive images" → read `image-presets.md` + `craft-plugins` → `image-optimize.md` (or `imager-x.md`)
- "Cache the nav/footer with `{% cache %}`" / "scripts blocked by CSP nonce after adding `{% cache %}`" → read `template-caching.md` (CSP Nonces)
- "First page view after upload is slow / why are images `generate-transform` URLs" → read `image-presets.md` (Transform Generation Timing) + `craft-plugins` → `image-optimize.md`
- "Add multi-brand theming" / "compose Tailwind classes without conflicts" → read `tailwind-conventions.md` + `twig-collections.md`
- "Decide between Alpine and Vue for a feature" → read `javascript-boundaries.md`
- "Understand atomic design methodology" → read `atomic-design.md`
- "Set up Vite + Tailwind" / "debug why assets aren't loading in production" → read `vite-buildchain.md`; `craft.vite.*` functions → `craft-plugins` → `vite.md`
- "Install GTM/analytics/CMP" / "plugin styles beat mine" (Plugin CSS Loads After Yours) / "replace a plugin's template, widget stopped enhancing" (Hand-Written Templates for Plugin Widgets) → read `third-party-integration.md`
- "Configure email delivery via SES" → read `third-party-integration.md` + `craft-plugins` → `amazon-ses.md`
- Plugin tasks → `craft-plugins` skill, `references/<plugin>.md`: SEOmatic for a section (`seomatic.md`), Blitz with Cloudflare (`blitz.md`), add a form (`formie.md`), CKEditor nested entries (`ckeditor.md`), navigation menu (`navigation.md`), link field (`hyper.md`), redirects (`retour.md`), recurring dates (`timeloop.md`), JSON API endpoint (`element-api.md`), N+1 debugging (`elements-panel.md`), security audit (`sherlock.md`), YouTube/Vimeo as asset (`embedded-assets.md`), live search / reactive filtering / load-more (`sprig.md`), import a feed (`feed-me.md`), Imager-X responsive images (`imager-x.md`)
- "Build a language switcher" / "hreflang tags" / "plan a multi-language architecture" → read `multi-site-patterns.md`
- "Add login/registration" / "password reset flow" → read `auth-flows.md`; "user profile edit page" → read `auth-account.md`
- "Build a search page" / "configure search settings" (Search Configuration) / "rebuild the search index" (Rebuilding) → read `search.md`
- "Create an RSS feed" / "XML sitemap" (XML Sitemap) / "JSON Feed" (JSON Feed) → read `feeds.md`
- "Headless Craft with Next.js" / "fix GraphQL preview tokens" / "consume Craft GraphQL from a front-end framework" → read `headless.md`; members logging in to a headless front end → `headless.md` (Signed-In Members over OAuth)
- "Use entry.render() for reusable card components" / "set up `_partials/` templates" / "render Matrix blocks with partials" → read `element-partials.md`; "use `{% render %}` / why is `loop` defined in my partial" → `element-partials.md` (The `{% render %}` Tag)
- "Ship example templates with a plugin (bundle + install command)" / "fluent render/tag builder (`craft.<handle>.thing().render()`)" → read `example-templates.md`

| Reference | Scope |
|-----------|-------|
| `references/atomic-design.md` | Methodology: atomic design principles, 5-to-3 tier compression, context-agnostic naming, decompose-downward workflow |
| `references/atomic-patterns.md` | Component construction: props/extends/block, variant files, button/link/text/icon atoms, component system conventions |
| `references/composition-patterns.md` | Molecules, organisms, structural embeds, include/extends/embed decision table, calling conventions |
| `references/component-inventory.md` | Classification decision tree, naming, props design, scaffolding, tier promotion, audit checklist |
| `references/boilerplate-routing.md` | Layout chain, section template paths, globals, routers, views, content builders, directory structure, routing conventions |
| `references/tailwind-conventions.md` | Named-key collections, `utilities` prop, dark mode, spacing, CSS & theming conventions (multi-brand tokens) |
| `references/vite-buildchain.md` | nystudio107 Vite bridge, `config/vite.php`, `vite.config.ts`, `craft.vite.script()`, per-page loading, Tailwind v4, DDEV |
| `references/image-presets.md` | Image atom with presets, srcset/sizes, ImageOptimize vs Craft Cloud, transform timing (`generateTransformsBeforePageLoad`) |
| `references/template-caching.md` | `{% cache %}`: keying (`globally`, `using key`), what may go inside, CSP nonces, nav/footer example, transform URLs, verification |
| `references/javascript-boundaries.md` | JS decision tree: Twig → Alpine/DataStar → Vue, mount points, data handoff, coexistence rules |
| `references/twig-collections.md` | `collect()` method reference: creating, accessing, transforming, filtering, sorting, slicing, arrow functions |
| `references/third-party-integration.md` | Script order, CMP, GTM/sGTM, analytics, SES transport, n8n webhooks, plugin CSS cascade, hand-written plugin widget templates, Blitz, head template |
| `references/multi-site-patterns.md` | Language switchers, hreflang, site architectures, cross-site queries, static translations, multi-site forms |
| `references/auth-flows.md` | Front-end authentication forms: login, registration, password reset, set new password |
| `references/auth-account.md` | Account management: edit profile, email verification, navigation partial, access control tags, user session helpers, GeneralConfig auth settings |
| `references/search.md` | Search: syntax, Twig queries, configuration, indexing, rebuilding, score and ranking |
| `references/feeds.md` | Feeds: RSS 2.0, Atom, JSON Feed, XML sitemap, custom routes, date filters |
| `references/headless.md` | headlessMode, GraphQL schemas and tokens, members over OAuth with `currentUser` [5.12+], CORS, preview tokens, Next.js/Nuxt/Astro |
| `references/element-partials.md` | Element partials: entry.render(), `{% render %}` tag and collection `render()` [5.12+], _partials/ directory, template lookup, custom variables, eager loading in partials |
| `references/example-templates.md` | Plugin example-template bundles and install command, fluent `craft.<handle>.<thing>({...}).render()` BaseTag builders, progressive enhancement |

### Plugin References

Per-plugin configuration, Twig API and pitfalls live in the **`craft-plugins`** skill (`references/<plugin>.md`), so back-end, migration and deployment tasks find them too. For Formie, SEOmatic, Blitz, Imager-X / ImageOptimize, Sprig, CKEditor, Hyper, Navigation, Embedded Assets, Vite, Typogrify or Colour Swatches, load `craft-plugins` and open the matching reference.
