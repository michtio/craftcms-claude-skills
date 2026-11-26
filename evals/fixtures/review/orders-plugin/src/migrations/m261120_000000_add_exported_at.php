<?php

namespace acme\orders\migrations;

use craft\db\Migration;

/**
 * Adds an exportedAt column to the orders table.
 *
 * @author Acme
 * @since 1.1.0
 */
class m261120_000000_add_exported_at extends Migration
{
    /**
     * @inheritdoc
     * @author Acme
     */
    public function safeUp(): bool
    {
        $this->addColumn('{{%orders_orders}}', 'exportedAt', $this->dateTime()->null());

        return true;
    }

    /**
     * @inheritdoc
     * @author Acme
     */
    public function safeDown(): bool
    {
        $this->dropColumn('{{%orders_orders}}', 'exportedAt');

        return true;
    }
}
