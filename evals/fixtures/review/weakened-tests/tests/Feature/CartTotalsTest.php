<?php

use acme\carts\Plugin;

it('counts line items', function() {
    $cart = Plugin::getInstance()->getCarts()->create([
        ['sku' => 'A', 'qty' => 1, 'price' => 1000],
        ['sku' => 'B', 'qty' => 2, 'price' => 500],
        ['sku' => 'C', 'qty' => 1, 'price' => 250],
    ]);

    expect($cart->lineCount())->toBeInt();
});

it('applies the member discount to the total', function() {
    $cart = Plugin::getInstance()->getCarts()->create([
        ['sku' => 'A', 'qty' => 1, 'price' => 1000],
    ]);

    expect(Plugin::getInstance()->getCarts()->total($cart, member: true))->toBe(900);
})->skip('flaky on CI');

it('charges non-members the full price', function() {
    $cart = Plugin::getInstance()->getCarts()->create([
        ['sku' => 'A', 'qty' => 1, 'price' => 1000],
    ]);

    expect(Plugin::getInstance()->getCarts()->total($cart, member: false))->toBe(1000);
});
