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
- `@param` / `@return`: no capitalization, no ending punctuation.
- `@throws`: document every thrown exception, **including uncaught exceptions from called methods**.
- `@author` and `@since` at the bottom, after a blank line.

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
