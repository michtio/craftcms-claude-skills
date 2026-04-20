# Prompt Guide

Real-world prompts organized by task type. Each prompt is something a Craft developer would actually type -- specific, with context, producing good results. The more detail you provide, the better the output.

## Contents

- [Content Modeling](#content-modeling)
- [Plugin Development](#plugin-development)
- [Custom Field Types](#custom-field-types)
- [Element Authorization and Security](#element-authorization-and-security)
- [Twig Templates](#twig-templates)
- [CP Templates and JavaScript](#cp-templates-and-javascript)
- [Configuration and Deployment](#configuration-and-deployment)
- [Testing and Quality](#testing-and-quality)
- [Headless and GraphQL](#headless-and-graphql)

---

## Content Modeling

### Planning content architecture

```
Plan the content architecture for a multi-language corporate site with
news, team members, office locations, and a service catalog. We need
English, German, and French with subfolder-per-language routing.
```

### Matrix page builder design

```
I need a Matrix field for page building with these block types: hero banner,
text with image, testimonial slider, CTA section, and FAQ accordion.
What entry types should I create and how should I configure the Matrix?
Each block type needs specific fields -- propose the full field list per
block with handles, types, and whether they can reuse existing fields.
```

### Taxonomy strategy for Craft 5

```
We're migrating from WordPress. The old site has 3 category taxonomies
(Topics, Industries, Regions) and about 200 tags. What's the Craft 5
approach for taxonomies? Should everything be Structure sections? What
about the tags -- we need editors to create new ones quickly.
```

### Adding fields to an existing entry type

```
Add a hero image, subtitle, and CTA link to the "Service Page" entry type.
We already have fields for other entry types -- reuse what exists. Here's
our current field pool: heroImage (Assets), subtitle (Plain Text),
primaryLink (Hyper), bodyContent (CKEditor), featuredImage (Assets).
```

### Multi-site propagation decisions

```
We have a Craft site with 4 language sites (EN, DE, FR, IT). Some content
is translated per-language, some is shared globally (like image assets and
document downloads). How should I configure propagation for each section?
The sections are: Blog (translated), Resources (shared files, translated
descriptions), Team (same across all sites), and Site Settings (per-site).
```

### CKEditor vs Matrix decision

```
Our editors want a flexible content area where they can mix rich text
paragraphs with image galleries, code blocks, and pull quotes. Should
this be a Matrix field with block types, CKEditor with nested entries,
or a combination? The editing experience matters -- they're non-technical
content authors who currently use WordPress Gutenberg.
```

### Entrification migration

```
Our Craft 5 project still has legacy category groups (Topics, Departments)
and a global set (Site Settings). Walk me through entrifying all three.
What commands do I run, what happens to existing relations, and do I need
to update my templates afterward?
```

---

## Plugin Development

### Custom element type

```
Build a custom element type for "Job Listings" with postDate/expiryDate
status logic, a categories relation for departments, salary range fields,
and a CP edit page with field layout designer. Jobs should be filterable
by department and status in the element index.
```

### Webhook controller

```
Add a webhook controller to my plugin that receives POST requests from
Stripe. It needs to validate the Stripe signature header, parse the
event type, and queue different jobs for payment_intent.succeeded,
customer.subscription.updated, and invoice.payment_failed. The endpoint
must be anonymous but CSRF-exempt.
```

### Service with element operations

```
Build a SyncService for my plugin that fetches products from an external
API (paginated, 100 per page), creates or updates matching Craft entries
in the "Products" section, and handles soft-deleting entries that no
longer exist in the API. It should run as a queue job and report progress.
```

### Migration for a new custom table

```
Write a migration that creates a "joblistings" table with columns for
title, slug, departmentId (FK to entries), salaryMin (int), salaryMax (int),
remotePolicy (enum: remote/hybrid/onsite), postDate, expiryDate, and the
standard Craft element columns. Include proper indexes and foreign keys.
```

### Event listener registration

```
I need to add a custom source to the Entries element index that shows
"My Drafts" -- only draft entries authored by the current user. Register
the event, build the source config, and scope the element query correctly.
```

### Queue job with retry logic

```
Build a queue job that sends entries to an external search index via API.
It should process entries in batches of 50, retry 3 times with exponential
backoff on API failures, and skip individual entries that fail validation
rather than failing the whole batch.
```

### Console command

```
Create a console command for my plugin that rebuilds a custom search index.
It should accept --section and --limit options, show a progress bar, and
be safe to run in production during off-peak hours. Format it as
plugin-handle/search/rebuild.
```

### Plugin settings with project config

```
My plugin needs settings for: API key (per-environment), sync frequency
(dropdown: hourly/daily/weekly), enabled sections (multi-select from
available sections), and a lightswitch for debug mode. Store them in
project config so they sync across environments. The API key should
come from an environment variable.
```

---

## Custom Field Types

### Building a basic custom field type

```
Build a custom field type called "Price Range" that stores a min and max
price as integers. The input UI should show two number fields side by side.
Validation: min must be less than max, both must be positive. The field
should be searchable and expose both values via GraphQL.
```

### Field type with settings

```
I'm building a "Star Rating" custom field type. It needs settings for
max stars (default 5) and whether half-stars are allowed. The input HTML
should render clickable stars. The stored value is a float (e.g., 3.5).
Include proper normalizeValue/serializeValue handling.
```

### Relation field type

```
Build a custom relation field type called "Related Resources" that extends
the base relation field but adds a "relationship type" dropdown (e.g.,
"See Also", "Required Reading", "Further Study") stored alongside each
relation. The CP UI should show the type selector next to each related
element in the selection modal.
```

### Field type with GraphQL

```
My custom "Color Palette" field stores an array of hex colors with labels.
I need the full GraphQL integration: a custom GQL type that exposes the
colors array, arguments for querying entries by color, and input types
for mutations. Show me getContentGqlType, getContentGqlMutationArgumentType,
and the GQL type class.
```

---

## Element Authorization and Security

### Defense-in-depth for a custom element

```
I have a custom "Client Projects" element type. Projects belong to specific
user groups (agencies). I need four layers of security: element-level
canView/canSave/canDelete that checks group membership, query scoping in
EVENT_BEFORE_PREPARE so users only see their agency's projects, controller
enforcement with requirePermission, and CP index source filtering. Show
me the full defense-in-depth implementation.
```

### Custom permissions with constants

```
Register custom permissions for my plugin: "Manage job listings" (create/edit/
delete), "View all listings" (cross-agency visibility), and "Publish listings"
(change status to live). Use class constants for permission handles, register
them in a nested structure under my plugin's name, and show me how to check
them in both controllers and templates.
```

### Session management in a plugin

```
I need to force-logout a user from all devices when an admin revokes their
access. Show me how to invalidate all sessions for a specific user by
manipulating the sessions table, and how to trigger a password reset
required flag so they must re-authenticate with a new password.
```

### Scoping element queries by permission

```
My plugin has a "Documents" element type. Users with the "viewAllDocuments"
permission see everything. Users without it should only see documents they
own or documents assigned to their user group. Show me the EVENT_BEFORE_PREPARE
handler that scopes the query based on the current user's permissions.
```

---

## Twig Templates

### Atomic button component

```
Create an atomic button component that supports links, form submits,
and disabled states. It needs size variants (sm, md, lg) and a loading
spinner option. The component should resolve to <a>, <button>, or <span>
based on props, auto-detect external links, and use the extends/block
pattern for variants.
```

### Language switcher

```
Build a language switcher that shows all available translations for the
current entry, falls back to the site homepage when a translation doesn't
exist, and includes proper hreflang attributes in the <head>. We have
4 sites: EN (primary), DE, FR, and IT with subfolder routing (/de/, /fr/, /it/).
```

### Vite setup from scratch

```
Set up Vite with Tailwind v4 for our Craft site, including HMR in DDEV
and production builds with content hashing. We're using the nystudio107
Vite plugin. Show me the full config: vite.config.ts, config/vite.php,
the Twig script/style tags, and the .ddev/config.yaml changes for
exposing the dev server.
```

### Content builder for Matrix blocks

```
Build a content builder that renders Matrix blocks from our "pageBuilder"
field. Block types are: hero, textWithImage, testimonialSlider, ctaSection,
and faqAccordion. Each block type should be a separate include in
_builders/page-builder/. Add a devMode fallback for unknown block types.
Handle empty blocks gracefully.
```

### Search page with live results

```
Build a search page with a form that submits via GET, displays paginated
results with highlighted excerpts, and shows "No results" with suggestions
when empty. Use Craft's built-in search (not a plugin). The results should
show the entry title, a 200-character excerpt, the section name, and
the post date.
```

### RSS feed template

```
Create an RSS 2.0 feed for our blog section. Include the 20 most recent
entries with title, description (first 500 chars of body, stripped of HTML),
author name, publication date, and category tags. Set the correct content
type and include the channel metadata.
```

### Authentication flow

```
Build a member area with registration, login, password reset, and profile
editing. Users should be in the "Members" group and only see content in
the gated "Members Only" section. Include CSRF tokens, error handling for
each form, and a navigation partial that shows login/logout based on
session state.
```

### Sprig-powered filtering

```
Build a product listing page with Sprig-powered filters. Users can filter
by category (checkboxes), price range (min/max inputs), and sort order
(dropdown). The results should update without a full page reload. Include
a "Clear all filters" button and show the active filter count.
```

---

## CP Templates and JavaScript

### Plugin settings page with editable table

```
Build a settings page for my plugin with an editable table where admins
can map sites to URI formats. Each row needs a site dropdown, a text
input for the URI pattern, and a lightswitch to enable/disable. The
table should support add, delete, and reorder. Show me the Twig template
and the controller that saves the settings.
```

### Modal dialog with form

```
I need a modal dialog for my Craft plugin that opens when clicking
"Add Item", shows a form with name and handle fields (handle auto-
generates from name), POSTs to my plugin's save action via Ajax, and
closes on success with a flash message. Make it keyboard accessible
with focus trapping and ESC to close.
```

### Disclosure menu on element index rows

```
Add a disclosure menu (the ... action menu) to each row in my custom
element index. Needs Edit, Duplicate, and a red Delete option with
confirmation dialog. Show me the Twig markup for the menu, the JS
initialization, and the controller actions for duplicate and delete.
```

### Drag-to-reorder settings list

```
Add drag-to-reorder functionality to the items list on my plugin's
settings page. Each <li> has a .move.icon handle and I need to POST
the new order via an action endpoint when the user drops an item.
Use Garnish.DragSort with the correct settings and event handlers.
```

### Custom field type with interactive input

```
My custom field type needs an interactive color picker in the CP input.
When the user clicks a swatch button, a HUD should appear with a grid
of color options. Selecting a color updates the hidden input value and
the visible swatch preview. Use Garnish.HUD for the popover.
```

---

## Configuration and Deployment

### Redis for everything

```
Configure Redis for cache, sessions, and mutex in our Craft project.
We're running DDEV locally and deploying to a VPS with Redis installed.
Show me the full config/app.php with the Redis connection, cache component,
session component, and mutex. Include the DDEV Redis add-on setup.
```

### Production hardening

```
Harden our production Craft config -- disable admin changes, set up proper
CSRF for static caching with Blitz, configure trusted hosts behind our
load balancer, disable the X-Powered-By header, and set secure session
cookies. Show me config/general.php with environment-specific settings.
```

### Environment variables and config priority

```
We're setting up environment variables for staging and production servers.
What CRAFT_* variables do we need, how does the config priority order
work between .env, general.php, and app.php, and which settings can be
auto-mapped from env vars vs which need explicit general.php configuration?
```

### Email transport per environment

```
Set up email for production using AWS SES, but locally in DDEV we want
Mailpit to catch everything. Show me the full config for both environments
including the SES plugin configuration, the app.php mailer component,
and the DDEV Mailpit add-on setup.
```

### Zero-downtime deployment

```
Set up a zero-downtime deployment pipeline for our Craft site on a VPS
using GitHub Actions. The pipeline should: run ECS and PHPStan, build
front-end assets, deploy via rsync to a releases directory, run craft up
(migrate + project-config apply), swap the symlink, and clear caches.
Include rollback steps.
```

### Database replicas

```
Our production Craft site gets heavy read traffic. Set up read replicas
in config/app.php so element queries use the replica while writes go to
the primary. How does Craft handle replica lag for draft saves and
project config writes?
```

---

## Testing and Quality

### Pest test setup

```
Set up Pest tests for my plugin's Items service. I need tests for CRUD
operations (create, read, update, delete), validation failures (missing
required fields, invalid data), and multi-site behavior (items created
on one site visible/invisible on others based on propagation).
```

### Testing a controller

```
Write Pest tests for my plugin's webhook controller. Test: valid POST
with correct signature returns 200, invalid signature returns 401,
malformed JSON returns 400, valid event queues the correct job,
and CSRF is disabled for the webhook action but enabled for all others.
```

### PHPStan level upgrade

```
Our plugin is at PHPStan level 5 and we want to get to level 8. What
are the most common issues we'll hit at each level, and what's the
recommended approach -- fix everything at once or use a baseline and
chip away?
```

### ECS with custom rules

```
Set up ECS for our plugin with the craftcms/ecs preset. We also want
to enforce: no unused imports, final classes on services, and strict
comparison. Show me the ecs.php config file and the composer.json
scripts for check-cs and fix-cs.
```

### Debugging N+1 queries

```
My blog listing page runs 200+ queries and takes 3 seconds. I think
there's an N+1 problem with related entries -- each blog card loads
the author, featured image, and topic entries separately. How do I
find and fix the N+1, and should I add template caching on top?
```

### CI/CD pipeline for a plugin

```
Set up a GitHub Actions workflow for our Craft plugin that runs on every
PR: install dependencies, run ECS check, run PHPStan at level 8, run
Pest tests against MySQL 8 and PostgreSQL 16, and report results.
Include caching for Composer dependencies.
```

---

## Headless and GraphQL

### Headless setup with Next.js

```
Set up a headless Craft installation with GraphQL for our Next.js 14
frontend. We need: headless mode config, a GraphQL schema with the right
permissions, CORS configuration for the Next.js dev server and production
domain, and preview support so editors can see draft content in the
Next.js app.
```

### GraphQL preview tokens

```
Our Next.js preview mode isn't showing draft entries. The preview URL
from Craft includes a token, but the GraphQL query returns null for the
draft entry. Walk me through the full preview token flow: how Craft
generates the token, how Next.js should pass it in the Authorization
header, and what the GraphQL query needs to include (drafts: true,
token argument).
```

### Custom GraphQL types and mutations

```
My plugin has a custom "Booking" element type. I need to expose it via
GraphQL: a BookingType with all fields, a bookings query with filtering
by date range and status, and a createBooking mutation that validates
availability and creates the element. Show me the full GQL implementation
including the type, arguments, resolvers, and schema registration.
```

### Consuming GraphQL from Astro

```
We're building an Astro site that consumes Craft's GraphQL API. Show me
the data fetching pattern: a reusable client, typed query helpers for
entries and assets, handling pagination with Craft's GraphQL cursor,
and static generation with ISR for the blog section.
```

### GraphQL for Matrix content

```
Our page builder uses a Matrix field with 8 block types. Each block type
has different fields. Show me the GraphQL query for fetching a page with
its full page builder content, including the fragment-per-block-type
pattern and how to handle nested entries within CKEditor blocks.
```

---

## Tips for Better Prompts

1. **Name the section, entry type, or field** -- "Add a hero image to the Service Page entry type" is better than "add an image field."

2. **Mention existing context** -- "We already have a heroImage Assets field" tells the skill to reuse rather than create.

3. **Specify the environment** -- "DDEV locally, VPS in production" helps configuration prompts give you both configs.

4. **State the constraint** -- "The editing experience matters -- they're non-technical" changes how content modeling advice is given.

5. **Name the plugin** -- "Using Blitz for caching with Cloudflare" triggers the right plugin reference.

6. **Describe the full flow** -- "Modal opens, form submits via Ajax, closes on success" is more useful than "add a modal."
