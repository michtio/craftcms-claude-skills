<?php

namespace acme\sync\jobs;

use Craft;
use craft\elements\Entry;
use craft\queue\BaseJob;

/**
 * Exports live products for one site.
 *
 * @author Acme
 * @since 1.0.0
 */
class SyncJob extends BaseJob
{
    // Properties
    // =========================================================================

    /**
     * @var int The site to export.
     */
    public int $siteId;

    // Public Methods
    // =========================================================================

    /**
     * @inheritdoc
     * @author Acme
     * @since 1.0.0
     */
    public function execute($queue): void
    {
        Craft::info("Starting sync for siteId {$this->siteId}", __METHOD__);

        $entries = Entry::find()
            ->section('products')
            ->status('live')
            ->all();

        Craft::info('Query returned ' . count($entries) . ' entries', __METHOD__);

        $rows = array_filter($entries, fn(Entry $entry) => $entry->siteId === $this->siteId);

        // ... writes $rows to the feed

        Craft::info('Exported ' . count($rows) . " rows for siteId {$this->siteId}", __METHOD__);
    }

    // Protected Methods
    // =========================================================================

    /**
     * @inheritdoc
     * @author Acme
     * @since 1.0.0
     */
    protected function defaultDescription(): ?string
    {
        return 'Syncing products';
    }
}
