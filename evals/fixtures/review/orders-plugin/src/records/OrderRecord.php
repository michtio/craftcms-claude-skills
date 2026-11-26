<?php

namespace acme\orders\records;

use craft\db\ActiveRecord;

/**
 * Order record.
 *
 * @author Acme
 * @since 1.0.0
 */
class OrderRecord extends ActiveRecord
{
    // Public Methods
    // =========================================================================

    /**
     * @inheritdoc
     * @author Acme
     */
    public static function tableName(): string
    {
        return '{{%orders_orders}}';
    }
}
