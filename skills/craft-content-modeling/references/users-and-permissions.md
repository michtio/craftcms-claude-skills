# Users, Addresses, and Permissions

Content modeling aspects of users, groups, permissions, and addresses in Craft CMS 5.

## CMS Editions and Content Features

Pricing and included seats may change — check https://craftcms.com/pricing for current details.

| Edition | Users | User Groups | Permissions | Key Features |
|---------|-------|-------------|-------------|-------------|
| **Solo** | 1 admin | No | No | Full content modeling, single user |
| **Team** | Multiple (seats included) | No | No | Multiple authors, `maxAuthors` on sections |
| **Pro** | Unlimited | Yes | Yes | Per-group permissions, public registration |
| **Enterprise** | Unlimited | Yes | Yes | SSO (SAML/OIDC), partner support |

Choose the edition before content modeling — it determines whether you can scope content access by user group. If any section needs per-group edit/view restrictions, you need Pro or Enterprise.

## Users as Content

Users are a full element type with their own field layout (Settings → Users → User Fields). They support:

- Custom fields on the user profile (bio, department, social links)
- Photo (single Asset relation)
- Addresses (nested Address elements — see below)
- Name fields (`fullName`, `firstName`, `lastName`)
- Email, username (or email-as-username)
- Preferences (language, locale, week start day)

### Relating Users to Content

Entries support multiple authors since Craft 5.0.0 (controlled by `maxAuthors` on the section). For additional user relations beyond authorship, use a Users relational field.

```twig
{# Entry authors #}
{% for author in entry.authors.all() %}
    {{ author.fullName }}
{% endfor %}

{# Custom Users field #}
{% set reviewers = entry.reviewers.eagerly().all() %}
```

### User Groups (Pro/Enterprise only)

Groups define permission sets. A user can belong to multiple groups. Group permissions are additive — a user gets the union of all their groups' permissions.

Content modeling implications:
- Sections can restrict editing by permission: `"saveEntries:{sectionUid}"`, `"viewEntries:{sectionUid}"`
- Per-section create/edit/delete permissions with site scoping
- Asset volumes have per-group upload/view permissions
- Global sets have per-group edit permissions

### User Condition Rules

For element index filtering and relation field source conditions:
`AdminConditionRule`, `GroupConditionRule`, `CredentialedConditionRule`, `EmailConditionRule`, `FirstNameConditionRule`, `LastNameConditionRule`, `LastLoginDateConditionRule`, `UsernameConditionRule`

## Addresses

Addresses are nested elements owned by another element (typically Users, but available on any element via the Addresses field since 5.0.0).

### Properties

Based on the `commerceguys/addressing` library:
- `countryCode` — two-letter ISO code (required)
- `administrativeArea` — state/province/region
- `locality` — city/town
- `dependentLocality` — suburb/district
- `postalCode`
- `sortingCode`
- `addressLine1`, `addressLine2`, `addressLine3`
- `organization`, `organizationTaxId`
- `fullName` (from NameTrait — first/last name)
- Geocoordinates via `LatLongField` in the field layout

### Twig Access

```twig
{% set address = entry.myAddressField.one() %}
{{ address|address }}           {# formatted output for the country #}
{{ address.addressLine1 }}
{{ address.locality }}, {{ address.administrativeArea }}
{{ address.countryCode }}       {# 'BE', 'US', etc. #}
```

### Content Modeling Decisions

- Addresses have no statuses, no URLs, no independent lifecycle — they exist only as children of another element
- Use the Addresses field when location data needs structured formatting (postal addresses, office locations)
- For simple location strings ("New York, NY"), a Plain Text field is simpler
- For geocoordinate-only data, consider a custom field or the address field's LatLongField layout element

## Field Layout UI Elements

Beyond custom fields, field layouts can include UI elements that improve the editorial experience. These are available in the field layout designer for all element types:

| Element | Purpose |
|---------|---------|
| **Heading** | Section headings within a tab |
| **Tip** | Informational callout (info, warning, or error style) |
| **Markdown** | Rendered markdown text — instructions, guidelines, context for editors |
| **Template** | Custom Twig template rendered inline — for dynamic help text or computed values |
| **Horizontal Rule** | Visual divider between field groups |
| **Line Break** | Spacing between fields |

Use these to create well-organized, self-documenting field layouts. A field layout with clear headings, tips explaining business rules, and logical grouping is significantly easier for editors to work with than a flat list of fields.

### Native Field Layout Elements

Certain element types have built-in field layout elements beyond the standard custom field:

**Entries:** Title field (with auto-generation option)
**Assets:** Title field, Alternative Text field (with its own translation method)
**Users:** Full Name, Email, Username, Photo, Affiliated Site
**Addresses:** Country Code, Address fields, Label, LatLong, Organization, Organization Tax ID

## Permissions Architecture

Permissions in Craft are hierarchical and additive. Key permission patterns for content modeling:

### Section Permissions
- `viewEntries:{sectionUid}` — view entries in this section
- `saveEntries:{sectionUid}` — edit entries (implies view)
- `createEntries:{sectionUid}` — create new entries
- `deleteEntries:{sectionUid}` — delete entries
- `viewPeerEntries:{sectionUid}` — view other users' entries
- `savePeerEntries:{sectionUid}` — edit other users' entries
- `deletePeerEntries:{sectionUid}` — delete other users' entries
- `viewPeerEntryDrafts:{sectionUid}` — view other users' drafts
- `savePeerEntryDrafts:{sectionUid}` — edit other users' drafts
- `deletePeerEntryDrafts:{sectionUid}` — delete other users' drafts

### Volume Permissions
- `viewAssets:{volumeUid}` — view assets in this volume
- `saveAssets:{volumeUid}` — upload/edit assets
- `deleteAssets:{volumeUid}` — delete assets
- `createFolders:{volumeUid}` — create subfolders
- `viewPeerAssets:{volumeUid}` — view other users' uploads
- `savePeerAssets:{volumeUid}` — edit other users' uploads
- `deletePeerAssets:{volumeUid}` — delete other users' uploads

### Global Set Permissions (legacy — use Singles for new projects)
- `editGlobalSet:{globalSetUid}` — edit this global set

### Utility Permissions
- `editUsers` — manage user accounts
- `assignUserGroups:{groupUid}` — assign users to this group
- `assignUserPermissions` — assign individual permissions
- `administrateUsers` — manage admin accounts
- `impersonateUsers` — log in as another user

Plan content model permissions early — retrofitting permission scoping onto an existing content model is painful because it requires restructuring sections and field access patterns.
