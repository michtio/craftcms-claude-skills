# Queue Jobs

## Documentation

- Queue jobs: https://craftcms.com/docs/5.x/extend/queue-jobs.html
- `craft\queue\BaseJob`: https://docs.craftcms.com/api/v5/craft-queue-basejob.html

## Common Pitfalls

- Naming jobs with a "Job" suffix — Craft convention has no suffix: `ResaveElements`, `UpdateSearchIndex`, not `ResaveElementsJob`.
- Missing `site('*')` on element queries — queue workers run in primary site context, elements on non-primary sites are invisible.
- Forgetting `->status(null)` — disabled/expired elements are filtered out by default.
- Not overriding `getTtr()` for long-running jobs — defaults may be too short, causing re-reservation.
- Using `$this->setProgress()` with wrong math — denominator must be total items, not current index.
- Forgetting `App::maxPowerCaptain()` — Craft calls this for queue jobs automatically, but custom long operations within a job may still hit limits.

## Scaffold

```bash
ddev craft make queue-job --with-docblocks
```

## Job Pattern

```php
class SyncItems extends BaseJob
{
    public int $categoryId;
    public ?int $siteId = null;

    public function execute($queue): void
    {
        $items = $this->_fetchItems();
        $total = count($items);

        foreach ($items as $i => $item) {
            $this->setProgress($queue, ($i + 1) / $total, "Processing {$item->title}");
            $this->_processItem($item);
        }
    }

    protected function defaultDescription(): ?string
    {
        return Craft::t('my-plugin', 'Syncing items for category {id}', [
            'id' => $this->categoryId,
        ]);
    }
}
```

## Critical: Site Context in Workers

Queue workers run in primary site context. Elements on non-primary sites are invisible:

```php
// BAD: misses elements on non-primary sites
$element = MyElement::find()->externalId($id)->one();

// GOOD: always use site('*') and status(null) in queue workers
$element = MyElement::find()
    ->site('*')
    ->externalId($id)
    ->categoryId($this->categoryId)
    ->status(null)
    ->one();
```

## TTR (Time-To-Reserve)

Override for long-running jobs. Default is 300 seconds:

```php
public function getTtr(): int
{
    return 600; // 10 minutes
}
```

## Retry Logic

```php
public function canRetry($attempt, $error): bool
{
    return $attempt < 3;
}
```

## Pushing to Queue

```php
// Standard push
Craft::$app->getQueue()->push(new SyncItems([
    'categoryId' => $category->id,
]));

// With delay (seconds)
Craft::$app->getQueue()->delay(60)->push(new SyncItems([
    'categoryId' => $category->id,
]));

// With priority (lower = higher priority)
Craft::$app->getQueue()->priority(1024)->push(new SyncItems([
    'categoryId' => $category->id,
]));
```

## Batch Operations

For parent jobs that spawn child operations, use `craft\queue\BaseBatchedJob` for automatic memory monitoring and configurable `$batchSize`.

For manual batching within a single job, use `Db::each()` for memory-safe iteration:

```php
use craft\helpers\Db;

public function execute($queue): void
{
    $query = MyElement::find()->categoryId($this->categoryId)->site('*')->status(null);

    foreach (Db::each($query) as $i => $element) {
        $this->setProgress($queue, $i / $query->count());
        $this->_processElement($element);
    }
}
```
