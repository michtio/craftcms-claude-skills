# Conditions Framework

Complete reference for Craft CMS 5's conditions system: building custom condition rules, registering them on element indexes, understanding where conditions are used, and the built-in condition rule base types. For element index filtering and sources, see `element-index.md`. For field layout conditions, see `fields.md`.

## Documentation

- Conditions: https://craftcms.com/docs/5.x/extend/conditions.html
- Element types: https://craftcms.com/docs/5.x/extend/element-types.html

## Common Pitfalls

- Forgetting `getExclusiveQueryParams()` — without it, conflicting rules can be added simultaneously (e.g., two rules both setting `sectionId`), producing unpredictable query results.
- Implementing `modifyQuery()` without `matchElement()` — the condition works for index filtering but fails for conditional field layout visibility (which uses in-memory matching).
- Listening on `BaseCondition::EVENT_REGISTER_CONDITION_RULES` instead of the specific condition class — registers the rule on every condition in the system, not just the one you want.
- Returning `false` from `isSelectable()` unconditionally — the rule becomes invisible in the UI. Use this only for programmatic rules that shouldn't be user-configurable.

## Contents

- [Architecture Overview](#architecture-overview)
- [Where Conditions Are Used](#where-conditions-are-used)
- [Built-in Condition Rule Base Types](#built-in-condition-rule-base-types)
- [Building a Custom Condition Rule](#building-a-custom-condition-rule)
- [Registering Condition Rules](#registering-condition-rules)
- [Condition Builder UI](#condition-builder-ui)

## Architecture Overview

The conditions system has three layers:

### Condition (container)

`craft\base\conditions\BaseCondition` — holds a collection of rules, renders the condition builder UI, and orchestrates evaluation.

`craft\elements\conditions\ElementCondition` — extends `BaseCondition` for element-aware behavior. Adds `modifyQuery()` (applies all rules to an element query) and `matchElement()` (AND logic: all rules must match for the element to pass).

Element-specific subclasses add their own selectable rules:
- `EntryCondition` — Section, Type, Author, PostDate, ExpiryDate, Level, HasDescendants
- `UserCondition` — Group, Admin, Credentialed, LastLogin
- `AssetCondition` — Volume, Kind, Width, Height, FileSize

### Condition Rule (single filter)

Implements `ConditionRuleInterface`. Each rule knows how to:
- Render its UI (`getHtml()`)
- Modify an element query (`modifyQuery()` via `ElementConditionRuleInterface`)
- Match an element in memory (`matchElement()`)
- Serialize to/from config (`getConfig()`)

### Condition Builder (UI)

Renders as an interactive form with add/remove/reorder controls. Uses htmx for dynamic updates. The `ConditionBuilderAsset` bundle is registered automatically.

## Where Conditions Are Used

| Location | Condition Class | Purpose |
|----------|----------------|---------|
| Element indexes | Element-specific (e.g., `EntryCondition`) | User-facing filters in the index toolbar |
| Source definitions | Element-specific | Per-source default filters |
| Conditional field layouts | `ElementCondition` + `UserCondition` | Show/hide fields and tabs based on element state or current user |
| Entry type assignment | `EntryCondition` | Determine available entry types |
| Field layout elements | `UserCondition` | Per-user field visibility |

### Conditional field layouts

Field layout tabs and fields can have both `userCondition` and `elementCondition`:

- **`userCondition`** — `UserCondition` that evaluates against the current logged-in user. Controls whether the user sees the field/tab.
- **`elementCondition`** — `ElementCondition` that evaluates against the element being edited. Controls whether the field/tab appears based on element state.

Both use `matchElement()` (in-memory matching), not `modifyQuery()`.

## Built-in Condition Rule Base Types

All in `craft\base\conditions\`:

### BaseTextConditionRule

| Property | Type | Purpose |
|----------|------|---------|
| `$value` | `string` | Text to match |
| `$operator` | `string` | One of: `=`, `beginsWith`, `endsWith`, `contains`, `empty`, `notEmpty` |

Methods: `matchValue(string $value): bool`, `paramValue(): mixed` (for `Db::parseParam`).

### BaseNumberConditionRule

| Property | Type | Purpose |
|----------|------|---------|
| `$value` | `string` | Number to match |
| `$maxValue` | `string` | Upper bound for "between" operator |
| `$operator` | `string` | `=`, `!=`, `<`, `<=`, `>`, `>=`, `between`, `empty`, `notEmpty` |

Renders number input, dual inputs for "between". Methods: `matchValue($value): bool`, `paramValue(): mixed`.

### BaseSelectConditionRule

| Property | Type | Purpose |
|----------|------|---------|
| `$value` | `string` | Selected option value |

Subclass must implement `options(): array` returning `['value' => 'Label']`. Renders a select dropdown.

### BaseMultiSelectConditionRule

| Property | Type | Purpose |
|----------|------|---------|
| `$values` | `array` | Selected option values |
| `$operator` | `string` | `in`, `not in` (optionally `empty`, `notEmpty`) |

Subclass must implement `options(): array`. Renders a Selectize multi-select. Methods: `matchValue($value): bool`, `paramValue(): mixed`.

### BaseDateRangeConditionRule

| Property | Type | Purpose |
|----------|------|---------|
| Range type | `string` | Today, this week/month/year, past 7/30/90 days, before/after N units, custom range, empty, not empty |

Renders a menu button with date pickers or period inputs. Methods: `matchValue($value): bool`, `queryParamValue(): mixed`.

### BaseLightswitchConditionRule

| Property | Type | Purpose |
|----------|------|---------|
| `$value` | `bool` | Toggle state |

Renders a lightswitch. Methods: `matchValue($value): bool`.

### BaseElementSelectConditionRule

| Property | Type | Purpose |
|----------|------|---------|
| `$elementIds` | `array` | Selected element IDs |

Renders an element select input. When `$forProjectConfig` is true, uses autosuggest with env var support.

## Building a Custom Condition Rule

### For element index filtering

Implement `ElementConditionRuleInterface` and extend a base type:

```php
namespace myplugin\conditions;

use craft\base\conditions\BaseMultiSelectConditionRule;
use craft\base\ElementInterface;
use craft\elements\conditions\ElementConditionRuleInterface;
use craft\elements\db\ElementQueryInterface;

class ItemCategoryConditionRule extends BaseMultiSelectConditionRule implements ElementConditionRuleInterface
{
    /**
     * @inheritdoc
     */
    public function getLabel(): string
    {
        return Craft::t('my-plugin', 'Item Category');
    }

    /**
     * @inheritdoc
     */
    public function getGroupLabel(): ?string
    {
        return Craft::t('my-plugin', 'My Plugin');
    }

    /**
     * @inheritdoc
     */
    public function getExclusiveQueryParams(): array
    {
        return ['categoryId'];
    }

    /**
     * @inheritdoc
     */
    protected function options(): array
    {
        $options = [];

        foreach (MyPlugin::getInstance()->getCategories()->getAllCategories() as $category) {
            $options[$category->id] = $category->name;
        }

        return $options;
    }

    /**
     * @inheritdoc
     */
    public function modifyQuery(ElementQueryInterface $query): void
    {
        $query->categoryId($this->paramValue());
    }

    /**
     * @inheritdoc
     */
    public function matchElement(ElementInterface $element): bool
    {
        return $this->matchValue($element->categoryId);
    }
}
```

### Key methods

| Method | Required | Purpose |
|--------|----------|---------|
| `getLabel()` | Yes | Display name in rule dropdown |
| `getGroupLabel()` | No | Optgroup header in dropdown |
| `getLabelHint()` | No | Hint text after label (since 4.6) |
| `getExclusiveQueryParams()` | Yes | Prevents conflicting rules |
| `modifyQuery()` | Yes | Applies filter to element query |
| `matchElement()` | Yes | In-memory matching for conditional layouts |
| `getConfig()` | Inherited | Serialization for storage |

### For field-level conditions

Field types can provide their own condition rule via `getElementConditionRuleType()`:

```php
// On the field type class
public function getElementConditionRuleType(): ?string
{
    return MyFieldConditionRule::class;
}
```

These rules automatically appear in condition builders for element types that include this field in their layout.

## Registering Condition Rules

Listen on the **specific condition class**, not on `BaseCondition`:

```php
use craft\elements\conditions\entries\EntryCondition;
use craft\base\conditions\BaseCondition;
use craft\events\RegisterConditionRulesEvent;
use yii\base\Event;

// For entry indexes
Event::on(
    EntryCondition::class,
    BaseCondition::EVENT_REGISTER_CONDITION_RULES,
    function(RegisterConditionRulesEvent $event) {
        $event->conditionRules[] = ItemCategoryConditionRule::class;
    }
);

// For user indexes
Event::on(
    UserCondition::class,
    BaseCondition::EVENT_REGISTER_CONDITION_RULES,
    function(RegisterConditionRulesEvent $event) {
        $event->conditionRules[] = PasswordExpiredConditionRule::class;
    }
);
```

The event carries `$conditionRules` — an array of class names or `['class' => ClassName, ...]` config arrays.

## Condition Builder UI

The condition builder renders inside element index toolbars, field layout designers, and source configuration screens.

### Rendering in custom contexts

```php
use craft\base\conditions\ConditionInterface;

// Create a condition
$condition = Craft::$app->getConditions()->createCondition([
    'class' => EntryCondition::class,
    'elementType' => Entry::class,
]);

// Render the builder
$html = $condition->getBuilderHtml();
```

### How the UI works

1. Rules appear as rows with a type-switcher dropdown, the rule's input controls, and a remove button
2. "Add a rule" button triggers an htmx POST to `conditions/render`
3. Rules can be reordered by drag handle (when `$sortable` is true)
4. The entire condition state is serialized as a hidden input for form submission
5. Evaluation is AND logic — all rules must pass for the condition to match
