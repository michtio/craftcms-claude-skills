<?php

namespace acme\orders\services;

use acme\orders\records\OrderRecord;
use craft\elements\Entry;
use craft\elements\User;
use yii\base\Component;

/**
 * Order queries.
 *
 * @author Acme
 * @since 1.0.0
 */
class OrdersService extends Component
{
    // Public Methods
    // =========================================================================

    /**
     * Returns one CSV row per order of a customer.
     *
     * @param int $customerId
     * @return array<int, array<string, mixed>>
     * @author Acme
     */
    public function exportRows(int $customerId): array
    {
        $rows = [];
        foreach (OrderRecord::find()->where(['customerId' => $customerId])->all() as $order) {
            $customer = User::find()->id($order->customerId)->one();
            $product = Entry::find()->id($order->productId)->one();
            $rows[] = [
                'number' => $order->number,
                'email' => $customer?->email,
                'product' => $product?->title,
                'total' => $order->total,
            ];
        }

        return $rows;
    }
}
