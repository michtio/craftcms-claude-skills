# Timeloop

Repeating date field by CraftPulse. Creates recurring dates (daily, weekly, monthly, yearly) without complex inputs — editors pick a frequency, cycle, and optional end date. Exposes a Twig variable API, a `recurringDates()` function for cross-entry queries, and full GraphQL support. CraftPulse's own plugin.

`craftpulse/craft-timeloop` — Free (internal)

## Documentation

- GitHub: https://github.com/craftpulse/craft-timeloop
- Packagist: https://packagist.org/packages/craftpulse/craft-timeloop

Source lives at `~/dev/craft-plugins/v5/craft-timeloop/src/`. When in doubt, read the source directly.

## Common Pitfalls

- Not setting an end date — without `loopEndDate`, the plugin defaults to start + 20 years. That's 7,300+ daily entries. Always set a sane end date or use `limit` in `getDates()`.
- Expecting `getUpcoming()` to return an array — it returns a single `DateTime|null` (the next occurrence). For multiple upcoming dates, use `getDates()` with a limit.
- Monthly frequency without timestring — when using monthly recurrence, set the ordinal + day (e.g., "second Tuesday") via the field UI. Without it, the plugin uses raw month arithmetic with end-of-month correction, which may not be what editors expect.
- Using `recurringDates()` on large element queries — the Twig function iterates every element and computes loops per entry. Pre-filter with element criteria to avoid performance hits.
- Forgetting `.eagerly()` on relation fields that carry Timeloop fields — the Timeloop field normalizes to a `TimeloopModel`, not a relation, so N+1 isn't the issue. But if the Timeloop field lives on a related entry type, eager-load the relation itself.
- `loopPeriod` stored as JSON text — the field stores its value as a JSON string in a TEXT column. Custom queries against the raw DB value need `JSON_EXTRACT` or similar.

## Field Configuration

The Timeloop field has one setting:

| Setting | Type | Description |
|---------|------|-------------|
| `showTime` | boolean | Enable time selection on start/end dates |

## Data Model

The field normalizes to a `TimeloopModel` with these properties:

| Property | Type | Description |
|----------|------|-------------|
| `loopStartDate` | `DateTime\|null` | Recurrence start |
| `loopEndDate` | `DateTime\|null` | Recurrence end (null = +20 years) |
| `loopStartTime` | `DateTime\|null` | Start time (when `showTime` enabled) |
| `loopEndTime` | `DateTime\|null` | End time (when `showTime` enabled) |
| `loopPeriod` | `array\|null` | `{ frequency, cycle, days[], timestring }` |
| `loopReminderValue` | `int\|null` | Reminder offset value |
| `loopReminderPeriod` | `string\|null` | Reminder offset unit (`days`, `weeks`, etc.) |

### Period Frequencies

| Frequency code | Meaning | Cycle example |
|---------------|---------|---------------|
| `P1D` | Daily | Every `cycle` days |
| `P1W` | Weekly | Every `cycle` weeks (with optional `days[]` selection) |
| `P1M` | Monthly | Every `cycle` months (with optional ordinal + day timestring) |
| `P1Y` | Yearly | Every `cycle` years |

## Twig API

### Variable: `craft.timeloop`

Access via the `craft.timeloop` variable on any element's Timeloop field value:

```twig
{% set timeloopData = entry.myTimeloopField %}

{# Next upcoming occurrence — returns DateTime|null #}
{% set next = craft.timeloop.getUpcoming(timeloopData) %}
{% if next %}
    <time datetime="{{ next|date('c') }}">{{ next|date('d M Y') }}</time>
{% endif %}

{# Next 5 upcoming dates — returns DateTime[] #}
{% set dates = craft.timeloop.getDates(timeloopData, 5) %}
{% for date in dates %}
    <li>{{ date|date('d M Y') }}</li>
{% endfor %}

{# All dates (including past) — set futureDates to false #}
{% set allDates = craft.timeloop.getDates(timeloopData, 10, false) %}

{# Reminder date for next occurrence — returns DateTime|null #}
{% set reminder = craft.timeloop.getReminder(timeloopData) %}

{# Period model — returns PeriodModel|null #}
{% set period = craft.timeloop.period(timeloopData) %}
```

### Variable Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `getUpcoming(data)` | `DateTime\|null` | Next single upcoming occurrence |
| `getDates(data, limit?, futureDates?)` | `DateTime[]` | Up to `limit` dates (default 100). `futureDates` default `true`. |
| `getReminder(data)` | `DateTime\|null` | Reminder date based on configured offset before next occurrence |
| `period(data)` | `PeriodModel\|null` | Raw period configuration model |

### Model Methods (on the field value directly)

The `TimeloopModel` also exposes methods directly:

```twig
{% set tl = entry.myTimeloopField %}

{{ tl.getUpcoming()|date('d M Y') }}
{{ tl.getNextUpcoming()|date('d M Y') }}
{{ tl.getDates(5)|length }} upcoming dates
{{ tl.getReminder()|date('d M Y') }}
{{ tl.loopStartTime }}
{{ tl.loopEndTime }}
```

| Method | Returns | Description |
|--------|---------|-------------|
| `getUpcoming()` | `DateTime\|null` | First upcoming date |
| `getNextUpcoming()` | `DateTime\|null` | Second upcoming date |
| `getDates(limit?, futureDates?)` | `DateTime[]\|null` | Computed occurrence list |
| `getReminder()` | `DateTime\|null` | Next reminder date |
| `getPeriod()` | `PeriodModel\|null` | Period configuration |
| `getLoopStartTime()` | `string\|null` | Formatted `H:i` |
| `getLoopEndTime()` | `string\|null` | Formatted `H:i` |

### Function: `recurringDates()`

Cross-entry date query — finds recurring dates across multiple entries within a date range:

```twig
{% set events = craft.entries.section('events') %}
{% set dates = recurringDates(events, 'myTimeloopField', '2025-04-01', '2025-06-30') %}

{% for item in dates %}
    <h3>{{ item.entryTitle }} (ID: {{ item.entryId }})</h3>
    {% for date in item.dates %}
        <li>{{ date|date('d M Y') }}</li>
    {% endfor %}
{% endfor %}
```

Returns an array of objects: `{ entryId, entryTitle, dates[] }`.

**Performance note:** This iterates every entry in the query and computes loops. Always scope the element query tightly.

## GraphQL

```graphql
{
  entries(section: "events") {
    ... on events_default_Entry {
      myTimeloopField {
        loopPeriod {
          frequency
          cycle
          days
          timestring {
            ordinal
            day
          }
        }
        loopStartDate
        loopStartTime
        loopEndDate
        loopEndTime
        loopReminder
        getUpcoming
        getReminder
        getDates(limit: 5, futureDates: true)
      }
    }
  }
}
```

## Pair With

- **SEOMatic** — use `getUpcoming()` to populate event structured data dates
- **Element API** — expose recurring dates as JSON endpoints for calendar integrations
- **Formie** — event registration forms linked to entries with Timeloop fields
