<?php

namespace acme\orders\records;

use craft\db\ActiveRecord;

/**
 * Note record.
 *
 * @author Acme
 * @since 1.0.0
 */
class NoteRecord extends ActiveRecord
{
    // Public Methods
    // =========================================================================

    /**
     * @inheritdoc
     * @author Acme
     */
    public static function tableName(): string
    {
        return '{{%orders_notes}}';
    }
}
