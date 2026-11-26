# PHPDoc Standards

PHPDocs on every class, method, and property. No exceptions.

## Class Docblocks

```php
/**
 * The Items service provides APIs for managing plugin entities.
 *
 * An instance of the service is available via `MyPlugin::$plugin->getItems()`.
 *
 * @property-read SomeType $thing
 *
 * @author <Author Name>
 * @since 5.0.0
 */
```

## Method Docblocks

```php
/**
 * Returns the item matching the given ID.
 *
 * @param int $id the item ID
 * @return Item|null
 * @throws InvalidConfigException if the service is not initialized
 *
 * @author <Author Name>
 * @since 5.0.0
 */
```

- Full sentence description, proper capitalization and punctuation.
- `@param` / `@return`: no capitalization, no ending punctuation. (The official Craft guideline says this, but core itself routinely capitalizes `@param`/`@return` descriptions; this project follows the official guideline as its house rule — lowercase, unpunctuated.)
- `@throws`: document every thrown exception, **including uncaught exceptions from called methods**.
- `@author` and `@since` at the bottom, after a blank line. (Craft *core* puts `@author` at the class level only — not on methods. Repeating it on each method is this project's house convention, not core style.)

## Property Docblocks

`@author` is NOT used on properties — only on classes and methods. Properties use `@var` and `@since`:

```php
/**
 * @var MemoizableArray<Item>|null
 * @see _items()
 */
private ?MemoizableArray $_items = null;

/**
 * @var int|null The parent entity this item belongs to.
 *
 * @since 5.0.0
 */
public ?int $parentId = null;
```

## Constant Docblocks

Follow Craft core pattern — `@event` for event constants, `@since` always:

```php
/**
 * @event ItemEvent The event that is triggered before an item is saved.
 * @since 5.0.0
 */
public const EVENT_BEFORE_SAVE_ITEM = 'beforeSaveItem';
```

## `@inheritdoc` Rule

Only when the parent class or interface has a meaningful doc comment. Otherwise write a full docblock.

## Type References

- Public service methods: reference interfaces (`ElementInterface`, not `Element`).
- Inline `@var` tags: reference implementations.
- Use `bool`/`int`, not `boolean`/`integer`.
- Use `static` as return type for chainable methods.
- Use typed arrays in docblocks: `ElementInterface[]`.
- Always import classnames in docblocks — never fully qualified names.
- For iterables, specify key and value types: `@param array<int, MyObject> $items`.

## Console Controller Docblocks Are Terminal Help

Yii renders console controller docblocks VERBATIM as operator-facing help, with no inline-tag resolution: the class docblock's second line becomes the command summary in `craft help`, the prose up to the first `@tag` becomes the `help <command>` body, each action method's docblock first line becomes that action's description, and option properties' `@var` text becomes `--option` help. Therefore, in every class extending `yii\console\Controller`: no `{@see}`/`{@link}`/`{@inheritdoc}` in class/property docblocks or action-method first lines (write command ids as plain text instead), no `=========` section-header rule as docblock line 2 (it prints as the command summary), no hanging-indent continuation lines on option `@var` tags (they render as ragged indents; match `craftcms/cms` `ResaveController`'s flush style), and the summary sentence goes on line 2. Verify with `ddev craft help <plugin>` — `craft help | grep '{@'` must return nothing.

Three specifics that survive that rule and still bite:

- **The summary is docblock line 2 *physically*, not the first sentence.** `parseDocCommentSummary()` (`yii\console\Controller`) returns `trim($docLines[1])` and nothing more — a first sentence that wraps onto line 3 prints only the fragment on line 2 (real summaries truncated at "and writes", "whether every row", "prints the new"). Keep the whole summary sentence on one physical line, even if it exceeds the usual wrap width.
- **A scaffolded `* Class FooController` on line 2 becomes the `craft help` summary verbatim.** Replace generator boilerplate with a real summary before shipping.
- **`getHelpSummary()` / `getHelp()` overrides make the docblock dead code.** Once a class overrides them, the docblock and the printed help are two sources of truth that disagree silently — and if `getHelp()` returns the summary verbatim, the command has no help body at all. Prefer docblocks alone; if an override exists (or you add one), delete or align the prose it shadows, and check `help <command>` prints an actual body.
