# Drafts & Revisions

Complete reference for Craft CMS 5's draft and revision system: draft types, provisional drafts, autosave, creating and applying drafts, merge behavior, revisions, and plugin considerations. For element save lifecycle, see `elements.md`. For authorization on drafts, see `element-authorization.md`.

## Documentation

- Drafts: https://craftcms.com/docs/5.x/system/elements.html#drafts
- Element types: https://craftcms.com/docs/5.x/extend/element-types.html

## Common Pitfalls

- Triggering side effects (queue jobs, API syncs, webhooks) in `afterSave()` for drafts — always check `!$this->getIsDraft() && !$this->getIsRevision()` before side effects.
- Firing side effects during propagation — check `!$this->propagating` to avoid duplicate actions when a save propagates to other sites.
- Not writing to the custom table for drafts — drafts need their data in `afterSave()`. Only skip side effects, not data persistence.
- Assuming `hasRevisions()` is a static method — it's an instance method. It must return `true` for revision tracking, and `hasDrafts()` must also return `true`.
- Setting `maxRevisions` to `0` without understanding the consequences — unlimited revisions means the `elements` table grows indefinitely.

## Contents

- [Draft Types](#draft-types)
- [Creating Drafts](#creating-drafts)
- [Autosave](#autosave)
- [Applying Drafts](#applying-drafts)
- [Merge and Change Tracking](#merge-and-change-tracking)
- [Revisions](#revisions)
- [Status-Checking Methods](#status-checking-methods)
- [Draft Ownership and Permissions](#draft-ownership-and-permissions)
- [Query Parameters](#query-parameters)
- [Plugin Considerations](#plugin-considerations)
- [Config Settings](#config-settings)

## Draft Types

| Type | How Created | Lifespan | Visibility |
|------|-------------|----------|-----------|
| **Provisional draft** | Auto-created when editing a canonical element | Until applied, discarded, or purged by GC | Only the creator |
| **Saved draft** | "Create a draft" button or programmatic | Until applied or deleted | All users with peer draft permissions |
| **Unpublished draft** | New element created but never published | Until published or deleted | Draft creator |

**Provisional drafts** are one-per-user-per-element. When a user starts editing a published entry, Craft creates a provisional draft behind the scenes. The editor sees an "unsaved changes" banner. The draft can be applied (publishes changes), converted to a saved draft, or discarded.

## Creating Drafts

### Programmatic creation

```php
// Create a saved draft
$draft = Craft::$app->getDrafts()->createDraft(
    $canonicalElement,  // The published element
    $creatorId,         // User ID of the creator
    'My Draft Name',    // Optional name
    'Draft notes here', // Optional notes
    [],                 // Optional new attribute overrides
    false               // $provisional — true for provisional drafts
);

// Save an existing unsaved element as a draft
$draft = Craft::$app->getDrafts()->saveElementAsDraft(
    $element,
    $creatorId,
    'Draft Name',
    'Notes',
    true   // $markAsSaved
);
```

### Authorization

`canCreateDrafts(User $user)` gates who can create drafts. For entries, this returns `true` by default — anyone with view access can create drafts. Custom elements must override this method.

## Autosave

Edits are automatically saved to the draft element as the user types. The CP shows:
- A spinner during autosave
- A caution icon on save failure
- A checkmark when saved

Drafts don't get their own provisional drafts — changes save directly against the draft. The autosave frequency is controlled by JS in the CP editor.

## Applying Drafts

```php
// Apply a draft to its canonical element
$canonicalElement = Craft::$app->getDrafts()->applyDraft($draft);
```

The apply process:
1. If `trackChanges()` is `true` and the draft is outdated, `mergeCanonicalChanges()` syncs canonical changes first
2. Draft content is merged into the canonical element
3. Validation runs (only if the element would be enabled)
4. The draft is deleted
5. A new revision of the canonical element is created (if `hasRevisions()`)
6. Returns the updated canonical element

### What happens to other drafts

When a draft is applied, other saved drafts for the same element remain. Their change tracking is updated to reflect the new canonical state — they may become "outdated" relative to the new content.

## Merge and Change Tracking

### Field-level change tracking

When `trackChanges()` returns `true`, Craft records which fields were modified in each draft. Modified fields show status badges in the editor sidebar.

### Merge behavior on apply

| Scenario | Result |
|----------|--------|
| Field modified in draft only | Draft value wins |
| Field modified in canonical only | Canonical value is merged into draft before apply |
| Field modified in both | Draft value wins (last-write-wins) |
| Field unchanged in either | Canonical value preserved |

This merge is automatic — there is no manual merge UI for field-level conflicts. The draft creator's changes always take precedence.

### Checking if a draft is outdated

```php
use craft\helpers\ElementHelper;

if (ElementHelper::isOutdated($draft)) {
    // Canonical element has been modified since the draft was created
    // mergeCanonicalChanges() will sync the non-conflicting changes
}
```

## Revisions

Revisions are read-only snapshots of canonical elements, captured each time a canonical element is saved.

### Enabling revisions

```php
// On your element class — both are instance methods
public static function hasDrafts(): bool
{
    return true; // Required for hasRevisions() to work
}

public function hasRevisions(): bool
{
    return true;
}
```

### Revision storage

Stored as derivative elements with a `revisionId`. Each revision captures the full element state including field values and relations. Accessible via the breadcrumb menu in the CP editor.

### Restoring a revision

Restoring a revision **copies** its content into the canonical element and creates a new revision of the current state. History is not rewound — the restore itself becomes the latest change.

```php
// Programmatic restore
Craft::$app->getRevisions()->revertToRevision($revision);
```

### Revision limits

`maxRevisions` config setting controls how many revisions to keep per element. Default: `50`. Set to `0` for unlimited (watch `elements` table growth). Old revisions are pruned during garbage collection.

## Status-Checking Methods

| Method | Returns `true` when |
|--------|-------------------|
| `getIsDraft()` | Element has a `draftId` (is a draft of any type) |
| `getIsRevision()` | Element has a `revisionId` |
| `getIsCanonical()` | Not a draft and not a revision (the live version) |
| `getIsDerivative()` | Is a draft OR a revision |
| `getIsProvisionalDraft()` | Auto-created provisional draft |
| `getIsUnpublishedDraft()` | Draft that was never published as canonical |
| `getCanonical()` | Returns the canonical element this derives from |

### Usage in element code

```php
// In afterSave() — safe pattern for side effects
if (!$this->getIsDraft() && !$this->getIsRevision() && !$this->propagating) {
    // Fire queue jobs, API syncs, webhooks
    MyPlugin::getInstance()->getSyncService()->syncElement($this);
}
```

## Draft Ownership and Permissions

### Creator access

`draftCreatorId` identifies who created the draft. The creator can always edit and delete their own drafts, regardless of peer draft permissions.

### Peer draft permissions (Entries)

| Permission | Allows |
|------------|-------|
| `viewPeerEntryDrafts:{sectionUid}` | View drafts created by other users |
| `savePeerEntryDrafts:{sectionUid}` | Edit drafts created by other users |
| `deletePeerEntryDrafts:{sectionUid}` | Delete drafts created by other users |

### Provisional draft visibility

Provisional drafts are only accessible to their creator. Other users see the canonical element. The `withProvisionalDrafts()` query parameter swaps the canonical element with the current user's provisional draft in results.

## Query Parameters

| Parameter | Purpose |
|-----------|---------|
| `drafts(true)` | Include only drafts in results |
| `draftOf($element)` | Drafts of a specific canonical element |
| `draftId($id)` | Specific draft by ID |
| `draftCreator($user)` | Drafts created by a specific user |
| `provisionalDrafts(true)` | Only provisional drafts |
| `withProvisionalDrafts()` | Swap canonical with user's provisional draft |
| `revisions(true)` | Include only revisions in results |
| `revisionOf($element)` | Revisions of a specific canonical element |
| `revisionId($id)` | Specific revision by ID |
| `revisionCreator($user)` | Revisions created by a specific user |

### Query examples

```php
// Get all saved drafts for an entry
$drafts = Entry::find()
    ->draftOf($entry)
    ->drafts(true)
    ->all();

// Get the current user's provisional draft
$provisional = Entry::find()
    ->draftOf($entry)
    ->draftCreator(Craft::$app->getUser()->getIdentity())
    ->provisionalDrafts(true)
    ->one();

// Get recent revisions
$revisions = Entry::find()
    ->revisionOf($entry)
    ->revisions(true)
    ->limit(10)
    ->orderBy('dateCreated DESC')
    ->all();
```

## Plugin Considerations

### Custom table writes in afterSave()

Always write to your custom table for drafts — they need their data. Only skip side effects:

```php
public function afterSave(bool $isNew): void
{
    // Always write custom table data (drafts need it)
    $record = MyElementRecord::findOne($this->id) ?? new MyElementRecord();
    $record->id = $this->id;
    $record->someField = $this->someField;
    $record->save(false);

    parent::afterSave($isNew);

    // Guard side effects
    if ($this->getIsDraft() || $this->getIsRevision()) {
        return;
    }

    if ($this->propagating) {
        return;
    }

    // Safe for queue jobs, API syncs, etc.
    Craft::$app->getQueue()->push(new SyncElementJob([
        'elementId' => $this->id,
    ]));
}
```

### afterPropagate()

The safest place for side effects that need all sites updated first. Fires after the element has been propagated to all sites.

### trackChanges()

Return `true` on custom elements that support drafts to enable field-level change tracking and merge behavior:

```php
public static function trackChanges(): bool
{
    return true;
}
```

## Config Settings

| Setting | Default | Purpose |
|---------|---------|---------|
| `maxRevisions` | `50` | Max revisions per element. `0` = unlimited. |
| `purgeUnsavedDraftsDuration` | `2592000` (30 days) | GC cleanup for unsaved provisional drafts |
