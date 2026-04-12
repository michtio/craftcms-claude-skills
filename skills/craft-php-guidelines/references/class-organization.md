# Class Organization

Every class uses section headers with separator lines. Only include sections that have content.

## Full Example

```php
class MyService extends Component
{
    // Traits
    // =========================================================================

    use SomeTrait;

    // Const Properties
    // =========================================================================

    public const EVENT_BEFORE_SAVE = 'beforeSave';

    // Static Properties
    // =========================================================================

    public static ?self $plugin = null;

    // Public Properties
    // =========================================================================

    public string $name = '';

    // Protected Properties
    // =========================================================================

    protected ?int $cachedCount = null;

    // Private Properties
    // =========================================================================

    private ?MemoizableArray $_items = null;

    // Public Methods
    // =========================================================================

    public function init(): void
    {
        parent::init();
    }

    // Protected Methods
    // =========================================================================

    protected function createSettingsModel(): ?Model
    {
        return new SettingsModel();
    }

    // Private Methods
    // =========================================================================

    private function _registerCpUrlRules(): void
    {
    }
}
```

## Ordering Within Sections

- **Imports**: Alphabetical, grouped: PHP built-ins → `Craft` namespace → plugin namespace → third-party. Blank line between groups.
- **Const Properties**: Alphabetical.
- **Properties**: Alphabetical within each visibility group.
- **Methods**: Lifecycle methods first (`init()`, `beforeAction()`, `afterSave()`), then alphabetical within each visibility group.

## Enums

Use PHP backed enums with PascalCase case names and lowercase backing values:

```php
enum BulkOperationStatus: string
{
    case Queued = 'queued';
    case Processing = 'processing';
    case Completed = 'completed';
    case Failed = 'failed';

    public function label(): string
    {
        return match ($this) {
            self::Queued => Craft::t('myplugin', 'Queued'),
            self::Processing => Craft::t('myplugin', 'Processing'),
            self::Completed => Craft::t('myplugin', 'Completed'),
            self::Failed => Craft::t('myplugin', 'Failed'),
        };
    }
}
```

- Place in `src/enums/` directory.
- Use `match` expressions for case-to-value mapping.
- Enums can have methods — use them for labels, colors, and computed values.
- Always string-back or int-back enums for database storage.

## Control Flow Examples

```php
// Happy path last — handle errors first
if (!$section) {
    throw new NotFoundHttpException('Section not found');
}

if (!$section->type) {
    return null;
}

// Process valid section...
return $this->saveSection($section);

// Short ternary
$name = $isFoo ? 'foo' : 'bar';

// Multi-line ternary — each part on its own line
$result = $element instanceof ElementInterface
    ? $element->title
    : 'A default value';

// match over switch
$label = match ($status) {
    'live' => Craft::t('app', 'Live'),
    'pending' => Craft::t('app', 'Pending'),
    'expired' => Craft::t('app', 'Expired'),
    default => Craft::t('app', 'Disabled'),
};

// Separate compound conditions
if (!$element->enabled) {
    return false;
}

if (!$element->enabledForSite) {
    return false;
}
```

## Comments

Code should be self-documenting through descriptive variable and function names. Adding comments should never be the first tactic to make code readable.

*Instead of:*
```php
// Get the failed jobs for this section
$jobs = $section->getJobs()->where(['status' => 'failed'])->all();
```

*Do this:*
```php
$failedJobs = $section->getJobs()->where(['status' => 'failed'])->all();
```

**When to comment:**
- Explain *why* something non-obvious is done, never *what* is being done.
- Document workarounds for Craft CMS or Yii2 quirks with a link to the issue.
- Never add comments to tests — test names should be descriptive enough.
- PHPDocs are not optional (see `references/phpdoc-standards.md`) — those serve a different purpose than inline comments.

## Whitespace

- Add blank lines between statements for readability — let code breathe.
- No extra empty lines between `{}` brackets.
- Exception: sequences of equivalent single-line operations (assignments, array items) can stay compact.
- One blank line after the section header separator, before the first item.

## Strings

- String interpolation over `sprintf` and `.` concatenation.
- Curly typographic quotes in project config messages: `"Save item \u201C{$handle}\u201D"`.
- `::class` for class references, never string class names.
