# Queue Jobs

Complete reference for queue job development in Craft CMS 5. For queue component configuration (Redis, TTR, attempts), see `config-app.md`.

## Documentation

- Queue jobs: https://craftcms.com/docs/5.x/extend/queue-jobs.html
- `craft\queue\BaseJob`: https://docs.craftcms.com/api/v5/craft-queue-basejob.html
- `craft\queue\BaseBatchedJob`: https://docs.craftcms.com/api/v5/craft-queue-basebatchedjob.html

## Contents

- [Common Pitfalls](#common-pitfalls)
- [Scaffold](#scaffold)
- [Job Pattern](#job-pattern)
- [Critical: Site Context in Workers](#critical-site-context-in-workers)
- [TTR (Time-To-Reserve)](#ttr-time-to-reserve)
- [Queue Infrastructure](#queue-infrastructure)
- [Pushing to Queue](#pushing-to-queue)
- [Job Priority](#job-priority)
- [Retry Strategies](#retry-strategies)
- [Failed Job Handling](#failed-job-handling)
- [Long-Running Job Patterns](#long-running-job-patterns)
- [Common Queue Job Patterns](#common-queue-job-patterns)
- [Built-in Queue Jobs](#built-in-queue-jobs)
- [Queue Health Monitoring](#queue-health-monitoring)

## Common Pitfalls

- Naming jobs with a "Job" suffix -- Craft convention has no suffix: `ResaveElements`, not `ResaveElementsJob`.
- Missing `site('*')` on element queries -- queue workers run in primary site context, elements on non-primary sites are invisible.
- Forgetting `->status(null)` -- disabled/expired elements are filtered out by default.
- Not overriding `getTtr()` for long-running jobs -- default is 300s (5 min). Exceeding TTR causes re-reservation and duplicate execution.
- Using `$this->setProgress()` with wrong math -- denominator must be total items, not current index.
- Forgetting `App::maxPowerCaptain()` -- Craft calls this automatically, but custom long operations within a job may still hit limits.
- Using `runQueueAutomatically` on high-traffic production sites -- the web runner blocks PHP-FPM workers. Use `craft queue/listen` instead.
- Accessing `Craft::$app->getUser()` in queue jobs -- no user session in queue context. Pass needed user IDs as job properties.
- Not reporting progress in long-running jobs -- CP shows a "stuck" indicator, admins retry thinking it failed.
- Memory leaks in batch operations -- element caches grow unbounded. Use `Db::each()` or paginated queries.

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

Override for long-running jobs. Default is 300s. Exceeding TTR causes re-reservation (duplicate execution). Set to at least 2x expected duration. Per-job `getTtr()` overrides the global `ttr` in `config/app.php`.

```php
public function getTtr(): int
{
    return 600; // 10 minutes
}
```

## Queue Infrastructure

### Web runner vs daemon

| Method | Config | When to use |
|--------|--------|-------------|
| Web runner | `runQueueAutomatically => true` (default) | Development, low-traffic sites |
| Daemon | `craft queue/listen` | Production, high-traffic, long-running jobs |

The web runner piggybacks on HTTP requests -- PHP stays alive after page delivery to process jobs. This blocks a PHP-FPM worker for the job's duration. On high-traffic sites, this exhausts the worker pool. Disable in `config/general.php` with `'runQueueAutomatically' => false`.

### Console commands

```bash
ddev craft queue/run                  # Process all pending jobs and exit
ddev craft queue/listen               # Long-running daemon (restarts after each job)
ddev craft queue/listen --verbose     # Daemon with logging (recommended for production)
```

In production, run `craft queue/listen` under a process supervisor (systemd, Supervisor). For DDEV, a terminal tab is sufficient.

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

## Job Priority

Lower number = higher priority. Default is 1024. Methods chain: `->delay(30)->priority(100)->push(...)`.

| Priority | Use case |
|----------|----------|
| 100 | User-triggered actions (exports, imports the user is waiting for) |
| 1024 | Default -- standard background tasks |
| 2048 | Background maintenance (cleanup, stats aggregation) |
| 4096 | Low-priority bulk operations (re-indexing, cache warming) |

`delay(N)` postpones execution by N seconds. Useful for rate limiting or debouncing rapid saves.

## Retry Strategies

### Basic retry

```php
public function canRetry($attempt, $error): bool
{
    return $attempt < 3;
}
```

### Selective retry by error type

Retry network/server errors, fail immediately on client errors (4xx):

```php
public function canRetry($attempt, $error): bool
{
    if ($attempt >= 5) { return false; }
    if ($error instanceof \GuzzleHttp\Exception\ConnectException) { return true; }
    if ($error instanceof \GuzzleHttp\Exception\ServerException) { return true; }
    if ($error instanceof \GuzzleHttp\Exception\ClientException) { return false; }
    return true;
}
```

### Global max attempts

In `config/app.php` (default: 1). Per-job `canRetry()` takes precedence when defined:

```php
'queue' => ['attempts' => 3],
```

### Manual exponential backoff

No built-in exponential backoff. Pattern: add a custom `$attempt` property, catch errors, re-push with increasing delay:

```php
public int $attempt = 0; // Custom property -- not built-in

public function execute($queue): void
{
    try {
        $this->_doWork();
    } catch (\GuzzleHttp\Exception\ServerException $e) {
        if ($this->attempt < 5) {
            $delay = (int)(30 * pow(2, $this->attempt)); // 30s, 60s, 120s...
            Craft::$app->getQueue()->delay($delay)->push(new self([
                'categoryId' => $this->categoryId, 'attempt' => $this->attempt + 1,
            ]));
            return;
        }
        throw $e;
    }
}
```

## Failed Job Handling

When `canRetry()` returns `false` or max attempts are exceeded, the job is marked as failed in the `queue` table.

```bash
ddev craft queue/info       # Pending, reserved, done, failed counts
ddev craft queue/retry      # Retry all failed jobs
ddev craft queue/release    # Release stuck/reserved jobs
```

To investigate, query the `queue` table: `SELECT id, description, error FROM queue WHERE fail = 1 ORDER BY timePushed DESC LIMIT 20;`. The CP queue manager (gear icon, bottom-left) also shows failed jobs with a retry button.

## Long-Running Job Patterns

### Progress reporting

Always report progress in jobs taking more than a few seconds. Include a meaningful message -- users see this in the CP:

```php
$this->setProgress($queue, ($i + 1) / $total, "Processing {$entry->title} (" . ($i + 1) . " of {$total})");
```

### Memory management

Element queries cache results. Over thousands of iterations, memory grows unbounded. Use `Db::each()` for memory-safe iteration:

```php
use craft\helpers\Db;

$query = Entry::find()->section('products')->site('*')->status(null);
foreach (Db::each($query) as $i => $entry) {
    $this->setProgress($queue, $i / $query->count());
    $this->_processEntry($entry);
}
```

For very large datasets, paginate and call `gc_collect_cycles()` between batches:

```php
for ($offset = 0; $offset < $query->count(); $offset += 100) {
    $entries = (clone $query)->offset($offset)->limit(100)->all();
    foreach ($entries as $entry) { $this->_processEntry($entry); }
    gc_collect_cycles();
}
```

For parent jobs that spawn child operations, use `craft\queue\BaseBatchedJob` for automatic memory monitoring and configurable `$batchSize`.

## Common Queue Job Patterns

### Resave elements

Use Craft's built-in job instead of writing a custom one:

```php
use craft\queue\jobs\ResaveElements;

Craft::$app->getQueue()->push(new ResaveElements([
    'elementType' => Entry::class,
    'criteria' => ['section' => 'products', 'site' => '*', 'status' => null],
]));
```

### Sync external data

Fetch from API, upsert elements. Key points: high TTR, retry only on network errors, `site('*')` + `status(null)`:

```php
class SyncProducts extends BaseJob
{
    public function execute($queue): void
    {
        $client = Craft::createGuzzleClient();
        $products = json_decode(
            $client->get('https://api.example.com/products')->getBody()->getContents(), true
        );
        foreach ($products as $i => $data) {
            $this->setProgress($queue, ($i + 1) / count($products));
            $entry = Entry::find()->section('products')->site('*')->status(null)
                ->externalId($data['id'])->one() ?? new Entry();
            $entry->sectionId = Craft::$app->getEntries()->getSectionByHandle('products')->id;
            $entry->title = $data['name'];
            Craft::$app->getElements()->saveElement($entry);
        }
    }
    public function getTtr(): int { return 900; }
    public function canRetry($attempt, $error): bool
    {
        return $attempt < 3 && $error instanceof \GuzzleHttp\Exception\ConnectException;
    }
    protected function defaultDescription(): ?string
    {
        return Craft::t('my-plugin', 'Syncing products');
    }
}
```

### Send notification emails

Push from controller, send in job. Never send email synchronously in web requests. Pass IDs as properties since there is no user session in queue context:

```php
class SendOrderConfirmation extends BaseJob
{
    public int $orderId;
    public string $recipientEmail;

    public function execute($queue): void
    {
        $order = Entry::find()->section('orders')->id($this->orderId)
            ->site('*')->status(null)->one();
        if (!$order) { return; }
        Craft::$app->getMailer()
            ->composeFromKey('order-confirmation', ['order' => $order])
            ->setTo($this->recipientEmail)->send();
    }
    protected function defaultDescription(): ?string
    {
        return Craft::t('my-plugin', 'Sending order confirmation');
    }
}
```

### Generate exports

Write to temp file, email as attachment:

```php
class GenerateCsvExport extends BaseJob
{
    public int $userId;
    public string $section;

    public function execute($queue): void
    {
        $entries = Entry::find()->section($this->section)->site('*')->status(null)->all();
        $tempPath = Craft::$app->getPath()->getTempPath() . '/export-' . time() . '.csv';
        $fp = fopen($tempPath, 'w');
        fputcsv($fp, ['Title', 'Status']);
        foreach ($entries as $i => $entry) {
            $this->setProgress($queue, ($i + 1) / count($entries));
            fputcsv($fp, [$entry->title, $entry->status]);
        }
        fclose($fp);

        $user = Craft::$app->getUsers()->getUserById($this->userId);
        if ($user) {
            Craft::$app->getMailer()->compose()
                ->setTo($user->email)->setSubject('Export ready')->attach($tempPath)->send();
        }
        unlink($tempPath);
    }
    protected function defaultDescription(): ?string
    {
        return Craft::t('my-plugin', 'Generating CSV export');
    }
}
```

## Built-in Queue Jobs

Craft uses these internally. Push them directly instead of writing custom equivalents:

| Job Class | When Craft Uses It |
|-----------|--------------------|
| `ResaveElements` | After bulk operations, field layout changes |
| `UpdateSearchIndex` | After element saves |
| `GenerateImageTransform` | When `generateTransformsBeforePageLoad` is false |
| `ApplyNewPropagationMethod` | After changing section propagation method |
| `PruneRevisions` | When `maxRevisions` config is lowered |
| `FindAndReplace` | CP Utilities > Find and Replace |
| `LocalizeRelations` | After changing a relational field to per-site |
| `PropagateElements` | After enabling a section for additional sites |

All live in the `craft\queue\jobs` namespace.

## Queue Health Monitoring

```bash
ddev craft queue/info       # Shows waiting, delayed, reserved, done, failed counts
ddev craft queue/release    # Release stuck/reserved jobs (worker crashed mid-job)
```

A job is "stuck" when reserved for longer than its TTR but not released -- typically means the worker process crashed. Signs: `reserved` count stays non-zero, CP shows spinning with no progress.

The CP queue manager (gear icon, bottom-left) shows pending/failed counts, a progress bar for running jobs, and a retry button for failures.

For DDEV development: `ddev craft queue/listen --verbose` to watch jobs in real-time, or `ddev craft queue/run --verbose` to process all pending and exit.
