<?php

namespace acme\hello;

use craft\base\Plugin as BasePlugin;

/**
 * Hello plugin.
 *
 * @author Acme
 * @since 1.0.0
 */
class Plugin extends BasePlugin
{
    // Properties
    // =========================================================================

    /**
     * @var string
     */
    public string $schemaVersion = '1.0.0';
}
