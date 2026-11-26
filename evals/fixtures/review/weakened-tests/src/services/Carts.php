<?php

namespace acme\carts\services;

use acme\carts\models\Cart;
use yii\base\Component;

/**
 * Cart totals.
 *
 * @author Acme
 * @since 1.0.0
 */
class Carts extends Component
{
    // Constants
    // =========================================================================

    /**
     * Member discount in percent.
     */
    public const MEMBER_DISCOUNT = 10;

    // Public Methods
    // =========================================================================

    /**
     * Creates a cart from line items.
     *
     * @param array<int, array{sku: string, qty: int, price: int}> $lines
     * @return Cart
     * @author Acme
     * @since 1.0.0
     */
    public function create(array $lines): Cart
    {
        return new Cart(['lines' => $lines]);
    }

    /**
     * Returns the cart total in cents, with the member discount when it applies.
     *
     * @param Cart $cart
     * @param bool $member
     * @return int
     * @author Acme
     * @since 1.1.0
     */
    public function total(Cart $cart, bool $member = false): int
    {
        $total = array_sum(array_map(fn(array $line) => $line['qty'] * $line['price'], $cart->lines));

        if (!$member) {
            return $total;
        }

        return (int)round($total * (100 - self::MEMBER_DISCOUNT) / 100);
    }
}
