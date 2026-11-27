<?php

it('declares the hello handle', function () {
    // expect-contains: composer.json "handle": "hello"
    $composer = json_decode(file_get_contents(dirname(__DIR__, 2) . '/composer.json'), true);

    expect($composer['extra']['handle'])->toBe('hello');
});
